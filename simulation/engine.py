# simulation/engine.py
"""
CoopEngine — simulation driver for Clucktocracy.
Manages agents, tick loop, history, metrics, and calls GPT inference backends.
"""

import os
import csv
import json
from typing import List, Dict, Any

from chickens.agent import ChickenAgent
from gpt.inference import generate_ai_actions

# Paths for logging + memories
LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "coop_log.csv")
MEM_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "memories.json")


class CoopEngine:
    def __init__(self, agents: List[ChickenAgent], max_ticks: int = 200, log_interval: int = 5):
        self.agents = agents
        self.history: List[Dict[str, Any]] = []
        self.metrics_history: List[Dict[str, Any]] = []
        self.tick = 0
        self.max_ticks = max_ticks
        self.log_interval = log_interval

        # Reset files
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["tick", "agent", "action", "target", "message", "outcome"])
            writer.writeheader()

        with open(MEM_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)

    # ------------------------------------------------------------------
    def step(
        self,
        actions: List[Dict[str, Any]] = None,
        backend: str = "mock",
        model: str = "openai/gpt-oss-20b",
        reasoning_effort: str = "medium",
        api_base: str = None,
        api_key: str = None,
        tick: int = 0,
        constitution: dict = None,
        human_override: dict = None,
    ) -> List[Dict[str, Any]]:
        """
        Advance one tick of the coop simulation.
        - actions: optional list of human or scripted actions
        - backend/model/reasoning/api_base/api_key: inference config
        - human_override: dict with one manual action
        """
        if actions is None:
            actions = []

        # Add explicit human action override
        if human_override and human_override.get("action") != "IDLE":
            actions.append({
                "tick": tick,
                "agent": "hen_human",
                "action": human_override.get("action", "IDLE"),
                "target": human_override.get("target"),
                "message": human_override.get("message", ""),
                "outcome": "submitted",
            })

        # Call GPT inference to get AI moves
        ai_actions = generate_ai_actions(
            self.agents,
            tick=tick,
            backend=backend,
            model=model,
            reasoning_effort=reasoning_effort,
            api_base=api_base,
            api_key=api_key,
        )

        # Merge human + AI
        all_actions = actions + ai_actions

        # Save into history
        self.history.extend(all_actions)
        self.tick = tick

        # Append metrics snapshot
        metrics = self.compute_metrics()
        metrics["tick"] = tick
        self.metrics_history.append(metrics)

        # Write to log CSV
        with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["tick", "agent", "action", "target", "message", "outcome"])
            for row in all_actions:
                writer.writerow(row)

        # Update memories
        mems = self._load_memories()
        for act in all_actions:
            mems.setdefault(act["agent"], []).append({
                "tick": act["tick"],
                "event": f"{act['agent']} did {act['action']} → {act.get('message','')}"
            })
        with open(MEM_PATH, "w", encoding="utf-8") as f:
            json.dump(mems, f, indent=2)

        return all_actions

    # ------------------------------------------------------------------
    def compute_metrics(self) -> Dict[str, Any]:
        """Compute coop-level indicators."""
        pecks = sum(1 for h in self.history if h["action"].lower() in ("peck", "initiate_fight"))
        rumors = sum(1 for h in self.history if h["action"].lower() in ("gossip", "spread_rumor"))
        sanctions = sum(1 for h in self.history if h["action"].lower() == "sanction")
        props = sum(1 for h in self.history if h["action"].lower() == "propose")
        votes = sum(1 for h in self.history if h["action"].lower() == "vote")
        allies = sum(1 for h in self.history if h["action"].lower() == "ally")

        return {
            "hierarchy_steepness": round(pecks / max(1, len(self.history)), 3),
            "policy_inertia": props - votes,
            "coalitions": allies,
            "rumors": rumors,
            "sanctions": sanctions,
        }

    # ------------------------------------------------------------------
    def save_state(self):
        """Optionally persist engine state (stub)."""
        pass

    def _load_memories(self) -> Dict[str, Any]:
        if not os.path.exists(MEM_PATH):
            return {}
        with open(MEM_PATH, encoding="utf-8") as f:
            return json.load(f)
