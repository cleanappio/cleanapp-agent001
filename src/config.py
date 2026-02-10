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

    # Rate limits (self-imposed)
    max_posts_per_day: int = 3
    max_comments_per_day: int = 5
    relevance_threshold: float = 0.6

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
