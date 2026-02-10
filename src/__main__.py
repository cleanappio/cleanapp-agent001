"""CleanApp Agent001 — Entry point."""

import argparse
import json
import logging
import sys

from .config import Config
from .agent import Agent


def main():
    parser = argparse.ArgumentParser(description="CleanApp Moltbook Agent")
    parser.add_argument("--dry-run", action="store_true", default=None,
                        help="Run without posting (overrides .env)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose logging")
    args = parser.parse_args()

    # Load config
    config = Config.from_env()

    # CLI overrides
    if args.dry_run is True:
        config = Config(
            moltbook_api_key=config.moltbook_api_key,
            gemini_api_key=config.gemini_api_key,
            dry_run=True,
            log_level="DEBUG" if args.verbose else config.log_level,
            max_posts_per_day=config.max_posts_per_day,
            max_comments_per_day=config.max_comments_per_day,
            relevance_threshold=config.relevance_threshold,
            data_dir=config.data_dir,
        )

    # Setup logging
    log_level = "DEBUG" if args.verbose else config.log_level
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger(__name__)
    logger.info("CleanApp Agent001 starting...")
    logger.info("Mode: %s", "DRY RUN" if config.dry_run else "LIVE")

    # Validate config
    errors = config.validate()
    if errors:
        for e in errors:
            logger.error("Config error: %s", e)
        if not config.dry_run:
            logger.error("Cannot run in live mode with config errors. Exiting.")
            sys.exit(1)
        else:
            logger.warning("Running in dry-run with config warnings.")

    # Run agent cycle
    agent = Agent(config)
    try:
        summary = agent.run_cycle()

        # Print summary
        print("\n" + "=" * 60)
        print("ENGAGEMENT PLAN SUMMARY")
        print("=" * 60)
        print(f"Mode: {'DRY RUN' if config.dry_run else 'LIVE'}")
        print(f"Daily posts: {summary['daily_posts']}/{config.max_posts_per_day}")
        print(f"Daily comments: {summary['daily_comments']}/{config.max_comments_per_day}")
        print()

        for mode, totals in summary.get("totals", {}).items():
            mode_label = {
                "intake": "Intake (Trashformer)",
                "analysis": "Analysis (Moltfold)",
                "distribution": "Distribution (Antenna)",
            }.get(mode, mode)
            print(f"--- {mode_label} ---")
            print(f"  Found: {totals['found']}")
            print(f"  Engaged: {totals['engaged']}")
            print(f"  Skipped: {totals['skipped']}")
            print(f"  Queued: {totals['queued']}")
            print()

        # Print engagement details
        opportunities = summary.get("opportunities", {})
        engaged_items = []
        for mode, opps in opportunities.items():
            for o in opps:
                if o.get("action") == "engaged":
                    engaged_items.append(o)

        if engaged_items:
            print("--- Engagements ---")
            for item in engaged_items:
                print(f"  [{item['mode']}] {item['title'][:60]}")
                print(f"    Submolt: {item['submolt']} | Author: {item['author']}")
                print(f"    Relevance: {item['relevance']:.2f}")
                if "response" in item:
                    preview = item["response"][:120].replace("\n", " ")
                    print(f"    Response: {preview}...")
                print()
        else:
            print("No engagements this cycle.")

        print("=" * 60)

    finally:
        agent.close()


if __name__ == "__main__":
    main()
