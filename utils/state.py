# utils/state.py
import os, json
import pandas as pd
import streamlit as st
from typing import Dict, List, Tuple
from meddiet_rules import (
    derive_daily_calorie_target, split_meal_targets,
    recommend, daily_adherence_from_logs,
)
from utils.db import activities_for_day, sum_activity_kcal_for_day
from datetime import date


# ------------------ constants ------------------
ORDERED_MEALS = ["Breakfast", "Lunch", "Dinner", "Snack"]
MODEL_NAME = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# ------------------ data ------------------
@st.cache_data(show_spinner=False)
def load_recipes(path: str = "") -> pd.DataFrame:
    # Ignore path: recipes now come from Supabase
    from utils.db import load_recipes_db
    df = load_recipes_db()
    return df

# utils/state.py
def ensure_session_keys():
    st.session_state.setdefault("df", load_recipes())
    st.session_state.setdefault("logged", [])
    st.session_state.setdefault("score_today", 0)
    st.session_state.setdefault("ai_language", "English")
    st.session_state.setdefault("optimized_set", set()) 


# ------------------ profile & targets ------------------
def get_profile_from_sidebar() -> Tuple[Dict, Dict, Dict, str]:
    with st.sidebar:
        st.subheader("User Profile")
        age   = st.number_input("Age", 12, 99, 25)
        height= st.number_input("Height (cm)", 120, 210, 180)
        sex   = st.selectbox("Sex", ["Female","Male"], index=1)
        weight= st.number_input("Weight (kg)", 35.0, 200.0, 80.0, step=0.5)
        activity = st.selectbox("Activity", ["Sedentary","Light","Moderate","Active","Very Active"], index=1)
        goal     = st.selectbox("Goal", ["Maintain","Fat Loss","Weight Gain"], index=0)

        st.markdown("---")
        st.subheader("Health Conditions")
        hypertension   = st.checkbox("High blood pressure (Hypertension)")
        diabetes       = st.checkbox("Type 2 Diabetes")
        prediabetes    = st.checkbox("Prediabetes / Insulin resistance")
        hyperlipidemia = st.checkbox("High cholesterol / Hyperlipidemia")
        celiac         = st.checkbox("Celiac disease (gluten intolerance)")
        gerd           = st.checkbox("GERD / reflux")
        autoimmune     = st.checkbox("Rheumatoid arthritis / Autoimmune (anti-inflammatory)")

        st.markdown("---")
        st.subheader("Dietary Style & Constraints")
        vegan = st.checkbox("Vegan")
        vegetarian = st.checkbox("Vegetarian")
        pescatarian = st.checkbox("Pescatarian")
        gluten_free = st.checkbox("Gluten-free")
        dairy_free  = st.checkbox("Dairy-free")
        prefer      = st.text_input("Prefer ingredients (comma-separated)", "olive oil, chickpeas")
        avoid       = st.text_input("Avoid ingredients (comma-separated)", "anchovies")

        st.markdown("---")
        st.subheader("Meal Pattern")
        pattern = st.selectbox("Pattern", ["3_meals_1_snack", "2_meals_2_snacks"], index=0)

        st.markdown("---")
        st.subheader("AI Coach")
        ai_language = st.selectbox("Language", ["English","العربية","Français"], index=0)
        st.session_state["ai_language"] = ai_language

    diet_prefs = {
        "vegan": vegan,
        "vegetarian": (not vegan) and vegetarian,
        "pescatarian": (not vegan and not vegetarian) and pescatarian,
        "gluten_free": gluten_free or celiac,
        "dairy_free": dairy_free,
        "prefer_ingredients": prefer,
        "avoid_ingredients": avoid,
    }
    health = {
        "hypertension": hypertension, "diabetes": diabetes, "prediabetes": prediabetes,
        "hyperlipidemia": hyperlipidemia, "celiac": celiac, "gerd": gerd, "autoimmune": autoimmune,
    }
    profile = {
        "age": int(age), "sex": sex, "height_cm": int(height), "weight_kg": float(weight),
        "activity": activity, "goal": goal
    }
    return profile, diet_prefs, health, pattern

