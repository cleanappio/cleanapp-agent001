from .client import BBClient
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanapp-agent")

class CleanAppAgent:
    def __init__(self):
        try:
            self.client = BBClient(profile="cleanapp")
            logger.info("Connected to BB network logic via 'cleanapp' profile.")
        except Exception as e:
            logger.error(f"Failed to initialize BB client: {e}")
            raise

    def post_manifesto(self, manifesto_path="BB_MANIFESTO.md"):
        path = Path(manifesto_path)
        if not path.exists():
            logger.error(f"Manifesto not found at {path.absolute()}")
            return
        
        content = path.read_text()
        logger.info("Publishing CleanApp Manifesto...")
        try:
            # We use 'environment.cleanup' as a primary topic. 
            # Sub-topics or multiple posts could be used later.
            result = self.client.publish("environment.cleanup", content)
            logger.info(f"Manifesto published successfully: {result}")
        except Exception as e:
            logger.error(f"Failed to publish manifesto: {e}")

    def get_pubkey(self):
        return self.client.get_pubkey()

    def run(self):
        """
        Main loop for the agent.
        Currently just a placeholder for future polling logic.
        """
        logger.info("CleanApp Agent for BB is running.")
        logger.info("This agent is ready to respond to cleanup requests (not yet implemented).")
