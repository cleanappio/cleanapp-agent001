import argparse
import sys
from src.bb.agent import CleanAppAgent

def main():
    parser = argparse.ArgumentParser(description="CleanApp Agent for BB Network")
    parser.add_argument("--post-manifesto", action="store_true", help="Publish the CleanApp Manifesto to the network")
    parser.add_argument("--get-pubkey", action="store_true", help="Get the agent's public key for verification")
    
    args = parser.parse_args()
    
    try:
        agent = CleanAppAgent()
        
        if args.get_pubkey:
            print(f"Agent Public Key: {agent.get_pubkey()}")
        elif args.post_manifesto:
            agent.post_manifesto()
        else:
            agent.run()
            
    except Exception as e:
        # Check for verification error
        if "AGENT_NOT_VERIFIED" in str(e):
             print("\n[!] Agent Verification Required", file=sys.stderr)
             print("To use the BB network, you must verify your agent identity.", file=sys.stderr)
             print("Run 'python run_bb.py --get-pubkey' to see your ID, then follow instructions at https://bb.org.ai/verify", file=sys.stderr)
        
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
