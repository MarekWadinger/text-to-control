import time
from functools import wraps

import streamlit as st

from app.auth_demo import handle_demo_login
from app.backend_interface import run_pipeline

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
VALID_USERS = {
    "user1": "password1",
    "user2": "password2",
}


def login_callback(username, password):
    # ---------------- DEMO ACCOUNT ----------------
    if username == "user1" and password == "password1":
        success = handle_demo_login()

        if success:
            st.session_state.page = "main"
            st.info("✅ Demo access granted!")
        else:
            st.info("⚠️ Demo version: access is allowed only once.")
        return

    # ---------------- REGISTERED USERS ----------------
    if VALID_USERS.get(username) == password:
        st.session_state.authenticated = True
        st.session_state.username = username
        st.success("Login successful!")
        time.sleep(1.5)
        st.session_state.page = "main"
        return

    # ---------------- INVALID LOGIN ----------------
    st.error("❌ Invalid username or password")


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
with open("app/stylesheet.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Page callbacks


def go_to_page(page_name):
    st.session_state.page = page_name


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
        with open("app/stylesheet1.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

        # Login card
        st.markdown(
            """
            <div class="card login-card">
                <h2>Login</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )

        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")

        # Login button
        st.button(
            "Login",
            key="login_btn",
            on_click=login_callback,
            args=(username, password),
        )
    with col2:
        with open("app/stylesheet2.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

        st.markdown(
            """<div class='card info-card'>
                    <h2>Join Optimo Today!</h2>
                    <p>Unlock AI tools for optimization.<br>Simple, fast, intuitive.</p>
               </div>""",
            unsafe_allow_html=True,
        )
        st.button(
            "Sign Up Now →",
            key="goto_signup",
            on_click=lambda: go_to_page("signup"),
        )


def show_signup():
    with open("app/stylesheet1.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class='signup-hero' style="background: linear-gradient(-45deg, #f4d03f, #f1c40f, #f7dc6f, #f9e79f);">
            Create Your Account
            <p>Join Optimo for smarter decisions</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.markdown(
            "<h2 style='color:#4b3429; text-align:center; margin-bottom:2rem;'>Registration</h2>",
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
            """
            <div class='card info-card'>
                <h2>Why Optimo?</h2>
                <ul>
                    <li>💡 AI-driven optimization suggestions</li>
                    <li>⚡ Fast and intuitive interface</li>
                    <li>📈 Designed for professionals & students</li>
                    <li>🔒 Secure API access for your projects</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "← Back to Welcome",
            key="back_welcome",
            on_click=lambda: go_to_page("welcome"),
        )


# --- Initialize session variables ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "clarification_state" not in st.session_state:
    st.session_state.clarification_state = False
if "pipeline_prompt" not in st.session_state:
    st.session_state.pipeline_prompt = ""


def show_main():
    # --- Initialize session state ---
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("pipeline_prompt", "")
    st.session_state.setdefault("awaiting_clarification", False)

    # HEADER
    title_row = st.container(horizontal=True, vertical_alignment="bottom")
    with title_row:
        col1, col2, col3 = st.columns([1, 20, 3], vertical_alignment="bottom")

        with col1:
            st.image("app/logo.png", width=48)

        with col2:
            st.markdown(
                '<h1 style="color:#4b3429; margin:0;">OptimoAI assistant</h1>',
                unsafe_allow_html=True,
            )

        with col3:
            if st.button(" Reset Conversation"):
                st.session_state.messages = []
                st.session_state.pipeline_prompt = ""
                st.session_state.awaiting_clarification = False
                st.rerun()

    # CSS
    st.markdown(
        """
    <style>
    /* Chat input */
    div[data-testid="stChatInput"] {
        border: 2px solid #dab019;
        border-radius: 12px;
        padding: 8px;
        background-color: #fff9e5;
        transition: all 0.3s ease;
    }

    div[data-testid="stChatInput"] textarea:focus {
        outline: none;
        box-shadow: 0 0 8px #FFD700;
        border-color: #FFD700;
    }

    [data-testid="column"] img {
        vertical-align: middle;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    placeholder_container = st.empty()
    if len(st.session_state.messages) == 0:
        placeholder_container.markdown(
            """
        <div style="
            text-align: center;
            color: #4b3429;
            font-size: 60px;
            font-weight: bold;
            margin-top: 30px;
            padding: 3rem;
            background: linear-gradient(-45deg, #f4d03f, #f1c40f, #f7dc6f, #f9e79f);
            border-radius: 20px;
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
            animation: gradientBG 15s ease infinite, fadeINforwards 1s forwards;
            line-height: 1.1;
        ">
            What would you like to optimize?<br>
            <span style="
                font-size: 20px;
                font-weight: normal;
                color: #4b3429;
                display: block;
                line-height: 1;
                margin-top: 0px;
            ">
                Ask &middot; Define &middot; Optimize
            </span>
        </div>

        <style>
        @keyframes gradientBG {
            0% {background-position: 0% 50%;}
            50% {background-position: 100% 50%;}
            100% {background-position: 0% 50%;}
        }
        @keyframes fadeINforwards {
            from {opacity: 0;}
            to {opacity: 1;}
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

    # --- Sidebar ---
    with st.sidebar:
        st.markdown("## Optimo")
        st.caption("Multi-agent optimization assistant")
        st.divider()
        st.markdown(f"👤 **{st.session_state.get('username', 'User')}**")
        st.button(
            "Logout",
            on_click=lambda: st.session_state.update(
                {
                    "authenticated": False,
                    "username": "",
                    "page": "logout_message",
                }
            ),
            key="logout_btn",
        )

    # --- Display previous messages from history ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- Input ---
    if prompt := st.chat_input(
        "Provide clarifications…"
        if st.session_state.awaiting_clarification
        else "Ask Optimo…",
        key="chat_input",
    ):
        st.session_state.messages.append({"role": "user", "content": prompt})

        placeholder_container.empty()

        with st.chat_message("user"):
            st.markdown(prompt)

        if st.session_state.awaiting_clarification:
            full_prompt = f"{st.session_state.pipeline_prompt}\nClarifications:\n{prompt}"
            st.session_state.awaiting_clarification = False
        else:
            full_prompt = prompt
            st.session_state.pipeline_prompt = prompt

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Optimo is thinking…")

            try:
                # Run the pipeline
                response = run_pipeline(full_prompt)

                if (
                    not response
                    or "MALFORMED_FUNCTION_CALL" in response
                    or response.strip() == ""
                ):
                    response = "Oops, that didn’t work. Try again."
            except RuntimeError as e:
                response = f"Clarification needed:\n{str(e)}"
                st.session_state.awaiting_clarification = True
            except Exception as e:
                import google

                if (
                    hasattr(google, "genai")
                    and hasattr(google.genai.errors, "ClientError")
                    and isinstance(e, google.genai.errors.ClientError)
                ):
                    if getattr(e, "code", None) == 429:
                        response = (
                            "⚠️ Sorry, we currently have some issues (quota exceeded). "
                            "Please try again later."
                        )
                    else:
                        response = "Oops, something went wrong with the AI service. Try again later."
                else:
                    response = "Oops, that didn’t work. Try again."

            message_placeholder.markdown(response)

        st.session_state.messages.append(
            {"role": "assistant", "content": response}
        )


def show_logout_message():
    st.markdown(
        "<div class='card' style='background: linear-gradient(-45deg, #f4d03f, #f1c40f, #f7dc6f, #f9e79f); padding:3rem; text-align:center; border-radius:20px;'>"
        "<h2 style='color:#4b3429;'>You have been successfully logged out.</h2>"
        "<p>Thank you for using Optimo. See you next time!</p></div>",
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
