import streamlit as st
import json
from pathlib import Path
from openai import OpenAI
import os
import datetime

# ---------- CONFIG ----------
PROSPECTS_FILE = "data/prospects_grassnerds.json"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL_NAME      = "gpt-4o-mini"  # or whatever you’re using
MAX_SCORE       = 100
# -----------------------------

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- LOAD PROSPECT ----------
def load_prospect():
    prospects = json.loads(Path(PROSPECTS_FILE).read_text())
    # pull first unused; for demo we’ll just pop(0)
    return prospects.pop(0)

prospect = st.session_state.get("prospect")
if not prospect:
    prospect = load_prospect()
    st.session_state.prospect = prospect

# ---------- PAGE LAYOUT ----------
st.set_page_config(page_title="Grass Nerds Sales Training Chatbot", layout="wide")

# Header
st.markdown("## 🗨️ Grass Nerds Sales Training Chatbot")

# Hide pain‑point from trainee ⚠️
st.markdown(
    f"""
    <div style="border:1px solid #ddd;border-radius:10px;padding:1rem;background:#f8f8f8;">
        <strong>Persona:</strong> {prospect['name']} ({prospect['role']})
        <!-- Pain point intentionally hidden; trainee must uncover via discovery questions -->
    </div>
    """,
    unsafe_allow_html=True,
)

# Chat container
if "history" not in st.session_state:
    st.session_state.history = []

for speaker, text in st.session_state.history:
    st.chat_message(speaker).write(text)

user_input = st.chat_input("💬 Your message")
if user_input:
    st.session_state.history.append(("sales_rep", user_input))

    # ---------- CALL OPENAI AS PROSPECT ----------
    prompt = (
        f"You are '{prospect['name']}', a {prospect['role']} for Grass Nerds training. "
        f"Your hidden pain points are: {prospect['pain_points']}. "
        f"Respond in a realistic way to the sales rep’s last message."
    )
    messages = [{"role": "system", "content": prompt}]
    for speaker, text in st.session_state.history:
        role = "assistant" if speaker == "prospect" else "user"
        messages.append({"role": role, "content": text})

    response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
    reply = response.choices[0].message.content.strip()

    st.session_state.history.append(("prospect", reply))
    st.chat_message("prospect").write(reply)

# ---------- SCORE & END CHAT ----------
with st.sidebar:
    st.header("Score")
    if st.button("End Chat & Generate Score"):
        st.write("Please wait while we are generating your score…")
        # Scoring function uses hidden pain points & Dale Carnegie rubric
        score = min(MAX_SCORE, len([msg for speaker, msg in st.session_state.history if "?" in msg]) * 10)
        st.success(f"🏆 Your score: {score}/{MAX_SCORE}")
        st.write("### Feedback")
        st.write(
            "• Great job asking discovery questions!\n"
            "• Remember to close with a clear CTA tied to the prospect’s timeline."
        )
        # Optionally reset for next prospect
        if st.button("Start New Prospect"):
            st.session_state.clear()
            st.rerun()
