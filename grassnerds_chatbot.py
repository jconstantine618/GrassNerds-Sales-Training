import streamlit as st
import json
import random

# Load prospect data
def load_prospects():
    with open('prospects.json', 'r') as file:
        return json.load(file)['prospects']

# Initialize session state
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'leaderboard' not in st.session_state:
    st.session_state.leaderboard = []
if 'current_prospect' not in st.session_state:
    st.session_state.current_prospect = None

st.title("Grass Nerds Sales Training Chatbot")
st.subheader("Welcome, Sales Trainee!")

# Load prospects
prospects = load_prospects()

# Select random prospect if none assigned
if not st.session_state.current_prospect:
    st.session_state.current_prospect = random.choice(prospects)

prospect = st.session_state.current_prospect
st.write(f"### Prospect: {prospect['name']}")
st.write(f"**Type:** {prospect['type']}")
st.write(f"**Pain Points:** {', '.join(prospect['pain_points'])}")

# Chat simulation
user_input = st.text_input("Your Message")

if user_input:
    # Check for keywords that reflect good sales practices
    positive_keywords = ['understand', 'solution', 'recommend', 'help', 'plan', 'value', 'improve', 'important', 'goal']
    if any(word in user_input.lower() for word in positive_keywords):
        st.session_state.score += 10
        st.write("✅ Great job applying sales principles!")
    else:
        st.session_state.score -= 5
        st.write("⚠️ Try focusing more on uncovering pain points and offering solutions.")

st.write(f"### Current Score: {st.session_state.score}")

# End chat and save score
if st.button("End Chat & Save Score"):
    st.session_state.leaderboard.append({
        'trainee': 'Sales Trainee',
        'score': st.session_state.score
    })
    st.session_state.score = 0
    st.session_state.current_prospect = None

# Show leaderboard
if st.session_state.leaderboard:
    st.write("### Leaderboard")
    sorted_board = sorted(st.session_state.leaderboard, key=lambda x: x['score'], reverse=True)
    for i, entry in enumerate(sorted_board):
        st.write(f"{i + 1}. {entry['trainee']} - {entry['score']} points")
