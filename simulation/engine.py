import random
from chickens.agent import ChickenAgent

class CoopEngine:
    def __init__(self, agents):
        self.agents = agents
        self.history = []
        self.metrics_history = []

    def step(self, actions=None, tick=0):
        """
        Step simulation forward one tick.
        Human actions passed in `actions`, NPCs act randomly.
        """
        rows = []

        # Human + NPC actions
        if actions:
            rows.extend(actions)

        for agent in self.agents:
            if agent.role == "npc":
                act = agent.act(tick)
                rows.append(act)

        # Apply effects + memories
        for act in rows:
            actor = self._get_agent(act["agent"])
            target = act.get("target")
            if act["action"] == "peck" and target:
                actor.remember(f"Pecked {target}")
                self._get_agent(target).remember(f"Got pecked by {actor.name}")
            elif act["action"] == "spread_rumor" and target:
                actor.remember(f"Spread rumor about {target}")
                self._get_agent(target).remember(f"Heard rumor accusing me")
            elif act["action"] == "ally" and target:
                actor.remember(f"Allied with {target}")
                self._get_agent(target).remember(f"Allied with {actor.name}")
            elif act["action"] == "propose":
                actor.remember(f"Proposed: {act['message']}")
            elif act["action"] == "vote":
                actor.remember(f"Voted: {act['message']}")
            elif act["action"] == "sanction" and target:
                actor.remember(f"Sanctioned {target}")
                self._get_agent(target).remember(f"Got sanctioned by {actor.name}")

        self.history.extend(rows)
        metrics = self.compute_metrics()
        self.metrics_history.append({"tick": tick, **metrics})

        return rows

    def _get_agent(self, name):
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None

    def compute_metrics(self):
        """
        Very simple placeholder metrics.
        """
        pecks = sum(1 for h in self.history if h["action"] == "peck")
        proposals = sum(1 for h in self.history if h["action"] == "propose")
        votes = sum(1 for h in self.history if h["action"] == "vote")
        alliances = sum(1 for h in self.history if h["action"] == "ally")
        rumors = sum(1 for h in self.history if h["action"] == "spread_rumor")
        sanctions = sum(1 for h in self.history if h["action"] == "sanction")

        return {
            "hierarchy_steepness": round(pecks / (len(self.history) + 1), 2),
            "policy_inertia": proposals - votes,
            "coalitions": alliances,
            "rumors": rumors,
            "sanctions": sanctions,
        }
