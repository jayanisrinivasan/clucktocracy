# chickens/agent.py
"""
ChickenAgent definition for Clucktocracy.
Agents can be human-controlled (hen_human) or AI-controlled (GPT-OSS, Ollama, Transformers).
"""

import random
from typing import List, Dict, Any, Optional

# Import the inference wrapper
from gpt.inference import generate_action_for_agent


class ChickenAgent:
    def __init__(self, name: str, personality: str, role: str):
        """
        Args:
            name: agent id string (e.g., "hen_2")
            personality: one of {"aggressive","submissive","scheming","curious","zen",...}
            role: freeform role label (e.g., "leader","follower","gossip","reformer")
        """
        self.name: str = name
        self.personality: str = personality
        self.role: str = role
        self.peck_rank: int = random.randint(1, 10)  # lower = stronger in fights
        self.memory: List[Dict[str, Any]] = []
        self.mood: str = "neutral"

    # ---------------------------
    # Core behaviors
    # ---------------------------
    def observe(self, event: Any) -> None:
        """
        Store a memory event (string or dict).
        Keeps memory bounded to ~24 entries.
        """
        if isinstance(event, str):
            event = {"event": event}
        event.setdefault("tick", None)
        self.memory.append(event)
        if len(self.memory) > 24:
            self.memory.pop(0)

    def decide_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decide what to do this tick.
        - If backend == "mock": use heuristic/random behavior.
        - Otherwise: call inference.generate_action_for_agent().
        Returns an action dict:
            { "action": str, "target": Optional[str], "message": str, "confidence": float }
        """
        backend = context.get("backend", "mock")
        model = context.get("model", "openai/gpt-oss-20b")
        reasoning_effort = context.get("reasoning_effort", "medium")
        api_base = context.get("api_base", "http://localhost:8000/v1")
        api_key = context.get("api_key", "test")

        if backend == "mock":
            # Toy personality-driven rule
            if self.personality == "aggressive":
                action = "PECK"
                msg = "dominance strike"
            elif self.personality == "scheming":
                action = "GOSSIP"
                msg = "plotting behind feathers"
            elif self.personality == "submissive":
                action = "ALLY"
                msg = "seeks protection"
            else:
                action = random.choice(["FORAGE","SCRATCH","IDLE"])
                msg = "wanders around"

            result = {
                "action": action,
                "target": None,
                "message": msg,
                "confidence": round(random.uniform(0.5, 0.9), 2),
            }
            self.observe(f"{self.name} mock-act: {result['action']}")
            return result

        # Otherwise, call GPT-OSS inference
        action = generate_action_for_agent(
            agent_name=self.name,
            personality=self.personality,
            role=self.role,
            context=context,
            backend=backend,
            model=model,
            reasoning_effort=reasoning_effort,
            api_base=api_base,
            api_key=api_key,
        )
        # Record trace
        self.observe({"event": f"{self.name} -> {action.get('action')} ({action.get('message','')[:40]})"})
        return action

    def react_to_rumor(self, rumor: str, source: Optional[str] = None, tick: Optional[int] = None) -> None:
        """
        React to a rumor (basic mood update + memory).
        Supports both simple signature (rumor) and rich signature (rumor, source, tick).
        """
        event = f"Rumor heard: {rumor}"
        if source:
            event += f" (from {source})"
        if tick is not None:
            event += f" [t={tick}]"

        self.memory.append({"event": event, "tick": tick})
        if len(self.memory) > 24:
            self.memory.pop(0)

        # Mood reaction: non-zen chickens get offended if targeted
        if self.personality != "zen" and self.name in rumor:
            self.mood = "offended"

    # ---------------------------
    # Representation
    # ---------------------------
    def __repr__(self) -> str:
        return f"{self.name} ({self.personality}, {self.role}, Rank {self.peck_rank})"
