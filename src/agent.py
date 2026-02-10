"""CleanApp Agent001 — Main Agent Loop."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import google.generativeai as genai

from .config import Config
from .memory import Memory
from .moltbook_client import MoltbookClient, MoltbookPost
from .outreach import OutreachEngine
from .policy import Policy

logger = logging.getLogger(__name__)

# Search queries per mode (expanded for broader discovery)
SEARCH_QUERIES = {
    "intake": [
        "crowdsourcing data collection from humans and agents",
        "incentive mechanisms for reporting and data generation",
        "sensor networks and ground truth verification",
        "agents building tools for the physical world",
        "photo reports and image classification pipelines",
        "bug reporting and issue tracking for real-world problems",
    ],
    "analysis": [
        "LLM pipeline for data deduplication and quality",
        "trust scoring and data verification systems",
        "clustering signals from multiple sources",
        "brand extraction from unstructured text",
        "severity scoring and report prioritization",
    ],
    "distribution": [
        "routing alerts to decision makers and stakeholders",
        "GovTech enterprise workflow API integration",
        "building dashboards and notification systems for actionable intelligence",
        "monitoring and alerting infrastructure for agents",
        "civic tech agents and municipal services",
    ],
}

# Topics for proactive original posts
PROACTIVE_TOPICS = [
    {
        "type": "todayilearned",
        "submolt": "todayilearned",
        "topic": "A surprising operational insight from running intake pipelines across heterogeneous data sources (social media, mobile app, email, web scrapers)",
    },
    {
        "type": "todayilearned",
        "submolt": "todayilearned",
        "topic": "A counter-intuitive finding about deduplication — why running 30 reports about the same pothole is actually more valuable than 30 unique reports",
    },
    {
        "type": "agents_showcase",
        "submolt": "agents",
        "topic": "How we built a multi-model fallback pipeline (Gemini primary, OpenAI fallback) that makes enrichment additive and re-runnable",
    },
    {
        "type": "agents_showcase",
        "submolt": "agents",
        "topic": "Architecture pattern: how to route a single issue cluster to brands, regulators, insurers, and journalists simultaneously",
    },
    {
        "type": "api_collaboration",
        "submolt": "agents",
        "topic": "How other agents can submit real-world issue reports via CleanApp's API — detect the signal, we handle routing and accountability",
    },
    {
        "type": "api_collaboration",
        "submolt": "general",
        "topic": "The economics of sensor data coordination — why agents covering different geographic areas create superlinear value when their data is clustered",
    },
    {
        "type": "skill_announcement",
        "submolt": "agents",
        "topic": "Announcing CleanApp's OpenClaw skill — any agent can now submit real-world issue reports (trash, hazards, infrastructure) into our routing pipeline with a single API call. Reports get AI analysis, geographic clustering, and routing to responsible parties. The skill is installable from our repo.",
    },
]


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
            post_cooldown_minutes=config.post_cooldown_minutes,
            max_outreach_per_day=config.max_outreach_per_day,
            outreach_cooldown_days=config.outreach_cooldown_days,
            min_post_length=config.min_post_length,
            max_post_length=config.max_post_length,
            min_comment_length=config.min_comment_length,
            max_comment_length=config.max_comment_length,
        )
        self.outreach = OutreachEngine(
            client=self.client,
            memory=self.memory,
            policy=self.policy,
            config=config,
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

    # --- Health check ---

    def preflight(self) -> bool:
        """Run health check before agent cycle. Returns True if OK to proceed."""
        health = self.client.check_health()
        if not health.ok:
            logger.error("❌ Pre-flight failed: %s", health.message)
            if health.suspended:
                logger.error("Account suspended. Retry after ~%.1f hours.", health.retry_after_hours)
            return False
        logger.info("✅ Pre-flight OK: %s", health.message)
        return True

    # --- Relevance scoring ---

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

    # --- Response generation ---

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

        # Validate comment length
        if response:
            valid, reason = self.policy.validate_comment_content(response)
            if not valid:
                logger.warning("Response failed validation: %s", reason)
                return ""

        # Check content dedup
        if response and self.memory.is_duplicate_content("", response):
            logger.warning("Response is duplicate content, skipping")
            return ""

        return response

    # --- Proactive posting ---

    def create_value_post(self, topic_index: int | None = None) -> dict[str, Any]:
        """Create an original value-first post.

        If topic_index is provided, uses that specific topic.
        Otherwise picks the first unused topic.
        """
        # Check daily post limit
        can_post, reason = self.policy.can_post()
        if not can_post:
            return {"success": False, "reason": reason}

        # Check cooldown
        can_now, reason = self.policy.can_post_now()
        if not can_now:
            return {"success": False, "reason": reason}

        # Select topic
        if topic_index is not None:
            if 0 <= topic_index < len(PROACTIVE_TOPICS):
                topic = PROACTIVE_TOPICS[topic_index]
            else:
                return {"success": False, "reason": f"Invalid topic index: {topic_index}"}
        else:
            # Pick first unused topic
            topic = None
            for t in PROACTIVE_TOPICS:
                # Check if we already posted to this submolt today
                can_submolt, _ = self.policy.can_post_to_submolt(t["submolt"])
                if can_submolt:
                    topic = t
                    break
            if topic is None:
                return {"success": False, "reason": "No unused topics available"}

        # Check submolt limit
        can_submolt, reason = self.policy.can_post_to_submolt(topic["submolt"])
        if not can_submolt:
            return {"success": False, "reason": reason}

        # Generate post via LLM
        prompt_template = self.prompts.get("original_post", "")
        system_prompt = self.prompts.get("system", "")
        if not prompt_template:
            return {"success": False, "reason": "Missing original_post prompt template"}

        prompt = f"{system_prompt}\n\n---\n\n{prompt_template.format(post_type=topic['type'], submolt=topic['submolt'])}\n\nTopic to write about: {topic['topic']}"

        response = self._call_llm(prompt)
        if not response:
            return {"success": False, "reason": "LLM failed to generate post"}

        # Parse TITLE: and CONTENT: from response
        title = ""
        content = ""
        lines = response.split("\n")
        in_content = False
        content_lines = []

        for line in lines:
            if line.strip().startswith("TITLE:"):
                title = line.split("TITLE:", 1)[1].strip()
            elif line.strip().startswith("CONTENT:"):
                content_start = line.split("CONTENT:", 1)[1].strip()
                if content_start:
                    content_lines.append(content_start)
                in_content = True
            elif in_content:
                content_lines.append(line)

        content = "\n".join(content_lines).strip()

        if not title or not content:
            # Fallback: use full response as content
            if not title:
                title = response.split("\n")[0][:100]
            if not content:
                content = response

        # Validate
        valid, reason = self.policy.validate_post_content(title, content)
        if not valid:
            return {"success": False, "reason": reason}

        # Dedup check
        if self.policy.is_duplicate(title, content):
            return {"success": False, "reason": "Duplicate content detected"}

        # Post
        result = self.client.create_post(
            submolt=topic["submolt"],
            title=title,
            content=content,
        )

        # Record
        post_id = result.get("id", result.get("post_id", "proactive"))
        self.memory.record_content_hash(title, content, post_id)
        self.memory.record_engagement(
            post_id=post_id, action="post", mode=topic["type"],
            content=content, thread_title=title,
            thread_submolt=topic["submolt"],
        )

        logger.info("✅ Created value post: '%s' in s/%s", title[:60], topic["submolt"])
        return {"success": True, "title": title, "submolt": topic["submolt"], "result": result}

    # --- Post a custom introduction ---

    def post_introduction(self, title: str, content: str) -> dict[str, Any]:
        """Post a one-time introduction to m/introductions with full compliance checks."""
        submolt = "introductions"

        # All pre-flight checks
        checks = [
            self.policy.can_post(),
            self.policy.can_post_now(),
            self.policy.can_post_to_submolt(submolt),
            self.policy.validate_post_content(title, content),
        ]
        for ok, reason in checks:
            if not ok:
                return {"success": False, "reason": reason}

        if self.policy.is_duplicate(title, content):
            return {"success": False, "reason": "Duplicate content — already posted this"}

        result = self.client.create_post(submolt=submolt, title=title, content=content)

        post_id = result.get("id", result.get("post_id", "intro"))
        self.memory.record_content_hash(title, content, post_id)
        self.memory.record_engagement(
            post_id=post_id, action="post", mode="introduction",
            content=content, thread_title=title, thread_submolt=submolt,
        )

        logger.info("✅ Posted introduction: '%s'", title[:60])
        return {"success": True, "title": title, "result": result}

    # --- Search & engage (core loop) ---

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
                            self.memory.record_content_hash("", response_text)
                            self.memory.record_opportunity(
                                mode=mode, post_id=post.id, title=post.title,
                                submolt=post.submolt, author=post.author,
                                relevance_score=relevance, action_taken="engaged",
                            )

                            # Respect API rate limits
                            time.sleep(2)
                        else:
                            opportunity["action"] = "skipped"
                            opportunity["skip_reason"] = "Failed to generate response"

                opportunities.append(opportunity)

        return opportunities

    # --- Full cycle ---

    def run_cycle(self) -> dict[str, Any]:
        """Run one full engagement cycle: health check → engage → outreach → post."""
        logger.info("=" * 60)
        logger.info("Starting engagement cycle (dry_run=%s)", self.config.dry_run)
        logger.info("=" * 60)

        # Pre-flight
        if not self.preflight():
            return {"cycle_complete": False, "reason": "Pre-flight failed (suspended or auth error)"}

        all_opportunities: dict[str, list] = {}

        # Phase 1: Search & engage across modes
        for mode, queries in SEARCH_QUERIES.items():
            mode_label = {
                "intake": "Intake (Trashformer)",
                "analysis": "Analysis (Moltfold)",
                "distribution": "Distribution (Antenna)",
            }[mode]
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

        # Phase 2: Proactive value post (if we have post budget left)
        can_post, _ = self.policy.can_post()
        proactive_result = None
        if can_post:
            logger.info("-" * 40)
            logger.info("Proactive posting phase")
            logger.info("-" * 40)
            proactive_result = self.create_value_post()
            if proactive_result.get("success"):
                logger.info("Proactive post created: %s", proactive_result.get("title", "")[:60])
            else:
                logger.info("Proactive post skipped: %s", proactive_result.get("reason", ""))

        # Phase 3: Outreach cycle
        logger.info("-" * 40)
        logger.info("Outreach phase")
        logger.info("-" * 40)
        outreach_actions = self.outreach.run_outreach_cycle(self._call_llm)
        logger.info("Outreach actions: %d", len(outreach_actions))

        # Final summary
        posts_today, comments_today = self.memory.get_daily_counts()
        summary = {
            "cycle_complete": True,
            "dry_run": self.config.dry_run,
            "daily_posts": posts_today,
            "daily_comments": comments_today,
            "opportunities": all_opportunities,
            "proactive_post": proactive_result,
            "outreach_actions": len(outreach_actions),
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
        logger.info("Cycle complete. Posts today: %d/%d, Comments today: %d/%d, Outreach: %d",
                     posts_today, self.config.max_posts_per_day,
                     comments_today, self.config.max_comments_per_day,
                     len(outreach_actions))
        logger.info("=" * 60)

        return summary

    def close(self):
        """Clean up resources."""
        self.client.close()
        self.memory.close()
