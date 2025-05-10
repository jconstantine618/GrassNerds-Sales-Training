import os, json, random, re, datetime, pathlib
import streamlit as st
from dotenv import load_dotenv
import openai

# ---------- ENV / CONFIG ----------
try:
    load_dotenv()
except ModuleNotFoundError:
    pass

OPENAI_KEY = os.getenv("OPENAI_API_KEY", st.secrets.get("OPENAI_API_KEY", ""))
client = openai.OpenAI(api_key=OPENAI_KEY)

MODEL = "gpt-4o"
DATA_FILE = "prospects_grassnerds.json"
TRANSCRIPTS = pathlib.Path("transcripts")
TRANSCRIPTS.mkdir(exist_ok=True)
CLOSE_PHRASES = [
    r"move forward", r"next step", r"go ahead",
    r"green light", r"get started", r"sign", r"deal"
]

# ---------- LOAD PROSPECTS ----------
@st.cache_data(show_spinner=False)
def load_prospects():
    try:
        return json.loads(pathlib.Path(DATA_FILE).read_text())
    except FileNotFoundError:
        st.error(f"❌ File not found: {DATA_FILE}")
        st.stop()

prospects = load_prospects()

# ---------- SIDEBAR ----------
st.sidebar.title("🌱 Grass Nerds Prospects")
if "prospect" not in st.session_state:
    st.session_state.prospect = random.choice(prospects)
    st.session_state.chat_log = []
    st.session_state.ended = False
    st.session_state.score = None

def pick_new(name):
    st.session_state.prospect = next(p for p in prospects if p["scenarioId"] == name)
    st.session_state.chat_log = []
    st.session_state.ended = False
    st.session_state.score = None

prospect_labels = [f"{p['scenarioId']} – {p['name']}" for p in prospects]
current_index = next(i for i, p in enumerate(prospects) if p == st.session_state.prospect)

selected_label = st.sidebar.selectbox(
    "Choose a prospect:",
    prospect_labels,
    index=current_index
)
selected_prospect = next(p for p in prospects if f"{p['scenarioId']} – {p['name']}" == selected_label)
if selected_prospect != st.session_state.prospect:
    pick_new(selected_prospect["scenarioId"])

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reset Chat"):
    pick_new(st.session_state.prospect["scenarioId"])

# ---------- SYSTEM PROMPT ----------
PROMPT_TMPL = \"\"\"
You are {persona_name}, a {persona_role} at {persona_context}.

GOAL:
– Have a realistic dialogue with a Grass Nerds sales trainee.
– Reveal pain points only when they ask good questions.
– Raise objections from the list below naturally.
– Reward rapport, empathy, and solutions.
– If the trainee proposes a next step that fits, agree to move forward.

PAIN POINTS: {pain_points}
OBJECTIONS: {likely_objections}
OUTCOME: {desired_outcome}

Be authentic, friendly, and conversational.
\"\"\"

def build_system_prompt(prospect):
    ctx = {
        \"persona_name\": prospect[\"name\"],
        \"persona_role\": prospect[\"role\"],
        \"persona_context\": prospect[\"context\"],
        \"pain_points\": \", \".join(prospect[\"painPoints\"]),
        \"likely_objections\": \", \".join(prospect[\"likelyObjections\"]),
        \"desired_outcome\": prospect[\"desiredOutcome\"]
    }
    return PROMPT_TMPL.format(**ctx)

# ---------- CHAT COMPLETION ----------
def persona_reply(user_msg):
    messages = [{\"role\": \"system\", \"content\": build_system_prompt(st.session_state.prospect)}]
    for entry in st.session_state.chat_log:
        messages.append({\"role\": entry[\"role\"], \"content\": entry[\"content\"]})
    messages.append({\"role\": \"user\", \"content\": user_msg})

    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7
    )
    return resp.choices[0].message.content.strip()

# ---------- SCORING ----------
def score_conversation():
    log = \" \".join([e[\"content\"].lower() for e in st.session_state.chat_log if e[\"role\"] == \"user\"])
    score = 0
    if re.search(r\"understand|plan|recommend|help\", log):
        score += 20
    if re.search(r\"value|important|goal\", log):
        score += 20
    if len(re.findall(r\"\\?\", log)) >= 3:
        score += 20
    if any(re.search(p, log) for p in CLOSE_PHRASES):
        score += 30
    return min(score, 100)

# ---------- MAIN UI ----------
st.title(\"💬 Grass Nerds Sales Training Chatbot\")

p = st.session_state.prospect
st.markdown(f\"\"\"
<div style='border:1px solid #ccc; border-radius:10px; padding:10px; background:#f9f9f9'>
<b>Persona:</b> {p['name']} ({p['role']})  <br>
<b>Context:</b> {p['context']}  
</div>
\"\"\", unsafe_allow_html=True)

chat_placeholder = st.container()

with st.form(\"chat_form\", clear_on_submit=True):
    user_input = st.text_input(\"💬 Your message\", key=\"input\")
    submitted = st.form_submit_button(\"Send\")
    if submitted and user_input.strip():
        st.session_state.chat_log.append({\"role\": \"user\", \"content\": user_input.strip()})
        with st.spinner(\"Prospect typing...\"):
            assistant_msg = persona_reply(user_input)
        st.session_state.chat_log.append({\"role\": \"assistant\", \"content\": assistant_msg})

for entry in st.session_state.chat_log:
    if entry[\"role\"] == \"assistant\":
        with chat_placeholder.container():
            st.markdown(
                f\"<div style='background-color:#fff3cd; padding:10px; border-radius:10px; margin:5px 0;'>\"
                f\"<b>Prospect:</b> {entry['content']}</div>\",
                unsafe_allow_html=True
            )
    else:
        with chat_placeholder.container():
            st.markdown(
                f\"<div style='background-color:#cce5ff; padding:10px; border-radius:10px; margin:5px 0;'>\"
                f\"<b>You:</b> {entry['content']}</div>\",
                unsafe_allow_html=True
            )

st.markdown(\"---\")
if st.button(\"🛑 End Chat & Score\", disabled=st.session_state.ended):
    st.session_state.ended = True
    st.session_state.score = score_conversation()
    ts = datetime.datetime.now().strftime(\"%Y-%m-%d_%H%M%S\")
    fname = TRANSCRIPTS / f\"{p['scenarioId']}_{ts}.md\"
    with fname.open(\"w\") as f:
        for e in st.session_state.chat_log:
            role = \"Prospect\" if e[\"role\"] == \"assistant\" else \"Trainee\"
            f.write(f\"**{role}:** {e['content']}\\n\\n\")
        f.write(f\"**Final Score:** {st.session_state.score}\\n\")
    st.success(f\"✅ Scoring complete! **Your score: {st.session_state.score}/100**\")
    st.info(f\"Transcript saved → {fname}\")
