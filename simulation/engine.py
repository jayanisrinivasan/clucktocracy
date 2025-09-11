import random
from gpt.inference import generate_ai_actions

VALID_ACTIONS = ["wander", "peck", "spread_rumor", "propose", "vote", "ally", "sanction"]

class CoopEngine:
    def __init__(self, agents):
        self.agents = agents
        self.history = []

    # -----------------------------
    # Core simulation step
    # -----------------------------
    def step(self, actions=None, backend="mock", model="openai/gpt-oss-20b",
             reasoning_effort="medium", api_base=None, api_key=None, tick=0):
        """
        Run one tick of the coop simulation.
        - actions: list of human or scripted actions
        - backend: "mock", "ollama", "transformers"
        - model: model name
        - reasoning_effort: low/medium/high
        - api_base/api_key: for Ollama
        """

        rows = []

        # -----------------------------
        # 1) Process human actions
        # -----------------------------
        if actions:
            for act in actions:
                rows.append({
                    "tick": tick,
                    "agent": act["agent"],
                    "action": act["action"],
                    "outcome": "human",
                    "message": act.get("message", ""),
                })
                self._update_memory(act["agent"], act)

        # -----------------------------
        # 2) Generate AI actions
        # -----------------------------
        ai_outputs = generate_ai_actions(
            self.agents,
            backend=backend,
            model=model,
            reasoning_effort=reasoning_effort,
            api_base=api_base,
            api_key=api_key,
            tick=tick
        )

        # -----------------------------
        # 3) Parse and normalize actions
        # -----------------------------
        for out in ai_outputs:
            raw_text = (out.get("message") or "").lower()

            # Match to valid action keywords
            action = None
            for a in VALID_ACTIONS:
                if a in raw_text:
                    action = a
                    break

            if not action:
                # fallback random if parsing fails
                action = random.choice(VALID_ACTIONS)

            rows.append({
                "tick": tick,
                "agent": out["agent"],
                "action": action,
                "outcome": "ai_generated",
                "message": raw_text[:120]  # truncate for readability
            })
            self._update_memory(out["agent"], out)

        # -----------------------------
        # 4) Save to history
        # -----------------------------
        self.history.extend(rows)
        return rows

    # -----------------------------
    # Memory handling
    # -----------------------------
    def _update_memory(self, agent_name, action_row):
        agent = next((a for a in self.agents if a.name == agent_name), None)
        if agent:
            mem_entry = f"{action_row['action']} ({action_row['outcome']})"
            if action_row.get("message"):
                mem_entry += f": {action_row['message']}"
            agent.observe(mem_entry)

    # -----------------------------
    # Metrics (toy example)
    # -----------------------------
    def compute_metrics(self):
        return {
            "Total Actions": len(self.history),
            "Rumors Spread": sum(1 for h in self.history if h["action"] == "spread_rumor"),
            "Pecks": sum(1 for h in self.history if h["action"] == "peck"),
            "Alliances": sum(1 for h in self.history if h["action"] == "ally"),
        }
