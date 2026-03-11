import time
from functools import wraps

import logfire
import streamlit as st

from app.access_control import check_can_use_free_tier, mark_free_tier_used
from app.backend_interface import run_pipeline
from config import Settings
from src.agents.expert import ExpertInquiry
from src.pipeline import ClarificationNeeded

settings = Settings()


def scrubbing_callback(m: logfire.ScrubMatch):
    if m.path == ("message", "e") and m.pattern_match.group(0) == "session":
        return m.value

    if m.path == ("attributes", "e") and m.pattern_match.group(0) == "session":
        return m.value


logfire.configure(
    token=settings.logfire_token,
    send_to_logfire="if-token-present",
    distributed_tracing=False,
    service_name="app",
    environment=settings.environment,
    scrubbing=logfire.ScrubbingOptions(callback=scrubbing_callback),
)
logfire.instrument_pydantic_ai()
# --- Setup ---
st.set_page_config(page_title="Optimo.ai", page_icon="🔮", layout="wide")

# Initialize API key in session state if not present
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# --- Session State Initialization (from app.py) ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pipeline_prompt" not in st.session_state:
    st.session_state.pipeline_prompt = ""
if "awaiting_clarification" not in st.session_state:
    st.session_state.awaiting_clarification = False
if "clarification_context" not in st.session_state:
    st.session_state.clarification_context = ""
if "last_call_time" not in st.session_state:
    st.session_state.last_call_time = 0

RATE_LIMIT_SECONDS = 3


# Rate limiting decorator
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


def get_user_email() -> str | None:
    """Return the logged-in user's email if available."""
    if not (st.user.is_logged_in and hasattr(st.user, "email")):
        return None
    user_email = st.user.email
    return user_email if isinstance(user_email, str) else None


@rate_limit
def run_backend(prompt_text):
    # Check usage before running
    system_key = st.secrets.get("OPENAI_API_KEY", "")

    # Check if we have a valid key to use (either system or user provided)
    has_valid_access = False

    user_email = get_user_email()
    if user_email:
        # Check if using free tier
        if st.session_state.api_key == system_key and system_key:
            # Re-verify free tier availability before execution
            if check_can_use_free_tier(user_email):
                mark_free_tier_used(user_email)
                has_valid_access = True
            else:
                # Should be caught by UI, but double check
                return "⚠️ **Daily limit reached.**\nPlease provide your own LLM API Key in the sidebar to continue."
        elif st.session_state.api_key:
            # Using personal key
            has_valid_access = True
        else:
            return "⚠️ **Daily limit reached.**\nPlease provide your own LLM API Key in the sidebar to continue."
    elif st.session_state.api_key:
        # Guest with key
        has_valid_access = True

    if not has_valid_access:
        return "🔒 **Access Restricted**\nPlease log in or provide a LLM API Key in the sidebar to proceed."

    return run_pipeline(prompt_text)


