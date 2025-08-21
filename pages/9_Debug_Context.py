# pages/9_Debug_Context.py
import json, streamlit as st
from utils.state import ensure_session_keys
ensure_session_keys()
st.title("Debug / Session")
st.json({
    "score_today": st.session_state.get("score_today"),
    "logged": st.session_state.get("logged"),
    "ai_language": st.session_state.get("ai_language"),
})
st.subheader("Coach Context")
st.code(json.dumps(st.session_state.get("__coach_ctx__",{}), indent=2, ensure_ascii=False))
