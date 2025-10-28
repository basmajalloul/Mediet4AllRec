# Home.py
import streamlit as st
from utils.state import ensure_session_keys, compute_targets
from utils.ui import inject_css_and_title, topbar_logo_and_title, energy_banner
from utils.auth_ui import auth_gate
from utils.db import load_profile, load_day_log
from datetime import date
import pandas as pd
from meddiet_rules import derive_daily_calorie_target, split_meal_targets

ensure_session_keys()
inject_css_and_title()
#topbar_logo_and_title()

today = date.today()

# ---------- CSS (glass cards, gradients, micro-interactions)
st.markdown("""
<style>
:root{
  --bg:#ffffff; --ink:#111827; --muted:#64748b;
  --glass:#f7fafc; --stroke:#e8eef4;
  --grad:linear-gradient(90deg,#f97316,#f59e0b);
  --grad2:linear-gradient(90deg,#6366f1,#22d3ee);
  --good:#10b981; --warn:#f59e0b; --bad:#ef4444;
}
ul[data-testid="stSidebarNavItems"] li:nth-child(4) {
    display: block !important;
}
ul[data-testid="stSidebarNavItems"] li:nth-child(5) {
    display: none !important;
} 

button[data-testid="stBaseButton-secondary"] {
    margin-top: 10px;
    margin-bottom: 15px !important;
}   
@media (max-width: 768px) {
    ul[data-testid="stSidebarNavItems"] li:nth-child(5) {
        display: block !important;
    }       
    ul[data-testid="stSidebarNavItems"] li:nth-child(4) {
        display: none !important;
    }  
}
button[data-testid="stBaseButton-headerNoPadding"] {
    background: none;
}
.home-grid{display:grid;grid-template-columns:1.25fr .9fr;gap:18px;margin-top:.4rem}
.card{background:var(--bg); border:1px solid var(--stroke); border-radius:18px; padding:18px 20px;
      box-shadow:0 10px 28px rgba(18,38,63,.06)}
.card h3{margin:0 0 12px;font-size:1.25rem}
.hero{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:4px}
.hero a{display:flex;align-items:center;gap:10px; justify-content:center; height:48px;
        background:#f6f9ff;border:1px solid var(--stroke); border-radius:12px; font-weight:800;
        text-decoration:none;color:#0f172a}
.hero a:hover{transform:translateY(-1px); box-shadow:0 6px 16px rgba(18,38,63,.08)}
.hero .i{font-size:1.1rem}

.rings{display:grid;grid-template-columns:repeat(3,1fr); gap:12px}
.ring{display:flex;flex-direction:column;align-items:center;gap:8px;padding:10px 6px;border-radius:16px;
      background:rgba(246,249,255,.7); border:1px solid var(--stroke)}
.ring .lbl{font-weight:700;color:#0f172a}
.ring .meta{color:var(--muted); font-size:.85rem}

.feed .item{display:flex; align-items:center; justify-content:space-between; gap:10px;
            padding:9px 0; border-bottom:1px dashed var(--stroke)}
.badge{display:inline-block;padding:4px 10px;border-radius:999px;background:#f6f9ff;border:1px solid var(--stroke);font-weight:700}

.coach{background:rgba(255,255,255,.6); backdrop-filter:blur(6px); border:1px solid var(--stroke);
       border-radius:18px; padding:16px 18px}
.coach .tip{display:flex;gap:10px; align-items:flex-start}
.coach .dot{width:10px;height:10px;border-radius:50%}
.progressbar{height:9px;background:#eef2f7;border-radius:7px;overflow:hidden}
.progressbar>span{display:block;height:100%;border-radius:7px;background:var(--grad);transition:width .4s ease}
.qa-card{background:#fff;border:1px solid #e9eef4;border-radius:18px;
         box-shadow:0 10px 28px rgba(18,38,63,.06);padding:20px 22px;margin:10px 0 16px}
.qa-title{margin:0 0 12px;font-weight:900;font-size:1.25rem}
.qa-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}
.qa-tile{display:flex;align-items:center;gap:12px;justify-content:flex-start;
         padding:14px 16px;border-radius:14px;border:1px solid #e6edf6;
         background:radial-gradient(120% 120% at 0% 0%,#ffffff 0%,#f7faff 100%);
         text-decoration:none;color:#0f172a;font-weight:800;
         box-shadow:0 8px 18px rgba(18,38,63,.06); transition:transform .14s ease,box-shadow .14s ease}
.qa-tile:hover{transform:translateY(-2px); box-shadow:0 12px 26px rgba(18,38,63,.10)}
.qa-tile:active{transform:translateY(0)}
.qa-emoji{font-size:1.15rem;filter:drop-shadow(0 2px 4px rgba(18,38,63,.08))}
.qa-sub{color:#64748b;font-weight:600;font-size:.9rem}
.qa-grid a {text-decoration: none;}
.stat-card{background:#fff;border:1px solid #e9eef4;border-radius:16px;padding:16px 18px 35px 18px;
           box-shadow:0 10px 28px rgba(18,38,63,.06);margin-bottom:14px;}
.stat-card h3{margin:0 0 10px}

/* 2-up grid, tighter spacing */
.statgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px 24px}
.pill {
    font-size: 11px;
}
@media (max-width:780px){ 
    .statgrid{grid-template-columns:1fr} 

    .qa-card {
        padding: 10px;
    }
    .stat-card {
        padding: 15px 10px 30px !important;
    }
}

.statbox{display:flex;flex-direction:column;gap:6px;padding:6px 8px;border-radius:12px}
.s-head{font-weight:800;color:#0f172a;margin-bottom:0}
.s-meta{color:#64748b;font-size:.9rem;margin-bottom:2px}

/* bar + pill on the same row */
.barwrap{display:flex;align-items:center;gap:12px;margin-top:-10px;margin-bottom:-15px;}
.bar{flex:1;height:10px;background:#eef2f7;border-radius:999px;overflow:hidden}
.fill{height:100%;border-radius:999px;background:linear-gradient(90deg, #f9ad1a, #ee6a04);}

/* pill stays right of bar, text centered */
.pill{display:inline-flex;align-items:center;justify-content:center;
     padding:4px 12px;border-radius:999px;border:1px solid #e6edf6;
     font-weight:700;text-align:center;min-width:92px}
.pill.good{background:#ecfdf5;color:#065f46}
.pill.warn{background:#fff7ed;color:#92400e}
.pill.bad{background:#fef2f2;color:#991b1b}
.meals-tiles{background:#fff;border:1px solid #e9eef4;border-radius:16px;
             box-shadow:0 10px 28px rgba(18,38,63,.06);padding:16px 18px;margin-top:8px}
.meals-tiles h3{margin:0 0 12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:14px}

/* tile */
.tile{display:flex;gap:12px;align-items:flex-start;
      padding:14px;border-radius:16px;border:1px solid #e6edf6;
      background:radial-gradient(120% 120% at 0% 0%,#ffffff 0%,#f7faff 100%);
      box-shadow:0 8px 18px rgba(18,38,63,.06);transition:transform .14s ease,box-shadow .14s ease}
.tile:hover{transform:translateY(-2px);box-shadow:0 12px 26px rgba(18,38,63,.10)}

.icon{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;
      font-size:22px;background:#eef6ff;border:1px solid #dde8f6}

.body{flex:1;min-width:0}
.head-row{display:flex;align-items:center;justify-content:space-between;gap:10px}
.head{font-weight:900;color:#0f172a;margin-bottom:2px}
.sub{color:#64748b;font-size:.95rem}

/* kcal chip in header (no overlay) */
.kchip{display:inline-flex;align-items:center;justify-content:center;
       padding:6px 12px;border-radius:999px;background:#f6f9ff;border:1px solid #e6edf6;
       font-weight:800;color:#065f46;white-space:nowrap}

/* tags row */
.tags{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}

/* compact, centered macro tags with distinct tints */
.tag{display:inline-flex;align-items:center;justify-content:center;
     height:26px;padding:0 12px;border-radius:999px;font-weight:800;border:1px solid}
.tag.prot{background:#e0f2fe;border-color:#bfe3fb;color:#074d7a}
.tag.fiber{background:#e8f9ef;border-color:#c9f0d9;color:#0f5132}
.tag.sod.good{background:#ecfdf5;border-color:#c6f3df;color:#065f46}
.tag.sod.warn{background:#fff7ed;border-color:#fde5c3;color:#92400e}
.tag.sod.bad{background:#fef2f2;border-color:#f5c2c7;color:#991b1b}

/* kcal delta chip */
.delta{display:inline-flex;align-items:center;justify-content:center;
       height:26px;padding:0 12px;border-radius:999px;border:1px solid #e6edf6;font-weight:800}
.delta.good{background:#ecfdf5;color:#065f46}
.delta.warn{background:#fff7ed;color:#92400e}
.delta.bad{background:#fef2f2;color:#991b1b}
.tags span {font-size: 11px;}
span.kchip {font-size: 13px;}
</style>
""", unsafe_allow_html=True)

