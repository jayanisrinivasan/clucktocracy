# simulation/engine.py

import os, csv, json
from datetime import datetime
from chickens.agent import ChickenAgent

LOG_PATH = os.path.join("logs", "coop_log.csv")
MEM_PATH = os.path.join("logs", "coop_mem.json")


class CoopEngine:
    def __init__(self, agents, max_ticks=200, log_interval=5):
        self.agents = agents
        self.history = []
        self.tick = 0
        self.max_ticks = max_ticks
        self.log_interval = log_interval

        os.makedirs("logs", exist_ok=True)
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["tick", "agent", "action", "target", "message"])
            writer.writeheader()
        with open(MEM_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)

    def step(self, backend="mock", human_override=None, constitution=None,
             reasoning_effort="medium", api_base=None, api_key=None):
        """
        Advance one tick of the coop simulation.
        Integrates GPT-OSS / Ollama / Transformers / Remote API backends.
        """
        actions = []

        # Human override
        if human_override and human_override.get("action") != "IDLE":
            actions.append({
                "tick": self.tick,
                "agent": "hen_human",
                "action": human_override.get("action"),
                "target": human_override.get("target"),
                "message": human_override.get("message", "")
            })

        # NPC actions
        for agent in self.agents:
            if agent.role != "player":
                act = agent.act(self.tick)
                act["tick"] = self.tick
                actions.append(act)

        # GPT inference (if not mock)
        if backend != "mock":
            try:
                from gpt.inference import generate_ai_actions
                ai_responses = generate_ai_actions(
                    actions,
                    backend=backend,
                    model="openai/gpt-oss-20b",  # default
                    reasoning_effort=reasoning_effort,
                    api_base=api_base,
                    api_key=api_key
                )
                if ai_responses:
                    actions.extend(ai_responses)
            except Exception as e:
                print(f"[WARN] GPT backend failed: {e}")

        # Save to history
        self.history.extend(actions)
        self.tick += 1
        self._write_logs(actions)
        self._update_memories(actions)

        return actions

    def _write_logs(self, actions):
        """Persist actions to CSV log"""
        with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["tick", "agent", "action", "target", "message"])
            for act in actions:
                writer.writerow(act)

    def _update_memories(self, actions):
        """Append memories per agent"""
        mems = {}
        if os.path.exists(MEM_PATH):
            with open(MEM_PATH, encoding="utf-8") as f:
                try:
                    mems = json.load(f)
                except json.JSONDecodeError:
                    mems = {}

        for act in actions:
            agent = act["agent"]
            if agent not in mems:
                mems[agent] = []
            mems[agent].append({
                "tick": act["tick"],
                "event": f"{agent} did {act['action']} targeting {act.get('target','')} :: {act.get('message','')}"
            })

        with open(MEM_PATH, "w", encoding="utf-8") as f:
            json.dump(mems, f, indent=2)

    def save_state(self):
        """Save engine state for persistence"""
        state = {
            "tick": self.tick,
            "history": self.history,
            "agents": [a.to_dict() for a in self.agents],
        }
        with open("logs/state.json", "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
