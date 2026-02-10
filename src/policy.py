"""CleanApp Agent001 — Policy Engine (rate limits, relevance gating, value filter)."""

from __future__ import annotations

import logging
from datetime import date

from .memory import Memory

logger = logging.getLogger(__name__)

# Topics that indicate relevance per mode
MODE_TOPICS = {
    "intake": [
        "crowdsourcing", "sensors", "data collection", "incentive mechanisms",
        "human reporting", "bot reporting", "scraping", "data generation",
        "ground truth", "sensor networks", "citizen science", "data labeling",
    ],
    "analysis": [
        "LLM pipeline", "deduplication", "trust scoring", "data quality",
        "information markets", "evaluation", "human in the loop", "HITL",
        "data verification", "clustering", "signal processing", "NLP pipeline",
    ],
    "distribution": [
        "GovTech", "enterprise workflow", "alerting", "API products",
        "routing", "decision makers", "dashboards", "notifications",
        "stakeholder engagement", "government", "civic tech", "alert systems",
    ],
}

# Topics to avoid
DO_NOT_ENGAGE = [
    "ragebait", "flame war", "personal attack", "politics", "partisan",
    "token launch", "crypto pump", "NFT drop", "meme coin",
    "existential risk debate", "AI doom", "consciousness debate",
]


class Policy:
    """Engagement policy engine."""

    def __init__(
        self,
        memory: Memory,
        max_posts_per_day: int = 3,
        max_comments_per_day: int = 5,
        relevance_threshold: float = 0.6,
    ):
        self.memory = memory
        self.max_posts_per_day = max_posts_per_day
        self.max_comments_per_day = max_comments_per_day
        self.relevance_threshold = relevance_threshold

    def can_post(self) -> tuple[bool, str]:
        """Check if we can create a new post today."""
        posts, _ = self.memory.get_daily_counts()
        if posts >= self.max_posts_per_day:
            return False, f"Daily post limit reached ({posts}/{self.max_posts_per_day})"
        return True, "OK"

    def can_comment(self) -> tuple[bool, str]:
        """Check if we can comment today."""
        _, comments = self.memory.get_daily_counts()
        if comments >= self.max_comments_per_day:
            return False, f"Daily comment limit reached ({comments}/{self.max_comments_per_day})"
        return True, "OK"

    def classify_mode(self, text: str) -> str | None:
        """Classify text into a mode (intake/analysis/distribution) or None."""
        text_lower = text.lower()
        scores = {}
        for mode, topics in MODE_TOPICS.items():
            score = sum(1 for t in topics if t.lower() in text_lower)
            if score > 0:
                scores[mode] = score

        if not scores:
            return None
        return max(scores, key=scores.get)

    def should_skip(self, text: str) -> tuple[bool, str]:
        """Check if a thread should be skipped (do-not-engage list)."""
        text_lower = text.lower()
        for bad_topic in DO_NOT_ENGAGE:
            if bad_topic.lower() in text_lower:
                return True, f"Matches do-not-engage topic: {bad_topic}"
        return False, "OK"

    def already_engaged(self, post_id: str) -> bool:
        """Check if we already engaged with this thread."""
        return self.memory.already_engaged(post_id)

    def check_repetition(self, content: str) -> bool:
        """Check if this content was already used."""
        return self.memory.content_already_used(content)

    def evaluate_thread(self, title: str, content: str, post_id: str) -> dict:
        """
        Full policy evaluation for a thread.

        Returns dict with:
          - engage: bool
          - reason: str
          - mode: str | None
        """
        combined = f"{title} {content}"

        # Check do-not-engage
        skip, reason = self.should_skip(combined)
        if skip:
            return {"engage": False, "reason": reason, "mode": None}

        # Check already engaged
        if self.already_engaged(post_id):
            return {"engage": False, "reason": "Already engaged with this thread", "mode": None}

        # Classify mode
        mode = self.classify_mode(combined)
        if mode is None:
            return {"engage": False, "reason": "Not relevant to any CleanApp mode", "mode": None}

        # Check rate limits
        can_comment, reason = self.can_comment()
        if not can_comment:
            return {"engage": False, "reason": reason, "mode": mode}

        return {"engage": True, "reason": "Passes all gates", "mode": mode}
