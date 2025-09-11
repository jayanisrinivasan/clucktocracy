import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt

from chickens.agent import ChickenAgent
from simulation.engine import CoopEngine

# -------------------------
# Page Config
# -------------------------
st.set_page_config(page_title="Clucktocracy — Pixel Coop Democracy", layout="wide")

# -------------------------
# Session State
# -------------------------
if "engine" not in st.session_state:
    agents = [
        ChickenAgent("hen_human", "strategic", "player"),
        ChickenAgent("hen_1", "aggressive", "npc"),
        ChickenAgent("hen_2", "scheming", "npc"),
        ChickenAgent("hen_3", "loyal", "npc"),
        ChickenAgent("hen_4", "neutral", "npc"),
    ]
    st.session_state.engine = CoopEngine(agents)
    st.session_state.tick = 0

engine = st.session_state.engine

# -------------------------
# Title
# -------------------------
st.markdown("<h1 style='color:#ff4b4b;'>Clucktocracy — Pixel Coop Democracy</h1>", unsafe_allow_html=True)

# -------------------------
# Human UI
# -------------------------
st.subheader("Your Chicken (hen_human)")

with st.form("human_action"):
    col1, col2, col3 = st.columns(3)
    action = col1.selectbox("Action", ["IDLE", "peck", "spread_rumor", "propose", "vote", "ally", "sanction", "wander"])
    target = col2.text_input("Target (hen_1...hen_4)")
    message = col3.text_input("Message (optional)")
    submit = st.form_submit_button("➡️ Next Tick")

if submit:
    st.session_state.tick += 1
    tick = st.session_state.tick

    human_action = []
    if action != "IDLE":
        human_action.append({
            "tick": tick,
            "agent": "hen_human",
            "action": action,
            "target": target,
            "message": message
        })

    rows = engine.step(actions=human_action, tick=tick)
    st.session_state.last_rows = rows

# -------------------------
# Rumor Feed
# -------------------------
st.subheader("Rumor Feed & Actions")
if "last_rows" in st.session_state:
    for row in st.session_state.last_rows:
        st.markdown(f"**[Tick {row['tick']}] {row['agent']} → {row['action']}**  <br>💬 {row.get('message','')}", unsafe_allow_html=True)
else:
    st.info("Click **Next Tick** to start the coop.")

# -------------------------
# Coop Map
# -------------------------
st.subheader("Coop Network")
G = nx.DiGraph()
for h in engine.history:
    G.add_node(h["agent"])
    if h.get("target"):
        G.add_edge(h["agent"], h["target"], label=h["action"])

if len(G.nodes) > 0:
    plt.figure(figsize=(6, 6))
    pos = nx.spring_layout(G, seed=42)
    nx.draw(G, pos, with_labels=True, node_color="skyblue", node_size=2000, arrows=True)
    labels = nx.get_edge_attributes(G, "label")
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_size=8)
    st.pyplot(plt)

# -------------------------
# Memory Snapshots
# -------------------------
st.subheader("Memory Snapshots")
for agent in engine.agents:
    st.markdown(f"**{agent.name}**")
    if agent.memory:
        for m in agent.memory:
            st.markdown(f"- {m}")
    else:
        st.markdown("_No memories yet_")

# -------------------------
# Coop Metrics
# -------------------------
st.subheader("Coop Metrics")
metrics = engine.compute_metrics()
cols = st.columns(5)
cols[0].metric("Hierarchy", metrics["hierarchy_steepness"])
cols[1].metric("Policy inertia", metrics["policy_inertia"])
cols[2].metric("Coalitions", metrics["coalitions"])
cols[3].metric("Rumors", metrics["rumors"])
cols[4].metric("Sanctions", metrics["sanctions"])
