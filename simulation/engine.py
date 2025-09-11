import random

class Engine:
    def __init__(self, agents):
        self.agents = agents
        self.tick = 0
        self.history = []  # stores all actions
        self.metrics_history = []  # stores metrics per tick

    def step(self):
        """Advance the simulation by one tick and record actions."""
        rows = []
        for agent in self.agents:
            action = agent.decide_action()
            row = {
                "tick": self.tick,
                "agent": agent.name,
                "action": action,
                "target": random.choice([a.name for a in self.agents if a != agent]) if action in ["peck", "spread_rumor", "ally", "sanction"] else None,
            }
            self.history.append(row)
            rows.append(row)

        # update tick counter
        self.tick += 1

        # record metrics snapshot
        self.metrics_history.append(self.compute_metrics())
        return rows

    def compute_metrics(self):
        """Return summary metrics for Coop dashboard at current tick."""
        metrics = {
            "tick": self.tick,
            "hierarchy_steepness": 0,
            "policy_inertia": 0,
            "coalitions": 0,
            "rumors": 0,
            "sanctions": 0,
        }

        # filter actions
        pecks = [h for h in self.history if h["action"] == "peck"]
        rumors = [h for h in self.history if h["action"] == "spread_rumor"]
        allies = [h for h in self.history if h["action"] == "ally"]
        sanctions = [h for h in self.history if h["action"] == "sanction"]
        proposals = [h for h in self.history if h["action"] == "propose"]
        votes = [h for h in self.history if h["action"] == "vote"]

        # Simple heuristics
        metrics["hierarchy_steepness"] = round(len(pecks) / max(1, self.tick), 2)
        metrics["policy_inertia"] = len(proposals) - len(votes)
        metrics["coalitions"] = len(allies)
        metrics["rumors"] = len(rumors)
        metrics["sanctions"] = len(sanctions)

        return metrics
