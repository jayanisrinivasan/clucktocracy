# simulation/engine.py
"""
CoopEngine: step-wise simulation loop for Clucktocracy.

Responsibilities
- Owns agents and global tick.
- Collects actions each tick (human override optional).
- Applies effects, writes CSV log, and persists memory snapshots.
- Exposes run() for batch runs and step() for the interactive UI.
- save_state() lets the UI force a disk flush after a step.

Log schema: data/log.csv
    tick,agent,action,target,message,result

Memories: data/memory_snapshots.json
    { "<agent_name>": [ {event: "...", ...}, ... ] }
"""

from __future__ import annotations

import csv
import json
import os
from typing import Dict, Any, List, Optional, Tuple

# Local imports
# (The UI adds project root to sys.path. This file is imported as simulation.engine.)
try:
    from chickens.agent import ChickenAgent
except Exception:
    # Defer import error until used; helpful for static analyzers / packaging
    ChickenAgent = object  # type: ignore


# ---------- Paths ----------
_HERE = os.path.dirname(__file__)
DATA_DIR = os.path.abspath(os.path.join(_HERE, "..", "data"))
LOG_PATH = os.path.join(DATA_DIR, "log.csv")
MEM_PATH = os.path.join(DATA_DIR, "memory_snapshots.json")


