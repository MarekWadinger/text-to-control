import json
import os

import requests
import streamlit as st

# ---------------- CONFIG ----------------
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

DEMO_LOG_FILE = "demo_log.json"
DEVELOPER_IPS = ["195.28.146.244", "46.34.243.58"]


# ---- IP detection ----
def get_public_ip():
    """Retrieves the user's public IP address using an external service."""
    try:
        ip = requests.get("https://api.ipify.org").text.strip()
        return ip
    except:
        return "unknown"


def load_demo_log():
    if os.path.exists(DEMO_LOG_FILE):
        try:
            with open(DEMO_LOG_FILE) as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        except json.JSONDecodeError:
            return []
    return []


def save_demo_log(log_list):
    """Saves the list of IPs that have already used the demo."""
    with open(DEMO_LOG_FILE, "w") as f:
        json.dump(log_list, f, indent=2)


# ---------------- DEMO LOGIN ----------------
def handle_demo_login():
    """Handles the demo login for 'user1/password1'."""
    ip = get_public_ip()
    demo_log = load_demo_log()

    if ip in DEVELOPER_IPS:
        st.session_state.authenticated = True
        st.session_state.username = "user1"
        st.session_state.demo_used = False
        return True

    if ip in demo_log:
        return False

    demo_log.append(ip)
    save_demo_log(demo_log)

    st.session_state.authenticated = True
    st.session_state.username = "user1"
    st.session_state.demo_used = True
    return True
