# chickens/scenarios.py
"""
Predefined coop scenarios for Clucktocracy.
Each scenario = dict with:
  - name: str
  - constitution: dict
  - chickens: list of archetype dicts (from personalities.py)
"""

from chickens.personalities import CHICKEN_ARCHETYPES

# Convenience: lookup by role/personality
_LOOKUP = {a["role"]: a for a in CHICKEN_ARCHETYPES}

SCENARIOS = [
    {
        "name": "Startup Coop",
        "constitution": {
            "term_limits": False,
            "rumor_audits": False,
            "equal_talk_time": True,
        },
        "chickens": [
            _LOOKUP["technocrat"],
            _LOOKUP["populist"],
            _LOOKUP["researcher"],
            _LOOKUP["chaos_agent"],
        ],
    },
    {
        "name": "Corrupt Coop",
        "constitution": {
            "term_limits": False,
            "rumor_audits": False,
            "equal_talk_time": False,
        },
        "chickens": [
            _LOOKUP["strongman"],
            _LOOKUP["gossip"],
            _LOOKUP["chaos_agent"],
            _LOOKUP["enforcer"],
        ],
    },
    {
        "name": "Utopian Coop",
        "constitution": {
            "term_limits": True,
            "rumor_audits": True,
            "equal_talk_time": True,
        },
        "chickens": [
            _LOOKUP["pacifist"],
            _LOOKUP["mediator"],
            _LOOKUP["researcher"],
            _LOOKUP["technocrat"],
        ],
    },
    {
        "name": "Rebellion Coop",
        "constitution": {
            "term_limits": True,
            "rumor_audits": False,
            "equal_talk_time": False,
        },
        "chickens": [
            _LOOKUP["insurgent"],
            _LOOKUP["populist"],
            _LOOKUP["gossip"],
            _LOOKUP["enforcer"],
        ],
    },
]
