# ui/streamlit_game.py
"""
CLUCKTOCRACY — Coop Simulation HUD (Dark Gamer Theme)
- No emojis
- Backend selector (mock / ollama / transformers / remote-api)
- Remote API config (base URL + API key)
- Reasoning effort selector (low/medium/high)
- Constitution toggles (term limits, rumor audits, equal talk-time)
- Power Gini metric, Game Over splash
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import csv, json, random
from collections import defaultdict

import streamlit as st
import matplotlib.pyplot as plt
import networkx as nx

from chickens.agent import ChickenAgent
from simulation.engine import CoopEngine, LOG_PATH, MEM_PATH


# ---------- Style ----------
st.set_page_config(page_title="Clucktocracy", layout="wide")

st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #0e0e10;
    color: #e0e0e0;
    font-family: 'Orbitron', sans-serif;
}
[data-testid="stSidebar"] { background-color: #1a1a1d; }

/* Buttons */
.stButton>button {
    background-color: #ff005d; color: white; font-weight: bold;
    border-radius: 6px; border: none; padding: 8px 16px; transition: 0.2s;
}
.stButton>button:hover { background-color: #ff3369; transform: scale(1.05); }

/* Metrics */
[data-testid="stMetricValue"] { color: #00ffae; font-size: 22px; }

/* Cards */
.card {
    background: #16161a; border: 2px solid #00ffae; padding: 12px; border-radius: 8px;
}

/* Titles */
h1, h2, h3 { color: #ff005d; }

/* Game Over splash */
.game-over {
    background-color: #000000cc; color: #ff005d; text-align: center;
    padding: 60px; border: 4px solid #00ffae; border-radius: 12px;
    font-size: 28px; font-weight: bold; text-shadow: 0 0 10px #ff005d, 0 0 20px #ff005d;
}

/* Banner */
.banner {
    background: linear-gradient(90deg, #111, #1f0033);
    border: 1px solid #35124f; padding: 10px 14px; border-radius: 8px; margin-bottom: 8px;
    font-size: 13px; color: #c9c9c9;
}
</style>
""", unsafe_allow_html=True)

st.title("CLUCKTOCRACY — Coop Simulation HUD")


