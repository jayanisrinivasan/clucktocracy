# ui/streamlit_game.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # add project root to path

import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

from chickens.agent import ChickenAgent
from simulation.engine import CoopEngine  # must expose step(...), optionally compute_metrics()

# ------------------------------------------
# Page Config
# ------------------------------------------
st.set_page_config(
    page_title="Clucktocracy — Pixel Coop Democracy",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------
# Session State Initialization
# ------------------------------------------
def _init_session():
    agents = [
        ChickenAgent("hen_human", "strategic", "player"),
        ChickenAgent("hen_1", "aggressive", "fighter"),
        ChickenAgent("hen_2", "scheming", "gossip"),
        ChickenAgent("hen_3", "loyal", "ally"),
        ChickenAgent("hen_4", "neutral", "wanderer"),
    ]
    st.session_state.engine = CoopEngine(agents)
    st.session_state.tick = 0
    st.session_state.backend = "mock"
    st.session_state.model = "openai/gpt-oss-20b"
    st.session_state.reasoning_effort = "medium"
    st.session_state.last_rows = []
    st.session_state.all_rows = []           # accumulated history for the graph
    st.session_state._last_merged_tick = -1  # guard so we only merge once per tick

if "engine" not in st.session_state:
    _init_session()

engine = st.session_state.engine

# ------------------------------------------
# Sidebar Controls
# ------------------------------------------
st.sidebar.title("Controls")

# Reset
if st.sidebar.button("Reset simulation", use_container_width=True):
    _init_session()
    st.rerun()

backend = st.sidebar.selectbox(
    "Model backend",
    ["mock", "ollama", "transformers"],
    index=["mock", "ollama", "transformers"].index(st.session_state.backend),
)
st.session_state.backend = backend

model_name = st.sidebar.text_input(
    "Model (for ollama / transformers)",
    value=st.session_state.model,
)
st.session_state.model = model_name

reasoning = st.sidebar.radio(
    "Reasoning Effort",
    ["low", "medium", "high"],
    index=["low", "medium", "high"].index(st.session_state.reasoning_effort),
)
st.session_state.reasoning_effort = reasoning

if backend == "ollama":
    api_base = st.sidebar.text_input("Ollama API base", value="http://localhost:11434/v1")
    api_key = st.sidebar.text_input("Ollama API key (optional)", type="password")
else:
    api_base, api_key = None, None

# Legend (always visible)
st.sidebar.markdown("### Coop Map Legend")
st.sidebar.markdown(
    """
    - <span style="color:red;">**Red**</span>: Peck (fight)  
    - <span style="color:purple;">**Purple**</span>: Spread Rumor  
    - <span style="color:green;">**Green**</span>: Ally (coalition)  
    - <span style="color:orange;">**Orange**</span>: Sanction
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------
# Title
# ------------------------------------------
st.markdown(
    "<h1 style='color:#ff4b4b;'>🎮 Clucktocracy — Pixel Coop Democracy</h1>",
    unsafe_allow_html=True,
)

# ------------------------------------------
# Human Player UI
# ------------------------------------------
st.subheader("🐥 Your Chicken (hen_human)")

with st.form("human_action"):
    col1, col2, col3 = st.columns(3)
    with col1:
        action = st.selectbox(
            "Choose action",
            ["IDLE", "peck", "spread_rumor", "propose", "vote", "ally", "sanction", "wander"],
        )
    with col2:
        target = st.text_input("Target (e.g., hen_2)")
    with col3:
        message = st.text_input("Message / Rumor / Policy (short)")

    submitted = st.form_submit_button("➡️ Next Tick", use_container_width=True)

if submitted:
    st.session_state.tick += 1
    tick = st.session_state.tick

    human_actions = []
    if action != "IDLE":
        payload = {
            "agent": "hen_human",
            "action": action,
            "message": message or "",
        }
        if target:
            payload["target"] = target
        human_actions.append(payload)

    # Run one tick of the engine (CoopEngine must accept these kwargs)
    rows = engine.step(
        actions=human_actions,
        backend=st.session_state.backend,
        model=st.session_state.model,
        reasoning_effort=st.session_state.reasoning_effort,
        api_base=api_base,
        api_key=api_key,
        tick=tick,
    )
    st.session_state.last_rows = rows

# ------------------------------------------
# Rumor Feed
# ------------------------------------------
st.subheader("📜 Rumor Feed & Actions")

if st.session_state.last_rows:
    for row in st.session_state.last_rows:
        txt = (
            f"**[Tick {row.get('tick','?')}] {row.get('agent','?')} → "
            f"{row.get('action','?')} ({row.get('outcome','?')})**"
        )
        msg = row.get("message", "")
        if msg:
            txt += f"<br>💬 {msg}"
        st.markdown(txt, unsafe_allow_html=True)
else:
    st.info("Click **Next Tick** to start the coop.")

# ------------------------------------------
# Coop Map (accumulates safely)
# ------------------------------------------
st.subheader("🌐 Coop Map")

# Merge the latest tick rows into the full history **once per tick**
if st.session_state.tick != st.session_state._last_merged_tick and st.session_state.last_rows:
    st.session_state.all_rows.extend(st.session_state.last_rows)
    st.session_state._last_merged_tick = st.session_state.tick

G = nx.DiGraph()

action_colors = {
    "peck": "red",
    "spread_rumor": "purple",
    "ally": "green",
    "sanction": "orange",
}

edge_list = []
edge_colors = []

for h in st.session_state.all_rows:
    src = h.get("agent")
    act = h.get("action")
    tgt = h.get("target")

    if src:
        G.add_node(src)
    if tgt:
        G.add_node(tgt)

    if act in action_colors and src and tgt:
        edge_list.append((src, tgt, {"label": act}))
        edge_colors.append(action_colors[act])

# add edges with labels
G.add_edges_from(edge_list)

if len(G.nodes) > 0:
    plt.figure(figsize=(6, 6))
    pos = nx.spring_layout(G, seed=42)

    nx.draw(
        G,
        pos,
        with_labels=True,
        node_color="skyblue",
        node_size=1800,
        font_size=10,
        font_weight="bold",
        arrows=True,
        edge_color=edge_colors if edge_colors else "gray",
        width=2,
        arrowsize=20,
    )

    labels = nx.get_edge_attributes(G, "label")
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_size=8)
    st.pyplot(plt.gcf())
else:
    st.info("No interactions yet. Play a few ticks to see the coop network.")

# ------------------------------------------
# Memory Snapshots
# ------------------------------------------
st.subheader("🧠 Memories")
for agent in getattr(engine, "agents", []):
    st.markdown(f"**{agent.name}**")
    if getattr(agent, "memory", []):
        for m in agent.memory[-8:]:
            st.markdown(f"- {m}")
    else:
        st.markdown("_No memories yet_")

# ------------------------------------------
# Coop Metrics (safe if engine doesn't expose compute_metrics/metrics_history)
# ------------------------------------------
st.subheader("📊 Coop Metrics")

if hasattr(engine, "compute_metrics"):
    metrics = engine.compute_metrics()

    # Show key indicators
    cols = st.columns(5)
    cols[0].metric("Hierarchy steepness", metrics.get("hierarchy_steepness", 0))
    cols[1].metric("Policy inertia", metrics.get("policy_inertia", 0))
    cols[2].metric("Coalitions", metrics.get("coalitions", 0))
    cols[3].metric("Rumors", metrics.get("rumors", 0))
    cols[4].metric("Sanctions", metrics.get("sanctions", 0))

    # Trend chart (if engine tracks metrics_history)
    if hasattr(engine, "metrics_history") and len(engine.metrics_history) > 1:
        df = pd.DataFrame(engine.metrics_history)
        if "tick" not in df.columns:
            df["tick"] = range(len(df))
        st.markdown("### 📈 Trends Over Time")

        fig, ax = plt.subplots(figsize=(8, 4))
        for col in ["hierarchy_steepness", "policy_inertia", "coalitions", "rumors", "sanctions"]:
            if col in df.columns:
                ax.plot(df["tick"], df[col], label=col)

        ax.set_xlabel("Tick")
        ax.set_ylabel("Value")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.6)
        st.pyplot(fig)
else:
    st.info("Metrics will appear when the engine exposes compute_metrics().")
