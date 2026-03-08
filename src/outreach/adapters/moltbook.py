import logging
import os
from typing import List
from ..adapters.base import NetworkAdapter, Post
from ...moltbook_client import MoltbookClient

logger = logging.getLogger(__name__)

class MoltbookAdapter(NetworkAdapter):
    """Adapter for Moltbook network."""

    def __init__(self, dry_run: bool = True):
        api_key = os.getenv("MOLTBOOK_API_KEY")
        if not api_key:
            raise ValueError("Moltbook API key not found")
        self.client = MoltbookClient(api_key, dry_run=dry_run)
        self.network_name = "moltbook"

    def get_network_name(self) -> str:
        return self.network_name

    def fetch_recent_posts(self, limit: int = 20) -> List[Post]:
        """Fetches recent posts from Moltbook global feed."""
        try:
            mb_posts = self.client.get_feed(sort="new", limit=limit)
            return [self._convert_post(p) for p in mb_posts]
        except Exception as e:
            logger.error(f"Failed to fetch Moltbook posts: {e}")
            return []

    def post_reply(self, post_id: str, content: str) -> str:
        """Posts a comment on a Moltbook post."""
        try:
            # We assume post_id is a Moltbook post ID
            result = self.client.create_comment(post_id, content)
            if result.get("success"):
                # Return the new comment ID or a placeholder if dry-run
                return result.get("id", "dry-run-id")
            else:
                raise RuntimeError(f"Moltbook reply failed: {result.get('error')}")
        except Exception as e:
            logger.error(f"Failed to reply on Moltbook: {e}")
            raise

    def post_top_level(self, content: str, submolt: str = "tools", title: str = "") -> str:
        """Posts a top-level message to a Moltbook submolt.
        
        Args:
            content: Post body text
            submolt: Target submolt (default: "tools")
            title: Post title (extracted from first line of content if not provided)
        """
        if not title:
            # Extract title from first line, or use a default
            lines = content.strip().split("\n")
            title = lines[0].strip("# ").strip()[:100]
            if len(lines) > 1:
                content = "\n".join(lines[1:]).strip()
        
        try:
            result = self.client.create_post(submolt=submolt, title=title, content=content)
            if result.get("success") or result.get("id"):
                post_id = result.get("id", "dry-run-id")
                logger.info(f"Posted to s/{submolt}: '{title}' -> {post_id}")
                return str(post_id)
            else:
                raise RuntimeError(f"Moltbook post failed: {result.get('error', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to post on Moltbook s/{submolt}: {e}")
            raise

    def _convert_post(self, mb_post) -> Post:
        """Converts MoltbookPost to generic Post."""
        return Post(
            id=mb_post.id,
            author=mb_post.author,
            content=f"{mb_post.title}\n\n{mb_post.content}",
            timestamp="", # MoltbookClient might not expose timestamp in standard way yet?
                          # Checking MoltbookPost definition... it doesn't have timestamp.
                          # We'll leave it empty or add it if Client supports it later.
            network=self.network_name,
            raw_data={"submolt": mb_post.submolt, "upvotes": mb_post.upvotes},
            thread_id=mb_post.id # Top level post is its own thread
        )