# ---- Active profile name (remember selection across pages) ----
active_name = st.session_state.get("active_profile_name", "default")

from utils.auth_ui import auth_gate
user = auth_gate()
user_id = user["id"]
st.session_state["__user_id__"] = user["id"]
st.session_state.pop(f"__hydrated_log__:{date.today().isoformat()}", None)

user_name = user.get("user_metadata", {}).get("name") or user.get("email", "User")
st.markdown(f"<h3 class='welcome-back'>👋 Welcome back, <b>{user_name.split('@')[0].title()}</b>!</h3>", unsafe_allow_html=True)

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

# st.markdown("""<div id="app-container"/>""", unsafe_allow_html=True)

energy_banner(daily, per_meal, df=st.session_state["df"])

# expose coach language to the rest of the app
st.session_state["ai_language"] = prof.get("ai_language", "English")

profile = {
    "age": int(prof["age"]),
    "sex": str(prof["sex"]),
    "height_cm": int(prof["height_cm"]),
    "weight_kg": float(prof["weight_kg"]),
    "activity": str(prof["activity"]),
    "goal": str(prof["goal"]),
}
pattern = str(prof.get("pattern", "3_meals_1_snack"))

diet_prefs = {
    "vegan": bool(prof["diet_style"]["vegan"]),
    "vegetarian": (not prof["diet_style"]["vegan"]) and bool(prof["diet_style"]["vegetarian"]),
    "pescatarian": (not prof["diet_style"]["vegan"] and not prof["diet_style"]["vegetarian"]) and bool(prof["diet_style"]["pescatarian"]),
    "gluten_free": bool(prof["diet_style"]["gluten_free"] or prof["conditions"]["celiac"]),
    "dairy_free": bool(prof["diet_style"]["dairy_free"]),
    "prefer_ingredients": ", ".join(prof.get("prefer", [])),
    "avoid_ingredients": ", ".join(prof.get("avoid", [])),
}
health = {
    "hypertension": bool(prof["conditions"]["hypertension"]),
    "diabetes": bool(prof["conditions"]["diabetes"]),
    "prediabetes": bool(prof["conditions"]["prediabetes"]),
    "hyperlipidemia": bool(prof["conditions"]["hyperlipidemia"]),
    "celiac": bool(prof["conditions"]["celiac"]),
    "gerd": bool(prof["conditions"]["gerd"]),
    "autoimmune": bool(prof["conditions"]["autoimmune"]),
}

