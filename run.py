# run.py

import argparse
import random
from chickens.agent import ChickenAgent
from simulation.engine import CoopEngine


def build_flock(num_agents: int = 4, use_llm: bool = False):
    """Create a flock of chickens with varied personalities and roles."""
    personalities = ["aggressive", "scheming", "submissive", "zen"]
    roles = ["leader", "follower", "gossip", "follower"]

    agents = []
    for i in range(num_agents):
        name = f"hen_{i+1}"
        personality = random.choice(personalities)
        role = roles[i % len(roles)]
        agents.append(ChickenAgent(name, personality, role, use_llm=use_llm))
    return agents


def main():
    parser = argparse.ArgumentParser(description="Run Clucktocracy: the chicken coop simulation")
    parser.add_argument("--episodes", type=int, default=1, help="Number of episodes to simulate")
    parser.add_argument("--ticks", type=int, default=20, help="Number of ticks per episode")
    parser.add_argument("--backend", type=str, default="mock",
                        choices=["mock", "ollama", "transformers"],
                        help="Backend to use for chicken brains")
    parser.add_argument("--num_agents", type=int, default=4, help="Number of chickens in the flock")
    parser.add_argument("--ollama-model", type=str, default="gpt-oss-20b", help="Ollama model name")
    parser.add_argument("--hf-model-id", type=str, default=None, help="HF model id (e.g., openmodel/gpt-oss-20b)")
    parser.add_argument("--verbose", action="store_true", help="Print detailed simulation output")

    args = parser.parse_args()

    for ep in range(args.episodes):
        print(f"\n=== Episode {ep+1}/{args.episodes} ===")

        # Build flock
        use_llm = args.backend in ["ollama", "transformers"]
        flock = build_flock(num_agents=args.num_agents, use_llm=use_llm)

        # Run engine
        coop = CoopEngine(flock, max_ticks=args.ticks, log_interval=5)
        coop.run(backend=args.backend, verbose=args.verbose)

    print("\nSimulation complete.")
    print("Logs: data/log.csv")
    print("Memories: data/memory_snapshots.json")


if __name__ == "__main__":
    main()
