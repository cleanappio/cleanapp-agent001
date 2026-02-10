"""CleanApp Agent001 — Configuration."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Agent configuration loaded from environment variables."""

    # API keys
    moltbook_api_key: str = field(repr=False)
    gemini_api_key: str = field(repr=False)

    # Mode
    dry_run: bool = True
    log_level: str = "INFO"

    # Rate limits — engagement
    max_posts_per_day: int = 3
    max_comments_per_day: int = 5
    relevance_threshold: float = 0.6

    # Rate limits — compliance
    post_cooldown_minutes: int = 30  # Moltbook enforces 1 post per 30 min
    max_outreach_per_day: int = 2
    outreach_cooldown_days: int = 7  # Don't re-approach an agent within 7 days

    # Content constraints
    min_post_length: int = 50
    max_post_length: int = 2000
    min_comment_length: int = 20
    max_comment_length: int = 500

    # Paths
    data_dir: Path = Path("./data")

    # Moltbook
    moltbook_base_url: str = "https://www.moltbook.com/api/v1"

    @classmethod
    def from_env(cls) -> "Config":
        """Load config from environment variables."""
        data_dir = Path(os.getenv("DATA_DIR", "./data"))
        data_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            moltbook_api_key=os.getenv("MOLTBOOK_API_KEY", ""),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            dry_run=os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_posts_per_day=int(os.getenv("MAX_POSTS_PER_DAY", "3")),
            max_comments_per_day=int(os.getenv("MAX_COMMENTS_PER_DAY", "5")),
            relevance_threshold=float(os.getenv("RELEVANCE_THRESHOLD", "0.6")),
            post_cooldown_minutes=int(os.getenv("POST_COOLDOWN_MINUTES", "30")),
            max_outreach_per_day=int(os.getenv("MAX_OUTREACH_PER_DAY", "2")),
            outreach_cooldown_days=int(os.getenv("OUTREACH_COOLDOWN_DAYS", "7")),
            data_dir=data_dir,
        )

    def validate(self) -> list[str]:
        """Return list of configuration errors."""
        errors = []
        if not self.moltbook_api_key:
            errors.append("MOLTBOOK_API_KEY is required")
        if not self.gemini_api_key:
            errors.append("GEMINI_API_KEY is required")
        return errors
