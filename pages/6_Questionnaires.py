# 3_Questionnaires.py
import streamlit as st
from utils.surveys import MEDLIFE_ITEMS, medlife_score, IpaqInput, ipaq_score
from utils.state import ensure_session_keys, ORDERED_MEALS
from utils.ui import inject_css_and_title, topbar_logo_and_title
from datetime import date
from utils.ui import energy_banner
from meddiet_rules import derive_daily_calorie_target, split_meal_targets
from utils.db import load_profile, load_day_log

import pandas as pd

today = date.today()

ensure_session_keys()
inject_css_and_title()
topbar_logo_and_title()

from utils.auth_ui import auth_gate
user = auth_gate()
user_id = user["id"]
st.session_state["__user_id__"] = user["id"]
st.session_state.pop(f"__hydrated_log__:{date.today().isoformat()}", None)

# hydrate from DB (cache per session/day)
key = f"__hydrated_log__:{today.isoformat()}"
if not st.session_state.get(key):
    rows = load_day_log(user_id, today)
    st.session_state["__today_rows__"] = rows
    st.session_state[key] = True

rows = st.session_state.get("__today_rows__", [])

df = st.session_state["df"]
diet_prefs  = st.session_state.get("__diet_prefs__", {})
health      = st.session_state.get("__health__", {})
per_meal    = st.session_state.get("__per_meal__", {"Breakfast":0,"Lunch":0,"Dinner":0,"Snack":0})

# --- normalize & compute targets from DB profile ---
def _default_profile():
    return {
        "age": 30, "height_cm": 170, "sex": "Female", "weight_kg": 70.0,
        "activity": "Light", "goal": "Maintain", "pattern": "3_meals_1_snack",
        "ai_language": "English",
        "conditions": {}, "diet_style": {}, "prefer": ["olive oil"], "avoid": ["anchovies"]
    }

def _normalize(p: dict) -> dict:
    base = _default_profile()
    p = p or {}
    base.update({k: p.get(k, base[k]) for k in ["age","height_cm","sex","weight_kg","activity","goal","pattern","ai_language"]})
    base["conditions"] = {**base["conditions"], **(p.get("conditions") or {})}
    base["diet_style"] = {**base["diet_style"], **(p.get("diet_style") or {})}
    base["prefer"] = p.get("prefer", base["prefer"])
    base["avoid"]  = p.get("avoid",  base["avoid"])
    return base

active_name = st.session_state.get("active_profile_name", "default")
saved = load_profile(user_id, active_name)         # {} if none
prof  = _normalize(saved)

profile = {
    "age": int(prof["age"]), "sex": prof["sex"],
    "height_cm": int(prof["height_cm"]), "weight_kg": float(prof["weight_kg"]),
    "activity": prof["activity"], "goal": prof["goal"],
}
pattern = prof.get("pattern", "3_meals_1_snack")
daily   = derive_daily_calorie_target(profile["age"], profile["weight_kg"], profile["height_cm"],
                                      profile["sex"], profile["activity"], profile["goal"])
per_meal = split_meal_targets(daily, pattern)
st.session_state["daily_cals"]  = daily
st.session_state["__per_meal__"] = per_meal

# --- hydrate session for UI widgets that rely on it ---
st.session_state["logged"] = [str(x["recipe_id"]) for x in rows]
st.session_state["score_today"] = len(st.session_state["logged"])

energy_banner(daily, per_meal, df=st.session_state["df"])

st.markdown("## Questionnaires")
st.caption("MEDLIFE (Mediterranean lifestyle) and IPAQ (physical activity)")

tabs = st.tabs(["MEDLIFE Index", "IPAQ-Short Form"])

# -------- MEDLIFE --------
with tabs[0]:
    st.subheader("MEDLIFE Index")
    st.caption("Tick **Yes** if you meet the criterion in a usual week; **No** otherwise. Each Yes=1 point.")
    yes_no = []
    cols = st.columns(2)
    for i, (label, _) in enumerate(MEDLIFE_ITEMS):
        with cols[i % 2]:
            yes_no.append(st.toggle(f"{i+1}. {label}", value=False))
    res = medlife_score(yes_no)
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("MEDLIFE Score", f"{res['total']} / 28")
    with c2:
        st.metric("Adherence Level", res["label"])
    st.info("Guide: Low 0–9, Moderate 10–18, High 19–28 (or use cohort tertiles).")

