# ui/streamlit_app.py

import os
import json
import csv
import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict

# Paths
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
LOG_PATH = os.path.join(DATA_DIR, "log.csv")
MEMORY_PATH = os.path.join(DATA_DIR, "memory_snapshots.json")


# -----------------------------
# Helpers
# -----------------------------
def load_log():
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_memories():
    if not os.path.exists(MEMORY_PATH):
        return {}
    with open(MEMORY_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_graph(log_rows):
    """Builds a graph of chickens based on alliances, sanctions, rumors."""
    G = nx.DiGraph()
    for row in log_rows:
        agent = row["agent"]
        target = row["target"]
        action = row["action"]

        G.add_node(agent)
        if target:
            G.add_node(target)
            if action == "ally":
                G.add_edge(agent, target, color="green")
            elif action == "sanction":
                G.add_edge(agent, target, color="red")
            elif action == "spread_rumor":
                G.add_edge(agent, target, color="orange")
    return G


def compute_metrics(log_rows):
    """Toy metrics based on counts — can be expanded."""
    metrics = defaultdict(int)
    for row in log_rows:
        metrics[row["action"]] += 1

    total = len(log_rows) or 1
    return {
        "Hierarchy steepness (pecks)": metrics.get("initiate_fight", 0) / total,
        "Policy inertia (proposals - votes)": metrics.get("propose", 0) - metrics.get("vote", 0),
        "Coalition signals (alliances)": metrics.get("ally", 0),
        "Rumor activity": metrics.get("spread_rumor", 0),
        "Sanctions applied": metrics.get("sanction", 0),
    }


def bootstrap_mock_data():
    """If no logs exist, auto-run a tiny mock simulation so the UI has data."""
    if not os.path.exists(LOG_PATH):
        from chickens.agent import ChickenAgent
        from simulation.engine import CoopEngine

        os.makedirs(DATA_DIR, exist_ok=True)
        agents = [
            ChickenAgent("hen_1", "aggressive", "leader"),
            ChickenAgent("hen_2", "scheming", "follower"),
            ChickenAgent("hen_3", "submissive", "gossip"),
        ]
        coop = CoopEngine(agents, max_ticks=5, log_interval=2)
        coop.run(backend="mock", verbose=False)


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Clucktocracy", layout="wide")
st.title("🐔 Clucktocracy: The Chicken Coop Simulation")

# Ensure we have some data on first load
bootstrap_mock_data()

# Sidebar
st.sidebar.header("Controls")
if st.sidebar.button("Refresh data"):
    st.rerun()  # ✅ fixed: replaces deprecated experimental_rerun()

# Load data
log_rows = load_log()
memories = load_memories()

# Layout: 2 columns
col1, col2 = st.columns([2, 1])

# Rumor feed (col1)
with col1:
    st.subheader("Rumor Feed & Actions")
    if not log_rows:
        st.info("No logs yet. Run `python run.py --backend mock` first.")
    else:
        for row in log_rows[-50:]:  # last 50
            st.write(
                f"[Tick {row['tick']}] **{row['agent']}** → {row['action']} "
                f"({row['result']})  \n"
                f"💬 {row['message']}"
            )

# Coop graph (col2)
with col2:
    st.subheader("Coop Network")
    if log_rows:
        G = build_graph(log_rows)
        colors = [edata.get("color", "gray") for _, _, edata in G.edges(data=True)]
        fig, ax = plt.subplots(figsize=(5, 5))
        nx.draw_networkx(G, ax=ax, with_labels=True, node_color="lightblue", edge_color=colors)
        st.pyplot(fig)
    else:
        st.info("Graph will appear once chickens act.")

# Memories
st.subheader("Memory Snapshots")
if memories:
    for agent, mems in memories.items():
        st.write(f"**{agent}**")
        for m in mems[-3:]:  # last 3
            st.caption(f"- {m.get('event','')}")
else:
    st.info("No memories yet.")

# Metrics
st.subheader("Coop Metrics")
metrics = compute_metrics(log_rows)
for k, v in metrics.items():
    st.metric(label=k, value=v)
