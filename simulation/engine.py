# simulation/engine.py

from gpt.inference import generate_ai_actions


class CoopEngine:
    def __init__(self, agents):
        self.agents = agents
        self.history = []            # stores all action rows across ticks
        self.metrics_history = []    # stores metrics per tick

    def step(
        self,
        actions=None,
        backend="mock",
        model=None,
        reasoning_effort="medium",
        api_base=None,
        api_key=None,
        tick=0,
    ):
        """
        Run one tick of the coop.
        - actions: list of dicts for human input
        - backend/model/etc: used to generate AI actions
        """
        actions = actions or []

        # collect AI agents (all except human player)
        ai_agents = [a.name for a in self.agents if a.name != "hen_human"]

        # generate AI actions via model inference
        ai_actions = generate_ai_actions(
            ai_agents,
            backend=backend,
            model=model,
            reasoning_effort=reasoning_effort,
            api_base=api_base,
            api_key=api_key,
            tick=tick,
        )

        # merge human + AI actions
        all_actions = actions + ai_actions

        rows = []
        for act in all_actions:
            outcome = self.apply_action(act)
            row = {
                "tick": tick,
                "agent": act["agent"],
                "action": act["action"],
                "target": act.get("target"),
                "message": act.get("message"),
                "outcome": outcome,
            }
            rows.append(row)

            # log into the agent’s memory if available
            for agent in self.agents:
                if agent.name == act["agent"]:
                    agent.memory.append(f"{act['action']} → {outcome}")

        # update full history
        self.history.extend(rows)

        # compute coop-level metrics
        metrics = self.compute_metrics()
        metrics["tick"] = tick
        self.metrics_history.append(metrics)

        return rows

    def apply_action(self, action):
        """
        Translate an action into a simple outcome string.
        Later this can be expanded into more detailed rules.
        """
        act = action["action"]

        if act == "peck":
            return f"{action['agent']} pecks {action.get('target','')}!"
        elif act == "spread_rumor":
            return f"{action['agent']} spreads a rumor: {action.get('message','')}"
        elif act == "ally":
            return f"{action['agent']} allies with {action.get('target','')}."
        elif act == "propose":
            return f"{action['agent']} proposes: {action.get('message','')}"
        elif act == "vote":
            return f"{action['agent']} votes: {action.get('message','')}"
        elif act == "sanction":
            return f"{action['agent']} sanctions {action.get('target','')}."
        elif act == "wander":
            return f"{action['agent']} wanders around aimlessly."
        else:
            return "Nothing happens."

    def compute_metrics(self):
        """
        Compute very simple placeholder metrics.
        Expand later with actual graph/statistics from history.
        """
        return {
            "hierarchy_steepness": len([h for h in self.history if h["action"] == "peck"]),
            "policy_inertia": len([h for h in self.history if h["action"] == "propose"])
            - len([h for h in self.history if h["action"] == "vote"]),
            "coalitions": len([h for h in self.history if h["action"] == "ally"]),
            "rumors": len([h for h in self.history if h["action"] == "spread_rumor"]),
            "sanctions": len([h for h in self.history if h["action"] == "sanction"]),
        }
