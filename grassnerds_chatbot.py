import streamlit as st
import json
from pathlib import Path
from openai import OpenAI

# CONFIG
PROSPECTS_FILE = "data/prospects_grassnerds.json"
MODEL_NAME = "gpt-4o"
MAX_SCORE = 100

# Load OpenAI API key from Streamlit Cloud Secrets
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=OPENAI_API_KEY)

# Load prospects
def load_prospects():
    prospects = json.loads(Path(PROSPECTS_FILE).read_text())
    return prospects

# Initialize session state
if "history" not in st.session_state:
    st.session_state.history = []
if "selected_prospect" not in st.session_state:
    st.session_state.selected_prospect = None
if "scoreboard" not in st.session_state:
    st.session_state.scoreboard = []
if "trainee_name" not in st.session_state:
    st.session_state.trainee_name = ""

# Page layout
st.set_page_config(page_title="Grass Nerds Sales Training Chatbot", layout="wide")
st.markdown("## 🗨️ Grass Nerds Sales Training Chatbot")

# Sidebar: trainee name input
with st.sidebar:
    st.header("Trainee Info")
    st.session_state.trainee_name = st.text_input("Enter your name", value=st.session_state.trainee_name)

# Load and select prospect
prospects = load_prospects()
prospect_names = [f"{p['name']} ({p['role']})" for p in prospects]
selected_name = st.selectbox("Select Prospect", prospect_names)

# Find and store selected prospect
selected_prospect = next((p for p in prospects if f"{p['name']} ({p['role']})" == selected_name), None)
st.session_state.selected_prospect = selected_prospect

# Show persona (hide pain points)
st.markdown(
    f"""
    <div style="border:1px solid #ddd;border-radius:10px;padding:1rem;background:#f8f8f8;">
        <strong>Persona:</strong> {selected_prospect['name']} ({selected_prospect['role']})
    </div>
    """,
    unsafe_allow_html=True,
)

# Chat container
for speaker, text in st.session_state.history:
    icon = "💬" if speaker == "sales_rep" else "🌱"
    label = "You" if speaker == "sales_rep" else "Prospect"
    st.chat_message(label, avatar=icon).write(text)

user_input = st.chat_input("💬 Your message")
if user_input:
    st.session_state.history.append(("sales_rep", user_input))

    # Prompt GPT as the prospect
    prompt = (
        f"You are '{selected_prospect['name']}', a {selected_prospect['role']} in a sales training simulation. "
        f"Your hidden pain points are: {selected_prospect.get('pain_points', 'no pain points provided')}. "
        f"Only reveal them if the trainee asks good discovery questions. Be realistic, friendly, and natural."
    )
    messages = [{"role": "system", "content": prompt}]
    for speaker, text in st.session_state.history:
        role = "assistant" if speaker == "prospect" else "user"
        messages.append({"role": role, "content": text})

    # Get GPT-generated prospect response
    response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
    reply = response.choices[0].message.content.strip()

    st.session_state.history.append(("prospect", reply))
    st.chat_message("Prospect", avatar="🌱").write(reply)

# Sidebar: Scoring & Leaderboard
with st.sidebar:
    st.header("Score")
    if st.button("End Chat & Generate Score"):
        if not st.session_state.trainee_name.strip():
            st.warning("Please enter your name before ending the chat.")
        else:
            # Prepare full transcript
            transcript = "\n".join(
                [f"{'Trainee' if s == 'sales_rep' else 'Prospect'}: {t}" for s, t in st.session_state.history]
            )

            eval_prompt = f"""
            You are a sales coach. Return ONLY a raw JSON object like the example below—no explanation, no formatting.
            Evaluate this sales chat and score each category from 0 to 10:

            {{
              "rapport": 0-10,
              "discovery": 0-10,
              "solution_alignment": 0-10,
              "objection_handling": 0-10,
              "closing": 0-10,
              "positivity": 0-10,
              "dale_carnegie_principles": 0-5,
              "feedback": {{
                "rapport": "...",
                "discovery": "...",
                "solution_alignment": "...",
                "objection_handling": "...",
                "closing": "...",
                "positivity": "...",
                "dale_carnegie_principles": "..."
              }}
            }}

            Chat transcript:
            {transcript}
            """

            eval_response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "system", "content": eval_prompt}]
            )

            response_text = eval_response.choices[0].message.content.strip()

            try:
                eval_result = json.loads(response_text)
            except json.JSONDecodeError:
                st.error("❌ GPT did not return valid JSON. Here's what it returned:")
                st.code(response_text)
                st.stop()

            total_score = sum([
                eval_result['rapport'],
                eval_result['discovery'],
                eval_result['solution_alignment'],
                eval_result['objection_handling'],
                eval_result['closing'],
                eval_result['positivity']
            ]) * (100 / 60)  # Normalize to 100

            # Save to scoreboard
            st.session_state.scoreboard.append({
                "name": st.session_state.trainee_name,
                "score": int(total_score)
            })
            st.session_state.scoreboard = sorted(st.session_state.scoreboard, key=lambda x: x["score"], reverse=True)[:10]

            # Display scores + feedback
            st.success(f"🏆 Your total score: {int(total_score)}/100")
            st.write("### Feedback")
            for k, v in eval_result['feedback'].items():
                st.write(f"**{k.capitalize()}**: {v}")

    if st.button("Start New Prospect"):
        st.session_state.history = []

    if st.session_state.scoreboard:
        st.write("### 🏅 Top 10 Scores")
        for entry in st.session_state.scoreboard:
            st.write(f"{entry['name']}: {entry['score']}")
