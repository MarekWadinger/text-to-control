import base64
import os
import time
from functools import wraps

import streamlit as st
from backend_interface import run_pipeline

# Page config

st.set_page_config(page_title="Optimo.ai", page_icon="🔮", layout="wide")


# Session state

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "last_call_time" not in st.session_state:
    st.session_state.last_call_time = 0
if "page" not in st.session_state:
    st.session_state.page = "welcome"


# Chat state

if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_started" not in st.session_state:
    st.session_state.chat_started = False
if "initial_question" not in st.session_state:
    st.session_state.initial_question = ""
if "selected_suggestion" not in st.session_state:
    st.session_state.selected_suggestion = None

RATE_LIMIT_SECONDS = 3
VALID_USERS = {"user1": "password1", "user2": "password2"}


# Rate limiting


def rate_limit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        now = time.time()
        elapsed = now - st.session_state.last_call_time
        if elapsed < RATE_LIMIT_SECONDS:
            st.warning(
                f"Wait {int(RATE_LIMIT_SECONDS - elapsed)}s before next request."
            )
            return None
        st.session_state.last_call_time = now
        return func(*args, **kwargs)

    return wrapper


@rate_limit
def run_backend(prompt_text, log_callback=None):
    return run_pipeline(prompt_text, log_callback=log_callback)


# CSS

st.markdown(
    """<style>
.stApp { background: #bfbfbf; font-family: 'Segoe UI', sans-serif; }
.card { background: white; padding: 25px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); margin-bottom: 25px; transition: transform 0.3s ease, box-shadow 0.3s ease, opacity 1.2s ease; opacity:0; animation: fadeIn 1s forwards;}
.card:hover { transform: scale(1.05); box-shadow: 0 15px 30px rgba(0,0,0,0.2);}
div.stButton > button { background-color: #8b5cf6; color: white; border-radius: 12px; height: 3rem; font-size: 1rem; width: 100%; font-weight:600; transition:0.3s;}
div.stButton > button:hover { background-color: #a78bfa; color: white; transform:scale(1.05);}
textarea, input[type="text"], input[type="password"] { background-color: white !important; color: black !important; border-radius: 10px; padding: 10px; width: 100%; border: 1px solid #ccc;}
.hero { background: linear-gradient(-45deg, #c4b5fd, #7c3aed, #d8b4fe, #a78bfa); background-size: 400% 400%; color: white; padding: 3rem; border-radius: 20px; text-align:center; margin-bottom:2rem; animation: gradientBG 15s ease infinite, fadeIn 1s forwards;}
.big-title { font-size: 4rem; font-weight: 700; color: #7c3aed; text-align: center; margin-bottom: 1rem; opacity:0; animation: fadeIn 1s forwards;}
@keyframes fadeIn { 0% { opacity: 0; transform: translateY(20px);} 100% { opacity: 1; transform: translateY(0);}}
@keyframes gradientBG {0% { background-position: 0% 50%; }50% { background-position: 100% 50%; }100% { background-position: 0% 50%; }}
[data-testid="stSidebar"] { background-color: #faf5ff; }
ul { padding-left:1.2rem; }
</style>""",
    unsafe_allow_html=True,
)


# Page callbacks


def go_to_page(page_name):
    st.session_state.page = page_name


def login_callback(username, password):
    if VALID_USERS.get(username) == password:
        st.session_state.authenticated = True
        st.session_state.username = username
        st.success("Login successful!")
        time.sleep(1.5)
        go_to_page("main")
    else:
        st.error("Invalid username or password")


def logout_callback():
    st.session_state.authenticated = False
    st.session_state.username = ""
    go_to_page("logout_message")


def register_callback(username, password, password2, api_key):
    if not (username and password and password2 and api_key):
        st.error("Fill all fields")
    elif password != password2:
        st.error("Passwords do not match")
    else:
        VALID_USERS[username] = password
        st.session_state.api_key = api_key
        st.success("Registration successful! Please login.")
        go_to_page("welcome")


# Pages


