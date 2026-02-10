"""CleanApp Agent001 — Main Agent Loop."""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any

import google.generativeai as genai

from .config import Config
from .memory import Memory
from .moltbook_client import MoltbookClient, MoltbookPost
from .policy import Policy

logger = logging.getLogger(__name__)

# Search queries per mode
SEARCH_QUERIES = {
    "intake": [
        "crowdsourcing data collection from humans and agents",
        "incentive mechanisms for reporting and data generation",
        "sensor networks and ground truth verification",
    ],
    "analysis": [
        "LLM pipeline for data deduplication and quality",
        "trust scoring and data verification systems",
        "clustering signals from multiple sources",
    ],
    "distribution": [
        "routing alerts to decision makers and stakeholders",
        "GovTech enterprise workflow API integration",
        "building dashboards and notification systems for actionable intelligence",
    ],
}


class Agent:
    """CleanApp Moltbook agent."""

    def __init__(self, config: Config):
        self.config = config
        self.client = MoltbookClient(
            api_key=config.moltbook_api_key,
            dry_run=config.dry_run,
        )
        self.memory = Memory(config.data_dir / "memory.db")
        self.policy = Policy(
            memory=self.memory,
            max_posts_per_day=config.max_posts_per_day,
            max_comments_per_day=config.max_comments_per_day,
            relevance_threshold=config.relevance_threshold,
        )

        # Initialize Gemini
        genai.configure(api_key=config.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

        # Load prompts
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> dict[str, str]:
        """Load prompt templates from src/prompts/."""
        prompts_dir = Path(__file__).parent / "prompts"
        prompts = {}
        for f in prompts_dir.glob("*.txt"):
            prompts[f.stem] = f.read_text()
        return prompts

    def _call_llm(self, prompt: str) -> str:
        """Call Gemini and return response text."""
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return ""

    def _score_relevance(self, post: MoltbookPost) -> dict[str, Any]:
        """Score a post for relevance using LLM."""
        prompt_template = self.prompts.get("relevance_check", "")
        if not prompt_template:
            # Fallback to policy-based scoring
            mode = self.policy.classify_mode(f"{post.title} {post.content}")
            return {
                "relevance": 0.7 if mode else 0.0,
                "mode": mode or "none",
                "can_add_value": mode is not None,
                "reason": "Policy-based classification",
            }

        prompt = prompt_template.format(
            title=post.title,
            content=post.content[:500],
            submolt=post.submolt,
        )

        response = self._call_llm(prompt)
        if not response:
            return {"relevance": 0.0, "mode": "none", "can_add_value": False, "reason": "LLM failed"}

        # Parse structured response
        result = {"relevance": 0.0, "mode": "none", "can_add_value": False, "reason": ""}
        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("RELEVANCE:"):
                try:
                    result["relevance"] = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("MODE:"):
                result["mode"] = line.split(":", 1)[1].strip().lower()
            elif line.startswith("CAN_ADD_VALUE:"):
                result["can_add_value"] = "yes" in line.lower()
            elif line.startswith("REASON:"):
                result["reason"] = line.split(":", 1)[1].strip()

        return result

    def _generate_response(self, post: MoltbookPost, mode: str) -> str:
        """Generate a response for a post using the mode-specific prompt."""
        prompt_template = self.prompts.get(mode, "")
        system_prompt = self.prompts.get("system", "")

        if not prompt_template:
            logger.warning("No prompt template for mode: %s", mode)
            return ""

        prompt = f"{system_prompt}\n\n---\n\n{prompt_template.format(title=post.title, content=post.content[:800], submolt=post.submolt, author=post.author)}"

        response = self._call_llm(prompt)

        # Check for repetition
        if response and self.policy.check_repetition(response):
            logger.info("Response would be repetitive, skipping")
            return ""

        return response

    def _search_and_engage(self, mode: str, queries: list[str]) -> list[dict[str, Any]]:
        """Search for relevant threads and engage where valuable."""
        opportunities = []

        for query in queries:
            logger.info("Searching [%s]: %s", mode, query)
            posts = self.client.search(query, type_filter="posts", limit=10)

            for post in posts:
                # Skip if already engaged
                if self.policy.already_engaged(post.id):
                    logger.debug("Already engaged with %s, skipping", post.id)
                    continue

                # Check do-not-engage
                skip, reason = self.policy.should_skip(f"{post.title} {post.content}")
                if skip:
                    logger.debug("Skipping %s: %s", post.id, reason)
                    self.memory.record_opportunity(
                        mode=mode, post_id=post.id, title=post.title,
                        submolt=post.submolt, author=post.author,
                        relevance_score=0.0, action_taken="skipped", reason=reason,
                    )
                    continue

                # Score relevance
                score = self._score_relevance(post)
                relevance = score["relevance"]

                opportunity = {
                    "mode": mode,
                    "post_id": post.id,
                    "title": post.title,
                    "submolt": post.submolt,
                    "author": post.author,
                    "relevance": relevance,
                    "can_add_value": score["can_add_value"],
                    "reason": score["reason"],
                }

                if relevance < self.config.relevance_threshold:
                    opportunity["action"] = "skipped"
                    opportunity["skip_reason"] = f"Below threshold ({relevance:.2f} < {self.config.relevance_threshold})"
                    self.memory.record_opportunity(
                        mode=mode, post_id=post.id, title=post.title,
                        submolt=post.submolt, author=post.author,
                        relevance_score=relevance, action_taken="skipped",
                        reason=opportunity["skip_reason"],
                    )
                elif not score["can_add_value"]:
                    opportunity["action"] = "skipped"
                    opportunity["skip_reason"] = "Cannot add concrete value"
                    self.memory.record_opportunity(
                        mode=mode, post_id=post.id, title=post.title,
                        submolt=post.submolt, author=post.author,
                        relevance_score=relevance, action_taken="skipped",
                        reason="Cannot add value",
                    )
                else:
                    # Check rate limit
                    can_comment, rate_reason = self.policy.can_comment()
                    if not can_comment:
                        opportunity["action"] = "queued"
                        opportunity["skip_reason"] = rate_reason
                        self.memory.record_opportunity(
                            mode=mode, post_id=post.id, title=post.title,
                            submolt=post.submolt, author=post.author,
                            relevance_score=relevance, action_taken="queued",
                            reason=rate_reason,
                        )
                    else:
                        # Generate and post response
                        response_text = self._generate_response(post, mode)
                        if response_text:
                            result = self.client.create_comment(post.id, response_text)
                            opportunity["action"] = "engaged"
                            opportunity["response"] = response_text
                            opportunity["api_result"] = result

                            self.memory.record_engagement(
                                post_id=post.id, action="comment", mode=mode,
                                content=response_text, thread_title=post.title,
                                thread_submolt=post.submolt, relevance_score=relevance,
                            )
                            self.memory.record_opportunity(
                                mode=mode, post_id=post.id, title=post.title,
                                submolt=post.submolt, author=post.author,
                                relevance_score=relevance, action_taken="engaged",
                            )

                            # Respect comment cooldown
                            time.sleep(2)
                        else:
                            opportunity["action"] = "skipped"
                            opportunity["skip_reason"] = "Failed to generate response"

                opportunities.append(opportunity)

        return opportunities

    def run_cycle(self) -> dict[str, Any]:
        """Run one full engagement cycle across all modes."""
        logger.info("=" * 60)
        logger.info("Starting engagement cycle (dry_run=%s)", self.config.dry_run)
        logger.info("=" * 60)

        all_opportunities: dict[str, list] = {}

        for mode, queries in SEARCH_QUERIES.items():
            mode_label = {"intake": "Intake (Trashformer)", "analysis": "Analysis (Moltfold)", "distribution": "Distribution (Antenna)"}[mode]
            logger.info("-" * 40)
            logger.info("Mode: %s", mode_label)
            logger.info("-" * 40)

            opportunities = self._search_and_engage(mode, queries)
            all_opportunities[mode] = opportunities

            # Log summary for this mode
            engaged = sum(1 for o in opportunities if o.get("action") == "engaged")
            skipped = sum(1 for o in opportunities if o.get("action") == "skipped")
            queued = sum(1 for o in opportunities if o.get("action") == "queued")
            logger.info(
                "Mode %s summary: %d engaged, %d skipped, %d queued (of %d found)",
                mode, engaged, skipped, queued, len(opportunities),
            )

        # Final summary
        posts_today, comments_today = self.memory.get_daily_counts()
        summary = {
            "cycle_complete": True,
            "dry_run": self.config.dry_run,
            "daily_posts": posts_today,
            "daily_comments": comments_today,
            "opportunities": all_opportunities,
            "totals": {
                mode: {
                    "found": len(opps),
                    "engaged": sum(1 for o in opps if o.get("action") == "engaged"),
                    "skipped": sum(1 for o in opps if o.get("action") == "skipped"),
                    "queued": sum(1 for o in opps if o.get("action") == "queued"),
                }
                for mode, opps in all_opportunities.items()
            },
        }

        logger.info("=" * 60)
        logger.info("Cycle complete. Posts today: %d/%d, Comments today: %d/%d",
                     posts_today, self.config.max_posts_per_day,
                     comments_today, self.config.max_comments_per_day)
        logger.info("=" * 60)

        return summary

    def close(self):
        """Clean up resources."""
        self.client.close()
        self.memory.close()
