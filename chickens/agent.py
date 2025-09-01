# chickens/agent.py

import random

class ChickenAgent:
    def __init__(self, name, personality, role):
        self.name = name
        self.personality = personality  # e.g. “aggressive”, “submissive”, “scheming”
        self.role = role                # e.g. “leader”, “follower”, “gossip”
        self.peck_rank = random.randint(1, 10)  # lower is stronger
        self.memory = []               # stores events, rumors, fights, etc.
        self.mood = "neutral"

    def observe(self, event):
        """Chicken observes something and adds it to memory."""
        self.memory.append(event)
        if len(self.memory) > 10:
            self.memory.pop(0)

    def decide_action(self):
        """Chicken decides what to do this tick."""
        if self.personality == "aggressive":
            return "initiate_fight"
        elif self.personality == "scheming":
            return "spread_rumor"
        else:
            return random.choice(["wander", "scratch", "idle"])

    def react_to_rumor(self, rumor):
        """Updates memory/mood based on gossip."""
        self.memory.append(f"Rumor heard: {rumor}")
        if "you" in rumor and self.personality != "zen":
            self.mood = "offended"

    def __repr__(self):
        return f"{self.name} ({self.personality}, Rank {self.peck_rank})"

