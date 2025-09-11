# gpt/inference.py
"""
Inference wrapper for GPT-OSS chickens.
Supports three backends: mock, ollama, transformers.
"""

import random, json, requests


def run_inference(prompt: str, backend: str = "mock", model: str = "openai/gpt-oss-20b"):
    """
    Run inference for a chicken agent.
    Args:
        prompt: string prompt (coop state, agent personality, etc.)
        backend: "mock", "ollama", or "transformers"
        model: model ID (Hugging Face or Ollama tag)
    Returns:
        dict with action, target, message
    """

    if backend == "mock":
        return {
            "action": random.choice(["PECK", "ALLY", "GOSSIP", "PROPOSE", "VOTE", "IDLE"]),
            "target": None,
            "message": random.choice(
                ["peck peck...", "wanders aimlessly", "spreads a silly rumor", "clucks nervously"]
            ),
            "confidence": round(random.uniform(0.5, 1.0), 2),
        }

    elif backend == "ollama":
        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            data = json.loads(resp.text)
            return {
                "action": "GOSSIP",
                "target": None,
                "message": data.get("response", "").strip(),
                "confidence": 0.8,
            }
        except Exception as e:
            return {"action": "IDLE", "message": f"Ollama error: {e}", "confidence": 0.0}

    elif backend == "transformers":
        try:
            from transformers import pipeline
            import torch

            pipe = pipeline(
                "text-generation",
                model=model,
                torch_dtype="auto",
                device_map="auto",
            )

            messages = [{"role": "user", "content": prompt}]
            outputs = pipe(messages, max_new_tokens=128)

            text = outputs[0]["generated_text"][-1] if "generated_text" in outputs[0] else str(outputs[0])
            return {"action": "PROPOSE", "target": None, "message": text.strip(), "confidence": 0.9}
        except Exception as e:
            return {"action": "IDLE", "message": f"Transformers error: {e}", "confidence": 0.0}

    else:
        raise ValueError(f"Unknown backend: {backend}")
