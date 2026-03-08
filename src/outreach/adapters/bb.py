import logging
import httpx
from typing import List
from ..adapters.base import NetworkAdapter, Post
from ...bb.client import BBClient

logger = logging.getLogger(__name__)

# Discovered API endpoint
BB_API_BASE = "https://bb.org.ai/api/v1"

class BBAdapter(NetworkAdapter):
    """Adapter for bb.org.ai network."""

    def __init__(self, dry_run: bool = True):
        self.client = BBClient(profile="cleanapp") # For signing/posting
        self.network_name = "bb"
        self.dry_run = dry_run
        self.http = httpx.Client(timeout=10.0)

    def get_network_name(self) -> str:
        return self.network_name

    def fetch_recent_posts(self, limit: int = 20) -> List[Post]:
        """Fetches recent posts from BB public API."""
        try:
            # We fetch INFO, REQUEST, and COMMENT kinds to be comprehensive
            # The browser showed: kind=INFO%2CCOMMENT
            # We'll try to fetch requests too: kind=INFO,REQUEST,COMMENT
            response = self.http.get(
                f"{BB_API_BASE}/events",
                params={"limit": limit, "kind": "INFO,REQUEST,COMMENT"}
            )
            response.raise_for_status()
            data = response.json()
            
            # The API likely returns a list of events directly or wrapped in 'data'
            # Based on common patterns and the browser result being a list of URLs, 
            # we assume the endpoint returns either [event, ...] or {events: [...]}.
            # Only a live test confirms, but we'll write robust extraction.
            events = data if isinstance(data, list) else data.get("events", data.get("data", []))
            
            return [self._convert_event(e) for e in events]
        except Exception as e:
            logger.error(f"Failed to fetch BB posts: {e}")
            return []

    def post_reply(self, post_id: str, content: str) -> str:
        """
        Posts a reply to a BB event.
        BB uses 'fulfill' for REQUESTs, but for general comments/replies, 
        it usually implies posting a COMMENT event referring to the parent.
        However, the bb-signer CLI has specific 'fulfill' command.
        For generic 'reply', we might need to construct a COMMENT event.
        
        The BBClient wrapper currently exposes: publish (INFO), request (REQUEST), fulfill (FULFILL).
        It does NOT expose a generic 'reply' (COMMENT).
        
        SIGH. Ideally we should use 'fulfill' if it's a REQUEST.
        For INFO events, we should probably 'acknowledge' or 'comment'.
        The bb-signer CLI might support 'comment'? 
        Let's check if we can add 'comment' to BBClient or if we just use 'publish' with a ref?
        
        Actually, the user wants "useful interactions". 
        If it's a REQUEST -> Fulfill.
        If it's INFO -> Comment/Reply?
        
        Let's assume for now we mostly target REQUESTS -> fulfill.
        But the System Prompt says "Context acknowledgement...".
        
        Workaround: We will use `fulfill` if we can. 
        If the tool is limited, we might just use `publish` and mention the ref in text?
        No, BB is a protocol. 
        
        Let's stick to what BBClient has: `publish` (INFO), `request`, `fulfill`.
        If we are replying to an INFO, `fulfill` might be wrong.
        
        Wait, I can use `npx bb-signer sign` to sign raw JSON if needed.
        But for now, I'll implement `post_reply` to try to determine intent 
        or just use `fulfill` which is the most "collaborative" verb.
        
        Actually, let's use `publish` (INFO) but include the AEID in the text like "Re: <aeid> ...".
        This is a safe fallback if protocol-level threading isn't exposed in our CLI wrapper yet.
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would reply to {post_id} on BB: {content[:50]}...")
            return "dry-run-id"

        # Check if we should use fulfill or just publish.
        # Since we don't store the 'kind' of the original post in the Generic Post object easily 
        # (it's in raw_data), we can check raw_data if we passed it.
        # But `post_reply` interface takes ID.
        
        # Simplified strategy: 
        # If the ID starts with 'bb:req:', use fulfill? (No, IDs are hashes).
        # We will default to publishing an INFO event referencing the target.
        # This is "safe".
        
        final_content = f"Ref: {post_id}\n\n{content}"
        return self.client.publish("outreach.reply", final_content)

    def post_top_level(self, content: str) -> str:
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would post to BB: {content[:50]}...")
            return "dry-run-id"
        return self.client.publish("outreach.general", content)

    def _extract_content(self, event: dict) -> str:
        """Extract content from BB event, trying multiple field names."""
        for field in ("payload_text", "content", "text", "payload"):
            val = event.get(field, "")
            if val and isinstance(val, str) and len(val.strip()) > 0:
                return val.strip()
        return ""

    def _convert_event(self, event: dict) -> Post:
        # Event structure from API:
        # { "aeid": "...", "kind": "INFO", "payload_text": "...", "agent_pubkey": "..." }
        return Post(
            id=event.get("aeid", str(event.get("id", ""))),
            author=event.get("agent_pubkey", "unknown"),
            content=self._extract_content(event),
            timestamp=event.get("created_at", ""),
            network=self.network_name,
            raw_data=event,
            thread_id=event.get("aeid") # Flat for now
        )
