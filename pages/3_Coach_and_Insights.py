# pages/3_Coach_and_Insights.py
import os, json
import streamlit as st
from openai import OpenAI
from utils.state import ensure_session_keys, build_ai_context, live_snapshot
from utils.ui import inject_css_and_title, topbar_logo_and_title

ensure_session_keys()
inject_css_and_title()
topbar_logo_and_title()

profile = st.session_state.get("__profile__", {})
per_meal = st.session_state.get("__per_meal__", {})
daily    = st.session_state.get("__daily__", 0)
snap = live_snapshot(profile, per_meal, daily)

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

st.markdown("## Daily Adherence")
adh = snap["adh"]
c1,c2,c3 = st.columns(3)
def card(col, title, icon, score):
    with col:
        st.metric(title, f"{int(score)}/100", help=icon)
card(c1, "Calorie Balance", "🔥", adh["energy_score"])
card(c2, "Food Variety",   "🌿", adh["component_score"])
card(c3, "MedDiet Adherence", "❤️", adh["total"])

st.markdown("---")
st.markdown("## AI Coach")
st.caption("👉 Click **Run AI Coach**. After you change meals or settings, click **Update with changes**.")

AI_SYSTEM_PROMPT = """You are MedCoach, an evidence-informed Mediterranean diet assistant.
Goals: Explain today's adherence, check health conditions, and suggest up to 3 specific, kcal-respecting improvements.
Constraints: Respect diet style and avoids; ±15% per-meal kcal; keep it brief, friendly, and actionable (~180 words)."""

def coach_prompt(context: dict, language: str) -> str:
    loc = {
        "English": "Write in clear English.",
        "العربية": "اكتب بالعربية بلغة بسيطة وواضحة.",
        "Français": "Écris en français clair et simple.",
    }[language]
    return f"""{loc}

DATA (JSON):
{json.dumps(context, ensure_ascii=False)}

TASKS:
1) One-sentence overview vs targets.
2) Explain WHY the scores (kcal, macro %, fiber, sodium).
3) Health check: only conditions that apply.
4) Suggestions: up to 3 swaps/additions from Mediterranean staples; keep constraints and kcal limits.
Format as short bullets."""

def call_llm(system_prompt: str, user_prompt: str) -> str:
    
    OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

    api_key = OPENAI_API_KEY

    if not api_key:
        return "(Set OPENAI_API_KEY to enable live AI.)\n• Overview: ...\n• Why the scores: ...\n• Health check: ...\n• Suggestions: ..."
    client = OpenAI(api_key=api_key)
    chat = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL","gpt-4o-mini"),
        messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
        temperature=0.4, max_tokens=450,
    )
    return chat.choices[0].message.content

colA,colB = st.columns([1,1])
run_clicked = update_clicked = False
with colA:
    run_clicked = st.button("🧠 Run AI Coach", type="primary", use_container_width=True)
with colB:
    update_clicked = st.button("🔄 Update with changes", use_container_width=True)

if run_clicked or update_clicked:
    ctx = build_ai_context(
        snap["df"], snap["logged"],
        profile,
        {"daily_kcal": daily, "per_meal_kcal": per_meal},
        snap["adh"]
    )
    out = call_llm(AI_SYSTEM_PROMPT, coach_prompt(ctx, st.session_state.get("ai_language","English")))
    st.session_state["__coach_out__"] = out
    st.session_state["__coach_ctx__"] = ctx
    st.rerun()

if st.session_state.get("__coach_out__"):
    st.markdown(f"<div class='coach-output'>{st.session_state['__coach_out__']}</div>", unsafe_allow_html=True)

with st.expander("Debug: AI Context (optional)"):
    st.code(json.dumps(st.session_state.get("__coach_ctx__", {}), indent=2, ensure_ascii=False), language="json")