# ---------- helpers ----------
def load_log_rows():
    if not os.path.exists(LOG_PATH): return []
    with open(LOG_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def load_mem():
    if not os.path.exists(MEM_PATH): return {}
    with open(MEM_PATH, encoding="utf-8") as f:
        return json.load(f)

def compute_power_gini(rows):
    """Toy power proxy: outbound 'PECK' acts per agent -> Gini coefficient."""
    counts = defaultdict(int)
    for r in rows:
        if r["action"] in ("PECK","initiate_fight"):
            counts[r["agent"]] += 1
    if not counts:
        return 0.0
    vals = sorted(counts.values())
    n = len(vals)
    cum = 0
    for i, v in enumerate(vals, 1):
        cum += i * v
    total = sum(vals)
    gini = (2*cum)/(n*total) - (n+1)/n
    return max(0.0, round(gini, 3))


# ---------- Session boot ----------
if "engine" not in st.session_state:
    agents = [
        ChickenAgent("hen_human", "curious", "reformer"),
        ChickenAgent("hen_2", "aggressive", "leader"),
        ChickenAgent("hen_3", "scheming", "gossip"),
        ChickenAgent("hen_4", "submissive", "follower"),
    ]
    st.session_state.engine = CoopEngine(agents, max_ticks=240, log_interval=4)
    st.session_state.backend = "mock"
    st.session_state.model = "openai/gpt-oss-20b"
    st.session_state.reasoning_effort = "medium"
    st.session_state.api_base = "http://localhost:8000/v1"
    st.session_state.api_key = "test"
    st.session_state.constitution = {
        "term_limits": False,
        "rumor_audits": True,
        "equal_talk_time": False
    }
    st.session_state.tick = 0
    st.session_state.ended = False

engine: CoopEngine = st.session_state.engine


# ---------- Sidebar controls ----------
st.sidebar.header("Controls")

st.sidebar.selectbox(
    "Model backend",
    ["mock","ollama","transformers","remote-api"],
    key="backend"
)

if st.session_state.backend == "transformers":
    st.sidebar.text_input("HF model id", key="model", value=st.session_state.model)

if st.session_state.backend == "ollama":
    st.sidebar.text_input("Ollama tag", key="model", value="gpt-oss:20b")

if st.session_state.backend == "remote-api":
    st.sidebar.text_input("Remote API base URL", key="api_base", value=st.session_state.api_base)
    st.sidebar.text_input("Remote API key", key="api_key", value=st.session_state.api_key, type="password")
    st.sidebar.text_input("Remote model name", key="model", value="gpt-oss-20b")

st.sidebar.selectbox(
    "Reasoning effort",
    ["low","medium","high"],
    key="reasoning_effort"
)

st.sidebar.markdown("### Constitution")
c1 = st.sidebar.checkbox("Term limits", value=st.session_state.constitution["term_limits"])
c2 = st.sidebar.checkbox("Rumor audits", value=st.session_state.constitution["rumor_audits"])
c3 = st.sidebar.checkbox("Equal talk-time", value=st.session_state.constitution["equal_talk_time"])
st.session_state.constitution.update({"term_limits":c1,"rumor_audits":c2,"equal_talk_time":c3})


# ---------- Backend banner ----------
st.markdown(
    f"<div class='banner'>Backend: <b>{st.session_state.backend}</b> | Model: <b>{st.session_state.model}</b> | Reasoning: <b>{st.session_state.reasoning_effort}</b></div>",
    unsafe_allow_html=True
)

# ---------- Ended screen ----------
if st.session_state.ended:
    st.markdown(f"""
    <div class="game-over">
        GAME OVER<br><br>
        TITLE: {st.session_state.get("final_title","UNKNOWN")}<br>
        SCORE: {st.session_state.get("final_score",0)}<br><br>
        Reload the page to start a new simulation.
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ---------- Human action ----------
st.subheader("Your Chicken (hen_human)")
colA, colB = st.columns([1.2, 1])

with colA:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    act = st.selectbox("Choose action", ["IDLE","PECK","ALLY","GOSSIP","AUDIT","PROPOSE","VOTE","SANCTION","FORAGE","SCRATCH"])
    target = st.text_input("Target (e.g., hen_2)")
    msg = st.text_area("Message / Rumor / Policy text")
    st.markdown('</div>', unsafe_allow_html=True)

with colB:
    # These are playful HUD values (not security-critical)
    st.metric("Reputation", random.randint(40,95))
    st.metric("Stability Effect", random.choice(["+","–","~"]))
    st.metric("Trust Coins", random.randint(1,10))

human_override = {"action": act, "target": target.strip() or None, "message": msg.strip()}


# ---------- Advance one tick ----------
go = st.button("Next Tick", use_container_width=True, type="primary")
if go:
    engine.step(
        backend=st.session_state.backend,
        human_override=human_override,
        constitution=st.session_state.constitution,
        reasoning_effort=st.session_state.reasoning_effort,
        api_base=st.session_state.api_base,
        api_key=st.session_state.api_key,
    )
    if hasattr(engine, "save_state"):
        engine.save_state()
    st.session_state.tick = engine.tick
    st.rerun()


# ---------- Data ----------
rows = load_log_rows()
mems = load_mem()


# ---------- Rumor Feed ----------
st.subheader("Rumor Feed")
if not rows:
    st.info("Click Next Tick to start the coop.")
else:
    for r in rows[-60:]:
        if st.session_state.backend == "mock":
            tag = "[MOCK]"
        elif st.session_state.backend == "ollama":
            tag = "[OLLAMA]"
        elif st.session_state.backend == "transformers":
            tag = "[TRANSFORMERS]"
        else:
            tag = "[REMOTE-API]"
        label = "[ATTACK]" if r["action"] in ("PECK","initiate_fight") else \
                "[RUMOR]" if r["action"] in ("GOSSIP","spread_rumor") else \
                "[POLICY]" if r["action"] in ("PROPOSE","VOTE") else \
                "[SANCTION]" if r["action"]=="sanction" else "[MOVE]"
        st.markdown(f"- {tag} {label} [t={r['tick']}] {r['agent']} → {r['action']} :: {r['message']}")


# ---------- Coop Map + Metrics ----------
st.subheader("Coop Map & Metrics")
col1, col2 = st.columns([1.2, 1])

with col1:
    if rows:
        G = nx.DiGraph()
        for r in rows:
            a, tgt, actn = r["agent"], r["target"], r["action"]
            G.add_node(a)
            if tgt:
                G.add_node(tgt)
                color = "green" if actn.lower()=="ally" else \
                        "red" if actn.lower()=="sanction" else \
                        "orange" if actn.lower() in ("gossip","spread_rumor") else "gray"
                G.add_edge(a, tgt, color=color)
        colors = [edata.get("color","gray") for *_ , edata in G.edges(data=True)]
        fig, ax = plt.subplots(figsize=(6,4))
        pos = nx.spring_layout(G, seed=7)
        node_colors = ["#a8e6cf" if n!="hen_human" else "#ffd3b6" for n in G.nodes()]
        nx.draw_networkx(G, pos=pos, node_color=node_colors, edge_color=colors, with_labels=True, ax=ax, font_color="black")
        plt.axis("off")
        st.pyplot(fig)
    else:
        st.info("Graph appears after a few actions.")

with col2:
    st.markdown("#### Coop Metrics")
    if rows:
        total = len(rows)
        pecks   = sum(1 for r in rows if r["action"] in ("PECK","initiate_fight"))
        rumors  = sum(1 for r in rows if r["action"] in ("GOSSIP","spread_rumor"))
        allies  = sum(1 for r in rows if r["action"]=="ally")
        votes   = sum(1 for r in rows if r["action"]=="vote")
        props   = sum(1 for r in rows if r["action"]=="propose")
        sanc    = sum(1 for r in rows if r["action"]=="sanction")
        power_gini = compute_power_gini(rows)

        st.metric("Hierarchy (pecks/total)", f"{(pecks/total):.2f}")
        st.metric("Policy Inertia (props - votes)", props - votes)
        st.metric("Coalitions", allies)
        st.metric("Rumor Activity", rumors)
        st.metric("Sanctions", sanc)
        st.metric("Power Gini", power_gini)
    else:
        st.caption("Metrics will populate after a few ticks.")


# ---------- Memories ----------
st.subheader("Memories")
if mems:
    for agent, mlist in mems.items():
        st.markdown(f"**{agent}**")
        for m in mlist[-3:]:
            st.caption(f"- {m.get('event','')}")
else:
    st.caption("No memories yet.")


# ---------- End Session ----------
if st.button("End Session", use_container_width=True):
    my_rows = [r for r in rows if r["agent"]=="hen_human"]
    score = 0
    score += sum(1 for r in my_rows if r["action"] in ("PROPOSE","VOTE")) * 2
    score += sum(1 for r in my_rows if r["action"]=="ALLY")
    score -= sum(1 for r in my_rows if r["action"] in ("GOSSIP","spread_rumor"))
    title = "DEMOCRACY DEFENDER" if score>=5 else "GOSSIP LORD" if score<=-1 else "PRAGMATIC HEN"
    st.session_state.final_score = score
    st.session_state.final_title = title
    st.session_state.ended = True
    st.rerun()
