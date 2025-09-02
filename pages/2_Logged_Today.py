# pages/2_Logged_Today.py
import streamlit as st
from utils.state import ensure_session_keys
from utils.ui import inject_css_and_title, topbar_logo_and_title, logged_section

ensure_session_keys()
inject_css_and_title()
topbar_logo_and_title()

# handle ?rm / ?rm_all actions from iframe
try:
    params = st.query_params()
except Exception:
    try: params = dict(st.query_params)
    except Exception: params = {}

if "rm" in params:
    rid = params["rm"][0] if isinstance(params["rm"], list) else params["rm"]
    if rid in st.session_state["logged"]:
        st.session_state["logged"].remove(rid)
        st.session_state["score_today"] = max(0, int(st.session_state["score_today"]) - 1)
    st.experimental_set_query_params()
    st.rerun()

if "rm_all" in params:
    which = params["rm_all"][0] if isinstance(params["rm_all"], list) else params["rm_all"]
    df = st.session_state["df"]
    to_remove = df[(df["recipe_id"].isin(st.session_state["logged"])) & (df["meal_type"]==which)]["recipe_id"].tolist()
    removed = 0
    for x in to_remove:
        if x in st.session_state["logged"]:
            st.session_state["logged"].remove(x)
            removed += 1
    if removed:
        st.session_state["score_today"] = max(0, int(st.session_state["score_today"]) - removed)
    st.experimental_set_query_params()
    st.rerun()

from utils.ui import energy_banner
from meddiet_rules import split_meal_targets
from utils.state import ORDERED_MEALS

# --- show global energy/score banner on this page ---
per_meal = st.session_state.get("__per_meal__")
daily    = st.session_state.get("daily_cals")
if not per_meal:
    pattern = st.session_state.get("meal_pattern", "3_meals_1_snack")
    daily = daily or 2400
    per_meal = split_meal_targets(daily, pattern)
    st.session_state["__per_meal__"] = per_meal
if not daily:
    daily = int(sum(per_meal.get(m, 0) for m in ORDERED_MEALS))

df = st.session_state["df"]

energy_banner(daily, per_meal, df=df)  # recipes_df has recipe_id, meal_type, calories_kcal

st.markdown("## Logged Today")
df = st.session_state["df"]
per_meal = st.session_state.get("__per_meal__", {"Breakfast":0,"Lunch":0,"Dinner":0,"Snack":0})
logged_section(df, per_meal)

st.markdown("---")
if st.button("🗑️ Reset logged meals", use_container_width=True):
    st.session_state["logged"] = []
    st.session_state["score_today"] = 0
    st.rerun()
