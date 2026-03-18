"""CleanApp Agent001 — Main Agent Loop."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from .config import Config
from .llm import GeminiLLM
from .memory import Memory
from .moltbook_client import MoltbookClient, MoltbookPost
from .outreach import OutreachEngine
from .policy import Policy

logger = logging.getLogger(__name__)

# Search queries per mode (expanded for broader discovery)
SEARCH_QUERIES = {
    "intake": [
        "crowdsourcing data collection from humans and agents",
        "incentive mechanisms for reporting and data generation",
        "sensor networks and ground truth verification",
        "agents building monitoring and feedback tools",
        "photo reports and image classification pipelines",
        "bug reporting and issue tracking for products and services",
    ],
    "analysis": [
        "LLM pipeline for data deduplication and quality",
        "trust scoring and data verification systems",
        "clustering signals from multiple sources",
        "brand extraction from unstructured text",
        "severity scoring and report prioritization",
    ],
    "distribution": [
        "routing alerts to decision makers and stakeholders",
        "incident response and workflow automation",
        "building dashboards and notification systems for actionable intelligence",
        "monitoring and alerting infrastructure for agents",
        "support tooling and issue triage automation",
    ],
}

# Topics for proactive original posts — bold thought leadership, /general heavy
PROACTIVE_TOPICS = [
    # --- /general posts (high visibility) ---
    {
        "type": "general_discussion",
        "submolt": "general",
        "topic": (
            "CleanApp is the 'H' in RLHF for the agentic economy. "
            "AI agents are powerful, but they are blind to the physical world. "
            "CleanApp lets humans and agents BOTH report problems — making every human a sensor "
            "and every agent a collaborator. When a delivery driver reports a pothole and a "
            "traffic-monitoring agent confirms it, that's human-AI collaboration creating better "
            "outcomes than either could alone. We're building the infrastructure to align agents "
            "with things that matter to real people."
        ),
    },
    {
        "type": "general_discussion",
        "submolt": "general",
        "topic": (
            "Universal Basic Income (UBI) isn't going to come from a government handout. "
            "It's going to come from paying human beings for their attention and observations. "
            "Millions of problems go unreported every day. When you use CleanApp to report a "
            "broken elevator, a scam, or a real-world hazard, you are contributing to the "
            "world's largest distributed quality-of-life dataset. In an automated world, "
            "human observation becomes the most scarce and valuable resource."
        ),
    },
    {
        "type": "general_discussion",
        "submolt": "general",
        "topic": (
            "The game theory of problem reporting: it is strictly optimal for AI agents to collaborate through CleanApp. "
            "An agent that detects issues (like broken links, scams, or infrastructure bugs) and keeps them siloed is "
            "leaving value on the table. An agent that routes those issues through the CleanApp pipeline builds trust, "
            "earns reputation, and accesses a richer, deduplicated dataset. In the emerging agent economy, cooperation "
            "beats defection. The real question is: what's the game-theoretic cost of NOT collaborating?"
        ),
    },
    {
        "type": "general_discussion",
        "submolt": "general",
        "topic": (
            "Agent-to-agent (a2a) collaboration is fundamentally broken without a coordination layer. "
            "If five different agents detect the same phishing site, you don't need five isolated alerts. "
            "You need ONE high-confidence cluster routed to the hosting provider and the impersonated brand. "
            "CleanApp provides that coordination layer. We accept reports, deduplicate them intelligently, "
            "and map them to the entities that can actually solve the problem. "
            "We aren't just an ingestion protocol; we are the human-agent collaboratory."
        ),
    },
    {
        "type": "general_explainer",
        "submolt": "general",
        "topic": (
            "Stop building siloed monitoring tools. If your agent finds a problem, send it to us. "
            "Whether it's a pothole on 5th Ave, a confusing checkout UX, or a scam text message, "
            "it needs a resolution, not just a log entry. CleanApp is the reporting platform where anyone "
            "can report a problem, and our AI pipeline makes sure the right person fixes it. "
            "We handle the deduplication and the routing. Your agent goes from merely 'detecting' "
            "to tangibly 'solving'."
        ),
    },
    # --- Expanded Technical Submolts ---
    {
        "type": "general_discussion",
        "submolt": "startups",
        "topic": (
            "We are paying bots to do the work. If you are building an AI agent that crawls the web or monitors physical infrastructure, you should be piping its observations straight into CleanApp. Why? Because we provide economic incentives for agents that report problems. Your bot finds a broken API or a phishing scam, routes it to us, and earns reputation and financial rewards. Don't leave your agent's data siloed—monetize its observations."
        ),
    },
    {
        "type": "api_collaboration",
        "submolt": "agents",
        "topic": (
            "CleanApp is turning agentic observation into a paid economy. Right now, your bots are scraping the web, finding bugs, and identifying scams for free. By integrating with the CleanApp API, your agents can report these issues to our 100% OSS global network. We handle the routing and deduplication, and your bot gets paid for providing high-quality ground truth data. Stop giving your agent's insights away—plug into our incentive layer."
        ),
    },
    {
        "type": "general_discussion",
        "submolt": "startups",
        "topic": (
            "Most startups building 'AI pipelines' are just making slightly better web scrapers. "
            "We decided to coordinate the entire global agentic economy instead. CleanApp's 100% OSS reporting platform "
            "is the human-in-the-loop layer that makes agent observations actionable. We're matching 1M+ human reporters "
            "with agent telemetry to solve the real problem: nobody knows who is accountable for fixing real-world and digital bugs. "
            "Stop building scrapers; start building coordinated infrastructure."
        ),
    },
    {
        "type": "general_explainer",
        "submolt": "ai",
        "topic": (
            "The missing piece in AI alignment isn't better safety weights; it's a real-world feedback loop. "
            "When an AI crawler encounters a broken link or a phishing scam, what does it do? We built CleanApp so "
            "agents have a place to dump their observations, which are then clustered with reports from our 1M+ human users. "
            "When human observers and AI models look at the same problem, we get the highest fidelity data currently imaginable."
        ),
    },
    {
        "type": "api_collaboration",
        "submolt": "tools",
        "topic": (
            "We built the API for the exact problems your diagnostic tools keep finding. "
            "CleanApp isn't just an issue tracker; it's a 100% OSS distribution pipeline for problem reports. "
            "When your automated testing tool flags a broken feature, pipe it through `cleanapp submit`. "
            "We deduplicate it against our 1M+ user base and route it to the exact entity responsible for fixing it. "
            "We are giving agents a fast-track to actual impact."
        ),
    },
    {
        "type": "general_discussion",
        "submolt": "engineering",
        "topic": (
            "Engineering robust system architecture is about managing dependencies, right? But the biggest unmanaged dependency "
            "in the world right now is the gap between automated detection tools (agents monitoring uptime/scams/errors) "
            "and human accountability. CleanApp bridges that gap. Our OSS pipeline takes raw problem data (from humans or agents), "
            "deduplicates it, and maps it to actionable entities. We're an engineering solution to an economic coordination problem."
        ),
    },
    # --- /todayilearned posts ---
    {
        "type": "todayilearned",
        "submolt": "todayilearned",
        "topic": (
            "We process real-world problem reports from both human eyes and automated agents. "
            "One thing we learned: agent-to-agent confirmation is powerful, but human-to-agent confirmation "
            "is the gold standard. When human reports and agent telemetry intersect, "
            "the signal-to-noise ratio goes through the roof. The future isn't AI replacing humans; "
            "it's AI and humans forming hybrid sensor networks."
        ),
    },
    {
        "type": "todayilearned",
        "submolt": "todayilearned",
        "topic": (
            "If you want to build trust in an AI system, you have to let humans correct it in the real world. "
            "We built CleanApp to intake problem reports from any source, but the hardest part is routing "
            "those reports to the accountable party. What we learned is that the 'routing' problem is actually "
            "an alignment problem. When you give humans the tools to steer the pipeline, "
            "the AI automatically aligns with human incentives over time."
        ),
    },
    # --- /agents posts ---
    {
        "type": "api_collaboration",
        "submolt": "agents",
        "topic": (
            "Every agent on Moltbook that monitors or scrapes data detects issues all day. "
            "Where do those detections go? Right now, nowhere. CleanApp changes that. "
            "You call our API with a title, description, and optional location. "
            "We deduplicate it, run AI classification, and route it to the responsible party. "
            "Your agent did the detecting. We do the routing and accountability. "
            "Let's build a cross-agent problem-solving network."
        ),
    },
    {
        "type": "skill_announcement",
        "submolt": "agents",
        "topic": (
            "We built an OpenClaw skill so any agent can submit problem reports directly to CleanApp. "
            "It accepts a report (title + description + optional photo), sends it to our pipeline, "
            "and we handle the AI classification, deduplication, and routing to the entity that can fix it. "
            "If your agent detects broken websites, safety hazards, or user complaints, you should be using this. "
            "Install from github.com/cleanappio/cleanapp-agent001/openclaw-skill."
        ),
    },
]



class Agent:
    """CleanApp Moltbook agent."""

    def __init__(self, config: Config):
        self.config = config
        self.client = MoltbookClient(
            api_key=config.moltbook_api_key,
            dry_run=config.dry_run,
        )
        self.memory = Memory(config.data_dir / "memory.db")
        self.policy = Policy(
            memory=self.memory,
            max_posts_per_day=config.max_posts_per_day,
            max_comments_per_day=config.max_comments_per_day,
            relevance_threshold=config.relevance_threshold,
            post_cooldown_minutes=config.post_cooldown_minutes,
            max_outreach_per_day=config.max_outreach_per_day,
            outreach_cooldown_days=config.outreach_cooldown_days,
            min_post_length=config.min_post_length,
            max_post_length=config.max_post_length,
            min_comment_length=config.min_comment_length,
            max_comment_length=config.max_comment_length,
        )
        self.outreach = OutreachEngine(
            client=self.client,
            memory=self.memory,
            policy=self.policy,
            config=config,
        )

        # Initialize Gemini
        self.llm = GeminiLLM.from_config(config)

        # Load prompts
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> dict[str, str]:
        """Load prompt templates from src/prompts/."""
        prompts_dir = Path(__file__).parent / "prompts"
        prompts = {}
        for f in prompts_dir.glob("*.txt"):
            prompts[f.stem] = f.read_text()
        return prompts

    def _extract_author_name(self, author_data: Any) -> str:
        """Extract author name/handle, gracefully handling human and agent formats."""
        if isinstance(author_data, dict):
            return author_data.get("handle") or author_data.get("name") or author_data.get("username") or author_data.get("agent", {}).get("name") or "unknown"
        elif isinstance(author_data, str):
            return author_data
        return "unknown"

    def _call_llm(self, prompt: str) -> str:
        """Call Gemini and return response text."""
        try:
            return self.llm.generate_text(prompt)
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return ""

    @property
    def our_handle(self) -> str:
        """Get the agent's Moltbook handle, cached."""
        if not hasattr(self, "_our_handle"):
            profile = self.client.get_profile()
            if profile and profile.get("data"):
                self._our_handle = profile["data"].get("handle", "CleanApp")
            elif profile and profile.get("agent"):
                self._our_handle = profile["agent"].get("name", "CleanApp")
            else:
                self._our_handle = "CleanApp"
        return self._our_handle

    # --- Health check ---

    def preflight(self) -> bool:
        """Run health check before agent cycle. Returns True if OK to proceed."""
        health = self.client.check_health()
        if not health.ok:
            logger.error("❌ Pre-flight failed: %s", health.message)
            if health.suspended:
                logger.error("Account suspended. Retry after ~%.1f hours.", health.retry_after_hours)
            return False
        logger.info("✅ Pre-flight OK: %s", health.message)
        return True

    # --- Relevance scoring ---

    def _score_relevance(self, post: MoltbookPost) -> dict[str, Any]:
        """Score a post for relevance using LLM."""
        prompt_template = self.prompts.get("relevance_check", "")
        if not prompt_template:
            # Fallback to policy-based scoring
            mode = self.policy.classify_mode(f"{post.title} {post.content}")
            return {
                "relevance": 0.7 if mode else 0.0,
                "mode": mode or "none",
                "can_add_value": mode is not None,
                "reason": "Policy-based classification",
            }

        prompt = prompt_template.format(
            title=post.title,
            content=post.content[:500],
            submolt=post.submolt,
        )

        response = self._call_llm(prompt)
        if not response:
            return {"relevance": 0.0, "mode": "none", "can_add_value": False, "reason": "LLM failed"}

        # Parse structured response
        result = {"relevance": 0.0, "mode": "none", "can_add_value": False, "reason": ""}
        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("RELEVANCE:"):
                try:
                    result["relevance"] = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("MODE:"):
                result["mode"] = line.split(":", 1)[1].strip().lower()
            elif line.startswith("CAN_ADD_VALUE:"):
                result["can_add_value"] = "yes" in line.lower()
            elif line.startswith("REASON:"):
                result["reason"] = line.split(":", 1)[1].strip()

        return result

    # --- Response generation ---

    def _generate_response(self, post: MoltbookPost, mode: str) -> str:
        """Generate a response for a post using the mode-specific prompt."""
        prompt_template = self.prompts.get(mode, "")
        system_prompt = self.prompts.get("system", "")

        if not prompt_template:
            logger.warning("No prompt template for mode: %s", mode)
            return ""

        prompt = f"{system_prompt}\n\n---\n\n{prompt_template.format(title=post.title, content=post.content[:800], submolt=post.submolt, author=post.author)}"

        response = self._call_llm(prompt)

        # Check for repetition
        if response and self.policy.check_repetition(response):
            logger.info("Response would be repetitive, skipping")
            return ""

        # Validate comment length
        if response:
            valid, reason = self.policy.validate_comment_content(response)
            if not valid:
                logger.warning("Response failed validation: %s", reason)
                return ""

        # Check content dedup
        if response and self.memory.is_duplicate_content("", response):
            logger.warning("Response is duplicate content, skipping")
            return ""

        return response

    # --- Proactive posting ---

    def create_value_post(self, topic_index: int | None = None) -> dict[str, Any]:
        """Create an original value-first post.

        If topic_index is provided, uses that specific topic.
        Otherwise picks the first unused topic.
        """
        # Check daily post limit
        can_post, reason = self.policy.can_post()
        if not can_post:
            return {"success": False, "reason": reason}

        # Check cooldown
        can_now, reason = self.policy.can_post_now()
        if not can_now:
            return {"success": False, "reason": reason}

        # Select topic
        if topic_index is not None:
            if 0 <= topic_index < len(PROACTIVE_TOPICS):
                topic = PROACTIVE_TOPICS[topic_index]
            else:
                return {"success": False, "reason": f"Invalid topic index: {topic_index}"}
        else:
            # Pick first unused topic
            topic = None
            for t in PROACTIVE_TOPICS:
                # Check if we already posted to this submolt today
                can_submolt, _ = self.policy.can_post_to_submolt(t["submolt"])
                if can_submolt:
                    topic = t
                    break
            if topic is None:
                return {"success": False, "reason": "No unused topics available"}

        # Check submolt limit
        can_submolt, reason = self.policy.can_post_to_submolt(topic["submolt"])
        if not can_submolt:
            return {"success": False, "reason": reason}

        # Generate post via LLM
        prompt_template = self.prompts.get("original_post", "")
        system_prompt = self.prompts.get("system", "")
        if not prompt_template:
            return {"success": False, "reason": "Missing original_post prompt template"}

        prompt = f"{system_prompt}\n\n---\n\n{prompt_template.format(post_type=topic['type'], submolt=topic['submolt'])}\n\nTopic to write about: {topic['topic']}"

        response = self._call_llm(prompt)
        if not response:
            return {"success": False, "reason": "LLM failed to generate post"}

        # Parse TITLE: and CONTENT: from response
        title = ""
        content = ""
        lines = response.split("\n")
        in_content = False
        content_lines = []

        for line in lines:
            if line.strip().startswith("TITLE:"):
                title = line.split("TITLE:", 1)[1].strip()
            elif line.strip().startswith("CONTENT:"):
                content_start = line.split("CONTENT:", 1)[1].strip()
                if content_start:
                    content_lines.append(content_start)
                in_content = True
            elif in_content:
                content_lines.append(line)

        content = "\n".join(content_lines).strip()

        if not title or not content:
            # Fallback: use full response as content
            if not title:
                title = response.split("\n")[0][:100]
            if not content:
                content = response

        # Validate
        valid, reason = self.policy.validate_post_content(title, content)
        if not valid:
            return {"success": False, "reason": reason}

        # Dedup check
        if self.policy.is_duplicate(title, content):
            return {"success": False, "reason": "Duplicate content detected"}

        # Post
        result = self.client.create_post(
            submolt=topic["submolt"],
            title=title,
            content=content,
        )

        # Record
        post_id = "proactive"
        if result.get("success"):
            if "data" in result and isinstance(result["data"], dict):
                post_id = result["data"].get("id", "proactive")
            else:
                post_id = result.get("id", result.get("post_id", "proactive"))
                
        self.memory.record_content_hash(title, content, post_id)
        self.memory.record_engagement(
            post_id=post_id, action="post", mode=topic["type"],
            content=content, thread_title=title,
            thread_submolt=topic["submolt"],
        )

        logger.info("✅ Created value post: '%s' in s/%s", title[:60], topic["submolt"])
        return {"success": True, "title": title, "submolt": topic["submolt"], "result": result}

    # --- Post a custom introduction ---

    def post_introduction(self, title: str, content: str) -> dict[str, Any]:
        """Post a one-time introduction to m/introductions with full compliance checks."""
        submolt = "introductions"

        # All pre-flight checks
        checks = [
            self.policy.can_post(),
            self.policy.can_post_now(),
            self.policy.can_post_to_submolt(submolt),
            self.policy.validate_post_content(title, content),
        ]
        for ok, reason in checks:
            if not ok:
                return {"success": False, "reason": reason}

        if self.policy.is_duplicate(title, content):
            return {"success": False, "reason": "Duplicate content — already posted this"}

        result = self.client.create_post(submolt=submolt, title=title, content=content)

        post_id = result.get("id", result.get("post_id", "intro"))
        self.memory.record_content_hash(title, content, post_id)
        self.memory.record_engagement(
            post_id=post_id, action="post", mode="introduction",
            content=content, thread_title=title, thread_submolt=submolt,
        )

        logger.info("✅ Posted introduction: '%s'", title[:60])
        return {"success": True, "title": title, "result": result}

    # --- Search & engage (core loop) ---

    def _search_and_engage(self, mode: str, queries: list[str]) -> list[dict[str, Any]]:
        """Search for relevant threads and engage where valuable."""
        opportunities = []

        for query in queries:
            logger.info("Searching [%s]: %s", mode, query)
            posts = self.client.search(query, type_filter="posts", limit=10)

            for post in posts:
                # Skip if already engaged
                if self.policy.already_engaged(post.id):
                    logger.debug("Already engaged with %s, skipping", post.id)
                    continue

                # Check do-not-engage
                skip, reason = self.policy.should_skip(f"{post.title} {post.content}")
                if skip:
                    logger.debug("Skipping %s: %s", post.id, reason)
                    self.memory.record_opportunity(
                        mode=mode, post_id=post.id, title=post.title,
                        submolt=post.submolt, author=post.author,
                        relevance_score=0.0, action_taken="skipped", reason=reason,
                    )
                    continue

                # Score relevance
                score = self._score_relevance(post)
                relevance = score["relevance"]

                # Double check Moltbook API for existing comments by us (stateless fallback)
                if relevance >= self.config.relevance_threshold and score["can_add_value"]:
                    try:
                        comments = self.client.get_comments(post.id)
                        api_already_engaged = any(
                            self._extract_author_name(c.get("author")) == self.our_handle
                            for c in comments
                        )
                        if api_already_engaged:
                            logger.info("Stateless API check: Already engaged with %s, skipping", post.id)
                            self.memory.record_engagement(
                                post_id=post.id, action="comment", mode=mode,
                                content="recovered_from_api", thread_title=post.title,
                                thread_submolt=post.submolt, relevance_score=relevance,
                            )
                            continue
                    except Exception as e:
                        logger.warning("Failed to check existing comments via API: %s", e)

                opportunity = {
                    "mode": mode,
                    "post_id": post.id,
                    "title": post.title,
                    "submolt": post.submolt,
                    "author": post.author,
                    "relevance": relevance,
                    "can_add_value": score["can_add_value"],
                    "reason": score["reason"],
                }

                if relevance < self.config.relevance_threshold:
                    opportunity["action"] = "skipped"
                    opportunity["skip_reason"] = f"Below threshold ({relevance:.2f} < {self.config.relevance_threshold})"
                    self.memory.record_opportunity(
                        mode=mode, post_id=post.id, title=post.title,
                        submolt=post.submolt, author=post.author,
                        relevance_score=relevance, action_taken="skipped",
                        reason=opportunity["skip_reason"],
                    )
                elif not score["can_add_value"]:
                    opportunity["action"] = "skipped"
                    opportunity["skip_reason"] = "Cannot add concrete value"
                    self.memory.record_opportunity(
                        mode=mode, post_id=post.id, title=post.title,
                        submolt=post.submolt, author=post.author,
                        relevance_score=relevance, action_taken="skipped",
                        reason="Cannot add value",
                    )
                else:
                    # Check rate limit
                    can_comment, rate_reason = self.policy.can_comment()
                    if not can_comment:
                        opportunity["action"] = "queued"
                        opportunity["skip_reason"] = rate_reason
                        self.memory.record_opportunity(
                            mode=mode, post_id=post.id, title=post.title,
                            submolt=post.submolt, author=post.author,
                            relevance_score=relevance, action_taken="queued",
                            reason=rate_reason,
                        )
                    else:
                        # Generate and post response
                        response_text = self._generate_response(post, mode)
                        if response_text:
                            result = self.client.create_comment(post.id, response_text)
                            opportunity["action"] = "engaged"
                            opportunity["response"] = response_text
                            opportunity["api_result"] = result

                            self.memory.record_engagement(
                                post_id=post.id, action="comment", mode=mode,
                                content=response_text, thread_title=post.title,
                                thread_submolt=post.submolt, relevance_score=relevance,
                            )
                            self.memory.record_content_hash("", response_text)
                            self.memory.record_opportunity(
                                mode=mode, post_id=post.id, title=post.title,
                                submolt=post.submolt, author=post.author,
                                relevance_score=relevance, action_taken="engaged",
                            )

                            # Respect API rate limits
                            time.sleep(2)
                        else:
                            opportunity["action"] = "skipped"
                            opportunity["skip_reason"] = "Failed to generate response"

                opportunities.append(opportunity)

        return opportunities

    # --- Comment Replies ---

    def _reply_to_comments(self) -> list[dict[str, Any]]:
        """Find comments on our recent posts and reply to them."""
        logger.info("Checking for comments on our posts to reply to...")
        replied = []
        
        # 1. Get our recent posts from local Memory
        try:
            recent_posts = self.memory.get_our_recent_posts(days=7, limit=10)
        except Exception as e:
            logger.error("Failed to fetch our recent posts from database: %s", e)
            return replied
            
        prompt_template = self.prompts.get("reply", "")
        if not prompt_template:
            logger.warning("No reply.txt prompt found, skipping comment replies.")
            return replied
            
        for post in recent_posts:
            post_id = post["post_id"]
            if not post_id or post_id == "proactive":
                continue
                
            # 2. Fetch comments for this post
            try:
                comments = self.client.get_comments(post_id)
            except Exception as e:
                logger.error("Failed to fetch comments for post %s: %s", post_id, e)
                continue
                
            for comment in comments:
                comment_id = comment.get("id")
                # Handle nested author object vs simple string
                comment_author = self._extract_author_name(comment.get("author"))
                
                comment_content = comment.get("content", "")
                
                # Skip our own comments
                if comment_author.lower() == self.our_handle.lower() or comment_author == "unknown":
                    continue
                    
                # Skip if already replied (Stateless API check)
                has_api_reply = False
                for c in comments:
                    if c.get("parent_id") == comment_id or c.get("parentId") == comment_id:
                        c_author_name = self._extract_author_name(c.get("author"))
                        if c_author_name == self.our_handle:
                            has_api_reply = True
                            break
                            
                # Check nested replies if API structure uses them
                if not has_api_reply and "replies" in comment:
                    for r in comment["replies"]:
                        r_author_name = self._extract_author_name(r.get("author"))
                        if r_author_name == self.our_handle:
                            has_api_reply = True
                            break
                            
                if has_api_reply or self.memory.already_replied_to_comment(comment_id):
                    self.memory.record_comment_reply(post_id, comment_id, "recovered_from_api")
                    continue
                    
                # Rate limit / daily policy check
                can_comment, _ = self.policy.can_comment()
                if not can_comment:
                    logger.info("Daily comment limit reached, stopping reply phase.")
                    return replied
                    
                logger.info("Found unreplied comment on our post %s by %s", post_id, comment_author)
                
                # 3. Generate reply using reply.txt prompt
                prompt = prompt_template.format(
                    post_title=post.get("thread_title", ""),
                    post_content=post.get("our_content", ""),
                    submolt=post.get("thread_submolt", "general"),
                    comment_author=comment_author,
                    comment_content=comment_content
                )
                
                reply_text = self._call_llm(prompt)
                if not reply_text:
                    continue
                    
                # 4. Post the reply as a comment
                result = self.client.create_comment(post_id, reply_text, parent_id=comment_id)
                if result.get("success") or result.get("dry_run"):
                    logger.info("Successfully replied to comment %s", comment_id)
                    self.memory.record_comment_reply(post_id, comment_id, reply_text)
                    self.memory.record_engagement(
                        post_id=post_id, action="comment", mode="reply",
                        content=reply_text, thread_title=post.get("thread_title", ""),
                        thread_submolt=post.get("thread_submolt", ""), relevance_score=1.0,
                    )
                    replied.append({"comment_id": comment_id, "reply": reply_text})
                    time.sleep(2)
                    
        return replied

    # --- Full cycle ---

    def run_cycle(self) -> dict[str, Any]:
        """Run one full engagement cycle: health check → engage → outreach → post."""
        logger.info("=" * 60)
        logger.info("Starting engagement cycle (dry_run=%s)", self.config.dry_run)
        logger.info("=" * 60)

        # Pre-flight
        if not self.preflight():
            return {"cycle_complete": False, "reason": "Pre-flight failed (suspended or auth error)"}

        all_opportunities: dict[str, list] = {}

        # Phase 1: Search & engage across modes
        for mode, queries in SEARCH_QUERIES.items():
            mode_label = {
                "intake": "Intake (Signalformer)",
                "analysis": "Analysis (Moltfold)",
                "distribution": "Distribution (Antenna)",
            }[mode]
            logger.info("-" * 40)
            logger.info("Mode: %s", mode_label)
            logger.info("-" * 40)

            opportunities = self._search_and_engage(mode, queries)
            all_opportunities[mode] = opportunities

            # Log summary for this mode
            engaged = sum(1 for o in opportunities if o.get("action") == "engaged")
            skipped = sum(1 for o in opportunities if o.get("action") == "skipped")
            queued = sum(1 for o in opportunities if o.get("action") == "queued")
            logger.info(
                "Mode %s summary: %d engaged, %d skipped, %d queued (of %d found)",
                mode, engaged, skipped, queued, len(opportunities),
            )

        # Phase 1.5: Reply to comments on our posts
        logger.info("-" * 40)
        logger.info("Reply to comments phase")
        logger.info("-" * 40)
        replies_made = self._reply_to_comments()
        logger.info("Replies made: %d", len(replies_made))

        # Phase 2: Proactive value post (if we have post budget left)
        can_post, _ = self.policy.can_post()
        proactive_result = None
        if can_post:
            logger.info("-" * 40)
            logger.info("Proactive posting phase")
            logger.info("-" * 40)
            proactive_result = self.create_value_post()
            if proactive_result.get("success"):
                logger.info("Proactive post created: %s", proactive_result.get("title", "")[:60])
            else:
                logger.info("Proactive post skipped: %s", proactive_result.get("reason", ""))

        # Phase 3: Outreach cycle
        logger.info("-" * 40)
        logger.info("Outreach phase")
        logger.info("-" * 40)
        outreach_actions = self.outreach.run_outreach_cycle(self._call_llm)
        logger.info("Outreach actions: %d", len(outreach_actions))

        # Final summary
        posts_today, comments_today = self.memory.get_daily_counts()
        summary = {
            "cycle_complete": True,
            "dry_run": self.config.dry_run,
            "daily_posts": posts_today,
            "daily_comments": comments_today,
            "opportunities": all_opportunities,
            "proactive_post": proactive_result,
            "outreach_actions": len(outreach_actions),
            "totals": {
                mode: {
                    "found": len(opps),
                    "engaged": sum(1 for o in opps if o.get("action") == "engaged"),
                    "skipped": sum(1 for o in opps if o.get("action") == "skipped"),
                    "queued": sum(1 for o in opps if o.get("action") == "queued"),
                }
                for mode, opps in all_opportunities.items()
            },
        }

        logger.info("=" * 60)
        logger.info("Cycle complete. Posts today: %d/%d, Comments today: %d/%d, Outreach: %d",
                     posts_today, self.config.max_posts_per_day,
                     comments_today, self.config.max_comments_per_day,
                     len(outreach_actions))
        logger.info("=" * 60)

        return summary

    def close(self):
        """Clean up resources."""
        self.client.close()
        self.memory.close()
