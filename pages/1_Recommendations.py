# pages/1_Recommendations.py
import streamlit as st
from meddiet_rules import recommend, derive_daily_calorie_target, split_meal_targets
from utils.state import ensure_session_keys, load_recipes
from utils.ui import inject_css_and_title, topbar_logo_and_title, render_recipe_card
from utils import ml  # <-- NEW

ensure_session_keys()
inject_css_and_title()
topbar_logo_and_title()

df = st.session_state["df"]
diet_prefs  = st.session_state.get("__diet_prefs__", {})
health      = st.session_state.get("__health__", {})
per_meal    = st.session_state.get("__per_meal__", {"Breakfast":0,"Lunch":0,"Dinner":0,"Snack":0})

# cache heavy bits once
idx = ml.build_recipe_index(df)
RESCORER = ml.train_rescorer(df, per_meal, diet_prefs, health)

st.markdown("## Daily Recommendations")
tabs = st.tabs(["Breakfast", "Lunch", "Dinner", "Snack"])
meal_order = ["Breakfast", "Lunch", "Dinner", "Snack"]

for tab, meal in zip(tabs, meal_order):
    with tab:
        target_kcal = per_meal[meal]
        # 1) Big candidate pool from rule-engine
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