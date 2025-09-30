# pages/1_Recommendations.py
import streamlit as st
from meddiet_rules import recommend, derive_daily_calorie_target, split_meal_targets
from utils.state import ensure_session_keys, ORDERED_MEALS
from utils.ui import inject_css_and_title, topbar_logo_and_title, render_recipe_card
from utils import ml
from datetime import date
from utils.ui import energy_banner, render_recipe_card_compact
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
health      = st.session_state.get("__health__", {})
per_meal    = st.session_state.get("__per_meal__", {"Breakfast":0,"Lunch":0,"Dinner":0,"Snack":0})

#print(df.head())



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

# Build diet_prefs for the rules engine (expects strings + booleans)
diet_prefs = {
    "vegan":        bool(prof.get("diet_style", {}).get("vegan")),
    "vegetarian":   bool(prof.get("diet_style", {}).get("vegetarian")),
    "pescatarian":  bool(prof.get("diet_style", {}).get("pescatarian")),
    "gluten_free":  bool(prof.get("diet_style", {}).get("gluten_free")),
    "dairy_free":   bool(prof.get("diet_style", {}).get("dairy_free")),
    # comma-separated strings, matched against recipe ingredient text
    "prefer_ingredients": ", ".join(prof.get("prefer", []) or []),
    "avoid_ingredients":  ", ".join(prof.get("avoid",  []) or []),
}
st.session_state["__diet_prefs__"] = diet_prefs

# cache heavy bits once
idx = ml.build_recipe_index(df)
RESCORER = ml.train_rescorer(df, per_meal, diet_prefs, health)

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

st.markdown("""<style>                
        .stRadio {
            width: calc(100vw - 470px);
            display: flex;
            flex-direction: row;
            flex-wrap: nowrap;
            align-content: center;
            align-items: center;
            justify-content: flex-end;
            column-gap: 10px;
            float: right !important;
            margin-bottom: -60px;
            position: relative;
            z-index: 100;
        }

        .stRadio * {
            font-size: 13px;
        }

        .stRadio input {position: relative;top: -3px !important;}

        .stRadio p {
            margin-top: 3px !important;
            color: #666;
            font-weight: bold;
        }

        .stRadio>label {
            position: relative;
            top: 2px;
        }  

        .stTabs button {
            position: relative;
            z-index: 200;
        } 
                
        .stTabs button p {
            font-weight: bold;
        }

        .stTabs {
            margin-top: -15px;
        } 
                
        .view-switch label {
            background: #f4f4f7;
            padding: 6px 12px;
            border-radius: 6px;
            margin-left: 6px;
            cursor: pointer;
        }
        .view-switch label[data-checked="true"] {
            background: #ff6600;
            color: white;
        }</style>""", unsafe_allow_html=True)

# --- Tabs with persistence ---
meal_order = ["Breakfast", "Lunch", "Dinner", "Snack"]
list_icon = "📃"   # or inline SVG if you prefer
grid_icon = "🔲"

view_mode = st.radio(
    "View mode:",
    ["Compact", "Expanded"],
    format_func=lambda x: f"{list_icon} Compact" if x=="Expanded" else f"{grid_icon} List",
    horizontal=True
)

# Get current tab from session (default = Breakfast)
active_tab = st.session_state.get("active_tab", meal_order[0])

# Build tabs
tabs = st.tabs(meal_order)


