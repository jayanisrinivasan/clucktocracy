import random

class ChickenAgent:
    def __init__(self, name, personality="neutral", role="npc"):
        self.name = name
        self.personality = personality
        self.role = role
        self.memory = []
        self.reputation = 100
        self.trust_coins = 10

    def act(self, tick, context=None):
        """
        Default NPC actions (simple random baseline).
        Human player will override via UI.
        """
        actions = ["peck", "spread_rumor", "propose", "vote", "ally", "sanction", "wander"]
        action = random.choice(actions)
        target = None
        if action in ["peck", "spread_rumor", "ally", "sanction"]:
            target = f"hen_{random.randint(1,4)}"

        return {
            "tick": tick,
            "agent": self.name,
            "action": action,
            "target": target,
            "message": ""
        }

    def remember(self, event: str):
        self.memory.append(event)
        if len(self.memory) > 10:
            self.memory.pop(0)