# -------- IPAQ --------
with tabs[1]:
    st.subheader("IPAQ-Short Form (last 7 days)")
    st.caption("Enter days/week and minutes/day. Report sitting time separately.")
    older = st.checkbox("Use older-adult MET factors (2.5 / 3.0 / 5.3)?", value=False)

    def block(title):
        st.markdown(f"**{title}**")
        d, m = st.columns(2)
        days = d.number_input("Days/week", 0, 7, 0, key=f"{title}_d")
        mins = m.number_input("Minutes/day", 0, 1440, 0, key=f"{title}_m")
        return days, mins

    vig_d, vig_m = block("Vigorous activity")
    mod_d, mod_m = block("Moderate activity")
    walk_d, walk_m = block("Walking (≥10 min)")

    st.markdown("**Sitting (weekday)**")
    sit_h, sit_m = st.columns(2)
    sit_hours = sit_h.number_input("Hours/day", 0, 24, 0)
    sit_mins  = sit_m.number_input("Minutes/day", 0, 59, 0)

    ip = IpaqInput(
        walk_days=walk_d, walk_min_per_day=walk_m,
        mod_days=mod_d,  mod_min_per_day=mod_m,
        vig_days=vig_d,  vig_min_per_day=vig_m,
        sit_hours_per_day=sit_hours, sit_min_per_day=sit_mins,
        use_older_adult_coeffs=older
    )
    out = ipaq_score(ip)

    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Walking MET-min/wk", out["walking_met_min_week"])
    with c2: st.metric("Moderate MET-min/wk", out["moderate_met_min_week"])
    with c3: st.metric("Vigorous MET-min/wk", out["vigorous_met_min_week"])
    with c4: st.metric("TOTAL MET-min/wk", out["total_met_min_week"])
    st.metric("Physical Activity Level", out["activity_level"])
    st.caption(f"Sitting: {out['sitting_min_per_day']} min/day (report separately).")

import datetime as dt
from utils.db import get_client  # you already use this in other pages
from utils.adherence import compute_general_adherence  # new helper below

user_id = st.session_state.get("user_id")  # however you store it
today = dt.date.today()

if st.button("💾 Save today’s questionnaire scores", type="primary", use_container_width=True):
    if not user_id:
        st.error("No user logged in.")
    else:
        # Pull current meal adherence (from your existing log)
        from meddiet_rules import daily_adherence_from_logs  # 
        df_all = st.session_state["df"]
        logged_ids = st.session_state.get("logged", [])
        adh = daily_adherence_from_logs(df_all, logged_ids)  # {energy_score, component_score, total} 

        # Compute combined score (see section 3)
        general = compute_general_adherence(
            energy_score=adh["energy_score"],
            variety_score=adh["component_score"],
            medlife_total=res["total"],
            ipaq_total_met=out["total_met_min_week"],
            ipaq_level=out["activity_level"],
            sitting_min_per_day=out["sitting_min_per_day"]
        )

        payload = {
            "user_id": user_id,
            "day": str(today),
            "medlife_answers": yes_no,
            "medlife_total": int(res["total"]),
            "medlife_label": res["label"],
            "ipaq_input": {
                "older_adult": older,
                "vig_days": int(vig_d), "vig_min": int(vig_m),
                "mod_days": int(mod_d), "mod_min": int(mod_m),
                "walk_days": int(walk_d), "walk_min": int(walk_m),
                "sit_hours": int(sit_hours), "sit_min": int(sit_mins),
            },
            "ipaq_walking_met": out["walking_met_min_week"],
            "ipaq_moderate_met": out["moderate_met_min_week"],
            "ipaq_vigorous_met": out["vigorous_met_min_week"],
            "ipaq_total_met": out["total_met_min_week"],
            "ipaq_level": out["activity_level"],
            "ipaq_sitting_min": out["sitting_min_per_day"],
            "general_adherence": int(general)
        }

        try:
            supa = get_client()
            supa.table("questionnaires").upsert(payload, on_conflict="user_id,day").execute()
            st.success(f"Saved! General Adherence = {general}/100")
        except Exception as e:
            st.error(f"DB save failed: {e}")