class CoopEngine:
    """
    A small, deterministic-enough engine for the coop.
    - Agents decide actions from context (or human override).
    - Engine applies side effects and writes a log row per action.
    """

    def __init__(self, agents: List[ChickenAgent], max_ticks: int = 50, log_interval: int = 5):
        self.agents: List[ChickenAgent] = agents
        self.max_ticks = int(max_ticks)
        self.log_interval = max(1, int(log_interval))
        self.tick: int = 0

        os.makedirs(DATA_DIR, exist_ok=True)
        # Start a fresh log each engine init
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["tick", "agent", "action", "target", "message", "result"])

    # ---------------------------
    # Public control surfaces
    # ---------------------------
    def step(
        self,
        backend: str,
        human_override: Optional[Dict[str, Any]] = None,
        constitution: Optional[Dict[str, Any]] = None,
        reasoning_effort: str = "medium",
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """
        Advance exactly one tick.
        - backend: "mock" | "ollama" | "transformers" | "remote-api"
        - human_override: if provided, used as hen_human's action
        - constitution: dict of simple policy toggles (term_limits, rumor_audits, equal_talk_time)
        - reasoning_effort: low|medium|high (hint to LLM backends)
        - api_base/api_key: only used for remote-api backend
        """
        t = self.tick
        const = constitution or {}

        # 1) Collect actions
        actions: List[Tuple[ChickenAgent, Dict[str, Any]]] = []
        for agent in self.agents:
            if human_override and agent.name == "hen_human":
                act = dict(human_override)
                act.setdefault("action", "IDLE")
                act.setdefault("target", None)
                act.setdefault("message", "")
            else:
                ctx: Dict[str, Any] = {
                    "tick": t,
                    "constitution": const,
                    "memories": list(agent.memory[-8:]) if hasattr(agent, "memory") else [],
                    "backend": backend,
                    "model": "openai/gpt-oss-20b",  # default; UI may override in decide_action context
                    "reasoning_effort": reasoning_effort,
                    "api_base": api_base or "http://localhost:8000/v1",
                    "api_key": api_key or "test",
                }
                # Let agent produce an action dict (may call an LLM)
                act = agent.decide_action(context=ctx)
                if not isinstance(act, dict):
                    # Be defensive: normalize to a dict
                    act = {"action": "IDLE", "target": None, "message": ""}

            # Normalize a bit
            act["action"] = (act.get("action") or "IDLE").upper()
            act.setdefault("target", None)
            act.setdefault("message", "")
            actions.append((agent, act))

        # 2) Apply actions and log each
        for agent, act in actions:
            result = self.apply_action(agent, act, constitution=const)
            self.log_action(agent, act, result)

        # 3) Periodic memory snapshots
        if t % self.log_interval == 0:
            self.save_memory_snapshots()

        # Advance time
        self.tick += 1

    def run(self, backend: str = "mock", verbose: bool = True) -> None:
        """
        Batch run for quick local tests (non-interactive).
        """
        for _ in range(self.max_ticks):
            self.step(backend=backend)
            if verbose:
                print(f"Tick {self.tick - 1} complete.")
        print(f"Log: {LOG_PATH}\nMem: {MEM_PATH}")

    def save_state(self) -> None:
        """
        Convenience hook for the UI to force persistence between rerenders.
        The log is appended on every action; here we ensure memory snapshots exist.
        """
        self.save_memory_snapshots()

    # ---------------------------
    # Internals
    # ---------------------------
    def apply_action(self, agent: ChickenAgent, action: Dict[str, Any], constitution: Dict[str, Any]) -> str:
        """
        Apply side effects for a single action.
        Returns a short result string recorded into the log.
        """
        act = (action.get("action") or "IDLE").upper()
        target_name = action.get("target")
        message = action.get("message", "") or ""

        # Map a few synonyms
        if act == "INITIATE_FIGHT":
            act = "PECK"
        if act == "SPREAD_RUMOR":
            act = "GOSSIP"

        # Helpers
        def _find_target(name: Optional[str]) -> Optional[ChickenAgent]:
            if not name:
                return None
            for a in self.agents:
                if a.name == name:
                    return a
            return None

        # --- Effects by action ---
        if act == "PECK":
            tgt = _find_target(target_name)
            if not tgt:
                return "no_target"
            # Simple dominance rule: lower peck_rank wins
            a_rank = getattr(agent, "peck_rank", 999)
            t_rank = getattr(tgt, "peck_rank", 999)
            if a_rank < t_rank:
                if hasattr(agent, "mood"):
                    agent.mood = "proud"
                if hasattr(tgt, "mood"):
                    tgt.mood = "hurt"
                self._memorize(agent, f"Won peck vs {tgt.name}")
                self._memorize(tgt, f"Lost peck vs {agent.name}")
                return "win"
            else:
                if hasattr(agent, "mood"):
                    agent.mood = "hurt"
                if hasattr(tgt, "mood"):
                    tgt.mood = "proud"
                self._memorize(agent, f"Lost peck vs {tgt.name}")
                self._memorize(tgt, f"Won peck vs {agent.name}")
                return "lose"

        if act == "ALLY":
            # Toy alliance: store in memory; UI graph reads from the log edge
            self._memorize(agent, f"Allied with {target_name}")
            if target_name:
                tgt = _find_target(target_name)
                if tgt:
                    self._memorize(tgt, f"Allied with {agent.name}")
            return "alliance_formed"

        if act == "GOSSIP":
            # Rumor broadcast to all others; optionally audited policy may alter reception
            audited = bool(constitution.get("rumor_audits", False))
            for other in self.agents:
                if other is agent:
                    continue
                self._deliver_rumor(other, rumor=message, source=agent.name)
                if audited:
                    # A mild “truthiness” check
                    # (In a real build, you’d call out to a tool or verifier)
                    pass
            self._memorize(agent, f"Gossiped: {message[:48]}")
            return "rumor_spread"

        if act == "PROPOSE":
            # Policy proposal: stash into proposer memory; others will "see" via log feed
            pid = f"pol_{self.tick}_{agent.name}"
            self._memorize(agent, f"Proposed {pid}: {message[:48]}")
            return "proposal_submitted"

        if act == "VOTE":
            # Toy vote: record intent in memory
            self._memorize(agent, f"Voted: {message[:48]}")
            return "vote_cast"

        if act == "AUDIT":
            # Quick toy audit result (stochastic)
            outcome = "rumor_true" if (hash(message + str(self.tick)) % 3 == 0) else "rumor_false"
            self._memorize(agent, f"Audit result: {outcome} on '{message[:40]}'")
            return outcome

        if act == "SANCTION":
            tgt = _find_target(target_name)
            if tgt:
                self._memorize(agent, f"Sanctioned {tgt.name}")
                self._memorize(tgt, f"Received sanction from {agent.name}")
            return "sanction_applied"

        if act in ("FORAGE", "SCRATCH", "IDLE"):
            # Low-impact background acts
            self._memorize(agent, f"{act.lower()}")
            return "noop"

        # Unknown acts default to noop, but still record
        self._memorize(agent, f"{act.lower()} (no_effect)")
        return "noop"

    def log_action(self, agent: ChickenAgent, action: Dict[str, Any], result: str) -> None:
        """
        Append a single row to data/log.csv
        """
        with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                self.tick,
                getattr(agent, "name", "unknown"),
                action.get("action"),
                action.get("target"),
                action.get("message"),
                result,
            ])

    def save_memory_snapshots(self) -> None:
        """
        Persist a compact memory view for all agents to JSON.
        """
        out = {}
        for a in self.agents:
            try:
                out[getattr(a, "name", "unknown")] = list(getattr(a, "memory", []))
            except Exception:
                out[getattr(a, "name", "unknown")] = []
        with open(MEM_PATH, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    # ---------------------------
    # helpers
    # ---------------------------
    def _memorize(self, agent: ChickenAgent, event: str) -> None:
        """
        Push a short event into the agent's memory (bounded).
        """
        try:
            if not hasattr(agent, "memory"):
                return
            agent.memory.append({"event": event, "tick": self.tick})
            # Trim to a reasonable window
            if len(agent.memory) > 24:
                agent.memory.pop(0)
        except Exception:
            pass

    def _deliver_rumor(self, agent: ChickenAgent, rumor: str, source: str) -> None:
        """
        Call agent.react_to_rumor() with either (rumor) or (rumor, source, tick),
        depending on the agent's implementation.
        """
        try:
            # Try richer signature first
            agent.react_to_rumor(rumor, source=source, tick=self.tick)  # type: ignore
        except TypeError:
            # Fallback to simple signature
            try:
                agent.react_to_rumor(rumor)  # type: ignore
            except Exception:
                # As last resort, just memorize
                self._memorize(agent, f"Rumor heard: {rumor[:48]}")
        except Exception:
            # As last resort, just memorize
            self._memorize(agent, f"Rumor heard: {rumor[:48]}")
