# simulation/engine.py

import os
import csv
import json
import random
from typing import List, Dict, Any

from chickens.agent import ChickenAgent


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
LOG_PATH = os.path.join(DATA_DIR, "log.csv")
MEMORY_PATH = os.path.join(DATA_DIR, "memory_snapshots.json")


class CoopEngine:
    def __init__(self, agents: List[ChickenAgent], max_ticks: int = 50, log_interval: int = 5):
        self.agents = agents
        self.tick = 0
        self.max_ticks = max_ticks
        self.log_interval = log_interval

        # Ensure data dir exists
        os.makedirs(DATA_DIR, exist_ok=True)

        # Reset logs
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["tick", "agent", "action", "target", "message", "result"])

    # -----------------------------
    # Core loop
    # -----------------------------
    def run(self, backend: str = "mock", verbose: bool = True):
        for t in range(self.max_ticks):
            self.tick = t
            if verbose:
                print(f"\n=== Tick {t} ===")

            for agent in self.agents:
                # Build context
                context = {"tick": t, "backend": backend}

                action = agent.decide_action(context=context)

                result = self.apply_action(agent, action)
                self.log_action(agent, action, result)

                if verbose:
                    print(f"{agent.name}: {action} -> {result}")

            # Save memory snapshots periodically
            if t % self.log_interval == 0:
                self.save_memory_snapshots()

    # -----------------------------
    # Apply action effects
    # -----------------------------
    def apply_action(self, agent: ChickenAgent, action: Dict[str, Any]) -> str:
        """Apply action consequences (simplified version)."""
        act = action.get("action", "idle")
        target_name = action.get("target")
        msg = action.get("message", "")

        if act == "initiate_fight":
            if target_name:
                # Simple dominance check
                target = self._find_agent(target_name)
                if target and agent.peck_rank < target.peck_rank:
                    outcome = "win"
                    agent.mood = "proud"
                    target.mood = "hurt"
                else:
                    outcome = "lose"
                    agent.mood = "hurt"
                return outcome
            return "no_target"

        elif act == "spread_rumor":
            for other in self.agents:
                if other != agent:
                    other.react_to_rumor(msg, source=agent.name, tick=self.tick)
            return "rumor_spread"

        elif act == "ally":
            return "alliance_formed"

        elif act == "propose":
            return "proposal_submitted"

        elif act == "vote":
            return "vote_cast"

        elif act == "audit":
            return "rumor_checked"

        elif act == "sanction":
            return "sanction_applied"

        else:
            return "noop"

    # -----------------------------
    # Logging
    # -----------------------------
    def log_action(self, agent: ChickenAgent, action: Dict[str, Any], result: str):
        with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                self.tick,
                agent.name,
                action.get("action"),
                action.get("target"),
                action.get("message"),
                result,
            ])

    def save_memory_snapshots(self):
        data = {}
        for agent in self.agents:
            data[agent.name] = agent.memory
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # -----------------------------
    # Helpers
    # -----------------------------
    def _find_agent(self, name: str) -> ChickenAgent:
        for a in self.agents:
            if a.name == name:
                return a
        return None


# -----------------------------
# Quick test
# -----------------------------
if __name__ == "__main__":
    # Create some chickens
    agents = [
        ChickenAgent("hen_1", "aggressive", "leader"),
        ChickenAgent("hen_2", "scheming", "follower"),
        ChickenAgent("hen_3", "submissive", "gossip"),
        ChickenAgent("hen_4", "zen", "follower"),
    ]

    coop = CoopEngine(agents, max_ticks=10, log_interval=2)
    coop.run(backend="mock", verbose=True)

    print(f"\nLog written to {LOG_PATH}")
    print(f"Memory snapshots saved to {MEMORY_PATH}")
