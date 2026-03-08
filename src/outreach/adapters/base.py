from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Post:
    id: str  # Unique ID on the network (e.g., AEID or Moltbook Post ID)
    author: str  # Author identifier
    content: str  # Post text content
    timestamp: str  # ISO timestamp
    network: str  # 'bb', 'moltbook', etc.
    raw_data: dict  # Original raw data payload
    thread_id: Optional[str] = None  # To group replies

class NetworkAdapter(ABC):
    """Abstract base class for network adapters."""

    @abstractmethod
    def get_network_name(self) -> str:
        """Returns the network identifier (e.g., 'bb')."""
        pass

    @abstractmethod
    def fetch_recent_posts(self, limit: int = 20) -> List[Post]:
        """Fetches recent posts relevant to the agent's interests."""
        pass

    @abstractmethod
    def post_reply(self, post_id: str, content: str) -> str:
        """Posts a reply to a specific post. Returns the new post ID."""
        pass
    
    @abstractmethod
    def post_top_level(self, content: str) -> str:
        """Posts a top-level message. Returns the new post ID."""
        pass
