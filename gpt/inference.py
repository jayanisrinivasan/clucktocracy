# gpt/inference.py
"""
Inference backends for Clucktocracy.
Supports: mock | ollama | transformers | remote-api (OpenAI-compatible).
"""

import os
import random
import requests
from typing import List, Dict, Any

# Optional: Hugging Face
try:
    from transformers import pipeline
except ImportError:
    pipeline = None


# ---------------------------------------------------------
# MOCK BACKEND
# ---------------------------------------------------------
def _mock_actions(agents, tick: int) -> List[Dict[str, Any]]:
    actions = []
    for agent in agents:
        if agent.name == "hen_human":
            continue  # handled separately
        act = random.choice(["peck", "ally", "spread_rumor", "wander", "propose", "vote"])
        target = random.choice([a.name for a in agents if a.name != agent.name])
        msg = f"{agent.name} did {act} to {target}"
        actions.append({
            "tick": tick,
            "agent": agent.name,
            "action": act,
            "target": target,
            "message": msg,
            "outcome": "ok"
        })
    return actions


# ---------------------------------------------------------
# OLLAMA BACKEND
# ---------------------------------------------------------
def _ollama_actions(agents, tick: int, model: str, api_base: str, **kwargs):
    actions = []
    url = f"{api_base}/chat/completions"
    for agent in agents:
        if agent.name == "hen_human":
            continue

        prompt = f"You are {agent.name} in a chicken coop democracy. Suggest one action."
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Respond with a JSON action: {action,target,message}"},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 100,
        }
        try:
            r = requests.post(url, json=payload, timeout=15)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            content = f"error: {e}"

        actions.append({
            "tick": tick,
            "agent": agent.name,
            "action": "ollama_act",
            "target": None,
            "message": content,
            "outcome": "ollama"
        })
    return actions


# ---------------------------------------------------------
# TRANSFORMERS BACKEND
# ---------------------------------------------------------
def _transformer_actions(agents, tick: int, model: str, **kwargs):
    actions = []
    if pipeline is None:
        return _mock_actions(agents, tick)

    pipe = pipeline("text-generation", model=model, device_map="auto", torch_dtype="auto")

    for agent in agents:
        if agent.name == "hen_human":
            continue
        prompt = f"{agent.name} is a chicken politician. Give one coop action."
        try:
            out = pipe(prompt, max_new_tokens=50)
            msg = out[0]["generated_text"]
        except Exception as e:
            msg = f"error: {e}"

        actions.append({
            "tick": tick,
            "agent": agent.name,
            "action": "gen_action",
            "target": None,
            "message": msg,
            "outcome": "transformers"
        })
    return actions


# ---------------------------------------------------------
# REMOTE API BACKEND (OpenAI-compatible)
# ---------------------------------------------------------
def _remote_api_actions(agents, tick: int, model: str, api_base: str, api_key: str, reasoning_effort: str):
    actions = []
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{api_base}/chat/completions"

    for agent in agents:
        if agent.name == "hen_human":
            continue

        messages = [
            {"role": "system", "content": f"You are {agent.name} in a political chicken coop."},
            {"role": "developer", "content": f"Always respond with JSON {{action,target,message}}. Reasoning effort={reasoning_effort}"},
            {"role": "user", "content": "Pick your next coop action."},
        ]
        payload = {"model": model, "messages": messages, "max_tokens": 100}

        try:
            r = requests.post(url, headers=headers, json=payload, timeout=20)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            content = f"error: {e}"

        actions.append({
            "tick": tick,
            "agent": agent.name,
            "action": "remote_action",
            "target": None,
            "message": content,
            "outcome": "remote"
        })
    return actions


# ---------------------------------------------------------
# PUBLIC ENTRY POINT
# ---------------------------------------------------------
def generate_ai_actions(
    agents,
    tick: int,
    backend: str = "mock",
    model: str = "openai/gpt-oss-20b",
    reasoning_effort: str = "medium",
    api_base: str = None,
    api_key: str = None,
) -> List[Dict[str, Any]]:
    """
    Unified interface. Returns list of AI agent actions.
    """

    if backend == "mock":
        return _mock_actions(agents, tick)

    elif backend == "ollama":
        return _ollama_actions(agents, tick, model=model, api_base=api_base or "http://localhost:11434/v1")

    elif backend == "transformers":
        return _transformer_actions(agents, tick, model=model)

    elif backend == "remote-api":
        return _remote_api_actions(agents, tick, model=model,
                                   api_base=api_base or "http://localhost:8000/v1",
                                   api_key=api_key or "test",
                                   reasoning_effort=reasoning_effort)

    else:
        return _mock_actions(agents, tick)
