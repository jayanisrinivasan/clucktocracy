# gpt/inference.py
"""
Inference wrapper for Clucktocracy agents using GPT-OSS.
Backends supported:
  - mock         : no model, fast demo
  - ollama       : local Ollama server (http://localhost:11434)
  - transformers : Hugging Face Transformers pipeline (local GPU)
  - remote-api   : OpenAI-compatible endpoint (e.g., vLLM, HF Inference Endpoint)

Features:
  - Reasoning effort control (low/medium/high) -> nudges model depth via system hints.
  - Harmony-style structured action output (compact JSON).
  - Resilient parsing: attempts JSON first, then falls back to heuristic extraction.
"""

from __future__ import annotations
import json
import random
import re
from typing import Dict, Any, Optional

import requests

try:
    import openai  # used for remote-api (OpenAI-compatible endpoints)
except ImportError:
    openai = None


# ---------- Prompt utilities ----------
ACTION_SCHEMA = """
Return ONLY a compact JSON object with keys:
{
  "action": "<one of: PECK, ALLY, GOSSIP, AUDIT, PROPOSE, VOTE, SANCTION, FORAGE, SCRATCH, IDLE>",
  "target": "<chicken name or policy id or null>",
  "message": "<short statement or proposal>",
  "confidence": <float 0.0-1.0>
}
No extra prose, no markdown, no code blocks.
"""

REASONING_HINT = {
    "low":    "Be decisive. Minimal deliberation.",
    "medium": "Consider last few memories, weigh 2 alternatives, then decide.",
    "high":   "Deliberate briefly about alliances vs sanctions vs policy, then decide."
}


def build_prompt(agent_name: str, personality: str, role: str, context: Dict[str, Any],
                 reasoning_effort: str = "medium") -> str:
    """
    Builds a concise instruction for the model with Harmony-like guidance.
    We do not include chain-of-thought; we instruct the model to output structured JSON only.
    """
    constitution = context.get("constitution", {})
    memories = context.get("memories", [])[-5:]
    tick = context.get("tick", 0)

    memory_lines = "; ".join(
        (m.get("event") if isinstance(m, dict) else str(m)) for m in memories
    )

    return (
        f"You are {agent_name}, a {personality} chicken with role '{role}' in a coop simulation.\n"
        f"Tick: {tick}. Constitution: {json.dumps(constitution)}.\n"
        f"Recent memories: {memory_lines or 'none'}.\n"
        f"Goal: act plausibly and strategically given your personality/role.\n"
        f"{REASONING_HINT.get(reasoning_effort, REASONING_HINT['medium'])}\n"
        f"{ACTION_SCHEMA}"
    )


# ---------- Parsing utilities ----------
_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)

def _coerce_action(text: str) -> Dict[str, Any]:
    """
    Parse the model text to our action dict. Prefers JSON; falls back to heuristics.
    Never raises; returns a safe default if parsing fails.
    """
    if not text:
        return {"action":"IDLE","target":None,"message":"","confidence":0.0}

    # Try strict JSON first
    m = _JSON_OBJ_RE.search(text)
    if m:
        snippet = m.group(0)
        try:
            obj = json.loads(snippet)
            # normalize
            obj.setdefault("target", None)
            obj.setdefault("message", "")
            obj.setdefault("confidence", 0.75)
            # uppercase action
            if "action" in obj and isinstance(obj["action"], str):
                obj["action"] = obj["action"].upper()
            return obj
        except Exception:
            pass

    # Heuristic fallback
    # Guess action keywords
    up = text.upper()
    for key in ["PECK","ALLY","GOSSIP","AUDIT","PROPOSE","VOTE","SANCTION","FORAGE","SCRATCH","IDLE"]:
        if key in up:
            action = key
            break
    else:
        action = "GOSSIP" if "RUMOR" in up else "IDLE"

    # Target heuristic
    target = None
    mt = re.search(r"(hen_[A-Za-z0-9]+)", text)
    if mt:
        target = mt.group(1)

    # Message heuristic
    msg = text.strip().split("\n")[0][:240]

    return {"action": action, "target": target, "message": msg, "confidence": 0.7}


# ---------- Backends ----------
def _mock_infer() -> Dict[str, Any]:
    return {
        "action": random.choice(["PECK","ALLY","GOSSIP","PROPOSE","VOTE","IDLE"]),
        "target": None,
        "message": random.choice([
            "peck peck...", "wanders the yard", "whispers about seeds near the silo",
            "calls for fair grain distribution", "observes quietly"
        ]),
        "confidence": round(random.uniform(0.5, 1.0), 2),
    }


def _ollama_infer(prompt: str, model: str) -> Dict[str, Any]:
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=90,
        )
        data = resp.json() if resp.headers.get("content-type","").startswith("application/json") else json.loads(resp.text)
        return _coerce_action(data.get("response",""))
    except Exception as e:
        return {"action":"IDLE","target":None,"message":f"Ollama error: {e}", "confidence":0.0}


def _transformers_infer(prompt: str, model: str) -> Dict[str, Any]:
    try:
        from transformers import pipeline
        pipe = pipeline(
            "text-generation",
            model=model,
            torch_dtype="auto",
            device_map="auto",
        )
        messages = [{"role":"user","content":prompt}]
        out = pipe(messages, max_new_tokens=192)
        # Transformers chat pipeline returns list of messages in generated_text
        text = out[0].get("generated_text", [""])[-1] if isinstance(out[0].get("generated_text"), list) else str(out[0])
        return _coerce_action(text)
    except Exception as e:
        return {"action":"IDLE","target":None,"message":f"Transformers error: {e}", "confidence":0.0}


def _remote_api_infer(prompt: str, model: str, api_base: str, api_key: str) -> Dict[str, Any]:
    if openai is None:
        return {"action":"IDLE","target":None,"message":"OpenAI client not installed", "confidence":0.0}
    try:
        openai.api_base = api_base.rstrip("/")
        openai.api_key = api_key or "test"
        # OpenAI-compatible Chat Completions
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[{"role":"user","content":prompt}],
            temperature=1.0,
            max_tokens=192,
        )
        text = resp["choices"][0]["message"]["content"]
        return _coerce_action(text)
    except Exception as e:
        return {"action":"IDLE","target":None,"message":f"Remote API error: {e}", "confidence":0.0}


# ---------- Public API ----------
def generate_action_for_agent(
    agent_name: str,
    personality: str,
    role: str,
    context: Dict[str, Any],
    backend: str = "mock",
    model: str = "openai/gpt-oss-20b",
    reasoning_effort: str = "medium",
    api_base: str = "http://localhost:8000/v1",
    api_key: str = "test",
) -> Dict[str, Any]:
    """
    Builds a structured prompt and queries the selected backend.
    Returns an action dict compliant with the engine expectations.
    """
    prompt = build_prompt(agent_name, personality, role, context, reasoning_effort)

    if backend == "mock":
        return _mock_infer()
    if backend == "ollama":
        return _ollama_infer(prompt, model)
    if backend == "transformers":
        return _transformers_infer(prompt, model)
    if backend == "remote-api":
        return _remote_api_infer(prompt, model, api_base, api_key)

    return {"action":"IDLE","target":None,"message":f"Unknown backend: {backend}", "confidence":0.0}
