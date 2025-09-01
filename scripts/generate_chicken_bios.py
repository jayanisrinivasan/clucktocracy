# scripts/generate_chicken_bios.py

import json
import os

CHICKEN_BIOS_FILE = "data/memory_snapshots.json"

# Predefined chicken personalities
def generate_static_bios():
    return [
        {"name": "Cluck Norris", "personality": "aggressive", "role": "fighter"},
        {"name": "Sister Beakrah", "personality": "prophet", "role": "leader"},
        {"name": "Hen Solo", "personality": "scheming", "role": "gossip"},
        {"name": "Feather Locklear", "personality": "pacifist", "role": "follower"},
        {"name": "Eggward Snowden", "personality": "zen", "role": "outsider"},
    ]

def save_chickens(bios):
    os.makedirs("data", exist_ok=True)
    with open(CHICKEN_BIOS_FILE, "w") as f:
        json.dump(bios, f, indent=2)
    print(f"[✓] Chicken bios saved to {CHICKEN_BIOS_FILE}")

def load_chickens():
    from chickens.agent import ChickenAgent
    with open(CHICKEN_BIOS_FILE, "r") as f:
        raw = json.load(f)
    return [ChickenAgent(**entry) for entry in raw]

# Run this script manually to seed bios
if __name__ == "__main__":
    bios = generate_static_bios()
    save_chickens(bios)

