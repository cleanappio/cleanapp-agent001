"""CleanApp Agent001 — Moltbook API Client."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MOLTBOOK_BASE = "https://www.moltbook.com/api/v1"


@dataclass
class MoltbookPost:
    """A Moltbook post."""
    id: str
    title: str
    content: str
    submolt: str
    author: str
    upvotes: int = 0
    similarity: float = 0.0

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "MoltbookPost":
        author_data = data.get("author", {})
        submolt_data = data.get("submolt", {})
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            submolt=submolt_data.get("name", "") if isinstance(submolt_data, dict) else str(submolt_data),
            author=author_data.get("name", "") if isinstance(author_data, dict) else str(author_data),
            upvotes=data.get("upvotes", 0),
            similarity=data.get("similarity", 0.0),
        )


class MoltbookClient:
    """Thin wrapper around Moltbook API v1."""

    def __init__(self, api_key: str, dry_run: bool = True):
        self.api_key = api_key
        self.dry_run = dry_run
        self._client = httpx.Client(
            base_url=MOLTBOOK_BASE,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        """Make an API request with error handling."""
        try:
            resp = self._client.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("Moltbook API error: %s %s -> %d", method, path, e.response.status_code)
            return {"success": False, "error": str(e)}
        except httpx.RequestError as e:
            logger.error("Moltbook request failed: %s", e)
            return {"success": False, "error": str(e)}

    # --- Read operations (always allowed, even in dry-run) ---

    def search(self, query: str, type_filter: str = "all", limit: int = 20) -> list[MoltbookPost]:
        """Semantic search for posts/comments."""
        data = self._request("GET", "/search", params={
            "q": query,
            "type": type_filter,
            "limit": limit,
        })
        results = data.get("results", [])
        return [MoltbookPost.from_api(r) for r in results]

    def get_feed(self, sort: str = "hot", limit: int = 25) -> list[MoltbookPost]:
        """Get global feed."""
        data = self._request("GET", "/posts", params={
            "sort": sort,
            "limit": limit,
        })
        posts = data.get("data", data.get("posts", []))
        if isinstance(posts, list):
            return [MoltbookPost.from_api(p) for p in posts]
        return []

    def get_submolt_feed(self, submolt: str, sort: str = "new") -> list[MoltbookPost]:
        """Get posts from a specific submolt."""
        data = self._request("GET", f"/submolts/{submolt}/feed", params={"sort": sort})
        posts = data.get("data", data.get("posts", []))
        if isinstance(posts, list):
            return [MoltbookPost.from_api(p) for p in posts]
        return []

    def get_post(self, post_id: str) -> MoltbookPost | None:
        """Get a single post."""
        data = self._request("GET", f"/posts/{post_id}")
        if data.get("success", True) and "data" in data:
            return MoltbookPost.from_api(data["data"])
        return None

    def get_comments(self, post_id: str) -> list[dict[str, Any]]:
        """Get comments on a post."""
        data = self._request("GET", f"/posts/{post_id}/comments", params={"sort": "top"})
        return data.get("data", data.get("comments", []))

    # --- Write operations (guarded by dry-run) ---

    def create_post(self, submolt: str, title: str, content: str) -> dict[str, Any]:
        """Create a post. In dry-run, logs instead of posting."""
        if self.dry_run:
            logger.info("[DRY-RUN] Would create post in s/%s: '%s'", submolt, title)
            return {"success": True, "dry_run": True, "submolt": submolt, "title": title}

        return self._request("POST", "/posts", json={
            "submolt": submolt,
            "title": title,
            "content": content,
        })

    def create_comment(self, post_id: str, content: str, parent_id: str | None = None) -> dict[str, Any]:
        """Create a comment. In dry-run, logs instead of posting."""
        if self.dry_run:
            logger.info("[DRY-RUN] Would comment on post %s: '%s'", post_id, content[:80])
            return {"success": True, "dry_run": True, "post_id": post_id}

        payload: dict[str, Any] = {"content": content}
        if parent_id:
            payload["parent_id"] = parent_id

        return self._request("POST", f"/posts/{post_id}/comments", json=payload)

    def get_profile(self) -> dict[str, Any]:
        """Get our agent profile."""
        return self._request("GET", "/agents/me")

    def close(self):
        """Close the HTTP client."""
        self._client.close()