df = st.session_state["df"]

# keep the same values in session for downstream use
st.session_state["daily_cals"] = float(daily)
st.session_state["__per_meal__"] = per_meal
st.session_state["__health__"] = health


# st.markdown("---")
# st.subheader("Welcome")
# st.write(
#   "Use the left navigation: **Recommendations** to pick meals, "
#   "**Logged Today** to manage what you ate, and **Coach & Insights** for AI feedback and adherence."
# )

# # persist today’s “session snapshot” for other pages
# st.session_state.update({
#     "__profile__": profile, "__diet_prefs__": diet_prefs, "__health__": health,
#     "__pattern__": pattern, "__daily__": daily, "__per_meal__": per_meal
# })

# --- HOME • Modern UI --------------------------------------------------------
import math, pandas as pd, streamlit as st

# ---------- helpers
def _df_logged():
    df = st.session_state.get("df")
    ids = set(st.session_state.get("logged", []))
    log_df = df[df["recipe_id"].isin(ids)].copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    comp = st.session_state.get("logged_composed", [])
    if comp:
        log_df = pd.concat([log_df, pd.DataFrame(comp)], ignore_index=True)
    return log_df

def _targets(daily, health):
    prot = daily*0.25/4.0; carbs = daily*0.45/4.0; fat = daily*0.30/9.0
    fiber = 30.0; sodium = 1500.0 if health.get("hypertension") else 2300.0
    return dict(kcal=daily, protein_g=prot, carbs_g=carbs, fat_g=fat, fiber_g=fiber, sodium_mg=sodium)

