# gpt/inference.py
import random
import requests


def generate_ai_actions(
    agents,
    backend="mock",
    model=None,
    reasoning_effort="medium",
    api_base=None,
    api_key=None,
    tick=0,
):
    """
    Generate AI actions for the given agents.
    Supports mock (random), ollama (local API), and transformers (Hugging Face).
    """
    actions = []

    if backend == "mock":
        # Random simple actions
        possible_actions = ["peck", "spread_rumor", "ally", "propose", "vote", "wander"]
        for agent in agents:
            act = random.choice(possible_actions)
            actions.append(
                {
                    "agent": agent,
                    "action": act,
                    "target": random.choice(agents) if act in ["peck", "ally"] else None,
                    "message": (
                        f"Policy idea at tick {tick}"
                        if act == "propose"
                        else f"Rumor at tick {tick}"
                        if act == "spread_rumor"
                        else None
                    ),
                }
            )

    elif backend == "ollama":
        if not api_base:
            api_base = "http://localhost:11434/v1"
        for agent in agents:
            prompt = f"""
            You are {agent}, a chicken in a political coop simulation.
            It's tick {tick}.
            Choose ONE action you will take:
            - peck (fight another hen)
            - spread_rumor (gossip about another hen)
            - ally (form a coalition)
            - propose (make a policy suggestion)
            - vote (vote YES/NO on policy)
            - wander (do nothing significant)

            Respond in JSON with keys: action, target (if any), message (if any).
            """
            try:
                r = requests.post(
                    f"{api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
                    json={
                        "model": model or "gpt-oss-20b",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 100,
                        "temperature": 0.8,
                    },
                    timeout=20,
                )
                data = r.json()
                content = data["choices"][0]["message"]["content"]

                # naive fallback parser
                if "peck" in content.lower():
                    action = "peck"
                elif "rumor" in content.lower():
                    action = "spread_rumor"
                elif "ally" in content.lower():
                    action = "ally"
                elif "propose" in content.lower():
                    action = "propose"
                elif "vote" in content.lower():
                    action = "vote"
                else:
                    action = "wander"

                actions.append(
                    {
                        "agent": agent,
                        "action": action,
                        "target": None,
                        "message": content.strip(),
                    }
                )
            except Exception as e:
                actions.append(
                    {"agent": agent, "action": "wander", "target": None, "message": str(e)}
                )

    elif backend == "transformers":
        try:
            from transformers import pipeline

            pipe = pipeline(
                "text-generation",
                model=model or "openai/gpt-oss-20b",
                torch_dtype="auto",
                device_map="auto",
            )
            for agent in agents:
                prompt = f"{agent} is a chicken at tick {tick}. Choose an action: peck, spread_rumor, ally, propose, vote, or wander."
                out = pipe(prompt, max_new_tokens=50, temperature=0.8)
                text = out[0]["generated_text"]

                if "peck" in text.lower():
                    action = "peck"
                elif "rumor" in text.lower():
                    action = "spread_rumor"
                elif "ally" in text.lower():
                    action = "ally"
                elif "propose" in text.lower():
                    action = "propose"
                elif "vote" in text.lower():
                    action = "vote"
                else:
                    action = "wander"

                actions.append(
                    {"agent": agent, "action": action, "target": None, "message": text.strip()}
                )
        except Exception as e:
            for agent in agents:
                actions.append(
                    {"agent": agent, "action": "wander", "target": None, "message": str(e)}
                )

    return actions
