import streamlit as st
import json
from pathlib import Path
import os
from openai import OpenAI

# CONFIG
PROSPECTS_FILE = "data/prospects_grassnerds.json"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL_NAME = "gpt-4o-mini"
MAX_SCORE = 100

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

# Page layout
st.set_page_config(page_title="Grass Nerds Sales Training Chatbot", layout="wide")
st.markdown("## 🗨️ Grass Nerds Sales Training Chatbot")

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
    if speaker == "sales_rep":
        icon = "💬"  # speech balloon
        label = "You"
    else:
        icon = "🌱"  # seedling
        label = "Prospect"
    st.chat_message(label, avatar=icon).write(text)

user_input = st.chat_input("💬 Your message")
if user_input:
    st.session_state.history.append(("sales_rep", user_input))

    # Prepare prompt
   prompt = (
    f"You are '{selected_prospect['name']}', a {selected_prospect['role']} being simulated in a sales training session. "
    f"You have hidden needs and pain points: {selected_prospect.get('pain_points', 'no pain points provided')}, "
    f"but you should only reveal them if the sales trainee asks good discovery questions. "
    f"If the trainee skips ahead to pitching or closing, push back politely and ask for more details. "
    f"Stay realistic, natural, and conversational."
    )
    messages = [{"role": "system", "content": prompt}]
    for speaker, text in st.session_state.history:
        role = "assistant" if speaker == "prospect" else "user"
        messages.append({"role": role, "content": text})

    # Get response
    response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
    reply = response.choices[0].message.content.strip()

    st.session_state.history.append(("prospect", reply))
    st.chat_message("Prospect", avatar="🌱").write(reply)

# Score section
with st.sidebar:
    st.header("Score")
    if st.button("End Chat & Generate Score"):
        st.write("Please wait while we are generating your score…")
        question_count = len([msg for speaker, msg in st.session_state.history if "?" in msg and speaker == "sales_rep"])
        score = min(MAX_SCORE, question_count * 10)
        st.success(f"🏆 Your score: {score}/{MAX_SCORE}")
        st.write("### Feedback")
        st.write(
            "• Great job asking discovery questions!\n"
            "• Remember to close with a clear CTA tied to the prospect’s timeline."
        )
        if st.button("Start New Prospect"):
            st.session_state.history = []
            st.rerun()
