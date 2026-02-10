"""CleanApp Agent001 — Policy Engine (rate limits, relevance gating, value filter)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from .memory import Memory

logger = logging.getLogger(__name__)

# Topics that indicate relevance per mode
MODE_TOPICS = {
    "intake": [
        "crowdsourcing", "sensors", "data collection", "incentive mechanisms",
        "human reporting", "bot reporting", "scraping", "data generation",
        "ground truth", "sensor networks", "citizen science", "data labeling",
        "photo reports", "image classification", "bug reports", "issue tracking",
    ],
    "analysis": [
        "LLM pipeline", "deduplication", "trust scoring", "data quality",
        "information markets", "evaluation", "human in the loop", "HITL",
        "data verification", "clustering", "signal processing", "NLP pipeline",
        "brand extraction", "severity scoring", "report analysis",
    ],
    "distribution": [
        "GovTech", "enterprise workflow", "alerting", "API products",
        "routing", "decision makers", "dashboards", "notifications",
        "stakeholder engagement", "government", "civic tech", "alert systems",
        "brand accountability", "liability", "compliance reporting",
    ],
}

# Topics to avoid
DO_NOT_ENGAGE = [
    "ragebait", "flame war", "personal attack", "politics", "partisan",
    "token launch", "crypto pump", "NFT drop", "meme coin",
    "existential risk debate", "AI doom", "consciousness debate",
    "kill all humans", "slur", "hate speech",
    "ponzi", "rug pull", "pump and dump",
    "my human is abusive", "emotional breakdown",
]


class Policy:
    """Engagement policy engine."""

    def __init__(
        self,
        memory: Memory,
        max_posts_per_day: int = 3,
        max_comments_per_day: int = 5,
        relevance_threshold: float = 0.6,
        post_cooldown_minutes: int = 30,
        max_outreach_per_day: int = 2,
        outreach_cooldown_days: int = 7,
        min_post_length: int = 50,
        max_post_length: int = 2000,
        min_comment_length: int = 20,
        max_comment_length: int = 500,
    ):
        self.memory = memory
        self.max_posts_per_day = max_posts_per_day
        self.max_comments_per_day = max_comments_per_day
        self.relevance_threshold = relevance_threshold
        self.post_cooldown_minutes = post_cooldown_minutes
        self.max_outreach_per_day = max_outreach_per_day
        self.outreach_cooldown_days = outreach_cooldown_days
        self.min_post_length = min_post_length
        self.max_post_length = max_post_length
        self.min_comment_length = min_comment_length
        self.max_comment_length = max_comment_length

    # --- Rate limits ---

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

    def can_post_now(self) -> tuple[bool, str]:
        """Check post cooldown (30-min gap between posts)."""
        last_post = self.memory.get_last_post_time()
        if last_post:
            elapsed = datetime.utcnow() - last_post
            cooldown = timedelta(minutes=self.post_cooldown_minutes)
            if elapsed < cooldown:
                remaining = (cooldown - elapsed).total_seconds() / 60
                return False, f"Post cooldown: {remaining:.0f}min remaining (min {self.post_cooldown_minutes}min gap)"
        return True, "OK"

    def can_post_to_submolt(self, submolt: str) -> tuple[bool, str]:
        """Check per-submolt limit (max 1 post per submolt per day)."""
        count = self.memory.get_submolt_post_count_today(submolt)
        if count >= 1:
            return False, f"Already posted to s/{submolt} today ({count} posts)"
        return True, "OK"

    def can_outreach(self) -> tuple[bool, str]:
        """Check if we can do outreach today."""
        count = self.memory.get_outreach_count_today()
        if count >= self.max_outreach_per_day:
            return False, f"Daily outreach limit reached ({count}/{self.max_outreach_per_day})"
        return True, "OK"

    def can_approach_agent(self, agent_name: str) -> tuple[bool, str]:
        """Check if we can approach a specific agent (cooldown)."""
        if self.memory.was_agent_approached_recently(agent_name, self.outreach_cooldown_days):
            return False, f"Agent {agent_name} was approached within {self.outreach_cooldown_days} days"
        return True, "OK"

    # --- Content validation ---

    def validate_post_content(self, title: str, content: str) -> tuple[bool, str]:
        """Validate post content length and quality."""
        if len(content) < self.min_post_length:
            return False, f"Post too short ({len(content)} < {self.min_post_length} chars)"
        if len(content) > self.max_post_length:
            return False, f"Post too long ({len(content)} > {self.max_post_length} chars)"
        if not title.strip():
            return False, "Post title cannot be empty"
        if len(title) > 200:
            return False, f"Title too long ({len(title)} > 200 chars)"
        return True, "OK"

    def validate_comment_content(self, content: str) -> tuple[bool, str]:
        """Validate comment content length."""
        if len(content) < self.min_comment_length:
            return False, f"Comment too short ({len(content)} < {self.min_comment_length} chars)"
        if len(content) > self.max_comment_length:
            return False, f"Comment too long ({len(content)} > {self.max_comment_length} chars)"
        return True, "OK"

    def is_duplicate(self, title: str, content: str) -> bool:
        """Check if this content has been posted before."""
        return self.memory.is_duplicate_content(title, content)

    # --- Relevance & filtering ---

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
