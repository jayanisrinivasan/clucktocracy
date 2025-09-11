# scripts/generate_chicken_bios.py

"""
Generate chicken bios for the Clucktocracy simulation.
Can run in mock mode (random) or using GPT-OSS models via inference.py.
"""

import argparse
import random
import json
import os

from chickens.agent import ChickenAgent
from gpt.inference import generate_action


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
BIO_PATH = os.path.join(DATA_DIR, "chicken_bios.json")


def random_bio(name: str) -> dict:
    personalities = ["aggressive", "scheming", "submissive", "zen", "curious"]
    roles = ["leader", "follower", "gossip", "watcher"]

    return {
        "name": name,
        "personality": random.choice(personalities),
        "role": random.choice(roles),
        "backstory": random.choice([
            "Raised near the grain silo, ambitious and bold.",
            "Once a quiet chick, now seeks influence.",
            "Prefers peace but won’t back down when challenged.",
            "Wanders the coop spreading whispers of intrigue."
        ])
    }


def generate_bios(num: int = 4, backend: str = "mock") -> list[dict]:
    bios = []
    for i in range(num):
        name = f"hen_{i+1}"
        if backend == "mock":
            bio = random_bio(name)
        else:
            # Use GPT backend to invent a backstory
            context = {"backend": backend}
            fake_agent = ChickenAgent(name, "scheming", "follower")
            action = generate_action(fake_agent, context)
            bio = {
                "name": name,
                "personality": random.choice(["aggressive", "scheming", "submissive", "zen"]),
                "role": random.choice(["leader", "follower", "gossip"]),
                "backstory": action.get("message", "A mysterious chicken with untold stories.")
            }
        bios.append(bio)

    with open(BIO_PATH, "w", encoding="utf-8") as f:
        json.dump(bios, f, indent=2)

    return bios


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate chicken bios")
    parser.add_argument("--num", type=int, default=4, help="Number of chickens")
    parser.add_argument("--backend", type=str, default="mock",
                        choices=["mock", "ollama", "transformers"],
                        help="Backend to use for backstory generation")
    args = parser.parse_args()

    bios = generate_bios(args.num, backend=args.backend)
    print(f"Generated {len(bios)} bios → {BIO_PATH}")