# --- Sidebar Logic ---
with st.sidebar:
    st.markdown("## 🔮 Optimo Access")
    st.markdown("---")

    # Login Section
    if not st.user.is_logged_in:
        st.markdown("#### 🔓 Log In")
        st.caption("Sign in with Google to get **1 free daily request**.")
        if st.button("Log in with Google", use_container_width=True):
            st.login("google")

        st.markdown("---")
        st.markdown("#### 🔑 Guest Access")
        st.caption(
            'Already have an API Key? Use it directly or go to <a href="https://aistudio.google.com" target="_blank">aistudio.google.com</a> and grab a new one.',
            unsafe_allow_html=True,
        )
        user_key = st.text_input(
            "LLM API Key",
            type="password",
            key="guest_api_key",
            placeholder="AIzaSy...",
        )
        if user_key and user_key != st.session_state.api_key:
            st.session_state.api_key = user_key
            st.toast("API Key accepted!", icon="✅")

    else:
        # User is logged in
        st.success(f"Welcome, **{st.user.name}**!")
        if st.button("Log out", use_container_width=True):
            st.logout()

        st.markdown("---")

        system_key = st.secrets.get("OPENAI_API_KEY", "")
        user_email = get_user_email()
        free_tier_available = (
            user_email is not None and check_can_use_free_tier(user_email)
        )

        if free_tier_available:
            st.info("✅ **Daily Free Request Available**")
            # If user hasn't provided a custom key, use system key
            if not st.session_state.api_key:
                st.session_state.api_key = system_key
        else:
            if not st.session_state.api_key:
                st.warning("⚠️ **Daily Free Limit Reached**")
            st.caption(
                "Please provide your own API key to continue using the app today."
            )
            # Reset key if it was the system key
            if st.session_state.api_key == system_key:
                st.session_state.api_key = ""

        # Allow overriding with personal key even if free tier is available
        user_key = st.text_input(
            "Your LLM API Key",
            type="password",
            value=st.session_state.api_key
            if st.session_state.api_key != system_key
            else "",
            key="user_api_key",
            placeholder="Paste your key here (overrides free tier)",
        )

        if user_key:

            def is_valid_llm_key(key: str) -> bool:
                return (
                    # (key.startswith("AIza") or key.startswith("GOCSPX"))  # Gemini API Key
                    isinstance(key, str)
                    and key.startswith("sk-")  # OpenAI API Key
                    and len(key) >= 30
                    and key != system_key
                )

            if user_key != st.session_state.api_key:
                with st.spinner("Validating API Key..."):
                    if is_valid_llm_key(user_key):
                        st.session_state.api_key = user_key
                        st.toast("API Key accepted and validated!", icon="✅")
                    else:
                        st.warning(
                            "❌ The provided API Key is invalid. Please check and try again."
                        )
        elif free_tier_available:
            # Re-ensure system key is set if user cleared the input but free tier is valid
            st.session_state.api_key = system_key

    st.markdown("---")
    st.caption("© 2026 Optimo.ai\nAgent-based control system design")


# --- Main Content ---
# Always show chat interface

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
        if st.button("Reset Chat", help="Clear conversation history"):
            st.session_state.messages = []
            st.session_state.pipeline_prompt = ""
            st.session_state.awaiting_clarification = False
            st.rerun()

# CSS for Chat Input
st.markdown(
    """
<style>
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

# Welcome Message Placeholder
placeholder_container = st.empty()
if len(st.session_state.messages) == 0:
    placeholder_container.html(
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
    )

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input Processing
if prompt := st.chat_input(
    "Provide clarifications…"
    if st.session_state.awaiting_clarification
    else "Ask Optimo…",
    key="chat_input",
    # TODO: Add file upload support by adding multimodal capabilities to the model
    # accept_file="directory",
    # file_type=["jpg", "jpeg", "png", "pdf"],
):
    st.session_state.messages.append({"role": "user", "content": prompt})

    placeholder_container.empty()

    with st.chat_message("user"):
        st.markdown(prompt)

    if st.session_state.awaiting_clarification:
        clarification_context = st.session_state.clarification_context
        if clarification_context:
            full_prompt = (
                f"{st.session_state.pipeline_prompt}\n"
                f"{clarification_context}\n"
                f"Clarifications:\n{prompt}"
            )
        else:
            full_prompt = f"{st.session_state.pipeline_prompt}\nClarifications:\n{prompt}"
        st.session_state.clarification_context = ""
        st.session_state.awaiting_clarification = False
    else:
        full_prompt = prompt
        st.session_state.pipeline_prompt = prompt

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Optimo is thinking…")

        try:
            # Run the pipeline using the rate-limited, access-aware wrapper
            response = run_backend(full_prompt)

            if (
                not response
                or "MALFORMED_FUNCTION_CALL" in response
                or response.strip() == ""
            ):
                response = "Oops, I couldn't process your request. Try again."
        except ClarificationNeeded as e:
            response = e.inquiry
            st.session_state.awaiting_clarification = True
            st.session_state.clarification_context = e.inquiry
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
                response = "Oops, that didn't work. Try again."
                # Log for debugging
                logfire.error("Error in pipeline: {error}", error=e)

        if isinstance(response, ExpertInquiry):
            with message_placeholder.form(
                "Clarification Form",
                border=False,
                enter_to_submit=True,
            ):
                st.markdown(response.explanation)
                answers = []
                for question in response.clarification_questions:
                    answer = st.radio(question.question, question.choices)
                    answers.append(answer)
                submitted = st.form_submit_button("Submit")
                if submitted:
                    st.session_state.clarification_context = (
                        f"Clarifications answers: \n{'\n'.join(answers)}"
                    )
                    st.session_state.awaiting_clarification = False
        else:
            message_placeholder.markdown(response)

    st.session_state.messages.append(
        {"role": "assistant", "content": response}
    )
