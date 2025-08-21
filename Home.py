# Home.py
import streamlit as st
from utils.state import ensure_session_keys, get_profile_from_sidebar, compute_targets
from utils.ui import inject_css_and_title, topbar_logo_and_title, energy_banner

ensure_session_keys()
inject_css_and_title()
topbar_logo_and_title()

profile, diet_prefs, health, pattern = get_profile_from_sidebar()
daily, per_meal = compute_targets(profile, pattern)
energy_banner(daily, {
    "Breakfast":per_meal["Breakfast"], "Lunch":per_meal["Lunch"],
    "Dinner":per_meal["Dinner"], "Snack":per_meal["Snack"]
})

st.markdown("---")
st.subheader("Welcome")
st.write(
  "Use the left navigation: **Recommendations** to pick meals, "
  "**Logged Today** to manage what you ate, and **Coach & Insights** for AI feedback and adherence."
)

# persist today’s “session snapshot” for other pages
st.session_state.update({
    "__profile__": profile, "__diet_prefs__": diet_prefs, "__health__": health,
    "__pattern__": pattern, "__daily__": daily, "__per_meal__": per_meal
})
