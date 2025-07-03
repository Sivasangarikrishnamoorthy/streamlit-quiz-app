import streamlit as st
from streamlit_autorefresh import st_autorefresh
import mysql.connector
import bcrypt
import pandas as pd
import random
import time

st.set_page_config(page_title="Quiz App", layout="centered")

# ----------------------
# Database Connection
# ----------------------
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Siva@123",
            database="quiz_app"
        )
        return conn
    except mysql.connector.Error as err:
        st.error(f"Database error: {err}")
        return None

# ----------------------
# User Authentication
# ----------------------
def login(username, password):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username=%s", (username,))
        result = cursor.fetchone()
        conn.close()
        if result and bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8')):
            return True
    return False

def signup(username, password):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password.decode('utf-8')))
        conn.commit()
        conn.close()

# ----------------------
# Fetch Random Questions
# ----------------------
def fetch_random_questions():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM questions")
        questions = cursor.fetchall()
        conn.close()
        return random.sample(questions, 10)
    return []

# ----------------------
# Save Results
# ----------------------
def save_result(username, score, total):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO results (username, score, total) VALUES (%s, %s, %s)", (username, score, total))
        conn.commit()
        conn.close()

# ----------------------
# Main App Logic
# ----------------------
st.title("📝 Online Quiz App")

if 'username' not in st.session_state:
    st.session_state.username = ""

if not st.session_state.username:
    choice = st.radio("Login or Signup", ["Login", "Signup"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button(choice):
        if choice == "Login" and login(username, password):
            st.session_state.username = username
            st.success(f"Welcome back, {username}!")
            st.rerun()
        elif choice == "Signup":
            signup(username, password)
            st.success("Account created successfully! Please log in.")
        else:
            st.error("Invalid credentials.")

# ----------------------
# Main App Sections
# ----------------------
if st.session_state.username:
    tab = st.selectbox("Options", ["Take Quiz", "Leaderboard", "Logout"])

    if tab == "Take Quiz":
        st.header("Python Quiz")

        if "quiz_started" not in st.session_state:
            st.session_state.quiz_started = False
            st.session_state.questions = []
            st.session_state.answers = {}
            st.session_state.score = 0
            st.session_state.quiz_ended = False
            st.session_state.submitted = False
            st.session_state.view_answers = False

        if not st.session_state.quiz_started and not st.session_state.submitted:
            if st.button("Start Quiz"):
                st.session_state.questions = fetch_random_questions()
                st.session_state.quiz_started = True
                st.session_state.start_time = time.time()
                st.rerun()

        if st.session_state.quiz_started:
            st_autorefresh(interval=1000, key="timer_refresh")

            elapsed = int(time.time() - st.session_state.start_time)
            remaining = max(0, 600 - elapsed)
            minutes, seconds = divmod(remaining, 60)
            timer_display = f"{minutes:02d}:{seconds:02d}"

            if remaining == 0:
                st.session_state.quiz_ended = True

            st.info(f"⏳ Time Remaining: {timer_display}")

            with st.form("quiz_form"):
                for i, q in enumerate(st.session_state.questions):
                    options = [q['option1'], q['option2'], q['option3'], q['option4']]
                    st.session_state.answers[i] = st.radio(
                        f"{i+1}. {q['question']}",
                        options,
                        key=f"q_{i}"
                    )
                submitted = st.form_submit_button("Submit")

            if submitted or st.session_state.quiz_ended:
                score = 0
                for i, q in enumerate(st.session_state.questions):
                    selected = st.session_state.answers.get(i, "")
                    if selected == q['answer']:
                        score += 1
                save_result(st.session_state.username, score, len(st.session_state.questions))
                st.session_state.score = score
                st.session_state.quiz_started = False
                st.session_state.submitted = True
                st.session_state.quiz_ended = False
                st.rerun()

        if st.session_state.submitted:
            st.success(f"🎉 You scored {st.session_state.score} / {len(st.session_state.questions)}")
            if not st.session_state.view_answers:
                if st.button("View Answers"):
                    st.session_state.view_answers = True
                    st.rerun()

        if st.session_state.submitted and st.session_state.view_answers:
            st.markdown("### ✅ Correct Answers & Your Choices")
            for i, q in enumerate(st.session_state.questions):
                user_answer = st.session_state.answers.get(i, "")
                correct = q['answer']
                is_correct = (user_answer == correct)

                st.markdown(f"**{i+1}. {q['question']}**")
                st.markdown(f"- Your answer: {'✅ ' if is_correct else '❌ '}{user_answer}")
                if not is_correct:
                    st.markdown(f"- Correct answer: ✅ {correct}")
                st.markdown("---")

    elif tab == "Leaderboard":
        st.header("🏆 Leaderboard")
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT username, MAX(score) AS best_score, MAX(total) AS total
                FROM results
                GROUP BY username
            """)
            data = cursor.fetchall()
            conn.close()

            if data:
                df = pd.DataFrame(data)
                df["Percentage (%)"] = round((df["best_score"] / df["total"]) * 100, 2)
                df["Rank"] = df["Percentage (%)"].rank(method='min', ascending=False).astype(int)
                df = df.sort_values(by="Rank")
                df = df[["Rank", "username", "best_score", "total", "Percentage (%)"]]
                df.columns = ["Rank", "Username", "Best Score", "Total Questions", "Percentage (%)"]
                st.dataframe(df)
            else:
                st.info("No results to display.")

    elif tab == "Logout":
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("Logged out successfully!")
        st.rerun()