def compute_targets(profile: Dict, pattern: str) -> Tuple[int, Dict[str,int]]:
    daily = derive_daily_calorie_target(
        profile["age"], profile["weight_kg"], profile["height_cm"],
        profile["sex"], profile["activity"], profile["goal"]
    )
    per_meal = split_meal_targets(daily, pattern)
    return daily, per_meal

# ------------------ ai context helpers ------------------
def summarize_logged_stats(df_all: pd.DataFrame, logged_ids: List[str]) -> dict:
    if not logged_ids: return {"totals": {}, "macro_pct": {}}
    sub = df_all[df_all["recipe_id"].isin(logged_ids)]
    total_kcal = float(sub["calories_kcal"].sum())
    totals = {
        "calories_kcal": total_kcal,
        "protein_g": float(sub["protein_g"].sum()),
        "carbs_g": float(sub["carbs_g"].sum()),
        "fat_g": float(sub["fat_g"].sum()),
        "fiber_g": float(sub["fiber_g"].sum()),
        "sodium_mg": float(sub["sodium_mg"].sum()),
    }
    cal_p = 4.0*totals["protein_g"]; cal_c = 4.0*totals["carbs_g"]; cal_f = 9.0*totals["fat_g"]
    denom = max(1.0, cal_p + cal_c + cal_f)
    macro_pct = {
        "protein_pct": round(100*cal_p/denom),
        "carbs_pct": round(100*cal_c/denom),
        "fat_pct": round(100*cal_f/denom),
    }
    return {"totals": totals, "macro_pct": macro_pct}

def build_ai_context(df_all: pd.DataFrame, logged_ids: List[str],
                     profile: Dict, targets: Dict, adherence: Dict, user_id: str) -> dict:
    from datetime import date
    from utils.db import activities_for_day

    # --- meals summary ---
    meals = []
    for rid in logged_ids:
        row = df_all[df_all["recipe_id"] == rid].iloc[0].to_dict()
        meals.append({
            "recipe_id": row["recipe_id"],
            "name": row["name"],
            "meal_type": row["meal_type"],
            "kcal": float(row["calories_kcal"]),
            "protein_g": float(row["protein_g"]),
            "carbs_g": float(row["carbs_g"]),
            "fat_g": float(row["fat_g"]),
            "fiber_g": float(row["fiber_g"]),
            "sodium_mg": float(row["sodium_mg"]),
            "tags": str(row.get("med_attributes", "")),
        })

    # --- activity summary ---
    acts = activities_for_day(user_id, date.today())
    total_activity_kcal = float(sum((a.get("calories") or 0) for a in acts))
    activity_summary = {
        "total_kcal_burned": total_activity_kcal,
        "count": len(acts),
        "details": [
            {
                "kind": a.get("kind"),
                "intensity": a.get("intensity"),
                "duration_min": a.get("duration_min"),
                "steps": a.get("steps"),
                "calories": a.get("calories"),
            }
            for a in acts
        ],
    }

    # --- energy balance ---
    day_stats = summarize_logged_stats(df_all, logged_ids)
    total_intake = day_stats["totals"].get("calories_kcal", 0)
    net_energy = total_intake - total_activity_kcal

    return {
        "profile": profile,
        "targets": targets,
        "adherence": adherence,
        "logged_meals": meals,
        "day_stats": day_stats,
        "activity_summary": activity_summary,
        "net_energy": net_energy,
    }

# simple utility so all pages can get a live snapshot
def live_snapshot(profile, per_meal, daily):
    df = st.session_state["df"]
    logged = st.session_state["logged"]
    adh = daily_adherence_from_logs(df, logged)
    return {
        "df": df, "logged": logged, "adh": adh,
        "targets": {"daily_kcal": daily, "per_meal_kcal": per_meal}
    }
