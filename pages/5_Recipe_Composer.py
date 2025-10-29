# pages/4_Recipe_Composer.py
import json, time
import streamlit as st
from utils.state import ensure_session_keys
from utils.ai import call_llm
from utils.compose import (
    build_system_prompt, build_user_prompt, _json_from_text,
    compute_fit_for_recipe, critique_message, refine_prompt
)
from meddiet_rules import split_meal_targets
from utils.ui import inject_css_and_title, topbar_logo_and_title
from utils.ui import energy_banner
from meddiet_rules import split_meal_targets, derive_daily_calorie_target
from utils.state import ORDERED_MEALS
from utils.db import load_profile
import pandas as pd

ensure_session_keys()
recipes_df = st.session_state["df"]

inject_css_and_title()
topbar_logo_and_title()

from utils.auth_ui import auth_gate
user = auth_gate()
user_id = user["id"]
st.session_state["__user_id__"] = user["id"]

user_name = user.get("user_metadata", {}).get("name") or user.get("email", "User")
st.markdown(f"<h3 class='welcome-back'>👋 Welcome back, <b>{user_name.split('@')[0].title()}</b>!</h3>", unsafe_allow_html=True)

st.set_page_config(page_title="Recipe Composer", layout="wide")
ensure_session_keys()

st.markdown("""
<style>
.compose-wrap{display:grid;grid-template-columns:1.6fr .9fr;gap:22px}
.hdr{font-weight:800;font-size:1.5rem;margin:0 0 6px}
.subcaps{color:#5b6675;font-size:.95rem;margin-bottom:12px}
.badge{display:inline-block;padding:4px 10px;border-radius:999px;background:#e8f3ea;color:#1c6b2a;font-weight:600;font-size:.80rem;margin-right:6px}
.card{background:#fff;border:1px solid #e9eef4;border-radius:16px;box-shadow:0 6px 18px rgba(18,38,63,0.06);padding:18px 20px;margin-bottom:14px}
.metricrow{display:flex;align-items:center;gap:12px;margin:6px 0}
.metricrow .label{min-width:140px;font-weight:600;color:#2a2f3a}
.metricrow .bar{flex:1;height:10px;background:#eef2f7;border-radius:999px;overflow:hidden}
.metricrow .bar>span{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#f9ad1a,#ee6a04)}
.metricrow .pct{color:#6a7485;font-size:.95rem;min-width:48px;text-align:right}
.actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:12px}
.actions .stButton>button{border-radius:10px;padding:12px 18px;font-weight:700}
h2#mediet-ai-recipe-composer {margin-bottom: 0px !important;}
@media (max-width: 768px) {
    h2#med-chef-recipe-composer {
        margin-bottom: 0px !important;
        margin-top: 20px;
    }
}
</style>
""", unsafe_allow_html=True)

rows = st.session_state.get("__today_rows__", [])
df = pd.DataFrame(rows)

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

#st.title("🧑Recipe Composer (MedDiet + AI)")
st.markdown("## MedChef Recipe Composer")
st.caption("Compose coherent recipes that respect your profile, pantry, and MedDiet rules. I’ll auto‑critique and fix obvious issues.")

# --- sidebar / inputs ---
meal = st.selectbox("Meal", ["Breakfast","Lunch","Dinner","Snack"], index=1)
servings = st.number_input("Servings", 1, 8, 2, step=1)
daily = st.session_state.get("daily_cals", 2000)
per_meal = st.session_state.get("__per_meal__", split_meal_targets(daily, "3_meals_1_snack"))
kcal_target = int(per_meal.get(meal, 600))

diet_prefs = st.session_state.get("__diet_prefs__", {
    "vegan": False,"vegetarian": False,"pescatarian": False,
    "gluten_free": False,"dairy_free": False,
    "prefer_ingredients": "", "avoid_ingredients": ""
})
health = st.session_state.get("__health__", {
    "hypertension": False,"diabetes": False,"prediabetes": False,
    "hyperlipidemia": False,"celiac": False,"gerd": False,"autoimmune": False
})

pantry = st.tags_input("Pantry ingredients (free text)", suggestions=[
    "olive oil","garlic","onion","tomato","spinach","lemon",
    "yogurt","oats","tuna","whole-grain pasta","brown rice","egg","zucchini","peppers"
]) if hasattr(st, "tags_input") else st.text_input("Pantry (comma‑separated)").split(",")

strict_pantry = st.checkbox("Use pantry only (no extra staples)", value=False)
st.caption("Tip: Add words like *wrap*, *stew*, *tray bake*, *skewers*, *pasta* to your pantry line to pull the format.")

