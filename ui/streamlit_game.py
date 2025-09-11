# ui/streamlit_game.py
"""
Streamlit UI for Clucktocracy — Coop Simulation HUD
Dark cyberpunk / gamer style HUD + Game Over splash screen
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import csv, json, random
import streamlit as st
import matplotlib.pyplot as plt
import networkx as nx

from chickens.agent import ChickenAgent
from simulation.engine import CoopEngine, LOG_PATH, MEM_PATH

# ---------- Style ----------
st.set_page_config(page_title="Clucktocracy", layout="wide")

st.markdown("""
<style>
/* Global dark theme */
html, body, [class*="css"] {
    background-color: #0e0e10;
    color: #e0e0e0;
    font-family: 'Orbitron', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #1a1a1d;
}

/* Buttons */
.stButton>button {
    background-color: #ff005d;
    color: white;
    font-weight: bold;
    border-radius: 6px;
    border: none;
    padding: 8px 16px;
    transition: 0.2s;
}
.stButton>button:hover {
    background-color: #ff3369;
    transform: scale(1.05);
}

/* Metrics */
[data-testid="stMetricValue"] {
    color: #00ffae;
    font-size: 22px;
}

/* Cards */
.pixel-card {
    background: #16161a;
    border: 2px solid #00ffae;
    padding: 12px;
    border-radius: 8px;
}

/* Headings */
h1, h2, h3 {
    color: #ff005d;
}

/* Game Over splash */
.game-over {
    background-color: #000000cc;
    color: #ff005d;
    text-align: center;
    padding: 60px;
    border: 4px solid #00ffae;
    border-radius: 12px;
    font-size: 28px;
    font-weight: bold;
    text-shadow: 0 0 10px #ff005d, 0 0 20px #ff005d;
}
</style>
""", unsafe_allow_html=True)

st.title("CLUCKTOCRACY — Coop Simulation HUD")

# ---------- Session boot ----------
if "engine" not in st.session_state:
    agents = [
        ChickenAgent("hen_human", "curious", "reformer"),
        ChickenAgent("hen_2", "aggressive", "leader"),
        ChickenAgent("hen_3", "scheming", "gossip"),
        ChickenAgent("hen_4", "submissive", "follower"),
    ]
    st.session_state.engine = CoopEngine(agents, max_ticks=200, log_interval=3)
    st.session_state.backend = "mock"
    st.session_state.tick = 0
    st.session_state.ended = False

engine: CoopEngine = st.session_state.engine

# ---------- Sidebar controls ----------
st.sidebar.header("Controls")
st.sidebar.selectbox("Model backend", ["mock", "ollama", "transformers"], key="backend")

with st.sidebar:
    st.markdown("### Active Constitution")
    st.caption("• Term limits: OFF\n• Rumor audits: ON\n• Equal talk-time: OFF")

# ---------- If session ended ----------
if st.session_state.ended:
    st.markdown(f"""
    <div class="game-over">
        GAME OVER<br><br>
        TITLE: {st.session_state.get("final_title","UNKNOWN")}<br>
        SCORE: {st.session_state.get("final_score",0)}<br><br>
        Refresh to start a new simulation.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ---------- Human action ----------
st.markdown("### Your Chicken (hen_human)")
colA, colB = st.columns([1.2, 1])
with colA:
    with st.container():
        st.markdown('<div class="pixel-card">', unsafe_allow_html=True)
        act = st.selectbox("Choose action", ["IDLE","PECK","ALLY","GOSSIP","AUDIT","PROPOSE","VOTE","SANCTION","FORAGE","SCRATCH"])
        target = st.text_input("Target (e.g., hen_2)")
        msg = st.text_area("Message / Rumor / Policy text")
        st.markdown('</div>', unsafe_allow_html=True)

with colB:
    st.metric("Reputation", random.randint(40,95))
    st.metric("Stability Effect", random.choice(["+","–","~"]))
    st.metric("Trust Coins", random.randint(1,10))

human_override = {"action": act, "target": target.strip() or None, "message": msg.strip()}

# ---------- Advance tick ----------
go = st.button("Next Tick", use_container_width=True, type="primary")
if go:
    engine.step(backend=st.session_state.backend, human_override=human_override)
    if hasattr(engine, "save_state"):
        engine.save_state()  # ensure logs/mem flush
    st.session_state.tick = engine.tick
    st.rerun()  # refresh rumor feed + UI instantly

# ---------- Load log/mem ----------
def load_log_rows():
    if not os.path.exists(LOG_PATH): return []
    with open(LOG_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def load_mem():
    if not os.path.exists(MEM_PATH): return {}
    with open(MEM_PATH, encoding="utf-8") as f:
        return json.load(f)

rows = load_log_rows()
mems = load_mem()

# ---------- Rumor Feed ----------
st.markdown("### Rumor Feed")
if not rows:
    st.info("Click Next Tick to start the coop.")
else:
    for r in rows[-40:]:
        label = "[ATTACK]" if r["action"] in ("PECK","initiate_fight") else \
                "[RUMOR]" if r["action"] in ("GOSSIP","spread_rumor") else \
                "[POLICY]" if r["action"] in ("PROPOSE","VOTE") else \
                "[SANCTION]" if r["action"]=="sanction" else "[MOVE]"
        st.markdown(f"- {label} [t={r['tick']}] {r['agent']} → {r['action']} :: {r['message']}")

# ---------- Coop Map ----------
st.markdown("### Coop Map")
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
        pos = nx.spring_layout(G, seed=3)
        nx.draw_networkx(G, pos=pos, node_color=["#a8e6cf" if n!="hen_human" else "#ffd3b6" for n in G.nodes()],
                         edge_color=colors, with_labels=True, ax=ax, font_color="black")
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
        st.metric("Hierarchy (pecks/total)", f"{pecks/total:.2f}")
        st.metric("Policy Inertia (props - votes)", props - votes)
        st.metric("Coalitions", allies)
        st.metric("Rumor Activity", rumors)
        st.metric("Sanctions", sanc)
    else:
        st.caption("Metrics will populate after a few ticks.")

# ---------- Memories ----------
st.markdown("### Memories")
if mems:
    for agent, mlist in mems.items():
        st.markdown(f"**{agent}**")
        for m in mlist[-3:]:
            st.caption(f"- {m.get('event','')}")
else:
    st.caption("No memories yet.")

# ---------- End screen ----------
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
    st.rerun()  # ✅ use stable rerun
