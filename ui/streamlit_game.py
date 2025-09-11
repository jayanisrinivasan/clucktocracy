import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # add project root to path

import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

from chickens.agent import ChickenAgent
from simulation.engine import CoopEngine

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
if "engine" not in st.session_state:
    # Default chickens
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

engine = st.session_state.engine

# ------------------------------------------
# Sidebar Controls
# ------------------------------------------
st.sidebar.title("Controls")

backend = st.sidebar.selectbox(
    "Model backend",
    ["mock", "ollama", "transformers"],
    index=["mock", "ollama", "transformers"].index(st.session_state.backend)
)
st.session_state.backend = backend

model_name = st.sidebar.text_input(
    "Model (for ollama / transformers)",
    value=st.session_state.model
)
st.session_state.model = model_name

reasoning = st.sidebar.radio(
    "Reasoning Effort",
    ["low", "medium", "high"],
    index=["low", "medium", "high"].index(st.session_state.reasoning_effort)
)
st.session_state.reasoning_effort = reasoning

if backend == "ollama":
    api_base = st.sidebar.text_input("Ollama API base", value="http://localhost:11434/v1")
    api_key = st.sidebar.text_input("Ollama API key (optional)", type="password")
else:
    api_base, api_key = None, None

# ------------------------------------------
# Title
# ------------------------------------------
st.markdown(
    """
    <h1 style='color:#ff4b4b;'>🎮 Clucktocracy — Pixel Coop Democracy</h1>
    """,
    unsafe_allow_html=True
)

# ------------------------------------------
# Human Player UI
# ------------------------------------------
st.subheader("🐥 Your Chicken (hen_human)")

with st.form("human_action"):
    col1, col2, col3 = st.columns(3)
    with col1:
        action = st.selectbox("Choose action", ["IDLE"] + [
            "peck", "spread_rumor", "propose", "vote", "ally", "sanction", "wander"
        ])
    with col2:
        target = st.text_input("Target (e.g., hen_2)")
    with col3:
        message = st.text_input("Message / Rumor / Policy (short)")

    submitted = st.form_submit_button("➡️ Next Tick")

if submitted:
    st.session_state.tick += 1
    tick = st.session_state.tick

    human_action = []
    if action != "IDLE":
        human_action.append({
            "agent": "hen_human",
            "action": action,
            "message": message or ""
        })

    rows = engine.step(
        actions=human_action,
        backend=st.session_state.backend,
        model=st.session_state.model,
        reasoning_effort=st.session_state.reasoning_effort,
        api_base=api_base,
        api_key=api_key,
        tick=tick
    )
    st.session_state.last_rows = rows

# ------------------------------------------
# Rumor Feed
# ------------------------------------------
st.subheader("📜 Rumor Feed & Actions")

if "last_rows" in st.session_state:
    for row in st.session_state.last_rows:
        st.markdown(
            f"**[Tick {row['tick']}] {row['agent']} → {row['action']} ({row['outcome']})**  "
            f"<br>💬 {row.get('message','')}",
            unsafe_allow_html=True
        )
else:
    st.info("Click **Next Tick** to start the coop.")

# ------------------------------------------
# Coop Map
# ------------------------------------------
st.subheader("🌐 Coop Map")

# Keep full history in session_state
if "all_rows" not in st.session_state:
    st.session_state.all_rows = []

# Add latest tick rows to history
if "last_rows" in st.session_state:
    st.session_state.all_rows.extend(st.session_state.last_rows)

G = nx.DiGraph()

# Color map for actions
action_colors = {
    "peck": "red",
    "spread_rumor": "purple",
    "ally": "green",
    "sanction": "orange",
}

# Build network with colored edges
edge_colors = []
for h in st.session_state.all_rows:
    G.add_node(h["agent"])
    if h.get("action") in action_colors:
        target = h.get("target")
        if target:
            G.add_edge(h["agent"], target, label=h["action"])
            edge_colors.append(action_colors[h["action"]])

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
    st.pyplot(plt)
else:
    st.info("No interactions yet. Play a few ticks to see the coop network.")

# ------------------------------------------
# Sidebar Legend
# ------------------------------------------
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
# Memory Snapshots
# ------------------------------------------
st.subheader("🧠 Memories")
for agent in engine.agents:
    st.markdown(f"**{agent.name}**")
    if agent.memory:
        for m in agent.memory:
            st.markdown(f"- {m}")
    else:
        st.markdown("_No memories yet_")

# ------------------------------------------
# Coop Metrics
# ------------------------------------------
st.subheader("📊 Coop Metrics")

if "engine" in st.session_state:
    engine = st.session_state.engine
    metrics = engine.compute_metrics()

    # Show key indicators
    cols = st.columns(5)
    cols[0].metric("Hierarchy steepness", metrics["hierarchy_steepness"])
    cols[1].metric("Policy inertia", metrics["policy_inertia"])
    cols[2].metric("Coalitions", metrics["coalitions"])
    cols[3].metric("Rumors", metrics["rumors"])
    cols[4].metric("Sanctions", metrics["sanctions"])

    # Plot trends over time
    if len(engine.metrics_history) > 1:
        import pandas as pd
        import matplotlib.pyplot as plt

        df = pd.DataFrame(engine.metrics_history)

        st.markdown("### 📈 Trends Over Time")

        fig, ax = plt.subplots(figsize=(8, 4))
        for col in ["hierarchy_steepness", "policy_inertia", "coalitions", "rumors", "sanctions"]:
            ax.plot(df["tick"], df[col], label=col)

        ax.set_xlabel("Tick")
        ax.set_ylabel("Value")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.6)
        st.pyplot(fig)
else:
    st.info("Run the simulation to see metrics.")

