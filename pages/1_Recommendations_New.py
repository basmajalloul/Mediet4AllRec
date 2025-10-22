import streamlit as st
import pandas as pd
from datetime import date
from utils.state import ensure_session_keys
from utils.ui import inject_css_and_title, topbar_logo_and_title
from utils.db import append_logged_meal

# --- page setup ---
st.set_page_config(page_title="MedDiet • Recommendations", layout="wide")
ensure_session_keys()
inject_css_and_title()
topbar_logo_and_title()

df = st.session_state["df"]  # Recipes table

st.markdown("""
<style>
button[kind="secondary"] {
    color: #222 !important;
    font-weight: 600 !important;
    border-radius: 0px;
    border-top: 0px !important;
    border-left: 0px !important;
    border-right: 0px !important;
    box-shadow: none;
    margin-bottom: 0px !important;
    padding-bottom: 10px !important;
    padding-top: 0px;
    margin-top: 0px !important;
    text-align: left !important;
    display: block;
    padding-left: 0;
    padding-right: 0px;
}
button[kind="secondary"] p {
    margin-top: -10px;
}
</style>
""", unsafe_allow_html=True)

# --- helper to reset ---
def go_back():
    if "__selected_recipe__" in st.session_state:
        del st.session_state["__selected_recipe__"]
    st.rerun()

# ---------------------------
# SCREEN 1: LIST VIEW
# ---------------------------
if "__selected_recipe__" not in st.session_state:
    st.markdown("## 🍽️ Browse Foods & Recipes")
    st.caption("Tap a food to view details and adjust serving size.")

    search = st.text_input("🔍 Search", placeholder="pasta, fish, salad")
    filtered = df[df["name"].str.contains(search, case=False, na=False)] if search else df

    # Styling like native mobile cards
    st.markdown("""
    <style>
    .food-btn button {
        background: #fff !important;
        border: 1px solid #eee !important;
        border-radius: 12px !important;
        color: #222 !important;
        font-weight: 600 !important;
        width: 100% !important;
        padding: 14px 10px !important;
        margin-bottom: 8px !important;
        text-align: left !important;
    }
    .stVerticalBlock > .stElementContainer {
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

    for i, row in filtered.iterrows():
        col = st.container()
        with col:
            if st.button(f"{row['name']}", key=f"rec_{i}"):
                st.session_state["__selected_recipe__"] = row.to_dict()
                st.rerun()

# ---------------------------
# SCREEN 2: DETAIL VIEW
# ---------------------------
else:
    r = st.session_state["__selected_recipe__"]
    # st.markdown("### ← [Back to list](#)", unsafe_allow_html=True)
    # st.markdown(
    #     "<script>document.querySelector('a[href=\"#\"]').addEventListener('click', ()=>{parent.postMessage({isBack:true},'*');});</script>",
    #     unsafe_allow_html=True
    # )

    if st.button("← Back", use_container_width=True, type="secondary"):
        go_back()

    st.image(r["image_url"], use_container_width=True)
    st.markdown(f"##### {r['name']}")
    st.caption(f"{r['cuisine']} • {r['meal_type']}")

    st.markdown("#### 🍽️ Log Meal As")
    meal_choice = st.radio(
        "Select which meal this should count for:",
        ["Breakfast", "Lunch", "Dinner", "Snack"],
        horizontal=True,
        index=["Breakfast", "Lunch", "Dinner", "Snack"].index(r.get("meal_type", "Lunch")),
    )

    # Serving adjustment
    st.markdown("#### ⚖️ Serving Weight")
    weight = st.number_input("Weight (g)", 50, 1000, 100, 25)
    factor = weight / 100.0

    # Nutritional values
    st.markdown("#### Nutrition per selected weight")
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Calories (kcal)", round(r["calories_kcal"] * factor, 1))
    with c2: st.metric("Protein (g)", round(r["protein_g"] * factor, 1))
    with c3: st.metric("Carbs (g)", round(r["carbs_g"] * factor, 1))
    c4, c5, c6 = st.columns(3)
    with c4: st.metric("Fat (g)", round(r["fat_g"] * factor, 1))
    with c5: st.metric("Fiber (g)", round(r["fiber_g"] * factor, 1))
    with c6: st.metric("Sodium (mg)", round(r["sodium_mg"] * factor, 1))

    # 🧂 INGREDIENTS SECTION
    st.markdown("#### 🧂 Ingredients")

    # Handle if stored as a list or a string
    st.write(r["ingredients"])

    st.markdown("#### 🧑‍🍳 Preparation Steps")
    st.write(r["instructions"])

    # Option to log
    if st.button("Log this meal", key="log_meal", use_container_width=True):
        try:
            payload = {
                "recipe_id": r["recipe_id"],
                "name": r["name"],
                "meal_type": meal_choice,  # ✅ user-chosen label
                "logged_date": str(date.today()),
                "calories_kcal": float(r["calories_kcal"]) * factor,
                "protein_g": float(r["protein_g"]) * factor,
                "carbs_g": float(r["carbs_g"]) * factor,
                "fat_g": float(r["fat_g"]) * factor,
                "fiber_g": float(r["fiber_g"]) * factor,
                "sodium_mg": float(r["sodium_mg"]) * factor,
            }

            user_id = st.session_state.get("__user_id__") or st.session_state.get("user_id")
            if not user_id:
                st.error("User not authenticated. Please sign in again.")
            else:
                append_logged_meal(user_id, payload)
                st.success(f"{r['name']} logged as {meal_choice} ✅")
                st.balloons()

        except Exception as e:
            st.error(f"Could not log meal: {e}")


    st.markdown("""
    <style>
    button[kind="primary"][title="Log this meal"],
    div[data-testid="stButton"] > button:has(span:contains('Log this meal')) {
        background: linear-gradient(90deg,#f9ad1a,#ee6a04) !important;
        color: white !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        padding: 12px !important;
        font-size: 1rem !important;
    }
    .stVerticalBlock > .stElementContainer {
        width: 100%;
    }

    .st-key-log_meal button {
        background: linear-gradient(90deg, #f9ad1a, #ee6a04);
        padding: 10px !important;
        border-radius: 5px;
    }

    .st-key-log_meal button p {
        color: #fff;
        font-weight: bold;
    }

    .st-key-log_meal button p {
        margin-top: 0px;
        text-align: center;
    }

    </style>
    """, unsafe_allow_html=True)
