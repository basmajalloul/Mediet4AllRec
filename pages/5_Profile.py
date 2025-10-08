# pages/1_Profile.py
from __future__ import annotations
import streamlit as st
from utils.auth_ui import auth_gate
from utils.db import list_profiles, load_profile, upsert_profile
from meddiet_rules import derive_daily_calorie_target, split_meal_targets
from utils.ui import inject_css_and_title, topbar_logo_and_title
from utils.state import ensure_session_keys

st.set_page_config(page_title="Profile • Mediet4All", layout="wide")

user = auth_gate()
user_id = user["id"]
st.session_state["__user_id__"] = user["id"]

user_name = user.get("user_metadata", {}).get("name") or user.get("email", "User")
st.markdown(f"<h3 class='welcome-back'>👋 Welcome back, <b>{user_name.split('@')[0].title()}</b>!</h3>", unsafe_allow_html=True)

ensure_session_keys()
inject_css_and_title()
topbar_logo_and_title()

st.markdown("## My Profile")
st.caption("Manage your personal details, goals, and dietary constraints. Changes are saved to your account.")

# ------------------ Profile picker ------------------
col_sel, col_new = st.columns([2, 1])
with col_sel:
    names = list_profiles(user_id)
    if "default" not in names: names = ["default"] + names
    sel_name = st.selectbox("Profile name", names, index=names.index("default") if "default" in names else 0)
with col_new:
    new_name = st.text_input("Create new profile", placeholder="e.g., cut-phase, pescatarian")

# Hydrate once per profile selection
hydrate_key = f"__hydrated_profile__:{sel_name}"
if not st.session_state.get(hydrate_key):
    saved = load_profile(user_id, sel_name)
    # defaults if empty
    st.session_state["age"]         = int(saved.get("age", 30))
    st.session_state["height_cm"]   = int(saved.get("height_cm", 170))
    st.session_state["sex"]         = str(saved.get("sex", "Female"))
    st.session_state["weight_kg"]   = float(saved.get("weight_kg", 70.0))
    st.session_state["activity"]    = str(saved.get("activity", "Light"))
    st.session_state["goal"]        = str(saved.get("goal", "Maintain"))
    st.session_state["pattern"]     = str(saved.get("pattern", "3_meals_1_snack"))
    st.session_state["ai_language"] = str(saved.get("ai_language", "English"))

    cond = saved.get("conditions", {}) if isinstance(saved.get("conditions", {}), dict) else {}
    st.session_state["hypertension"]   = bool(cond.get("hypertension", False))
    st.session_state["diabetes"]       = bool(cond.get("diabetes", False))
    st.session_state["prediabetes"]    = bool(cond.get("prediabetes", False))
    st.session_state["hyperlipidemia"] = bool(cond.get("hyperlipidemia", False))
    st.session_state["celiac"]         = bool(cond.get("celiac", False))
    st.session_state["gerd"]           = bool(cond.get("gerd", False))
    st.session_state["autoimmune"]     = bool(cond.get("autoimmune", False))

    diet = saved.get("diet_style", {}) if isinstance(saved.get("diet_style", {}), dict) else {}
    st.session_state["vegan"]        = bool(diet.get("vegan", False))
    st.session_state["vegetarian"]   = bool(diet.get("vegetarian", False))
    st.session_state["pescatarian"]  = bool(diet.get("pescatarian", False))
    st.session_state["gluten_free"]  = bool(diet.get("gluten_free", False))
    st.session_state["dairy_free"]   = bool(diet.get("dairy_free", False))

    st.session_state["prefer_str"]   = ", ".join(saved.get("prefer", ["olive oil"]))
    st.session_state["avoid_str"]    = ", ".join(saved.get("avoid", ["anchovies"]))

    st.session_state[hydrate_key] = True

