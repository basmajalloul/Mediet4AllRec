# auth_ui.py
from __future__ import annotations
import streamlit as st
from utils.db import current_user, sign_in_password, sign_up_password, send_otp, verify_otp, sign_out

def _sidebar_status(user: dict):
    with st.sidebar:
        st.success(f"Signed in as {user.get('email', 'user')}")
        if st.button("Sign out"):
            sign_out()
            st.rerun()

def auth_gate() -> dict:
    """
    Blocks the page until a user is authenticated.
    Returns the user dict when signed in.
    """
    user = current_user()
    if user:
        _sidebar_status(user)
        return user

    st.title("Welcome to Mediet4All")
    st.caption("Sign in or create an account to continue.")

    tab_login, tab_signup, tab_otp = st.tabs(["Sign In", "Create Account", "Email Code (OTP)"])

    # ---- Sign In ----
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In")
        if submitted:
            if not email or not password:
                st.error("Please enter your email and password.")
            else:
                try:
                    res = sign_in_password(email, password)
                    if res.get("user"):
                        st.success("Signed in ✅")
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
                except Exception as e:
                    st.error(f"Sign in failed: {e}")

    # ---- Create Account ----
    with tab_signup:
        with st.form("signup_form"):
            email_s = st.text_input("Email", key="su_email")
            pw_s = st.text_input("Password (min 8 chars)", type="password", key="su_pw")
            pw2_s = st.text_input("Confirm password", type="password", key="su_pw2")
            privacy = st.checkbox("I agree to the Privacy Policy and Terms")
            submitted_s = st.form_submit_button("Create Account")
        if submitted_s:
            if not email_s or not pw_s or not pw2_s:
                st.error("Please complete all fields.")
            elif len(pw_s) < 8:
                st.error("Password must be at least 8 characters.")
            elif pw_s != pw2_s:
                st.error("Passwords do not match.")
            elif not privacy:
                st.error("Please agree to the Privacy Policy and Terms.")
            else:
                try:
                    res = sign_up_password(email_s, pw_s)
                    if res.get("user"):
                        st.success("Account created ✅. You can sign in now.")
                        st.info("If email confirmation is enabled, please verify your email before signing in.")
                    else:
                        st.error("Sign up failed. Try a different email.")
                except Exception as e:
                    st.error(f"Sign up failed: {e}")

    # ---- OTP (Email code) ----
    with tab_otp:
        st.write("Passwordless login: receive a one-time code by email.")
        col1, col2 = st.columns([2,1])
        with col1:
            email_o = st.text_input("Email for OTP", key="otp_email", placeholder="you@example.com")
        with col2:
            if st.button("Send code"):
                if not email_o:
                    st.error("Enter an email first.")
                else:
                    try:
                        send_otp(email_o)
                        st.success("Code sent. Check your inbox.")
                    except Exception as e:
                        st.error(f"Could not send code: {e}")
        code = st.text_input("Enter the 6-digit code", max_chars=6)
        if st.button("Verify code"):
            if not email_o or not code:
                st.error("Provide both email and code.")
            else:
                try:
                    res = verify_otp(email_o, code)
                    if res.get("user"):
                        st.success("Signed in ✅")
                        st.rerun()
                    else:
                        st.error("Invalid or expired code.")
                except Exception as e:
                    st.error(f"Verification failed: {e}")

    st.stop()  # prevent the rest of the page from rendering until signed in

    # auth_ui.py (replace _sidebar_status)
import hashlib
def _sidebar_status(user: dict):
    email = user.get("email", "user@example.com")
    initials = (email[:1] or "U").upper()
    # deterministic soft color from email hash
    hue = int(hashlib.md5(email.encode()).hexdigest(), 16) % 360
    bg = f"hsl({hue}, 75%, 90%)"
    fg = f"hsl({hue}, 60%, 30%)"

    with st.sidebar:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:12px;margin:10px 0 6px 0;">
              <div style="width:42px;height:42px;border-radius:50%;
                          display:flex;align-items:center;justify-content:center;
                          background:{bg};color:{fg};font-weight:800;">
                {initials}
              </div>
              <div>
                <div style="font-weight:700">{email}</div>
                <div style="font-size:12px;opacity:.7">Signed in</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        # Link to Profile page (works with multipage apps)
        try:
            st.page_link("pages/5_Profile.py", label="👤 Edit Profile")
        except Exception:
            st.write("👤 Open Profile page from the sidebar")

        if st.button("Sign out"):
            sign_out()
            st.rerun()
