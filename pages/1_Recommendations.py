# pages/1_Recommendations.py
import streamlit as st
from meddiet_rules import recommend, derive_daily_calorie_target, split_meal_targets
from utils.state import ensure_session_keys, ORDERED_MEALS
from utils.ui import inject_css_and_title, topbar_logo_and_title, render_recipe_card
from utils import ml
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

#print(df.head())

# cache heavy bits once
idx = ml.build_recipe_index(df)
RESCORER = ml.train_rescorer(df, per_meal, diet_prefs, health)


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

st.markdown("## Daily Recommendations")
tabs = st.tabs(["Breakfast", "Lunch", "Dinner", "Snack"])
meal_order = ["Breakfast", "Lunch", "Dinner", "Snack"]

for tab, meal in zip(tabs, meal_order):
    with tab:
        target_kcal = per_meal[meal]
        # 1) Big candidate pool from rule-engine
        # st.write("Unique meal types:", df["meal_type"].unique().tolist())
        # st.write("Calories sample:", df[["name","meal_type","calories_kcal"]].head(10))

        pool = recommend(
            df, meal, target_kcal, diet_prefs, health,
            k=24,
            exclude_recipe_ids=st.session_state.get("logged", [])
        )
        if pool.empty:
            st.warning("No matching recipes found for current filters. Try relaxing constraints.")
            continue

        # 2) Learned re-score + blend
        pool = ml.apply_rescorer_blend(pool, RESCORER, alpha=0.6)

        # 3) Diversity-aware top‑k via MMR
        emb_rows = [idx["rid2pos"][rid] for rid in pool["recipe_id"].tolist()]
        emb_pool = idx["emb"][emb_rows]
        topk = ml.mmr_rerank(pool.reset_index(drop=True), emb_pool, k=6, lambda_tradeoff=0.8, rel_col="fit_blend")

        # 4) Render cards (3 per row)
        rows = [topk.iloc[i:i+3] for i in range(0, len(topk), 3)]
        for chunk in rows:
            cols = st.columns(len(chunk))
            for c, (_, rr) in zip(cols, chunk.iterrows()):
                with c:
                    render_recipe_card(rr, kcal_target=target_kcal, diet_prefs=diet_prefs, health=health, log_key_prefix=meal.lower())

# ---- Auto-pick a balanced day (uses optimizer) ----
st.markdown("---")
if st.button("🎯 Auto-pick a balanced day", use_container_width=True):
    B = recommend(df, "Breakfast", per_meal["Breakfast"], diet_prefs, health, k=10, exclude_recipe_ids=[])
    L = recommend(df, "Lunch",     per_meal["Lunch"],     diet_prefs, health, k=10, exclude_recipe_ids=[])
    D = recommend(df, "Dinner",    per_meal["Dinner"],    diet_prefs, health, k=10, exclude_recipe_ids=[])
    S = recommend(df, "Snack",     per_meal["Snack"],     diet_prefs, health, k=10, exclude_recipe_ids=[])

    daily = st.session_state.get("daily_cals")
    if not daily:
        # build daily target from defaults (same as your code path)
        age = int(st.session_state.get("age", 32))
        weight_kg = float(st.session_state.get("weight_kg", 68.0))
        height_cm = float(st.session_state.get("height_cm", 165.0))
        sex = st.session_state.get("sex", "Female")
        activity = st.session_state.get("activity", "Light")
        goal = st.session_state.get("goal", "Maintain")
        daily = derive_daily_calorie_target(age, weight_kg, height_cm, sex, activity, goal)
        st.session_state["daily_cals"] = daily

    targ = {
        "kcal": daily,
        "protein_g": daily * 0.25 / 4.0,
        "carb_g":    daily * 0.45 / 4.0,
        "fat_g":     daily * 0.30 / 9.0,
    }
    picks = ml.optimize_day(B, L, D, S, targ)
    st.session_state["optimized_set"] = set(picks or [])
    st.success("Suggested a balanced set for today (cards are tagged 🎯 Picked).")
    st.rerun()