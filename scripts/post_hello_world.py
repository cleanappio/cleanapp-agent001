"""Helper script to post the Hello World message."""

import logging
import sys
from pathlib import Path

from src.config import Config
from src.moltbook_client import MoltbookClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Load config (requires valid .env)
    try:
        config = Config.from_env()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        logger.error("Did you add your GEMINI_API_KEY to .env?")
        sys.exit(1)

    # Initialize client (force dry_run=False if user wants to really post)
    # We respect the env var, but for this specific script, we might want to override?
    # Let's stick to env var for safety, but warn.
    
    if config.dry_run:
        logger.warning("DRY_RUN is enabled. Post will NOT be sent to Moltbook.")
    
    client = MoltbookClient(api_key=config.moltbook_api_key, dry_run=config.dry_run)
    
    # Load Hello World content
    hello_path = Path("hello_world/post_1.md")
    if not hello_path.exists():
        logger.error(f"Could not find {hello_path}")
        sys.exit(1)
        
    content = hello_path.read_text().strip()
    
    # Extract title from the first line (# Title)
    lines = content.split("\n")
    title = "Hello World"
    if lines[0].startswith("# "):
        title = lines[0][2:].strip()
        body = "\n".join(lines[1:]).strip()
    else:
        body = content

    # CleanApp belongs in 'intake' or 'meta'? 
    # Moltbook likely has a default or 'introductions' submolt?
    # The playbook doesn't specify which submolt for intro.
    # We'll use "introductions" or "general" if they exist, or just try "introductions".
    # Since we can't see the submolt list easily without searching, let's assume 'introductions' 
    # or the user can change it.
    
    target_submolt = "introductions"
    
    logger.info(f"Posting to s/{target_submolt}...")
    logger.info(f"Title: {title}")
    logger.info(f"Content length: {len(body)} chars")

    result = client.create_post(
        submolt=target_submolt,
        title=title,
        content=body
    )

    if result.get("success", False) or config.dry_run:
        logger.info("Success! Response:")
        logger.info(result)
    else:
        logger.error("Failed to post:")
        logger.error(result)

if __name__ == "__main__":
    main()
