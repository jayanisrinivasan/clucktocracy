# gpt/inference.py
"""
Inference layer for Clucktocracy.
Supports backends: mock, ollama, transformers, remote-api.
"""

import random
import requests

try:
    from transformers import pipeline
except ImportError:
    pipeline = None


# ---------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------
def generate_ai_actions(
    actions,
    backend="mock",
    model="openai/gpt-oss-20b",
    reasoning_effort="medium",
    api_base=None,
    api_key=None
):
    """
    Given the current actions, call the chosen backend and return new AI actions.

    actions: list of dicts (tick, agent, action, target, message)
    backend: mock | ollama | transformers | remote-api
    model: model name / id
    reasoning_effort: "low" | "medium" | "high"
    """

    if backend == "mock":
        return mock_actions(actions)

    elif backend == "ollama":
        return ollama_actions(actions, model)

    elif backend == "transformers":
        return transformers_actions(actions, model)

    elif backend == "remote-api":
        return remote_api_actions(actions, model, reasoning_effort, api_base, api_key)

    else:
        print(f"[WARN] Unknown backend: {backend}")
        return []


# ---------------------------------------------------------
# Mock backend (random playful moves)
# ---------------------------------------------------------
def mock_actions(actions):
    agents = ["hen_1", "hen_2", "hen_3", "hen_4"]
    possible = ["PECK", "ALLY", "GOSSIP", "SANCTION", "VOTE", "PROPOSE", "WANDER"]

    results = []
    for a in agents:
        act = random.choice(possible)
        target = random.choice(agents + ["hen_human"]) if act not in ["PROPOSE","WANDER"] else None
        msg = f"{a} does {act.lower()}"
        results.append({
            "tick": actions[-1]["tick"] if actions else 0,
            "agent": a,
            "action": act,
            "target": target,
            "message": msg
        })
    return results


# ---------------------------------------------------------
# Ollama backend
# ---------------------------------------------------------
def ollama_actions(actions, model):
    """
    Calls Ollama local server (http://localhost:11434 by default).
    You must have `ollama serve` running.
    """
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": make_prompt(actions),
            },
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json().get("response", "")
        return parse_ai_response(text, actions)
    except Exception as e:
        print(f"[ERR] Ollama backend failed: {e}")
        return []


# ---------------------------------------------------------
# Transformers backend
# ---------------------------------------------------------
def transformers_actions(actions, model):
    if pipeline is None:
        print("[ERR] Transformers not installed.")
        return []
    try:
        pipe = pipeline("text-generation", model=model, device_map="auto", torch_dtype="auto")
        msgs = make_prompt(actions)
        out = pipe(msgs, max_new_tokens=150)
        text = out[0]["generated_text"]
        return parse_ai_response(text, actions)
    except Exception as e:
        print(f"[ERR] Transformers backend failed: {e}")
        return []


# ---------------------------------------------------------
# Remote API backend (OpenAI-compatible API)
# ---------------------------------------------------------
def remote_api_actions(actions, model, reasoning_effort, api_base, api_key):
    """
    Expects an OpenAI-compatible /v1/chat/completions endpoint.
    """
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": f"You are a chicken in a coop democracy game. Reasoning effort={reasoning_effort}."},
                    {"role": "user", "content": make_prompt(actions)},
                ],
                "max_tokens": 150,
                "temperature": 1.0,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return parse_ai_response(text, actions)
    except Exception as e:
        print(f"[ERR] Remote API backend failed: {e}")
        return []


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def make_prompt(actions):
    """Turn past actions into a text prompt for the model."""
    desc = []
    for a in actions[-10:]:  # last 10 actions
        desc.append(f"[t={a['tick']}] {a['agent']} -> {a['action']} ({a.get('target','')}) :: {a.get('message','')}")
    return "\n".join(desc) + "\nSuggest next chicken moves."


def parse_ai_response(text, actions):
    """
    Parse model text into structured actions.
    Expect lines like: 'hen_2: GOSSIP about hen_3 "I saw hen_3 steal seeds!"'
    """
    results = []
    tick = actions[-1]["tick"]+1 if actions else 0
    for line in text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        try:
            agent, rest = line.split(":", 1)
            agent = agent.strip()
            if agent not in ["hen_1","hen_2","hen_3","hen_4"]:
                continue
            if " " in rest:
                parts = rest.strip().split(" ", 1)
                action = parts[0].upper()
                msg = parts[1] if len(parts)>1 else ""
            else:
                action, msg = rest.strip().upper(), ""
            results.append({
                "tick": tick,
                "agent": agent,
                "action": action,
                "target": None,
                "message": msg
            })
        except Exception:
            continue
    return results