for i, (tab, meal) in enumerate(zip(tabs, meal_order)):
    with tab:
        # mark this tab as active ONLY if it's the one actually open
        if st.session_state.get("_current_tab") != meal:
            st.session_state["_current_tab"] = meal
        # use that for persistence
        active_tab = st.session_state["_current_tab"]

        target_kcal = per_meal[meal]
        pool = recommend(df, meal, target_kcal, diet_prefs, health, k=24,
                         exclude_recipe_ids=st.session_state.get("logged", []))
        if pool.empty:
            st.warning("No matching recipes found for current filters. Try relaxing constraints.")
            continue

        pool = ml.apply_rescorer_blend(pool, RESCORER, alpha=0.6)
        emb_rows = [idx["rid2pos"][rid] for rid in pool["recipe_id"].tolist()]
        emb_pool = idx["emb"][emb_rows]

        default_k = 25
        # get current "how many to show"
        k_val = st.session_state.get(f"shown_{meal}", default_k)

        # rerank top-k
        topk = ml.mmr_rerank(pool.reset_index(drop=True), emb_pool,
                            k=min(k_val, len(pool)), lambda_tradeoff=0.8, rel_col="fit_blend")

        if view_mode == "Expanded":
            # 3 columns per row
            rows = [topk.iloc[i:i+3] for i in range(0, len(topk), 3)]
            for chunk in rows:
                cols = st.columns(3)
                for c, (_, rr) in zip(cols, chunk.iterrows()):
                    with c:
                        st.markdown("""<style>
                                    .stTabs [role="tabpanel"] button {
                                            margin-bottom: -45px !important;
                                        }
                                    .instructions {
                                        display: -webkit-box;
                                        -webkit-line-clamp: 4;  /* show 4 lines max */
                                        -webkit-box-orient: vertical;
                                        overflow: hidden;
                                        text-overflow: ellipsis;
                                        white-space: normal;
                                    }
                                    </style>""", unsafe_allow_html=True)
                        render_recipe_card(rr, kcal_target=target_kcal, diet_prefs=diet_prefs, health=health, log_key_prefix=meal.lower())
        else:
            # Compact → 4 per row
            rows = [topk.iloc[i:i+5] for i in range(0, len(topk), 5)]
            for chunk in rows:
                cols = st.columns(5)
                for c, (_, rr) in zip(cols, chunk.iterrows()):
                    with c:
                        st.markdown("""<style>
                                    .stTabs [role="tabpanel"] button {
                                            margin-bottom: 0px !important;
                                        }
                                    .title {
                                        font-size: 0.9rem;
                                        height: 50px;
                                    }
                                    .pill {
                                        font-size: 11px;
                                    }
                                    .pills {
                                        height: 50px;
                                    }
                                    span.badge {
                                        margin-bottom: -35px;
                                        display: block;
                                        width: fit-content;
                                        float: right;
                                        font-size: 12px;
                                        margin-top: -18px;
                                    }
                                    .stTabs [role="tabpanel"] button p {
                                        font-size: 13px;
                                    }

                                    .stTabs [role="tabpanel"] button {
                                        min-height: 2rem;
                                    }

                                    .sub {
                                        font-size: 12px;
                                    }

                                    p {
                                        margin: 0px !important;
                                    }

                                    a.link {
                                        margin-top: 20px;
                                    }
                                    </style>""", unsafe_allow_html=True)                        
                        render_recipe_card_compact(rr, kcal_target=target_kcal, diet_prefs=diet_prefs, health=health, log_key_prefix=meal.lower())


        # show "Load more" if we haven't reached the end
        if k_val < len(pool):
            if st.button(f"⬇️ Load more {meal} recipes", key=f"more_{meal}"):
                st.session_state[f"shown_{meal}"] = k_val + default_k
                st.rerun()

# ---- Auto-pick a balanced day (uses optimizer) ----
# st.markdown("---")
# if st.button("🎯 Auto-pick a balanced day", use_container_width=True):
#     B = recommend(df, "Breakfast", per_meal["Breakfast"], diet_prefs, health, k=10, exclude_recipe_ids=[])
#     L = recommend(df, "Lunch",     per_meal["Lunch"],     diet_prefs, health, k=10, exclude_recipe_ids=[])
#     D = recommend(df, "Dinner",    per_meal["Dinner"],    diet_prefs, health, k=10, exclude_recipe_ids=[])
#     S = recommend(df, "Snack",     per_meal["Snack"],     diet_prefs, health, k=10, exclude_recipe_ids=[])

#     daily = st.session_state.get("daily_cals")
#     if not daily:
#         # build daily target from defaults (same as your code path)
#         age = int(st.session_state.get("age", 32))
#         weight_kg = float(st.session_state.get("weight_kg", 68.0))
#         height_cm = float(st.session_state.get("height_cm", 165.0))
#         sex = st.session_state.get("sex", "Female")
#         activity = st.session_state.get("activity", "Light")
#         goal = st.session_state.get("goal", "Maintain")
#         daily = derive_daily_calorie_target(age, weight_kg, height_cm, sex, activity, goal)
#         st.session_state["daily_cals"] = daily

#     targ = {
#         "kcal": daily,
#         "protein_g": daily * 0.25 / 4.0,
#         "carb_g":    daily * 0.45 / 4.0,
#         "fat_g":     daily * 0.30 / 9.0,
#     }
#     picks = ml.optimize_day(B, L, D, S, targ)
#     st.session_state["optimized_set"] = set(picks or [])
#     st.success("Suggested a balanced set for today (cards are tagged 🎯 Picked).")
#     st.rerun()