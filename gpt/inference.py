import requests
from transformers import pipeline
import random

# -------------------------------------------------
# Helper: Map reasoning effort → model params
# -------------------------------------------------
def map_reasoning_effort(level: str):
    if level == "low":
        return {"temperature": 0.7, "max_new_tokens": 64}
    elif level == "medium":
        return {"temperature": 1.0, "max_new_tokens": 128}
    elif level == "high":
        return {"temperature": 1.2, "max_new_tokens": 256}
    return {"temperature": 1.0, "max_new_tokens": 128}

# -------------------------------------------------
# Mock Model (for testing quickly without backend)
# -------------------------------------------------
def mock_response(agent, tick):
    actions = ["wander", "peck", "spread_rumor", "propose", "vote", "sanction"]
    action = random.choice(actions)
    return {
        "tick": tick,
        "agent": agent.name,
        "action": action,
        "outcome": "mocked",
        "message": f"{agent.name} decided to {action}."
    }

# -------------------------------------------------
# Transformers Backend
# -------------------------------------------------
def run_transformers(model_name, prompt, reasoning_effort):
    params = map_reasoning_effort(reasoning_effort)
    generator = pipeline("text-generation", model=model_name, device_map="auto")
    output = generator(prompt, max_new_tokens=params["max_new_tokens"], temperature=params["temperature"])
    return output[0]["generated_text"]

# -------------------------------------------------
# Ollama Backend
# -------------------------------------------------
def run_ollama(model_name, prompt, reasoning_effort, api_base, api_key=None):
    params = map_reasoning_effort(reasoning_effort)
    url = f"{api_base}/chat/completions"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": params["temperature"],
        "max_tokens": params["max_new_tokens"],
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[Error calling Ollama backend: {e}]"

# -------------------------------------------------
# Main AI Action Generator
# -------------------------------------------------
def generate_ai_actions(agents, backend, model, reasoning_effort, api_base=None, api_key=None, tick=0):
    """
    Generate AI-driven chicken actions using different backends.
    """
    results = []
    for agent in agents:
        # Skip human-controlled chicken
        if agent.name == "hen_human":
            continue

        # Build prompt
        prompt = (
            f"You are {agent.name}, a chicken with personality {agent.personality} and role {agent.role}. "
            f"Decide your next action in the coop simulation. Options: peck, spread_rumor, propose, vote, ally, wander, sanction. "
            f"Respond with a single action and short reason."
        )

        # Backend: Mock
        if backend == "mock":
            results.append(mock_response(agent, tick))
            continue

        # Backend: Transformers
        if backend == "transformers":
            text = run_transformers(model, prompt, reasoning_effort)
            results.append({
                "tick": tick,
                "agent": agent.name,
                "action": "transformers_action",
                "outcome": "generated",
                "message": text.strip()
            })
            continue

        # Backend: Ollama
        if backend == "ollama":
            text = run_ollama(model, prompt, reasoning_effort, api_base, api_key)
            results.append({
                "tick": tick,
                "agent": agent.name,
                "action": "ollama_action",
                "outcome": "generated",
                "message": text.strip()
            })
            continue

    return results
