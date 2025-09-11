def generate_ai_actions(agent, tick, context=None):
    """
    Stubbed GPT action generator.
    Later versions swapped this with transformers/ollama.
    """
    return {
        "tick": tick,
        "agent": agent.name,
        "action": "wander",
        "target": None,
        "message": ""
    }