c1, c2 = st.columns(2)
with c1:
    btn = st.button("✨ Compose recipe", type="primary", use_container_width=True)
with c2:
    regen = st.button("🔄 Regenerate", use_container_width=True)

# --- Initialize loading state ---
if "compose_loading" not in st.session_state:
    st.session_state["compose_loading"] = False

# --- Handle click events ---
if (btn or regen) and not st.session_state["compose_loading"]:
    st.session_state["compose_loading"] = True
    st.session_state["__compose_action__"] = "regen" if regen else "compose"
    st.session_state["last_recipe"] = None
    st.rerun()

# --- If loading: show message & generate recipe ---
# --- If loading: show message & generate recipe ---
if st.session_state["compose_loading"]:
    st.markdown(
        """
        <div style="
            background-color:#fff7e6;
            border:1px solid #f9ad1a;
            color:#b46b00;
            border-radius:10px;
            padding:14px 16px;
            font-weight:400;
            display:flex;
            align-items:center;
            gap:8px;
            margin-top:10px;
        ">
            🍳 MedChef is preparing your recipe… please wait ⏳
        </div>
        """,
        unsafe_allow_html=True
    )

    try:
        sys_prompt = build_system_prompt()
        st.session_state["sys_prompt"] = sys_prompt

        user_prompt = build_user_prompt(
            meal, kcal_target, diet_prefs, health,
            [p.strip() for p in pantry if p.strip()],
            servings, strict_pantry
        )

        raw = call_llm([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ])

        recipe = _json_from_text(raw)
        score, dbg = compute_fit_for_recipe(recipe, kcal_target, diet_prefs, health)
        critique = critique_message(score, dbg, recipe)

        if critique and "Looks good" not in critique:
            sys_prompt = st.session_state.get("sys_prompt", build_system_prompt())

            raw2 = call_llm([
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": refine_prompt(recipe, critique)}
            ], temperature=0.5, max_tokens=1000)
            recipe = _json_from_text(raw2)
            score, dbg = compute_fit_for_recipe(recipe, kcal_target, diet_prefs, health)

        st.session_state["last_recipe"] = recipe
        st.session_state["compose_loading"] = False
        st.rerun()

    except Exception as e:
        st.session_state["compose_loading"] = False
        st.error(f"❌ Recipe generation failed: {e}")

