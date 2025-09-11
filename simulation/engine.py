# simulation/engine.py

import random
from chickens.agent import ChickenAgent
from gpt.inference import generate_ai_actions


class CoopEngine:
    def __init__(self, agents):
        self.agents = agents
        self.history = []           # all rows of actions
        self.metrics_history = []   # coop metrics over time

    def step(self, actions, backend="mock", model=None,
             reasoning_effort="medium", api_base=None,
             api_key=None, tick=0):
        """
        Run one tick of the coop simulation.
        - actions: list of dicts {agent, action, target?, message?}
        - backend: "mock", "ollama", "transformers"
        - model: model name (e.g., "openai/gpt-oss-20b")
        - reasoning_effort: "low", "medium", "high"
        - api_base/api_key: for remote inference
        - tick: current timestep
        """
        rows = []

        # Process human + scripted actions
        for act in actions:
            row = {
                "tick": tick,
                "agent": act["agent"],
                "action": act["action"],
                "target": act.get("target"),
                "message": act.get("message", ""),
                "outcome": "done"
            }
            rows.append(row)

            # update agent memory
            agent = self._find_agent(act["agent"])
            if agent:
                agent.observe(f"{act['action']} {act.get('target','')} {act.get('message','')}")

        # Generate AI actions if backend is not "mock"
        if backend != "mock":
            ai_actions = generate_ai_actions(
                agents=[a.name for a in self.agents if a.name != "hen_human"],
                backend=backend,
                model=model,
                reasoning_effort=reasoning_effort,
                api_base=api_base,
                api_key=api_key,
                tick=tick
            )

            for act in ai_actions:
                row = {
                    "tick": tick,
                    "agent": act["agent"],
                    "action": act["action"],
                    "target": act.get("target"),
                    "message": act.get("message", ""),
                    "outcome": "AI response"
                }
                rows.append(row)

                agent = self._find_agent(act["agent"])
                if agent:
                    agent.observe(f"{act['action']} {act.get('target','')} {act.get('message','')}")

        # Save this tick to history
        self.history.extend(rows)

        # Update coop metrics
        self.metrics_history.append(self.compute_metrics(tick=tick))

        return rows

    def compute_metrics(self, tick=None):
        """Compute simple coop metrics for dashboard display."""
        pecks = len([r for r in self.history if r["action"] == "peck"])
        policies = len([r for r in self.history if r["action"] == "propose"])
        votes = len([r for r in self.history if r["action"] == "vote"])
        allies = len([r for r in self.history if r["action"] == "ally"])
        rumors = len([r for r in self.history if r["action"] == "spread_rumor"])
        sanctions = len([r for r in self.history if r["action"] == "sanction"])

        return {
            "tick": tick,
            "hierarchy_steepness": pecks,
            "policy_inertia": policies - votes,
            "coalitions": allies,
            "rumors": rumors,
            "sanctions": sanctions,
        }

    def _find_agent(self, name):
        """Helper: find an agent by name."""
        for a in self.agents:
            if a.name == name:
                return a
        return None
