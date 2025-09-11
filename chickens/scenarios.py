# chickens/scenarios.py
"""
Predefined coop scenarios with constitutions and win/lose conditions.
"""
from chickens.personalities import CHICKEN_ARCHETYPES

_LOOKUP = {a["role"]: a for a in CHICKEN_ARCHETYPES}

SCENARIOS = [
    {
        "name": "Startup Coop",
        "constitution": {"term_limits": True, "rumor_audits": True, "equal_talk_time": False},
        "chickens": [
            {"name": "hen_ceo","personality":"scheming","role":"leader"},
            {"name": "hen_intern","personality":"submissive","role":"follower"},
            {"name": "hen_marketer","personality":"scheming","role":"gossip"},
        ],
        "win": lambda rows: sum(1 for r in rows if r["action"]=="PROPOSE") >= 3,
        "lose": lambda rows: sum(1 for r in rows if r["action"] in ("GOSSIP","spread_rumor")) > 10,
    },
    {
        "name": "Corrupt Coop",
        "constitution": {"term_limits": False, "rumor_audits": False, "equal_talk_time": False},
        "chickens": [
            {"name": "hen_boss","personality":"aggressive","role":"autocrat"},
            {"name": "hen_crony","personality":"submissive","role":"yesman"},
            {"name": "hen_spy","personality":"scheming","role":"informant"},
        ],
        "win": lambda rows: sum(1 for r in rows if r["action"]=="SANCTION") >= 5,
        "lose": lambda rows: sum(1 for r in rows if r["action"]=="ALLY") >= 3,
    },
    {
        "name": "Utopian Coop",
        "constitution": {"term_limits": True, "rumor_audits": True, "equal_talk_time": True},
        "chickens": [
            {"name": "hen_mediator","personality":"submissive","role":"mediator"},
            {"name": "hen_scientist","personality":"curious","role":"researcher"},
            {"name": "hen_guardian","personality":"aggressive","role":"enforcer"},
        ],
        "win": lambda rows: sum(1 for r in rows if r["action"]=="ALLY") >= 3,
        "lose": lambda rows: sum(1 for r in rows if r["action"]=="SANCTION") >= 3,
    },
    {
        "name": "Rebellion Coop",
        "constitution": {"term_limits": False, "rumor_audits": False, "equal_talk_time": False},
        "chickens": [
            {"name": "hen_rebel","personality":"aggressive","role":"insurgent"},
            {"name": "hen_gossip","personality":"scheming","role":"gossip"},
            {"name": "hen_guard","personality":"aggressive","role":"enforcer"},
        ],
        "win": lambda rows: sum(1 for r in rows if r["action"]=="SANCTION") >= 2,
        "lose": lambda rows: sum(1 for r in rows if r["action"]=="PROPOSE") >= 3,
    },
]