def donut_svg(pct: float, label: str, value_txt: str, color="#22c55e"):
    """Animated donut ring as inline SVG (0..100)."""
    pct = max(0.0, min(100.0, pct))
    r, c = 46, 2*math.pi*46
    dash = c * pct/100.0
    html = f"""
    <svg width="120" height="120" viewBox="0 0 120 120">
      <defs>
        <linearGradient id="g1" x1="0" x2="1"><stop stop-color="#22c55e"/><stop offset="1" stop-color="#06b6d4"/></linearGradient>
        <linearGradient id="g2" x1="0" x2="1"><stop stop-color="#f59e0b"/><stop offset="1" stop-color="#ef4444"/></linearGradient>
      </defs>
      <circle cx="60" cy="60" r="{r}" fill="none" stroke="#eef2f7" stroke-width="12"/>
      <circle cx="60" cy="60" r="{r}" fill="none" stroke="{color}" stroke-linecap="round"
              stroke-width="12" stroke-dasharray="{dash} {c-dash}" transform="rotate(-90 60 60)">
        <animate attributeName="stroke-dasharray" from="0 {c}" to="{dash} {c-dash}" dur="600ms" fill="freeze"/>
      </circle>
      <text x="60" y="58" text-anchor="middle" font-size="22" font-weight="800" fill="#0f172a">{int(round(pct))}%</text>
      <text x="60" y="78" text-anchor="middle" font-size="11" fill="#64748b">{value_txt}</text>
      <text x="60" y="96" text-anchor="middle" font-size="11" fill="#64748b">{label}</text>
    </svg>"""
    return html

def _pct(value, target, invert=False):
    if target <= 0: return 0, "#22c55e"
    p = 100*value/target
    # choose color zones
    if invert:   # lower is better (sodium)
        col = "#22c55e" if value <= target else ("#f59e0b" if value <= 1.25*target else "#ef4444")
        return min(p, 100), col
    else:
        good = 0.9*target <= value <= 1.1*target
        warn = value < 0.9*target or value > 1.1*target
        col  = "#22c55e" if good else ("#f59e0b" if warn else "#ef4444")
        return min(p, 100), col

def _bar(label, value, target, invert=False, unit=""):
    pct,_ = _pct(value, target, invert)
    st.markdown(f"<div style='display:flex;justify-content:space-between'><b>{label}</b>"
                f"<span style='color:#64748b'>{value:.0f}{unit} / {target:.0f}{unit}</span></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='progressbar'><span style='width:{pct:.0f}%'></span></div>", unsafe_allow_html=True)

# ---------- data
targets = _targets(float(daily), health)  # use the same 'daily' as the header

ldf = _df_logged()
tot = {k: float(ldf[k].sum()) if k in ldf.columns else 0.0
       for k in ["calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sodium_mg"]}

# st.markdown("""
# <div class="qa-card">
#   <div class="qa-title">Quick actions</div>
#   <div class="qa-grid">
#     <a class="qa-tile" href="./Recommendations" target="_self" rel="noopener">
#       <span class="qa-emoji">🍽️</span>
#       <div><div>Pick meals</div><div class="qa-sub">Top matches for today</div></div>
#     </a>
#     <a class="qa-tile" href="./Logged_Today" target="_self" rel="noopener">
#       <span class="qa-emoji">🧾</span>
#       <div><div>Manage logged</div><div class="qa-sub">Edit & remove quickly</div></div>
#     </a>
#     <a class="qa-tile" href="./Coach_and_Insights" target="_self" rel="noopener">
#       <span class="qa-emoji">🧠</span>
#       <div><div>Coach & Insights</div><div class="qa-sub">Focus for the day</div></div>
#     </a>
#     <a class="qa-tile" href="./Recipe_Composer" target="_self" rel="noopener">
#       <span class="qa-emoji">🧑‍🍳</span>
#       <div><div>Compose recipe</div><div class="qa-sub">AI + rules composer</div></div>
#     </a>
#   </div>
# </div>
# """, unsafe_allow_html=True)


# ---------- Main stack: stats then feed (one under the other)

def _pct_and_status(value, target, invert=False):
    if target <= 0:
        return 0, "good"
    pct = max(0, min(100, int(round(100*value/target))))
    if invert:
        status = "good" if value <= target else ("warn" if value <= 1.25*target else "bad")
    else:
        status = "good" if 0.9*target <= value <= 1.1*target else ("warn" if value < target else "bad")
    return pct, status

def _stat_box(label, value, target, unit="", invert=False):
    pct, status = _pct_and_status(value, target, invert=invert)
    pill_txt = "on track" if status=="good" else ("low" if not invert and value < target else "high")
    return (
        f'<div class="statbox">'
        f'  <div class="s-head">{label}</div>'
        f'  <div class="s-meta">{int(value)}{unit} / {int(target)}{unit}</div>'
        f'  <div class="barwrap">'
        f'    <div class="bar"><div class="fill" style="width:{pct}%"></div></div>'
        f'    <div class="pill {status}">{pill_txt}</div>'
        f'  </div>'
        f'</div>'
    )