# --- Render final recipe after loading ---
if not st.session_state.get("compose_loading") and st.session_state.get("last_recipe"):
    recipe = st.session_state["last_recipe"]
    st.success("✅ Recipe ready!")
    
    # ---- 2) Critique with rules ----
    score, dbg = compute_fit_for_recipe(recipe, kcal_target, diet_prefs, health)
    critique = critique_message(score, dbg, recipe)   # pass recipe

    sys_prompt = st.session_state.get("sys_prompt", build_system_prompt())

    # ---- 3) If issues, ask the LLM to refine once ----
    if critique and "Looks good" not in critique:
        raw2 = call_llm([
            {"role":"system","content": sys_prompt},
            {"role":"user","content": refine_prompt(recipe, critique)}
        ], temperature=0.5, max_tokens=1000)
        try:
            recipe = _json_from_text(raw2)
            score, dbg = compute_fit_for_recipe(recipe, kcal_target, diet_prefs, health)
        except Exception:
            pass  # keep first draft if refine fails

    # ---- Present result ----
    st.subheader(recipe.get("title","Untitled"))
    ui_c1, ui_c2 = st.columns([2,1])

    with ui_c1:
        st.markdown(f"**Cuisine:** {recipe.get('cuisine','-')}  ·  **Servings:** {recipe.get('servings','-')}")
        if score is not None:
            pct = int(round(score*100))
            st.markdown(f"**MedDiet fit (rules):** {pct}%")
        else:
            st.warning("No nutrition provided; showing recipe without a fit score.")

        st.markdown("### Ingredients")
        for ing in recipe.get("ingredients", []):
            notes = f" ({ing.get('notes')})" if ing.get("notes") else ""
            st.write(f"- {ing.get('qty')} {ing.get('unit')} {ing.get('item')}{notes}")

        st.markdown("### Steps")
        for i, step in enumerate(recipe.get("steps", []), 1):
            st.write(f"{i}. {step}")

    with ui_c2:
        st.markdown("### Nutrition (per serving)")
        nut = recipe.get("nutrition") or {}
        st.write(nut)
        st.markdown("### Med tags")
        st.write(", ".join(recipe.get("med_tags", [])) or "-")
        st.markdown("### Why this works")
        st.caption(recipe.get("rationale",""))

        # ---- Actions (integrated with rest of app) ----
    import pandas as pd
    import io, time

    # compact helper: make a valid DF row for the app from our composed recipe
    def _row_from_composed(recipe_dict, meal_type: str) -> dict:
        nut = recipe_dict.get("nutrition") or {}
        # Nutrition is per serving in our composer
        def g(key, default=0.0):
            try:
                return float(nut.get(key, default))
            except Exception:
                return float(default)

        med_tags = [t.strip().lower().replace(" ", "_")
                    for t in recipe_dict.get("med_tags", []) if t.strip()]

        return {
            "recipe_id": f"custom_{int(time.time()*1000)}",
            "name": recipe_dict.get("title", "Composed recipe"),
            "meal_type": meal_type,                          # Breakfast/Lunch/Dinner/Snack
            "cuisine": recipe_dict.get("cuisine", "Modern Med"),
            "ingredients": ", ".join([i.get("item","") for i in recipe_dict.get("ingredients",[])]),
            "instructions": " ".join([str(s) for s in recipe_dict.get("steps", [])]),
            # per-serving macros
            "calories_kcal": g("calories_kcal", 0),
            "protein_g":     g("protein_g", 0),
            "carbs_g":       g("carbs_g", 0),
            "fat_g":         g("fat_g", 0),
            "fiber_g":       g("fiber_g", 0),
            "sodium_mg":     g("sodium_mg", 0),
            # tags/flags best-effort from med tags
            "diet_tags": ", ".join(recipe_dict.get("diet_tags", [])),
            "med_attributes": ", ".join(med_tags),
            "is_vegetarian":  bool("vegetarian" in med_tags),
            "is_vegan":       bool("vegan" in med_tags),
            "is_pescatarian": bool("fish" in med_tags or "pescatarian" in med_tags),
            "is_gluten_free": bool("gluten-free" in recipe_dict.get("med_tags", []) or "gluten_free" in med_tags),
            "is_dairy_free":  bool("dairy-free" in recipe_dict.get("med_tags", []) or "dairy_free" in med_tags),
            "image_url": recipe_dict.get("image_url",""),
        }

    c3, c4, c5 = st.columns(3)

    # # (1) Download JSON (no more state reset)
    # json_bytes = io.BytesIO(json.dumps(recipe, ensure_ascii=False, indent=2).encode("utf-8"))
    # with c3:
    #     st.download_button(
    #         "⬇️ Save JSON",
    #         data=json_bytes,
    #         file_name=f"{recipe.get('title','recipe')}.json",
    #         mime="application/json",
    #         use_container_width=True,
    #         key="compose_dl_json",
    #     )

    # # (2) Ask for more protein → refine once with the LLM and re-render
    # with c4:
    #     if st.button("📝 Tweak: more protein", use_container_width=True, key="compose_tweak_pro"):
    #         try:
    #             # nudge prompt: keep the same dish but raise protein by ~15–25% within kcal ±10%
    #             tweak_note = critique + "\n\nImprove protein by ~20% while staying within ±10% kcal; keep style & pantry."
    #             raw2 = call_llm(
    #                 [{"role":"system","content": sys_prompt},
    #                  {"role":"user","content": refine_prompt(recipe, tweak_note)}],
    #             )
    #             recipe = _json_from_text(raw2)
    #             # re-score & redraw immediately
    #             score, dbg = compute_fit_for_recipe(recipe, kcal_target, diet_prefs, health)
    #             st.session_state["last_recipe"] = recipe
    #             st.success("Tweaked for higher protein.")
    #             st.rerun()
    #         except Exception as e:
    #             st.warning(f"Couldn’t tweak automatically: {e}")

    # # (3) Log as today’s meal → append into df + add to logged + toast
    # with c5:
    #     if st.button("📥 Log as today’s meal", use_container_width=True, key="compose_log"):
    #         try:
    #             row = _row_from_composed(recipe, meal)
    #             # make sure df exists
    #             if "df" not in st.session_state:
    #                 st.session_state["df"] = pd.DataFrame([row])
    #             else:
    #                 st.session_state["df"] = pd.concat(
    #                     [st.session_state["df"], pd.DataFrame([row])],
    #                     ignore_index=True
    #                 )
    #             # add id to logged so the rest of the app picks it up
    #             st.session_state.setdefault("logged", []).append(row["recipe_id"])
    #             # bump score like the cards do
    #             st.session_state["score_today"] = int(st.session_state.get("score_today", 0)) + 1
    #             st.toast(f"Logged ✅  (score {st.session_state['score_today']})")
    #             st.success("Recipe added to Logged Today and included in Adherence & AI Coach.")
    #             st.rerun()
    #         except Exception as e:
    #             st.error(f"Couldn’t log meal: {e}")