def show_welcome():
    st.markdown(
        """<div class='hero'><h1 style='font-size:4rem; font-weight:700;'>Welcome to Optimo</h1><p style='font-size:1.5rem;'>Your AI-powered optimization assistant </p></div>""",
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.markdown(
            """<div class='card' style='background: linear-gradient(135deg, #ede9fe, #c4b5fd); color: #5b21b6; padding: 1rem 1rem; border-radius: 15px; text-align: center; box-shadow: 0 8px 20px rgba(0,0,0,0.1); max-width: 400px; min-height: 15px; margin: 0 auto; transition: transform 0.3s ease, box-shadow 0.3s ease;'><h2 style='font-size:1.6rem; font-weight:650; margin-bottom:1rem;'>Log In</h2></div>""",
            unsafe_allow_html=True,
        )
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        st.button(
            "Login",
            key="login_btn",
            on_click=login_callback,
            args=(username, password),
        )
    with col2:
        st.markdown(
            """<div class='card' style='background:linear-gradient(135deg, #ede9fe, #c4b5fd); color:#4b5563; text-align:center;'><h2 style='color:#5b21b6;'>Join Optimo Today!</h2><p>Unlock AI tools for optimization. Simple, fast, intuitive.</p></div>""",
            unsafe_allow_html=True,
        )
        st.button(
            "Sign Up Now →",
            key="goto_signup",
            on_click=lambda: go_to_page("signup"),
        )


def show_signup():
    st.markdown(
        """<div style='text-align:center; margin-bottom:2rem;'><h1 style='font-size:3.5rem; font-weight:700; color:#7c3aed;'>Create Your Account</h1><p style='font-size:1.2rem; color:#4b5563;'>Join Optimo for smarter decisions </p></div>""",
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.markdown(
            "<h3 style='color:#5b21b6; text-align:center; margin-bottom:1rem;'>Registration</h3>",
            unsafe_allow_html=True,
        )
        reg_username = st.text_input("Username", key="reg_user")
        reg_password = st.text_input(
            "Password", type="password", key="reg_pass"
        )
        reg_password2 = st.text_input(
            "Confirm Password", type="password", key="reg_pass2"
        )
        api_key = st.text_input(
            "API Key", type="password", key="api_key_input"
        )
        st.button(
            "Register",
            key="reg_submit",
            on_click=register_callback,
            args=(reg_username, reg_password, reg_password2, api_key),
        )
    with col2:
        st.markdown(
            """<div class='card' style='background:linear-gradient(135deg, #ede9fe, #c4b5fd);'><h2 style='color:#5b21b6;'>Why Optimo?</h2><ul><li>💡 AI-driven optimization suggestions</li><li>⚡ Fast and intuitive interface</li><li>📈 Designed for professionals & students</li><li>🔒 Secure API access for your projects</li></ul></div>""",
            unsafe_allow_html=True,
        )
        st.button(
            "← Back to Welcome",
            key="back_welcome",
            on_click=lambda: go_to_page("welcome"),
        )


def show_main():
    import streamlit as st

    # Session init
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "awaiting_clarification" not in st.session_state:
        st.session_state.awaiting_clarification = False
    if "pipeline_prompt" not in st.session_state:
        st.session_state.pipeline_prompt = ""
    if "clarification_prompt" not in st.session_state:
        st.session_state.clarification_prompt = ""

    # Sidebar
    with st.sidebar:
        st.markdown("## Optimo")
        st.caption("Multi-agent optimization assistant")
        st.divider()
        st.markdown(f"👤 **{st.session_state.username}**")
        st.button(
            "Logout",
            on_click=lambda: st.session_state.update(
                {
                    "authenticated": False,
                    "username": "",
                    "page": "logout_message",
                }
            ),
        )

    # Base CSS
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #f5f5f7 !important;
            font-family: 'Inter', sans-serif;
            color: #1f2937;
        }

        .header-container {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 16px 24px;
            position: sticky;
            top: 0;
            background: #ffffff;
            border-bottom: 1px solid #e5e7eb;
            z-index: 10;
        }

        .header-container img {
            width: 48px;
            height: 48px;
            border-radius: 50%;
        }

        .chat-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
            padding: 16px;
            max-width: 800px;
            margin: auto;
        }

        .bubble {
            padding: 14px 20px;
            border-radius: 20px;
            max-width: 70%;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            line-height: 1.5;
            font-size: 1rem;
        }

        .bubble-user { background: linear-gradient(135deg, #c4b5fd, #7c3aed); color:white; align-self:flex-end; }

        .bubble-assistant { background:#ffffff; color:#1f2937; align-self:flex-start; }

        .bubble-final { background:#e5e7eb; color:#1f2937; align-self:flex-start; font-family:monospace; white-space:pre-wrap; }

        .typing {
            font-style: italic;
            color: #9ca3af;
            margin-bottom: 8px;
        }

        .stChatInput {
            border-top: 1px solid #e5e7eb;
            padding: 12px 16px;
            position: sticky;
            bottom: 0;
            background: #f5f5f7;
            z-index: 5;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Header
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(BASE_DIR, "bot_avatar.png")
    logo_base64 = base64.b64encode(open(logo_path, "rb").read()).decode()

    st.markdown(
        f"""
        <div class="header-container">
            <img src="data:image/png;base64,{logo_base64}" />
            <div>
                <h2 style="margin:0; color:#7c3aed;">Optimo Assistant</h2>
                <p style="margin:0; color:#6b7280; font-size:0.95rem;">Ask, refine and optimize decisions</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Chat container
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)

    if not st.session_state.messages:
        st.markdown(
            """
            <div style="text-align:center; margin-top:4rem;">
                <h1 style="color:#7c3aed; font-size:2.5rem;">
                    What would you like to optimize?
                </h1>
                <p style="color:#6b7280; font-size:1rem;">
                    Constraints · Objectives · Trade-offs · Decisions
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Chat messages
    for msg in st.session_state.messages:
        cls = "bubble-user" if msg["role"] == "user" else "bubble-assistant"
        if msg.get("final", False):
            cls = "bubble-final"
        st.markdown(
            f'<div class="{cls}">{msg["content"]}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # --- Pipeline runner ---
    def _run_pipeline(prompt):
        placeholder = st.empty()  # miesto pre dynamické logy
        logs = []

        # callback pre logy z main.py
        def log_callback(msg):
            msg = msg.strip()
            if msg:
                logs.append(msg)
                # dynamické zobrazenie posledných logov + chat
                html = ""
                for m in st.session_state.messages[-20:]:
                    cls = (
                        "bubble-assistant"
                        if m["role"] == "assistant"
                        else "bubble-user"
                    )
                    html += f'<div class="{cls}">{m["content"]}</div>'
                for log_msg in logs[-5:]:
                    html += (
                        f'<div class="bubble bubble-assistant">{log_msg}</div>'
                    )
                placeholder.markdown(html, unsafe_allow_html=True)

        try:
            # spustenie pipeline
            final_msg = run_pipeline(prompt, log_callback=log_callback)
            # pridáme finálnu správu iba raz
            st.session_state.messages.append(
                {"role": "assistant", "content": final_msg, "final": True}
            )
            logs.clear()
        except RuntimeError as e:
            # Expert potrebuje klarifikáciu
            st.session_state.awaiting_clarification = True
            st.session_state.pipeline_prompt = prompt
            st.session_state.clarification_prompt = str(e)

    # --- Chat input ---
    if st.session_state.awaiting_clarification:
        st.markdown(
            f"<div class='bubble bubble-assistant'>{st.session_state.clarification_prompt}</div>",
            unsafe_allow_html=True,
        )
        clar_input = st.text_input(
            "Provide clarifications for Expert Agent:", key="clar_input"
        )
        if st.button("Submit clarification", key="submit_clar"):
            if clar_input.strip():
                st.session_state.messages.append(
                    {"role": "user", "content": clar_input}
                )
                st.session_state.awaiting_clarification = False
                updated_prompt = (
                    st.session_state.pipeline_prompt
                    + f"\nClarifications: {clar_input}\n"
                )
                _run_pipeline(updated_prompt)
    else:
        prompt = st.chat_input("Ask Optimo…", key="chat_input")
        if prompt:
            st.session_state.messages.append(
                {"role": "user", "content": prompt}
            )
            st.session_state.pipeline_prompt = prompt
            _run_pipeline(prompt)


def show_logout_message():
    st.markdown(
        "<div class='card' style='text-align:center; padding:3rem;'><h2 style='color:#7c3aed;'>You have been successfully logged out. </h2><p>Thank you for using Optimo. See you next time!</p></div>",
        unsafe_allow_html=True,
    )
    st.button("Back to Login", on_click=lambda: go_to_page("welcome"))


# Render
if st.session_state.page == "welcome":
    show_welcome()
elif st.session_state.page == "signup":
    show_signup()
elif st.session_state.page == "main" and st.session_state.authenticated:
    show_main()
elif st.session_state.page == "logout_message":
    show_logout_message()
else:
    show_welcome()