with st.form("profile_form", clear_on_submit=False):
    # --------- Layout columns ----------
    c1, c2, c3 = st.columns(3)
    with c1:
        age       = st.number_input("Age", 12, 99, value=st.session_state["age"])
        height_cm = st.number_input("Height (cm)", 120, 210, value=st.session_state["height_cm"])
        sex       = st.selectbox("Sex", ["Female","Male"], index=0 if st.session_state["sex"]=="Female" else 1)
    with c2:
        weight_kg = st.number_input("Weight (kg)", 35.0, 200.0, value=st.session_state["weight_kg"], step=0.5)
        activity  = st.selectbox("Activity", ["Sedentary","Light","Moderate","Active","Very Active"],
                                 index=["Sedentary","Light","Moderate","Active","Very Active"].index(st.session_state["activity"]))
        goal      = st.selectbox("Goal", ["Maintain","Fat Loss","Weight Gain"],
                                 index=["Maintain","Fat Loss","Weight Gain"].index(st.session_state["goal"]))
    with c3:
        pattern   = st.selectbox("Meal pattern", ["3_meals_1_snack","2_meals_2_snacks"],
                                 index=0 if st.session_state["pattern"]=="3_meals_1_snack" else 1)
        ai_lang   = st.selectbox("AI Coach language", ["English","العربية","Français"],
                                 index=["English","العربية","Français"].index(st.session_state["ai_language"]))
        st.write("")  # spacer

    st.markdown("### Health Conditions")
    hc1, hc2, hc3 = st.columns(3)
    with hc1:
        hypertension   = st.checkbox("Hypertension", value=st.session_state["hypertension"])
        diabetes       = st.checkbox("Type 2 Diabetes", value=st.session_state["diabetes"])
        prediabetes    = st.checkbox("Prediabetes", value=st.session_state["prediabetes"])
    with hc2:
        hyperlipidemia = st.checkbox("Hyperlipidemia", value=st.session_state["hyperlipidemia"])
        celiac         = st.checkbox("Celiac (strict gluten-free)", value=st.session_state["celiac"])
        gerd           = st.checkbox("GERD / reflux", value=st.session_state["gerd"])
    with hc3:
        autoimmune     = st.checkbox("Autoimmune / RA (anti-inflammatory)", value=st.session_state["autoimmune"])

    st.markdown("### Dietary Style & Constraints")
    dc1, dc2, dc3 = st.columns(3)
    with dc1:
        vegan        = st.checkbox("Vegan", value=st.session_state["vegan"])
        vegetarian   = st.checkbox("Vegetarian", value=st.session_state["vegetarian"])
    with dc2:
        pescatarian  = st.checkbox("Pescatarian", value=st.session_state["pescatarian"])
        gluten_free  = st.checkbox("Gluten-free", value=st.session_state["gluten_free"])
    with dc3:
        dairy_free   = st.checkbox("Dairy-free", value=st.session_state["dairy_free"])

    prefer_str = st.text_input("Prefer ingredients (comma-separated)",
                               value=st.session_state["prefer_str"])
    avoid_str  = st.text_input("Avoid ingredients (comma-separated)",
                               value=st.session_state["avoid_str"])

    # --------- Live target preview ----------
    daily_kcal = derive_daily_calorie_target(int(age), float(weight_kg), int(height_cm), sex, activity, goal)
    per_meal   = split_meal_targets(daily_kcal, pattern)
    st.info(f"**Daily energy target:** {daily_kcal} kcal  "
            f"• Breakfast {per_meal['Breakfast']}  • Lunch {per_meal['Lunch']}  "
            f"• Dinner {per_meal['Dinner']}  • Snack {per_meal['Snack']} kcal")

    # --------- Submit row ----------
    save_col, spacer, create_col = st.columns([1,6,1])
    save_clicked  = save_col.form_submit_button("💾 Save")
    create_clicked = create_col.form_submit_button("➕ Save as New")

if save_clicked or create_clicked:
    target_name = (new_name.strip() if create_clicked and new_name.strip() else sel_name)
    payload = {
        "age": int(age), "height_cm": int(height_cm), "sex": sex, "weight_kg": float(weight_kg),
        "activity": activity, "goal": goal, "pattern": pattern, "ai_language": ai_lang,
        "conditions": {
            "hypertension": hypertension, "diabetes": diabetes, "prediabetes": prediabetes,
            "hyperlipidemia": hyperlipidemia, "celiac": celiac, "gerd": gerd, "autoimmune": autoimmune
        },
        "diet_style": {
            "vegan": vegan, "vegetarian": vegetarian, "pescatarian": pescatarian,
            "gluten_free": gluten_free, "dairy_free": dairy_free
        },
        "prefer": [s.strip() for s in prefer_str.split(",") if s.strip()],
        "avoid":  [s.strip() for s in avoid_str.split(",") if s.strip()],
    }
    try:
        upsert_profile(user_id, target_name, payload)
        st.success(f"Profile saved: **{target_name}**")
        # Reset hydration so if they switched name we reload fresh
        try:
            list_profiles.clear()  # type: ignore
            load_profile.clear()   # type: ignore
        except Exception:
            pass
        st.session_state.pop(f"__hydrated_profile__:{sel_name}", None)
        st.session_state["active_profile_name"] = target_name
        st.rerun()
    except Exception as e:
        st.error(f"Could not save profile: {e}")
