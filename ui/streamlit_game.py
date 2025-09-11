# ui/streamlit_game.py
import sys, os, csv, json, random
from collections import defaultdict
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from chickens.agent import ChickenAgent
from chickens.scenarios import SCENARIOS
from chickens.personalities import CHICKEN_ARCHETYPES
from simulation.engine import CoopEngine, LOG_PATH, MEM_PATH
from ui.pixel_map import render_pixel_map
from gpt.inference import run_inference

# ---------- Page & Theme ----------
st.set_page_config(page_title="Clucktocracy", layout="wide")

st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #0e0e10;
    color: #e0e0e0;
    font-family: 'Orbitron', sans-serif;
}
[data-testid="stSidebar"] { background-color: #1a1a1d; }

.stButton>button {
    background-color: #ff005d; color: white; font-weight: bold;
    border-radius: 6px; border: none; padding: 8px 16px; transition: 0.2s;
}
.stButton>button:hover { background-color: #ff3369; transform: scale(1.05); }

[data-testid="stMetricValue"] { color: #00ffae; font-size: 22px; }

.card {
    background: #16161a; border: 2px solid #00ffae; padding: 12px; border-radius: 8px;
}

h1, h2, h3 { color: #ff005d; }

.game-over {
    background-color: #000000cc; color: #ff005d; text-align: center;
    padding: 40px; border: 4px solid #00ffae; border-radius: 12px;
    font-size: 26px; font-weight: bold; text-shadow: 0 0 10px #ff005d, 0 0 20px #ff005d;
}

.banner {
    background: linear-gradient(90deg, #111, #1f0033);
    border: 1px solid #35124f; padding: 10px 14px; border-radius: 8px; margin-bottom: 8px;
    font-size: 13px; color: #c9c9c9;
}
</style>
""", unsafe_allow_html=True)

st.title("CLUCKTOCRACY — Coop Simulation HUD")

# ---------- Helpers ----------
def load_log_rows():
    if not os.path.exists(LOG_PATH): return []
    with open(LOG_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def load_mem():
    if not os.path.exists(MEM_PATH): return {}
    with open(MEM_PATH, encoding="utf-8") as f:
        return json.load(f)

# ---------- Sidebar ----------
st.sidebar.header("Scenario")
scenario_name = st.sidebar.selectbox("Scenario", [s["name"] for s in SCENARIOS] + ["Custom"])

st.sidebar.header("Backend")
backend = st.sidebar.selectbox("Model backend", ["mock","ollama","transformers","remote-api"], key="backend")
model = st.sidebar.text_input("Model name", value="openai/gpt-oss-20b", key="model")
reasoning_effort = st.sidebar.selectbox("Reasoning effort", ["low","medium","high"], key="reasoning_effort")
api_base = st.sidebar.text_input("API base", value="http://localhost:8000/v1", key="api_base")
api_key = st.sidebar.text_input("API key", value="test", type="password", key="api_key")

st.sidebar.header("Constitution")
c1 = st.sidebar.checkbox("Term limits", value=False)
c2 = st.sidebar.checkbox("Rumor audits", value=True)
c3 = st.sidebar.checkbox("Equal talk-time", value=False)

# ---------- Session Init ----------
if "engine" not in st.session_state:
    agents = [ChickenAgent("hen_human", "curious", "reformer")]
    if scenario_name != "Custom":
        scenario = next(s for s in SCENARIOS if s["name"]==scenario_name)
        for arche in scenario["chickens"]:
            agents.append(ChickenAgent(**arche))
        st.session_state.constitution = dict(scenario["constitution"])
    else:
        chosen = random.sample(CHICKEN_ARCHETYPES, 3)
        for arche in chosen:
            agents.append(ChickenAgent(**arche))
        st.session_state.constitution = {"term_limits": c1,"rumor_audits": c2,"equal_talk_time": c3}
    st.session_state.engine = CoopEngine(agents, max_ticks=240, log_interval=4)

st.session_state.setdefault("tick",0)
st.session_state.setdefault("ended",False)
engine: CoopEngine = st.session_state.engine
st.session_state.constitution.update({"term_limits": c1,"rumor_audits": c2,"equal_talk_time": c3})

# ---------- HUD Banner ----------
st.markdown(
    f"<div class='banner'>Scenario: <b>{scenario_name}</b> | Backend: <b>{backend}</b> | Model: <b>{model}</b> | Reasoning: <b>{reasoning_effort}</b></div>",
    unsafe_allow_html=True
)

# ---------- End Screen ----------
if st.session_state.ended:
    st.markdown(f"""
    <div class="game-over">
        GAME OVER<br><br>
        TITLE: {st.session_state.get("final_title","UNKNOWN")}<br>
        SCORE: {st.session_state.get("final_score",0)}<br>
    </div>
    """, unsafe_allow_html=True)
    st.subheader("📑 GPT-OSS Postmortem Report")
    st.write(st.session_state.get("postmortem","No report generated."))
    st.stop()

# ---------- Human Controls ----------
st.subheader("Your Chicken (hen_human)")
colA, colB = st.columns([1.2, 1])
with colA:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    act = st.selectbox("Action", ["IDLE","PECK","ALLY","GOSSIP","AUDIT","PROPOSE","VOTE","SANCTION","FORAGE","SCRATCH"])
    target = st.text_input("Target (e.g., hen_2)")
    msg = st.text_area("Message / Rumor / Policy")
    st.markdown('</div>', unsafe_allow_html=True)
with colB:
    st.metric("Reputation", random.randint(40,95))
    st.metric("Stability", random.choice(["+","–","~"]))
    st.metric("Trust Coins", random.randint(1,10))

human_override = {"action":act,"target":target.strip() or None,"message":msg.strip()}

if st.button("Next Tick", type="primary", use_container_width=True):
    engine.step(
        backend=backend,
        human_override=human_override,
        constitution=st.session_state.constitution,
        reasoning_effort=reasoning_effort,
        api_base=api_base,
        api_key=api_key,
    )
    engine.save_state()
    st.session_state.tick = engine.tick
    st.rerun()

# ---------- Data ----------
rows = load_log_rows()
mems = load_mem()

# ---------- Rumor Feed ----------
st.subheader("Rumor Feed")
if rows:
    for r in rows[-40:]:
        st.markdown(f"- [t={r['tick']}] {r['agent']} → {r['action']} :: {r['message']}")
else:
    st.info("Click Next Tick to start the coop.")

# ---------- Coop Map ----------
st.subheader("Coop Map")
render_pixel_map(rows, engine.agents)

# ---------- Metrics ----------
st.subheader("Coop Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("Total Actions", len(rows))
col2.metric("Rumors", sum(1 for r in rows if r["action"] in ("GOSSIP","spread_rumor")))
col3.metric("Sanctions", sum(1 for r in rows if r["action"]=="SANCTION"))

# ---------- Memories ----------
st.subheader("Memories")
for a,m in mems.items():
    st.markdown(f"**{a}**")
    for ev in m[-3:]:
        st.caption(f"- {ev.get('event','')}")

# ---------- End Button ----------
if st.button("End Session", use_container_width=True):
    st.session_state.ended = True
    score = len(rows)
    st.session_state.final_score = score
    st.session_state.final_title = "DEMOCRACY DEFENDER" if score>20 else "GOSSIP LORD"

    scenario = next((s for s in SCENARIOS if s["name"]==scenario_name), None)
    if scenario:
        if scenario["win"](rows): st.session_state.final_title="VICTORY!"
        elif scenario["lose"](rows): st.session_state.final_title="DEFEAT!"

    if backend!="mock":
        summary = f"Analyze this coop simulation with {len(rows)} actions, constitution {st.session_state.constitution}."
        report = run_inference(summary, backend=backend, model=model, api_base=api_base, api_key=api_key)
        st.session_state.postmortem = report.get("message","No report")
    else:
        st.session_state.postmortem = "Mock: coalitions collapsed, rumors dominated, governance fragile."
    st.rerun()
