# gpt/inference.py

import os
import json
import random
import requests
from typing import Dict, Any

# Optional imports for transformers backend
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    import torch
except ImportError:
    AutoTokenizer = None
    AutoModelForCausalLM = None
    pipeline = None


# -----------------------------
# Global config
# -----------------------------
DEFAULT_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "chicken_prompt.txt")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
HF_MODEL_ID = os.environ.get("HF_MODEL_ID", "openmodel/gpt-oss-20b")

# Cache HF pipeline to avoid reloading each call
_hf_pipeline = None


# -----------------------------
# Utilities
# -----------------------------
def _load_prompt_template() -> str:
    with open(DEFAULT_PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


# -----------------------------
# Backend: Mock
# -----------------------------
def mock_action(agent, context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a simple fake action (no model)."""
    options = [
        {"action": "wander", "target": None, "message": f"{agent.name} wanders aimlessly."},
        {"action": "scratch", "target": None, "message": f"{agent.name} scratches the ground."},
        {"action": "idle", "target": None, "message": ""},
        {"action": "spread_rumor", "target": "hen_2", "message": "I heard Hen_2 stole seeds!"}
    ]
    return random.choice(options)


# -----------------------------
# Backend: Ollama
# -----------------------------
def ollama_action(agent, context: Dict[str, Any], model_name: str = "gpt-oss-20b") -> Dict[str, Any]:
    """Call Ollama local model."""
    system_prompt = _load_prompt_template()
    memory_text = "\n".join([str(m) for m in agent.memory[-5:]]) or "No memories."
    user_prompt = f"Name: {agent.name}, Role: {agent.role}, Personality: {agent.personality}\n"
    user_prompt += f"Recent memory: {memory_text}\n"
    user_prompt += f"Context: {json.dumps(context)}\n"
    user_prompt += "Decide your next action."

    payload = {
        "model": model_name,
        "prompt": system_prompt + "\n" + user_prompt,
        "stream": False
    }

    resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
    resp.raise_for_status()
    text = resp.json().get("response", "").strip()

    # Try parse JSON output
    try:
        action = json.loads(text)
        if isinstance(action, dict):
            return action
    except Exception:
        pass

    # Fallback
    return {"action": "idle", "target": None, "message": text[:200]}


# -----------------------------
# Backend: Hugging Face / Transformers
# -----------------------------
def _load_hf_pipeline(model_id: str = None):
    global _hf_pipeline
    if _hf_pipeline is not None:
        return _hf_pipeline

    model_id = model_id or HF_MODEL_ID
    if AutoTokenizer is None or AutoModelForCausalLM is None:
        raise ImportError("transformers not installed. Please pip install transformers accelerate.")

    print(f"[Loading HF model: {model_id}]")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16, device_map="auto")
    _hf_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer)
    return _hf_pipeline


def hf_action(agent, context: Dict[str, Any], model_id: str = None) -> Dict[str, Any]:
    system_prompt = _load_prompt_template()
    memory_text = "\n".join([str(m) for m in agent.memory[-5:]]) or "No memories."
    user_prompt = f"Name: {agent.name}, Role: {agent.role}, Personality: {agent.personality}\n"
    user_prompt += f"Recent memory: {memory_text}\n"
    user_prompt += f"Context: {json.dumps(context)}\n"
    user_prompt += "Decide your next action. Respond in JSON."

    generator = _load_hf_pipeline(model_id)
    outputs = generator(system_prompt + "\n" + user_prompt, max_new_tokens=200, do_sample=True, top_p=0.9)
    text = outputs[0]["generated_text"].split(user_prompt)[-1].strip()

    try:
        return json.loads(text)
    except Exception:
        return {"action": "idle", "target": None, "message": text[:200]}


# -----------------------------
# Main dispatcher
# -----------------------------
def generate_action(agent, context: Dict[str, Any]) -> Dict[str, Any]:
    """Select backend based on env/config and generate an action."""
    backend = context.get("backend", os.environ.get("BACKEND", "mock"))

    if backend == "mock":
        return mock_action(agent, context)
    elif backend == "ollama":
        model_name = context.get("ollama_model", os.environ.get("OLLAMA_MODEL", "gpt-oss-20b"))
        return ollama_action(agent, context, model_name=model_name)
    elif backend == "transformers":
        model_id = context.get("hf_model_id", HF_MODEL_ID)
        return hf_action(agent, context, model_id=model_id)
    else:
        raise ValueError(f"Unknown backend: {backend}")
