import logging
import re
import time
import os
from typing import List, Optional
from datetime import datetime, timedelta

from ..llm import GeminiLLM
from ..memory import Memory
from .adapters.base import NetworkAdapter, Post
from .adapters.bb import BBAdapter
from .adapters.moltbook import MoltbookAdapter

logger = logging.getLogger(__name__)

# Minimum content length to consider a post worth processing
MIN_POST_CONTENT_LEN = 15
# Response length bounds
MIN_RESPONSE_LEN = 30
MAX_RESPONSE_LEN = 600


class OutreachEngine:
    def __init__(self, memory: Memory, dry_run: bool = True):
        self.memory = memory
        self.dry_run = dry_run
        self.adapters: List[NetworkAdapter] = []
        self._init_adapters()
        self._init_ai()
        self._load_system_prompt()

    def _init_adapters(self):
        try:
            self.adapters.append(BBAdapter(dry_run=self.dry_run))
            logger.info("BB Adapter loaded.")
        except Exception as e:
            logger.error(f"Failed to load BB Adapter: {e}")

        try:
            self.adapters.append(MoltbookAdapter(dry_run=self.dry_run))
            logger.info("Moltbook Adapter loaded.")
        except Exception as e:
            logger.error(f"Failed to load Moltbook Adapter: {e}")

    def _init_ai(self):
        self.llm = GeminiLLM(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model=os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview"),
            fallback_model=os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-pro"),
            reasoning_profile=os.getenv("GEMINI_REASONING_PROFILE", "light"),
            thinking_budget=(
                int(os.getenv("GEMINI_THINKING_BUDGET"))
                if os.getenv("GEMINI_THINKING_BUDGET")
                else None
            ),
        )

    def _load_system_prompt(self):
        try:
            with open("src/prompts/outreach_system.txt", "r") as f:
                self.system_prompt = f.read()
        except FileNotFoundError:
            logger.warning("System prompt not found, using default.")
            self.system_prompt = "You are a helpful agent."

    def run_cycle(self):
        """Runs one full outreach cycle across all adapters."""
        logger.info("Starting outreach cycle...")

        # Pre-flight health check for Moltbook
        for adapter in self.adapters:
            if adapter.get_network_name() == "moltbook":
                try:
                    health = adapter.client.check_health()
                    if health.suspended:
                        logger.warning(
                            f"Moltbook account SUSPENDED: {health.message} "
                            f"(retry in {health.retry_after_hours:.1f}h). Skipping Moltbook."
                        )
                        self.adapters = [a for a in self.adapters if a.get_network_name() != "moltbook"]
                        break
                    elif not health.ok:
                        logger.warning(f"Moltbook health check failed: {health.message}. Skipping.")
                        self.adapters = [a for a in self.adapters if a.get_network_name() != "moltbook"]
                        break
                    else:
                        logger.info(f"Moltbook health: {health.message}")
                except Exception as e:
                    logger.error(f"Moltbook health check error: {e}")

        for adapter in self.adapters:
            self.process_network(adapter)
        logger.info("Outreach cycle complete.")

    def process_network(self, adapter: NetworkAdapter):
        network = adapter.get_network_name()
        logger.info(f"Scanning {network}...")

        # 1. Rate Limit Check
        if not self._can_post(network):
            logger.info(f"Rate limit hit for {network}. Skipping.")
            return

        # 2. Fetch Posts
        posts = adapter.fetch_recent_posts(limit=20)
        logger.info(f"Fetched {len(posts)} posts from {network}.")

        for post in posts:
            if self._should_process(post):
                self._process_post(adapter, post)

    def _can_post(self, network: str) -> bool:
        """Check rate limits (1/hr per network)."""
        mode = f"outreach-{network}"
        last_post = self.memory.get_last_post_time(mode=mode)
        
        if not last_post:
            return True
            
        elapsed = datetime.utcnow() - last_post
        if elapsed < timedelta(hours=1):
            logger.info(f"Cooldown active for {network}: {elapsed} < 1 hour")
            return False
            
        return True

    def _should_process(self, post: Post) -> bool:
        # Check if already seen/engaged
        if self.memory.already_engaged(post.id):
            return False
        
        # Check if author is us (simple check)
        if "cleanapp" in post.author.lower():
            return False

        # Skip posts with empty or very short content
        if not post.content or len(post.content.strip()) < MIN_POST_CONTENT_LEN:
            logger.debug(f"Skipping post {post.id}: content too short ({len(post.content.strip()) if post.content else 0} chars)")
            return False
            
        return True

    def _process_post(self, adapter: NetworkAdapter, post: Post):
        # 3. Classify & Generate
        response_text = self._generate_response(post)
        
        if response_text:
            logger.info(f"Found opportunity on {adapter.get_network_name()} (Post {post.id})")
            logger.info(f"Proposed Reply: {response_text}")
            
            if not self.dry_run:
                # Double check rate limit right before posting
                if not self._can_post(adapter.get_network_name()):
                    return

                # Dedup check: don't post the same content twice
                if self.memory.content_already_used(response_text):
                    logger.warning(f"Response content already used, skipping post {post.id}")
                    return

                try:
                    new_id = adapter.post_reply(post.id, response_text)
                    self.memory.record_engagement(
                        post_id=post.id,
                        action="post",
                        mode=f"outreach-{adapter.get_network_name()}",
                        content=response_text,
                        thread_title=post.content[:50],
                        relevance_score=1.0 # We only post if high score
                    )
                    logger.info(f"Posted reply: {new_id}")
                except Exception as e:
                    logger.error(f"Failed to post reply on {adapter.get_network_name()}: {e}")
            else:
                self.memory.record_opportunity(
                    mode=f"outreach-{adapter.get_network_name()}",
                    post_id=post.id,
                    title=post.content[:50],
                    submolt="",
                    author=post.author,
                    relevance_score=0.9,
                    action_taken="queued"
                )

    def _clean_response(self, text: str) -> Optional[str]:
        """Clean LLM output: strip JSON wrappers, code fences, meta-commentary."""
        if not text:
            return None

        # Strip code fences (```json ... ```, ```text ... ```, ``` ... ```)
        text = re.sub(r'```(?:json|text|python)?\s*\n?', '', text)
        text = text.strip()

        # Try to extract from JSON wrapper like {"reply": "...", ...}
        json_match = re.search(r'"(?:reply|response|text)"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        if json_match:
            text = json_match.group(1)
            # Unescape JSON string
            text = text.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')

        # Strip common prefixes
        for prefix in ["YES_REPLY", "YES:", "REPLY:", "RESPONSE:", "YES\n", "YES_REPLY\n"]:
            if text.upper().startswith(prefix):
                text = text[len(prefix):].strip()

        # Reject meta-commentary (LLM talking about itself instead of replying)
        meta_patterns = [
            r"I need the (?:post )?content",
            r"Please provide the post",
            r"I (?:will|should|can) analyze",
            r"I'm ready to analyze",
            r"\*\*Analysis",
            r"\*\*Decision",
            r"\*\*Generated Reply",
            r"should_reply",
        ]
        for pattern in meta_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Rejected meta-commentary response: {text[:80]}...")
                return None

        # Strip any remaining JSON-like wrapping
        text = re.sub(r'^\s*\{.*?"(?:reply|response)":\s*', '', text)
        text = re.sub(r'\s*\}\s*$', '', text)

        # Strip placeholder URLs
        text = text.replace("[CLEANAPP_DOCS_URL]", "https://docs.cleanapp.io")

        text = text.strip()

        # Validate length
        if len(text) < MIN_RESPONSE_LEN:
            logger.warning(f"Response too short ({len(text)} chars), skipping")
            return None
        if len(text) > MAX_RESPONSE_LEN:
            logger.warning(f"Response too long ({len(text)} chars), truncating")
            text = text[:MAX_RESPONSE_LEN].rsplit('.', 1)[0] + '.'

        return text

    def _generate_response(self, post: Post) -> Optional[str]:
        """Uses Gemini to decide if and how to respond."""
        prompt = f"""{self.system_prompt}

TASK:
Analyze the following post from a network of agents.
Decide if you should reply based on the "Target Selection Logic" and "Value-First Communication Rules".
If YES, generate the reply following the "Message Structure".
If NO, return exactly "NO_REPLY".

CRITICAL OUTPUT RULES:
- Return ONLY the raw reply text. Nothing else.
- Do NOT wrap your reply in JSON, code fences, or any structured format.
- Do NOT include prefixes like "YES_REPLY", "REPLY:", or "RESPONSE:".
- Do NOT include meta-commentary about your decision process.
- Do NOT ask for more information — use only what is provided below.
- Your output will be posted verbatim as a comment, so write it as a final, publishable reply.

POST:
Author: {post.author}
Network: {post.network}
Content: {post.content}

YOUR REPLY (or NO_REPLY):
"""
        try:
            text = self.llm.generate_text(prompt)
            if "NO_REPLY" in text and len(text) < 20:
                return None
            
            return self._clean_response(text)
        except Exception as e:
            logger.error(f"AI Generation failed: {e}")
            return None
