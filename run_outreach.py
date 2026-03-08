import argparse
import os
import sys
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

from src.memory import Memory
from src.outreach.engine import OutreachEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("outreach.log")
    ]
)
logger = logging.getLogger("cleanapp-outreach")

def main():
    parser = argparse.ArgumentParser(description="CleanApp Global Outreach Engine")
    parser.add_argument("--dry-run", action="store_true", help="Run without posting", default=False)
    parser.add_argument("--loop", action="store_true", help="Run continuously with sleep intervals")
    parser.add_argument("--interval", type=int, default=300, help="Sleep interval in seconds (default: 300)")
    parser.add_argument("--limit", type=int, default=1, help="Max posts per cycle (not fully implemented yet, relies on rate limiter)")

    args = parser.parse_args()
    load_dotenv()

    # Initialize Memory
    db_path = Path(os.getenv("DATA_DIR", "./data")) / "memory.sqlite"
    memory = Memory(db_path)

    # Initialize Engine
    engine = OutreachEngine(memory=memory, dry_run=args.dry_run)
    logger.info(f"Outreach Engine initialized (Dry Run: {args.dry_run})")

    try:
        if args.loop:
            logger.info(f"Starting continuous loop (Interval: {args.interval}s)")
            while True:
                engine.run_cycle()
                logger.info(f"Sleeping for {args.interval} seconds...")
                time.sleep(args.interval)
        else:
            engine.run_cycle()

    except KeyboardInterrupt:
        logger.info("Outreach Engine stopped by user.")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        memory.close()

if __name__ == "__main__":
    import os
    main()
