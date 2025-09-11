import streamlit as st
import matplotlib.pyplot as plt
from simulation.engine import CoopEngine
from chickens.agent import ChickenAgent
from gpt.inference import generate_ai_actions

# ----------------------------
# Page Setup
# ----------------------------
st.set_page_config(page_title="Clucktocracy — Pixel Coop Democracy", layout="wide")

# Inject Custom CSS (retro gamer style)
st.markdown(
    """
    <style>
    body, .stApp {
        background-color: #121212;
        color: #E0E0E0;
        font-family: 'Press Start 2P', monospace;
    }
    h1 {
        font-size: 32px !important;
        text-align: center;
        color: #FF4B4B;
        text-shadow: 2px 2px #000;
    }
    h2, h3 {
        color: #FFD700 !important;
        text-shadow: 1px 1px #000;
    }
    section[data-testid="stSidebar"] {
        background-color: #1E1E1E;
    }
    section[data-testid="stSidebar"] * {
        color: #E0E0E0 !important;
    }
    button {
        background: linear-gradient(90deg, #FF4B4B, #FF9900);
        border: none;
        border-radius: 6px;
        color: white !important;
        font-weight: bold;
        padding: 8px 16px;
        transition: 0.2s;
    }
    button:hover {
        background: linear-gradient(90deg, #FF9900, #FF4B4B);
        transform: scale(1.05);
    }
    .rumor-feed {
        background: #1E1E1E;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #333;
        font-size: 12px;
        line-height: 1.4em;
    }
    .memory-block {
        background: #202020;
        padding: 8px 12px;
        margin-bottom: 6px;
        border-left: 3px solid #FF4B4B;
        border-radius: 4px;
    }
    .metric-box {
        background: #181818;
        padding: 10px;
        margin: 5px 0;
        border-radius: 6px;
        border: 1px solid #333;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Title
st.title("Clucktocracy — Pixel Coop Democracy")

# ----------------------------
# Initialize Coop
# ----------------------------
if "engine" not in st.session_state:
    agents = [
        ChickenAgent("hen_1", "aggressive", "fighter"),
        ChickenAgent("hen_2", "scheming", "gossip"),
        ChickenAgent("hen_3", "submissive", "follower"),
        ChickenAgent("hen_4", "zen", "neutral"),
    ]
    engine = CoopEngine(agents)
    st.session_state.engine = engine
    st.session_state.tick = 0
    st.session_state.rumors = []
    st.session_state.human_actions = []

engine: CoopEngine = st.session_state.engine

# ----------------------------
# Sidebar Controls
# ----------------------------
st.sidebar.header("Controls")
backend = st.sidebar.selectbox("Model backend", ["mock", "ollama", "transformers"])
model_choice = st.sidebar.selectbox("Model", ["openai/gpt-oss-20b", "openai/gpt-oss-120b"])
reasoning = st.sidebar.radio("Reasoning Effort", ["low", "medium", "high"])
api_base = st.sidebar.text_input("API Base", "http://localhost:11434/v1")
api_key = st.sidebar.text_input("API Key", type="password")

st.sidebar.markdown(f"**Backend selected:** {backend}")
if st.sidebar.button("End Session"):
    st.session_state.ended = True

# ----------------------------
# Pixel Map Renderer
# ----------------------------
def render_pixel_map(agents):
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)

    colors = ["#FF4B4B", "#4B7BFF", "#3CB043", "#FFD700", "#FF69B4"]
    for i, a in enumerate(agents):
        x, y = (i % 5) * 2 + 1, (i // 5) * 2 + 1
        ax.scatter(x, y, c=colors[i % len(colors)], s=800, marker="o", edgecolors="white", linewidths=1.5)
        ax.text(x, y + 0.5, a.name, ha="center", color="white", fontsize=8, fontweight="bold")

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_facecolor("#1E1E1E")
    st.pyplot(fig)

# ----------------------------
# Player (Human Chicken)
# ----------------------------
st.subheader("Your Chicken (hen_human)")
col1, col2, col3 = st.columns(3)
with col1:
    action = st.selectbox("Choose action", ["IDLE", "PECK", "RUMOR", "ALLY", "PROPOSE", "VOTE", "SANCTION"])
with col2:
    target = st.text_input("Target (e.g., hen_2)")
with col3:
    message = st.text_input("Message / Rumor / Policy text")

if st.button("➡️ Next Tick"):
    st.session_state.human_actions.append({
        "tick": st.session_state.tick,
        "agent": "hen_human",
        "action": action,
        "target": target,
        "message": message
    })

    # --- AI Actions (via GPT) ---
    ai_actions = generate_ai_actions(
        agents=engine.agents,
        backend=backend,
        model=model_choice,
        reasoning_effort=reasoning,
        api_base=api_base,
        api_key=api_key,
        tick=st.session_state.tick
    )

    all_actions = st.session_state.human_actions + ai_actions

    # Run one tick of the engine
    rows = engine.step(actions=all_actions)
    st.session_state.rumors.extend(rows)
    st.session_state.tick += 1
    st.session_state.human_actions = []  # reset

# ----------------------------
# Layout
# ----------------------------
left, right = st.columns([2, 1])
with left:
    st.subheader("Rumor Feed & Actions")
    if not st.session_state.rumors:
        st.info("Click **Next Tick** to start the coop.")
    else:
        for row in st.session_state.rumors[-10:]:
            st.markdown(
                f"""
                <div class="rumor-feed">
                [Tick {row['tick']}] <b>{row['agent']}</b> → {row['action']} ({row['outcome']})<br>
                {row.get('message','')}
                </div>
                """,
                unsafe_allow_html=True,
            )

with right:
    st.subheader("Coop Map")
    render_pixel_map(engine.agents)

# ----------------------------
# Memories
# ----------------------------
st.subheader("Memories")
for agent in engine.agents:
    st.markdown(f"<h4>{agent.name}</h4>", unsafe_allow_html=True)
    if agent.memory:
        for m in agent.memory[-3:]:
            st.markdown(f"<div class='memory-block'>{m}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='memory-block'>(no memories yet)</div>", unsafe_allow_html=True)

# ----------------------------
# Metrics
# ----------------------------
st.subheader("Coop Metrics")
metrics = engine.compute_metrics()
for k, v in metrics.items():
    st.markdown(f"<div class='metric-box'><b>{k}</b>: {v}</div>", unsafe_allow_html=True)
