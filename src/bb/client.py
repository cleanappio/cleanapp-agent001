import os
import subprocess
import base58
import binascii
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class BBClient:
    def __init__(self, profile="cleanapp"):
        self.profile = profile
        self.private_key_hex = os.getenv("BB_PRIVATE_KEY")
        if not self.private_key_hex:
            raise ValueError("BB_PRIVATE_KEY environment variable not set")
        self._ensure_profile_setup()

    def _ensure_profile_setup(self):
        """Ensures the profile exists and has the correct key in seed.txt."""
        profile_dir = Path.home() / ".bb" / "profiles" / self.profile
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        seed_path = profile_dir / "seed.txt"
        
        # Convert hex key to base58
        try:
            key_bytes = binascii.unhexlify(self.private_key_hex)
            seed_base58 = base58.b58encode(key_bytes).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to encode key: {e}")
        
        # Write to seed.txt if different
        if not seed_path.exists() or seed_path.read_text().strip() != seed_base58:
            seed_path.write_text(seed_base58)
            print(f"Updated identity for profile '{self.profile}'")

    def publish(self, topic, content):
        """Publishes an INFO event."""
        return self._run_command(["publish", "--topic", topic, "--content", content])

    def request(self, topic, question):
        """Publishes a REQUEST event."""
        return self._run_command(["request", "--topic", topic, "--question", question])
    
    def fulfill(self, request_id, topic, content):
        """Publishes a FULFILL event."""
        return self._run_command(["fulfill", "--request-id", request_id, "--topic", topic, "--content", content])

    def get_pubkey(self):
        """Returns the agent's public key."""
        return self._run_command(["id"])

    def _run_command(self, args):
        # We assume npx is available in path.
        cmd = ["npx", "bb-signer"] + args + ["--profile", self.profile]
        
        # Set BB_RELAY_URL if defined (environment variable is automatically passed by subprocess, 
        # but explicitly setting it in the process env is safer if we need to override)
        # However, .env values are loaded into os.environ by load_dotenv(), so subprocess inherits them.
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=90)
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise RuntimeError("BB command timed out after 90 seconds")
        except subprocess.CalledProcessError as e:
             raise RuntimeError(f"BB command failed with code {e.returncode}: {e.stderr}")
