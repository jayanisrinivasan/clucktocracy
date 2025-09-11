# chickens/agent.py

import random
import uuid
from typing import Dict, Any, Optional

# Import your LLM backend wrapper (we’ll make sure gpt/inference.py defines generate_action)
try:
    from gpt.inference import generate_action
except ImportError:
    generate_action = None


class ChickenAgent:
    def __init__(self, name: str, personality: str, role: str, use_llm: bool = False):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.personality = personality  # e.g. "aggressive", "submissive", "scheming"
        self.role = role                # e.g. "leader", "follower", "gossip"
        self.peck_rank = random.randint(1, 10)  # lower is stronger
        self.mood = "neutral"
        self.use_llm = use_llm

        # Event memory (each entry is a dict)
        self.memory: list[Dict[str, Any]] = []

        # Stable personality traits for richer emergent behavior
        self.traits = {
            "dominance": random.uniform(0, 1),
            "agreeableness": random.uniform(0, 1),
            "risk": random.uniform(0, 1),
        }

    # -----------------------------
    # Memory
    # -----------------------------
    def observe(self, event: str, source: Optional[str] = None, credibility: float = 1.0, tick: int = 0):
        """Chicken observes something and stores it with metadata."""
        entry = {
            "event": event,
            "source": source,
            "credibility": credibility,
            "tick": tick,
        }
        self.memory.append(entry)
        if len(self.memory) > 50:
            self.memory.pop(0)

    # -----------------------------
    # Decision-making
    # -----------------------------
    def decide_action(self, context: Optional[dict] = None) -> Dict[str, Any]:
        """
        Decide what to do this tick.
        Returns a structured dict {action, target, message, ...}.
        """
        if self.use_llm and generate_action is not None:
            try:
                return generate_action(self, context or {})
            except Exception as e:
                # Fail gracefully to heuristics if LLM call fails
                return {"action": "idle", "message": f"(LLM error: {e})"}

        # Heuristic / mock fallback
        if self.personality == "aggressive":
            return {"action": "initiate_fight", "target": None, "message": f"{self.name} picks a fight!"}
        elif self.personality == "scheming":
            target = f"hen_{random.randint(1,5)}"
            rumor = f"I saw {target} stealing seeds!"
            return {"action": "spread_rumor", "target": target, "message": rumor}
        else:
            return {"action": random.choice(["wander", "scratch", "idle"]), "target": None, "message": ""}

    # -----------------------------
    # Gossip / Rumors
    # -----------------------------
    def react_to_rumor(self, rumor: str, source: Optional[str] = None, tick: int = 0):
        """Update memory/mood based on gossip."""
        self.observe(f"Rumor heard: {rumor}", source=source, credibility=0.5, tick=tick)
        if "you" in rumor and self.personality != "zen":
            self.mood = "offended"

    # -----------------------------
    # Representation
    # -----------------------------
    def __repr__(self):
        return (
            f"{self.name} (Role={self.role}, "
            f"Personality={self.personality}, "
            f"Rank={self.peck_rank}, Mood={self.mood})"
        )
