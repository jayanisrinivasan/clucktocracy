# simulation/engine.py

import random
import csv
from chickens.agent import ChickenAgent
from scripts.generate_chicken_bios import load_chickens
from gpt.inference import query_gpt
from datetime import datetime

# Path to data log
LOG_FILE = "data/log.csv"

# Load agents at start
chickens = load_chickens()

def run_simulation(ticks=10):
    for t in range(ticks):
        print(f"\n=== Tick {t+1} ===")
        for chicken in chickens:
            action = chicken.decide_action()
            log_event = f"{chicken.name} decided to {action}"

            if action == "initiate_fight":
                opponent = random.choice([c for c in chickens if c != chicken])
                result = resolve_fight(chicken, opponent)
                log_event = result

            elif action == "spread_rumor":
                rumor = query_gpt(f"Generate a juicy farmyard rumor involving {chicken.name}")
                targets = random.sample([c for c in chickens if c != chicken], 2)
                for target in targets:
                    target.react_to_rumor(rumor)
                log_event = f"{chicken.name} spread a rumor: '{rumor.strip()}'"

            log_to_csv(log_event)
            print(log_event)

def resolve_fight(c1, c2):
    if c1.peck_rank < c2.peck_rank:
        winner, loser = c1, c2
    else:
        winner, loser = c2, c1

    # Slightly adjust peck ranks to simulate shifting dominance
    loser.peck_rank += 1
    winner.peck_rank = max(1, winner.peck_rank - 1)

    return f"{winner.name} pecked {loser.name}. Pecking order adjusted."

def log_to_csv(event):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", newline='') as file:
        writer = csv.writer(file)
        writer.writerow([now, event])

