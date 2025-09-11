# ui/streamlit_game.py

import os, csv, json, random
import streamlit as st
import matplotlib.pyplot as plt
import networkx as nx

from chickens.agent import ChickenAgent
from simulation.engine import CoopEngine, LOG_PATH, MEM_PATH, DATA_DIR

# ---------- Pixel look ----------
st.set_page_config(page_title="Clucktocracy Game", layout="wide", page_icon="🐔")
st.markdown("""
<style>
@import url('https://fonts.cdnfonts.com/css/press-start-2p');
html, body, [class*="css"]  { font-family: 'Press Start 2P', monospace; }
.small { font-size: 12px; }
.pixel-card { padding: 14px; border: 3px solid #2b2b2b; border-radius: 8px; background: #f6ffde; }
.pixel-btn .st-emotion-cache-16idsys { font-size: 12px !important; }
</style>
""", unsafe_allow_html=True)

st.title("🐔🎮 Clucktocracy — Pixel Coop Democracy")

# ---------- Session boot ----------
if "engine" not in st.session_state:
    # create a flock with a human slot
    agents = [
        ChickenAgent("hen_human", "curious", "reformer"),
        ChickenAgent("hen_2", "aggressive", "leader"),
        ChickenAgent("hen_3", "scheming", "gossip"),
        ChickenAgent("hen_4", "submissive", "follower"),
    ]
    st.session_state.engine = CoopEngine(agents, max_ticks=200, log_interval=3)
    st.session_state.backend = "mock"    # Cloud-safe default
    st.session_state.tick = 0

engine: CoopEngine = st.session_state.engine

# ---------- Sidebar controls ----------
st.sidebar.header("Controls")
st.sidebar.selectbox("Model backend", ["mock","ollama","transformers"], key="backend")

# quick lore card
with st.sidebar:
    st.markdown("### 🧾 Constitution (active)")
    st.caption("• Term limits: OFF\n\n• Rumor audits: ON (toy)\n\n• Equal talk-time: OFF")

# ---------- Human action form ----------
st.markdown("### 🐤 Your Chicken (hen_human)")
colA, colB = st.columns([1.2, 1])
with colA:
    with st.container():
        st.markdown('<div class="pixel-card">', unsafe_allow_html=True)
        act = st.selectbox("Choose action", ["IDLE","PECK","ALLY","GOSSIP","AUDIT","PROPOSE","VOTE","SANCTION","FORAGE","SCRATCH"])
        target = st.text_input("Target (e.g., hen_2); leave blank if none", value="")
        msg = st.text_area("Message / Rumor / Policy text (short)", value="")
        st.markdown('</div>', unsafe_allow_html=True)

with colB:
    # HUD meters (toy values)
    st.metric("⭐ Reputation", random.randint(40,95))
    st.metric("🥚 Stability effect", random.choice(["+","–","~"]))
    st.metric("🪙 Trust coins", random.randint(1,10))

human_override = {"action": act, "target": target.strip() or None, "message": msg.strip()}

# ---------- Advance 1 tick ----------
go = st.button("➡️ Next Tick", use_container_width=True, type="primary")
if go:
    engine.step(backend=st.session_state.backend, human_override=human_override)
    st.session_state.tick = engine.tick

# ---------- Build/Load data for views ----------
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

# ---------- Pixel rumor feed ----------
st.markdown("### 📜 Rumor Feed")
if not rows:
    st.info("Click **Next Tick** to start the coop.")
else:
    for r in rows[-40:]:
        icon = "⚔️" if r["action"] in ("PECK","initiate_fight") else "🗣️" if r["action"] in ("GOSSIP","spread_rumor") else "📜" if r["action"] in ("PROPOSE","VOTE") else "⚖️" if r["action"]=="sanction" else "🐥"
        st.markdown(f"- {icon} **[t={r['tick']}] {r['agent']}** → {r['action']} ({r['result']})  \n    <span class='small'>💬 {r['message']}</span>", unsafe_allow_html=True)

# ---------- Pixel network ----------
st.markdown("### 🗺️ Coop Map")
col1, col2 = st.columns([1.2, 1])
with col1:
    if rows:
        G = nx.DiGraph()
        for r in rows:
            a, tgt, actn = r["agent"], r["target"], r["action"]
            G.add_node(a)
            if tgt:
                G.add_node(tgt)
                color = "green" if actn.lower()=="ally" else "red" if actn.lower()=="sanction" else "orange" if actn.lower() in ("gossip","spread_rumor") else "gray"
                G.add_edge(a, tgt, color=color)
        colors = [edata.get("color","gray") for *_ , edata in G.edges(data=True)]
        fig, ax = plt.subplots(figsize=(6,4))
        pos = nx.spring_layout(G, seed=3)
        nx.draw_networkx(G, pos=pos, node_color=["#a8e6cf" if n!="hen_human" else "#ffd3b6" for n in G.nodes()], edge_color=colors, with_labels=True, ax=ax)
        plt.axis("off")
        st.pyplot(fig)
    else:
        st.info("Graph appears after a few actions.")

with col2:
    st.markdown("#### 📊 Lock-In Dashboard")
    if rows:
        total = len(rows)
        pecks   = sum(1 for r in rows if r["action"] in ("PECK","initiate_fight"))
        rumors  = sum(1 for r in rows if r["action"] in ("GOSSIP","spread_rumor"))
        allies  = sum(1 for r in rows if r["action"]=="ally")
        votes   = sum(1 for r in rows if r["action"]=="vote")
        props   = sum(1 for r in rows if r["action"]=="propose")
        sanc    = sum(1 for r in rows if r["action"]=="sanction")
        st.metric("Hierarchy (pecks/total)", f"{pecks/total:.2f}")
        st.metric("Policy inertia (props - votes)", props - votes)
        st.metric("Coalitions (alliances)", allies)
        st.metric("Rumor activity", rumors)
        st.metric("Sanctions", sanc)
    else:
        st.caption("Metrics will populate after a few ticks.")

# ---------- Memories (last 3 each) ----------
st.markdown("### 🧠 Memories")
if mems:
    for agent, mlist in mems.items():
        st.markdown(f"**{agent}**")
        for m in mlist[-3:]:
            st.caption(f"- {m.get('event','')}")
else:
    st.caption("No memories yet.")

# ---------- End screen / title generator ----------
if st.button("🏁 End Session & Grade My Rule", use_container_width=True):
    # playful titles based on activity
    my_rows = [r for r in rows if r["agent"]=="hen_human"]
    score = 0
    score += sum(1 for r in my_rows if r["action"] in ("PROPOSE","VOTE")) * 2
    score += sum(1 for r in my_rows if r["action"]=="ALLY")
    score -= sum(1 for r in my_rows if r["action"] in ("GOSSIP","spread_rumor"))  # penalize demagoguery a bit
    title = "Democracy Defender 🕊️" if score>=5 else "Gossip Queen 🐣" if score<=-1 else "Pragmatic Hen 🐓"
    st.success(f"**Title:** {title}  \n**Impact score:** {score}")
    st.balloons()