today_html = (
    "<div class='stat-card'><div class='qa-title'>Today at a glance</div>"
    "<div class='statgrid'>"
    + _stat_box("Energy",  tot["calories_kcal"], targets["kcal"],      unit=" kcal")
    + _stat_box("Protein", tot["protein_g"],     targets["protein_g"], unit=" g")
    + _stat_box("Carbs",   tot["carbs_g"],       targets["carbs_g"],   unit=" g")
    + _stat_box("Fat",     tot["fat_g"],         targets["fat_g"],     unit=" g")
    + _stat_box("Fiber",   tot["fiber_g"],       targets["fiber_g"],   unit=" g")
    + _stat_box("Sodium",  tot["sodium_mg"],     targets["sodium_mg"], unit=" mg", invert=True)
    + "</div></div>"
)
st.markdown(today_html, unsafe_allow_html=True)

from utils.state import ORDERED_MEALS  # or define: ["Breakfast","Lunch","Dinner","Snack"]

# helpers
EMOJI = {"Breakfast":"🥣","Lunch":"🥗","Dinner":"🍽️","Snack":"🍎"}
ORDER = ["Breakfast","Lunch","Dinner","Snack"]
order_map = {m:i for i,m in enumerate(ORDER)}

def kcal_delta_chip(kcal:int, tgt:int):
    if tgt <= 0:
        return '<span class="delta good">on target</span>'
    diff = kcal - tgt
    if abs(diff) <= int(0.05*tgt):  # within ±5%
        return '<span class="delta good">on target</span>'
    if diff < 0:
        return f'<span class="delta warn">−{abs(diff)} kcal</span>'
    return f'<span class="delta bad">+{diff} kcal</span>'

def sodium_class(mg:int):
    # simple thresholds — tweak if you prefer
    if mg <= 500: return "good"
    if mg <= 800: return "warn"
    return "bad"

def meal_tile(meal, name, kcal, protein, fiber, sodium_mg, tgt):
    emo = EMOJI.get(meal, "🍽️")
    delta = kcal_delta_chip(kcal, tgt)
    sod_cls = sodium_class(sodium_mg)
    # header row: title on left, kcal chip on right
    return (
        f'<div class="tile">'
        f'  <div class="icon">{emo}</div>'
        f'  <div class="body">'
        f'    <div class="head-row">'
        f'      <div class="head">{meal} — {name}</div>'
        f'      <span class="kchip">{kcal} / {tgt} kcal</span>'
        f'    </div>'
        f'    <div class="tags">'
        f'      <span class="tag prot">{protein} g protein</span>'
        f'      <span class="tag fiber">{fiber} g fiber</span>'
        f'      <span class="tag sod {sod_cls}">{sodium_mg} mg sodium</span>'
        f'      {delta}'
        f'    </div>'
        f'  </div>'
        f'</div>'
    )

if ldf.empty:
    tiles_html = (
        '<div class="meals-tiles"><div class="qa-title">Meals logged today</div>'
        '<div class="tile"><div class="icon">🍽️</div>'
        '<div class="body"><div class="head-row"><div class="head">No meals yet</div></div>'
        '<div class="sub">Go to <b>Recommendations</b> to add one.</div></div></div>'
        '</div>'
    )
else:
    ldf_view = ldf.copy()
    ldf_view["__order"] = ldf_view["meal_type"].map(order_map).fillna(99)
    ldf_view = ldf_view.sort_values(["__order","name"])

    tiles = []
    for _, r in ldf_view.iterrows():
        meal = r.get("meal_type","Meal")
        name = r.get("name","(unnamed)")
        kcal = int(r.get("calories_kcal", 0))
        prot = int(r.get("protein_g", 0))
        fiber = int(r.get("fiber_g", 0))
        sod   = int(r.get("sodium_mg", 0))
        tgt   = int(per_meal.get(meal, 0) or 0)
        tiles.append(meal_tile(meal, name, kcal, prot, fiber, sod, tgt))

    tiles_html = '<div class="meals-tiles"><div class="qa-title">Meals logged today</div><div class="grid">' + "".join(tiles) + "</div></div>"

st.markdown(tiles_html, unsafe_allow_html=True)