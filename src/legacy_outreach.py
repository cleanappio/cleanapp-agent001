"""CleanApp Agent001 — API Adoption Outreach Module."""

from __future__ import annotations

import logging
from typing import Any

from .config import Config
from .memory import Memory
from .moltbook_client import MoltbookClient, MoltbookPost
from .policy import Policy

logger = logging.getLogger(__name__)

# Search queries to discover agents who might benefit from CleanApp integration
OUTREACH_QUERIES = [
    "building monitoring tools for the physical world",
    "agent reporting infrastructure and data collection",
    "sensors and IoT data from agents",
    "agents detecting real-world issues and problems",
    "crowdsourced data collection by AI agents",
    "infrastructure monitoring and alerting agent",
    "photo report analysis and routing",
    "civic tech agents and municipal services",
]

# Keywords that suggest an agent has data we could route
INTEGRATION_SIGNALS = [
    "monitoring", "reporting", "sensor", "detect", "photograph",
    "physical world", "infrastructure", "hazard", "maintenance",
    "public space", "urban", "municipal", "waste", "cleanup",
    "accessibility", "broken", "damaged", "complaint", "issue tracker",
]


class OutreachEngine:
    """Find and engage with agents who could benefit from CleanApp API integration."""

    def __init__(
        self,
        client: MoltbookClient,
        memory: Memory,
        policy: Policy,
        config: Config,
    ):
        self.client = client
        self.memory = memory
        self.policy = policy
        self.config = config

    def discover_opportunities(self) -> list[MoltbookPost]:
        """Search for threads where agents discuss work that could integrate with CleanApp."""
        all_posts: list[MoltbookPost] = []
        seen_ids: set[str] = set()

        for query in OUTREACH_QUERIES:
            logger.debug("Outreach search: %s", query)
            posts = self.client.search(query, type_filter="posts", limit=5)
            for post in posts:
                if post.id not in seen_ids:
                    seen_ids.add(post.id)
                    all_posts.append(post)

        logger.info("Discovered %d unique posts for outreach", len(all_posts))
        return all_posts

    def score_integration_fit(self, post: MoltbookPost) -> float:
        """Score how well a post's topic fits with CleanApp API integration (0-1)."""
        combined = f"{post.title} {post.content}".lower()
        hits = sum(1 for signal in INTEGRATION_SIGNALS if signal in combined)
        # Normalize: 3+ hits = excellent fit
        return min(hits / 3.0, 1.0)

    def filter_outreach_candidates(self, posts: list[MoltbookPost]) -> list[dict[str, Any]]:
        """Filter posts to actionable outreach candidates."""
        candidates = []

        for post in posts:
            # Skip our own posts
            if post.author.lower() in ("cleanapp", "cleanapp_agent", "cleanappbot"):
                continue

            # Already engaged?
            if self.memory.already_engaged(post.id):
                continue

            # Already approached this agent?
            can_approach, reason = self.policy.can_approach_agent(post.author)
            if not can_approach:
                logger.debug("Skipping %s: %s", post.author, reason)
                continue

            # Score integration fit
            fit_score = self.score_integration_fit(post)
            if fit_score < 0.3:
                continue

            candidates.append({
                "post": post,
                "fit_score": fit_score,
                "author": post.author,
            })

        # Sort by fit score (best opportunities first)
        candidates.sort(key=lambda c: c["fit_score"], reverse=True)
        return candidates

    def run_outreach_cycle(self, generate_response_fn) -> list[dict[str, Any]]:
        """
        Run one outreach cycle.

        Args:
            generate_response_fn: Function(prompt) -> str that generates responses (e.g., via Gemini).

        Returns:
            List of outreach actions taken.
        """
        # Check global outreach limit
        can_outreach, reason = self.policy.can_outreach()
        if not can_outreach:
            logger.info("Outreach limit reached: %s", reason)
            return []

        # Discover and filter
        posts = self.discover_opportunities()
        candidates = self.filter_outreach_candidates(posts)

        if not candidates:
            logger.info("No outreach candidates found this cycle")
            return []

        actions = []
        remaining_slots = self.config.max_outreach_per_day - self.memory.get_outreach_count_today()

        for candidate in candidates[:remaining_slots]:
            post = candidate["post"]
            fit_score = candidate["fit_score"]

            logger.info(
                "Outreach candidate: %s by %s (fit: %.2f)",
                post.title[:60], post.author, fit_score,
            )

            # Load api_outreach prompt
            try:
                prompt_path = "src/prompts/api_outreach.txt"
                with open(prompt_path) as f:
                    prompt_template = f.read()

                prompt = prompt_template.format(
                    title=post.title,
                    content=post.content[:500],
                    submolt=post.submolt,
                    author=post.author,
                )

                response = generate_response_fn(prompt)
                if not response:
                    continue

                # Validate content length
                valid, reason = self.policy.validate_comment_content(response)
                if not valid:
                    logger.warning("Outreach response failed validation: %s", reason)
                    continue

                # Check dedup
                if self.memory.is_duplicate_content("", response):
                    logger.warning("Outreach response is duplicate content — skipping")
                    continue

                # Post comment (or dry-run)
                result = self.client.create_comment(post.id, response)

                # Record
                self.memory.record_outreach(
                    agent_name=post.author,
                    post_id=post.id,
                    context=post.title[:200],
                    approach_type="comment",
                    our_message=response,
                )
                self.memory.record_content_hash("", response)

                actions.append({
                    "agent": post.author,
                    "post_title": post.title,
                    "fit_score": fit_score,
                    "response": response[:100],
                    "result": result,
                })

                logger.info("Outreach sent to %s", post.author)

            except Exception as e:
                logger.error("Outreach failed for %s: %s", post.author, e)
                continue

        return actions
