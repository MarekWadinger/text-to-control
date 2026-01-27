from datetime import date, datetime

import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection


def get_usage_df(conn):
    try:
        df = conn.read(worksheet="UsageLog", ttl="0")
        return df
    except Exception:
        # If sheet is empty or doesn't exist, return empty DF
        return pd.DataFrame(columns=["email", "last_used_date"])


def check_can_use_free_tier(email: str | None) -> bool:
    """Check whether the user used their free request today."""
    if not email:
        return False

    if email in st.secrets.auth.admin_emails:
        return True

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = get_usage_df(conn)

        # Check if email exists
        user_row = df[df["email"] == email]

        if user_row.empty:
            return True

        last_date_str = user_row.iloc[0]["last_used_date"]

        try:
            last_date = datetime.strptime(
                str(last_date_str), "%Y-%m-%d"
            ).date()
            return last_date < date.today()
        except (ValueError, TypeError):
            # If date format is wrong, assume they used it (fail closed)
            return False

    except Exception as e:
        # If connection fails (e.g. no secrets set up), log error and fail closed
        print(f"Error checking free tier: {e}")
        return False


def mark_free_tier_used(email: str | None):
    """Record whether the user used their free request today."""
    if not email:
        return

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = get_usage_df(conn)

        today_str = date.today().strftime("%Y-%m-%d")

        # Update or append
        if email in df["email"].values:
            df.loc[df["email"] == email, "last_used_date"] = today_str
        else:
            new_row = pd.DataFrame(
                [{"email": email, "last_used_date": today_str}]
            )
            df = pd.concat([df, new_row], ignore_index=True)

        conn.update(worksheet="UsageLog", data=df)

    except Exception as e:
        print(f"Error marking free tier used: {e}")
