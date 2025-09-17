from datetime import date
from utils.db import load_day_log, clear_meal, remove_log_by_recipe
from utils.ui import inject_css_and_title, topbar_logo_and_title, energy_banner, logged_section
from utils.state import ORDERED_MEALS
from utils.auth_ui import auth_gate
import streamlit as st
import pandas as pd 
from utils.state import ensure_session_keys
from utils.db import load_profile
from meddiet_rules import derive_daily_calorie_target, split_meal_targets

inject_css_and_title()
topbar_logo_and_title()
ensure_session_keys()

user = auth_gate()
user_id = user["id"]
st.session_state["__user_id__"] = user["id"]
today = date.today()

def hydrate_logged_from_db():
    # (a) re-fetch if dirty or first time today
    key = f"__hydrated_log__:{today.isoformat()}"
    must_refresh = st.session_state.pop("__log_dirty__", False) or not st.session_state.get(key)

    if must_refresh:
        rows = load_day_log(user_id, today)
        st.session_state["__today_rows__"] = rows
        st.session_state["logged_db"] = [str(x["recipe_id"]) for x in rows]
        st.session_state[key] = True

        # drop any optimistic items that are now in DB
        local = st.session_state.get("__logged_local__", set())
        st.session_state["__logged_local__"] = {rid for rid in local if rid not in st.session_state["logged_db"]}

    # (b) effective = DB ∪ local
    db_ids   = st.session_state.get("logged_db", [])
    local_ids = st.session_state.get("__logged_local__", set())
    effective = sorted(set(db_ids) | set(local_ids))

    st.session_state["logged"] = effective
    st.session_state["score_today"] = len(effective)

hydrate_logged_from_db()


# hydrate from DB (cache per session/day)
key = f"__hydrated_log__:{today.isoformat()}"
if not st.session_state.get(key):
    rows = load_day_log(user_id, today)
    st.session_state["__today_rows__"] = rows
    st.session_state[key] = True

rows = st.session_state.get("__today_rows__", [])
df = pd.DataFrame(rows)

st.session_state["logged"] = [str(x["recipe_id"]) for x in rows]
st.session_state["score_today"] = len(st.session_state["logged"])

today = date.today()
rows = load_day_log(user_id, today)  

# normalize keys so UI helpers don't break
for r in rows:
    r["rid"] = r.get("recipe_id") or r.get("id")


qp = st.query_params  # <-- property, not a function

# ?rm=<recipe_id>
rid = qp.get("rm")
if rid:
    if isinstance(rid, list):  # tolerate both str and [str]
        rid = rid[0]
    remove_log_by_recipe(user_id, today, str(rid))
    if "rm" in st.query_params:
        del st.query_params["rm"]   # clear the param (replace experimental API)
    st.rerun()

# ?rm_all=<meal_type>
which = qp.get("rm_all")
if which:
    if isinstance(which, list):
        which = which[0]
    clear_meal(user_id, today, str(which))
    if "rm_all" in st.query_params:
        del st.query_params["rm_all"]
    st.rerun()

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

st.markdown("## Logged Today")
logged_section(rows, per_meal)

if st.button("🗑️ Reset logged meals", use_container_width=True):
    from utils.state import ORDERED_MEALS
    for m in ORDERED_MEALS:
        clear_meal(user_id, today, m)
    st.rerun()

