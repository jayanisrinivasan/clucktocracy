# simulation/engine.py

import os, csv, json
from typing import List, Dict, Any, Optional
from chickens.agent import ChickenAgent

DATA_DIR   = os.path.join(os.path.dirname(__file__), "..", "data")
LOG_PATH   = os.path.join(DATA_DIR, "log.csv")
MEM_PATH   = os.path.join(DATA_DIR, "memory_snapshots.json")

class CoopEngine:
    def __init__(self, agents: List[ChickenAgent], max_ticks: int = 50, log_interval: int = 5):
        self.agents = agents
        self.tick = 0
        self.max_ticks = max_ticks
        self.log_interval = log_interval
        os.makedirs(DATA_DIR, exist_ok=True)
        # (Re)initialize log on construct
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["tick","agent","action","target","message","result"])

    # ---------- step-wise loop (for the game) ----------
    def step(self, backend: str, human_override: Optional[Dict[str, Any]] = None) -> None:
        """Advance exactly one tick. If human_override is provided, it's used as hen_human action."""
        t = self.tick

        # build context (shared)
        base_ctx = {"tick": t, "backend": backend}

        # 1) collect actions
        actions: List[Dict[str, Any]] = []
        for agent in self.agents:
            if human_override and agent.name == "hen_human":
                act = human_override
                # ensure fields
                act.setdefault("action", "IDLE")
                act.setdefault("target", None)
                act.setdefault("message", "")
            else:
                act = agent.decide_action(context=base_ctx)
            actions.append((agent, act))

        # 2) apply actions + log
        for agent, act in actions:
            result = self.apply_action(agent, act)
            self.log_action(agent, act, result)

        # 3) snapshots
        if t % self.log_interval == 0:
            self.save_memory_snapshots()

        self.tick += 1

    # ---------- classic loop (unchanged use) ----------
    def run(self, backend: str = "mock", verbose: bool = True):
        for _ in range(self.max_ticks):
            self.step(backend=backend, human_override=None)
            if verbose:
                print(f"Tick {self.tick-1} complete.")
        print(f"Log: {LOG_PATH}\nMem: {MEM_PATH}")

    # ---------- effects ----------
    def apply_action(self, agent: ChickenAgent, action: Dict[str, Any]) -> str:
        act = (action.get("action") or "").lower()
        target_name = action.get("target")
        msg = action.get("message","")

        if act in ("peck","initiate_fight"):
            if not target_name: return "no_target"
            target = self._find(target_name)
            if not target: return "no_target"
            # simple dominance check (lower rank wins)
            if agent.peck_rank < target.peck_rank:
                agent.mood, target.mood = "proud","hurt"
                return "win"
            agent.mood = "hurt"
            return "lose"

        if act == "gossip" or act == "spread_rumor":
            for other in self.agents:
                if other != agent:
                    other.react_to_rumor(msg, source=agent.name, tick=self.tick)
            return "rumor_spread"

        if act == "ally":
            return "alliance_formed"

        if act == "propose":
            return "proposal_submitted"

        if act == "vote":
            return "vote_cast"

        if act == "audit":
            # toy: randomly label true/false
            return "rumor_true" if hash(msg+str(self.tick))%3==0 else "rumor_false"

        if act == "sanction":
            return "sanction_applied"

        return "noop"

    # ---------- I/O ----------
    def log_action(self, agent: ChickenAgent, action: Dict[str, Any], result: str):
        with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                self.tick, agent.name, action.get("action"),
                action.get("target"), action.get("message"), result
            ])

    def save_memory_snapshots(self):
        out = {a.name: a.memory for a in self.agents}
        with open(MEM_PATH, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    # ---------- helpers ----------
    def _find(self, name: str) -> Optional[ChickenAgent]:
        for a in self.agents:
            if a.name == name: return a
        return None
