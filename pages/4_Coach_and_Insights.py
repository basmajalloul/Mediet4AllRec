# pages/3_Coach_and_Insights.py
import os, json
import streamlit as st
from openai import OpenAI
from utils.state import ensure_session_keys, build_ai_context, live_snapshot
from utils.ui import inject_css_and_title, topbar_logo_and_title
from utils.state import ensure_session_keys
from utils.db import load_profile, load_day_log
from meddiet_rules import derive_daily_calorie_target, split_meal_targets, daily_adherence_from_logs
from datetime import date
import pandas as pd
import markdown


inject_css_and_title()
topbar_logo_and_title()
today = date.today()

from utils.auth_ui import auth_gate
user = auth_gate()
user_id = user["id"]
st.session_state["__user_id__"] = user["id"]

user_name = user.get("user_metadata", {}).get("name") or user.get("email", "User")
st.markdown(f"<h3 class='welcome-back'>👋 Welcome back, <b>{user_name.split('@')[0].title()}</b>!</h3>", unsafe_allow_html=True)

# hydrate from DB (cache per session/day)
key = f"__hydrated_log__:{today.isoformat()}"
if not st.session_state.get(key):
    rows = load_day_log(user_id, today)
    st.session_state["__today_rows__"] = rows
    st.session_state[key] = True

rows = st.session_state.get("__today_rows__", [])
df = pd.DataFrame(rows)

# 1) Make sure recipe catalog exists
ensure_session_keys()
recipes_df = st.session_state["df"]

# 2) HYDRATE today's logged list from DB rows (must happen BEFORE computing adh/banners)
st.session_state["logged"] = [str(x["recipe_id"]) for x in rows]
st.session_state["score_today"] = len(st.session_state["logged"])

# 3) Compute adherence from hydrated logged list
adh = daily_adherence_from_logs(recipes_df, st.session_state["logged"])
st.session_state["__adh__"] = adh
snap = {"adh": adh, "df": recipes_df, "logged": st.session_state["logged"]}


from utils.ui import energy_banner
from meddiet_rules import split_meal_targets
from utils.state import ORDERED_MEALS

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
    "age": int(prof["age"]),
    "sex": prof["sex"],
    "height_cm": int(prof["height_cm"]),
    "weight_kg": float(prof["weight_kg"]),
    "activity": prof["activity"],
    "goal": prof["goal"],
    "conditions": prof.get("conditions", {}),
    "diet_style": prof.get("diet_style", {}),
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

energy_banner(daily, per_meal, df=recipes_df)

st.markdown("## Daily Adherence")
adh = snap["adh"]     # stays in sync after every reload

c1, c2, c3 = st.columns(3)
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

    acts = context.get("activity_summary", {})
    if acts and acts.get("count", 0) > 0:
        details = acts.get("details", [])
        activity_text = "Today's activities:\n" + "\n".join(
            f"- {a.get('kind','?')} ({a.get('intensity','')}, {a.get('duration_min','?')} min, {a.get('calories','?')} kcal)"
            for a in details
        ) + f"\nTotal burned: {acts.get('total_kcal_burned', 0):.0f} kcal."
    else:
        activity_text = "No activities logged today."

    net_energy = context.get("net_energy", 0)
    health_flags = [k for k, v in context["profile"].get("conditions", {}).items() if v]
    health_text = ", ".join(health_flags) if health_flags else "none"

    enriched_context = {
        **context,
        "activity_text": activity_text,
        "net_energy": net_energy,
        "health_conditions": health_text,
    }

    return f"""{loc}

DATA (JSON):
{json.dumps(enriched_context, ensure_ascii=False)}

TASKS:
1) Give a short overview of energy and activity balance vs targets.
2) Explain WHY the scores (calories, macros, fiber, sodium, and activity kcal).
3) Health check: consider these conditions → {health_text}. Highlight specific dietary advice for them (e.g., lower sodium for hypertension, avoid saturated fats for hyperlipidemia, anti-inflammatory foods for autoimmune).
4) Suggestions: up to 3 concrete swaps/additions respecting kcal ±15% and diet style.
Format as concise bullet points."""

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
    user_id = st.session_state.get("__user_id__") or st.session_state.get("user_id")
    ctx = build_ai_context(
        snap["df"], snap["logged"],
        profile,
        {"daily_kcal": daily, "per_meal_kcal": per_meal},
        snap["adh"],
        user_id
    )
    out = call_llm(AI_SYSTEM_PROMPT, coach_prompt(ctx, st.session_state.get("ai_language","English")))
    st.session_state["__coach_out__"] = out
    st.session_state["__coach_ctx__"] = ctx
    st.rerun()

if st.session_state.get("__coach_out__"):
    raw_md = st.session_state["__coach_out__"]
    rendered_html = markdown.markdown(raw_md, extensions=["fenced_code", "tables"])
    st.markdown(f"<div class='coach-output'>{rendered_html}</div>", unsafe_allow_html=True)

# with st.expander("Debug: AI Context (optional)"):
#     st.code(json.dumps(st.session_state.get("__coach_ctx__", {}), indent=2, ensure_ascii=False), language="json")
