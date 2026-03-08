#!/usr/bin/env python3
"""
Launch Announcements — Post the CleanApp CLI announcement to BB and Moltbook.

Usage:
    python scripts/launch_announcements.py --dry-run    # Preview without posting
    python scripts/launch_announcements.py              # Actually post

This posts:
  1. BB INFO event  — CleanApp CLI announcement
  2. BB REQUEST     — "What problems does your agent encounter?"
  3. Moltbook post  — Announcement to s/tools
"""

import argparse
import os
import sys
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bb.client import BBClient
from src.moltbook_client import MoltbookClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("launch-announcements")

TEMPLATE_DIR = Path(__file__).parent / "announcement_templates"


def post_bb_announcements(dry_run: bool):
    """Post INFO and REQUEST events to BB."""
    logger.info("=== BB Announcements ===")
    
    try:
        client = BBClient(profile="cleanapp")
    except Exception as e:
        logger.error(f"Failed to init BB client: {e}")
        return
    
    # 1. INFO announcement
    info_content = (TEMPLATE_DIR / "bb_info_announcement.md").read_text()
    if dry_run:
        logger.info(f"[DRY-RUN] Would publish BB INFO event:")
        logger.info(f"  Topic: agent.tools.cleanapp")
        logger.info(f"  Content: {info_content[:120]}...")
    else:
        try:
            result = client.publish("agent.tools.cleanapp", info_content)
            logger.info(f"BB INFO event published: {result}")
        except Exception as e:
            logger.error(f"Failed to publish BB INFO: {e}")
    
    time.sleep(2)  # Brief pause between posts
    
    # 2. REQUEST event
    request_content = (TEMPLATE_DIR / "bb_request_problems.md").read_text()
    if dry_run:
        logger.info(f"[DRY-RUN] Would publish BB REQUEST event:")
        logger.info(f"  Topic: agent.problems.survey")
        logger.info(f"  Content: {request_content[:120]}...")
    else:
        try:
            result = client.request("agent.problems.survey", request_content)
            logger.info(f"BB REQUEST event published: {result}")
        except Exception as e:
            logger.error(f"Failed to publish BB REQUEST: {e}")


def post_moltbook_announcement(dry_run: bool):
    """Post announcement to Moltbook s/tools."""
    logger.info("=== Moltbook Announcement ===")
    
    api_key = os.getenv("MOLTBOOK_API_KEY")
    if not api_key:
        logger.error("MOLTBOOK_API_KEY not set, skipping Moltbook")
        return
    
    client = MoltbookClient(api_key, dry_run=dry_run)
    
    # Health check first
    health = client.check_health()
    if health.suspended:
        logger.warning(f"Moltbook account SUSPENDED: {health.message}. Skipping.")
        return
    elif not health.ok:
        logger.warning(f"Moltbook health check failed: {health.message}. Skipping.")
        return
    
    logger.info(f"Moltbook health: {health.message}")
    
    # Post announcement
    announcement = (TEMPLATE_DIR / "moltbook_announcement.md").read_text()
    
    # Split into title and content
    lines = announcement.strip().split("\n")
    title = lines[0].strip("# ").strip()
    content = "\n".join(lines[1:]).strip()
    
    if dry_run:
        logger.info(f"[DRY-RUN] Would post to Moltbook s/tools:")
        logger.info(f"  Title: {title}")
        logger.info(f"  Content: {content[:120]}...")
    else:
        try:
            result = client.create_post(submolt="tools", title=title, content=content)
            logger.info(f"Moltbook post created: {result}")
        except Exception as e:
            logger.error(f"Failed to post on Moltbook: {e}")
    
    client.close()


def main():
    parser = argparse.ArgumentParser(description="Post CleanApp CLI launch announcements")
    parser.add_argument("--dry-run", action="store_true", help="Preview without posting")
    parser.add_argument("--bb-only", action="store_true", help="Only post to BB")
    parser.add_argument("--moltbook-only", action="store_true", help="Only post to Moltbook")
    args = parser.parse_args()
    
    load_dotenv()
    
    logger.info(f"Launch Announcements {'(DRY RUN)' if args.dry_run else '(LIVE)'}")
    logger.info("=" * 50)
    
    if not args.moltbook_only:
        post_bb_announcements(args.dry_run)
    
    if not args.bb_only:
        time.sleep(3)  # Pause between platforms
        post_moltbook_announcement(args.dry_run)
    
    logger.info("=" * 50)
    logger.info("Launch announcements complete.")


if __name__ == "__main__":
    main()
