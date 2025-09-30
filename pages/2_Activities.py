# 2_Activities.py — modernized Activities page
import streamlit as st
from datetime import date

from utils.auth_ui import auth_gate
from utils.ui import inject_css_and_title, topbar_logo_and_title, energy_banner
from utils.db import (
    load_profile, load_day_log,
    activities_for_day, insert_activity, sum_activity_kcal_for_day, get_client
)
from meddiet_rules import derive_daily_calorie_target, split_meal_targets

# ---------- Global CSS + Title (same vibe as other pages) ----------
inject_css_and_title()
topbar_logo_and_title()

# ---------- Auth & Profile ----------
user = auth_gate()
user_id = user["id"]
today = date.today()

active_name = st.session_state.get("active_profile_name", "default")
prof = (load_profile(user_id, active_name) or {})
age        = int(prof.get("age", 30))
height_cm  = int(prof.get("height_cm", 170))
sex        = prof.get("sex", "Female")
weight_kg  = float(prof.get("weight_kg", 70.0))
activity   = prof.get("activity", "Light")
goal       = prof.get("goal", "Maintain")
pattern    = prof.get("pattern", "3_meals_1_snack")

daily   = derive_daily_calorie_target(age, weight_kg, height_cm, sex, activity, goal)
per_meal = split_meal_targets(daily, pattern)
st.session_state["daily_cals"]    = daily
st.session_state["__per_meal__"]  = per_meal

foods = load_day_log(user_id, today) or []

def minutes_to_burn(kcal_target, kind, intensity, weight):
    met = _MET.get((kind,intensity), 5.0)
    # kcal = MET × weight × hours
    hours = kcal_target / (met * max(weight,40))
    return int(round(hours * 60))

# ---------- Page-specific micro-CSS to style cards + quick boxes ----------
st.markdown("""
<style>
/* Section heading chip */
.hchip{
  display:inline-flex;gap:10px;align-items:center;
  font-weight:800;font-size:1.05rem;color:#263244;margin:6px 0 8px;
}
.hchip .ico{width:34px;height:34px;border-radius:10px;display:flex;align-items:center;justify-content:center;
  background:#f1f6ff;border:1px solid #e3ecff;font-size:18px}

/* 2-column quick actions look like cards */
.quickcard{
  background:#fff;border:1px solid #e9eef4;border-radius:14px;padding:14px 16px;
  box-shadow:0 4px 14px rgba(18,38,63,0.06);
}
.quickbtn > button{
  width:100%; border-radius:10px; padding:10px 16px; font-weight:700;
}

/* Activity/Net banner using same .metriccard look */
.metricrow .neg{opacity:.9}

/* Logs as sleek cards */
.actcard{
  background:#fff;border:1px solid #e9eef4;border-radius:12px;padding:12px 14px;margin-bottom:10px;
  box-shadow:0 2px 10px rgba(18,38,63,0.05);
}
.acthead{display:flex;align-items:center;gap:10px;margin-bottom:4px}
.acticon{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  background:#eef7ff;border:1px solid #e1ecfb;font-size:16px}
.acttitle{font-weight:800;color:#263244}
.actmeta{color:#5f6b7a;font-size:.9rem}
#root > div:nth-child(1) > div.withScreencast > div > div > div > section > div.stMainBlockContainer.block-container > div {padding: 0px !important; box-shadow: none !important; border: 0px !important;}
</style>
""", unsafe_allow_html=True)

# ---------- Tiny kcal estimators (local, overridable) ----------
_MET = {
    ("Walk","Low"):2.8,("Walk","Moderate"):3.5,("Walk","Vigorous"):5.0,
    ("Run","Low"):8.0,("Run","Moderate"):10.0,("Run","Vigorous"):12.5,
    ("Cycle","Low"):4.0,("Cycle","Moderate"):6.8,("Cycle","Vigorous"):9.5,
    ("Swim","Low"):5.8,("Swim","Moderate"):7.0,("Swim","Vigorous"):9.8,
    ("Strength","Low"):3.5,("Strength","Moderate"):5.0,("Strength","Vigorous"):6.0,
    ("Yoga","Low"):2.5,("Yoga","Moderate"):3.0,("Yoga","Vigorous"):4.0,
    ("Other","Low"):3.0,("Other","Moderate"):5.0,("Other","Vigorous"):7.0,
}
def estimate_kcal(kind, intensity, duration_min, weight):
    met = _MET.get((kind,intensity),5.0)
    return round(met * max(weight,40) * (max(duration_min,0)/60), 1)

def estimate_kcal_steps(steps, weight):
    # ~0.0005 * steps * weight_kg
    return round(max(steps,0) * max(weight,40) * 0.0005, 1)

# ---------- Activity + Net banner (harmonized with metric cards) ----------
def render_activity_strip():
    # Food kcal today (DB backed; falls back to 0)
    try:
        day_rows = st.session_state.get("__today_rows__")
        if day_rows is None:
            day_rows = load_day_log(user_id, today) or []
            st.session_state["__today_rows__"] = day_rows
        food_kcal = sum(float(r.get("calories_kcal") or 0) for r in day_rows)
    except Exception:
        food_kcal = 0.0

    activity_kcal = sum_activity_kcal_for_day(user_id, today)
    net_kcal = max(food_kcal - activity_kcal, 0.0)

    c1, c2 = st.columns([2,1])
    with c1:
        st.markdown(
            f"""
            <div class="metriccard">
              <div class="metricrow">
                <div class="metricicon">🏃</div>
                <div>
                  <div class="metricmain">Activity today: -{int(activity_kcal)} kcal</div>
                  <div class="metricsub">Food logged: {int(food_kcal)} kcal &nbsp;•&nbsp; Net: <b>{int(net_kcal)}</b> kcal</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="metriccard">
              <div class="metricrow">
                <div class="metricicon">🎯</div>
                <div>
                  <div class="metricmain">Daily target: {int(daily)} kcal</div>
                  <div class="metricsub">Keep net close to target</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

def delete_activities_for_day(user_id: str, d: date) -> tuple[bool, str | None]:
    try:
        get_client().table("activities").delete().eq("user_id", user_id).eq("d", d.isoformat()).execute()
        return True, None
    except Exception as e:
        return False, str(e)

# ---- Compact Energy + Activity banner (single card) ----
from utils.db import load_day_log  # already imported above

def energy_banner_compact(daily_kcal: int, per_meal: dict, user_id: str, d: date):
    # food kcal from your DB/session (same logic as other pages)
    try:
        day_rows = st.session_state.get("__today_rows__")
        if day_rows is None:
            day_rows = load_day_log(user_id, d) or []
            st.session_state["__today_rows__"] = day_rows
        food_kcal = sum(float(r.get("calories_kcal") or 0) for r in day_rows)
    except Exception:
        food_kcal = 0.0

    activity_kcal = sum_activity_kcal_for_day(user_id, d)
    net_kcal = food_kcal - activity_kcal


    # subtle CSS tweaks for the compact layout
    st.markdown("""
    <style>
      .mini-metrics{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:14px;margin-top:8px}
      .mm{background: #fff;
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-radius: 14px;
        padding: 12px 14px;
        box-shadow: 0 1px 5px rgba(0, 0, 0, 0.05);
        margin: 20px 0;
        text-align: center;}
      .mm .lbl{font-weight:700;color:#1a3d7c;font-size:0.95rem}
      .mm .val{font-size:1.35rem;font-weight:900;margin-top:2px;color:#162a52}
      .pm{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;color:#4b5563}
      .pm .chip{background:#eef2f7;border:1px solid #e4e9f1;color:#334155;padding:3px 8px;border-radius:999px;font-size:.82rem;font-weight:700}
    </style>
    """, unsafe_allow_html=True)

    # one card with four mini metrics + per-meal line
    st.markdown(f"""
    <div class="metriccard">
      <div class="metricrow">
        <div class="metricicon">⚡</div>
        <div>
          <div class="metricmain">Daily energy overview</div>
          <div class="metricsub">Keep <b>Net</b> close to <b>Target</b></div>
        </div>
      </div>
      <div class="mini-metrics">
        <div class="mm">
          <div class="lbl">Food</div>
          <div class="val">{int(food_kcal)} kcal</div>
        </div>
        <div class="mm">
          <div class="lbl">Activity</div>
          <div class="val">-{int(activity_kcal)} kcal</div>
        </div>
        <div class="mm">
          <div class="lbl">Net</div>
          <div class="val">{int(net_kcal)} kcal</div>
        </div>
        <div class="mm">
          <div class="lbl">Target</div>
          <div class="val">{int(daily_kcal)} kcal</div>
        </div>
      </div>
      <div class="pm">
        <span class="chip">Breakfast {per_meal['Breakfast']} kcal</span>
        <span class="chip">Lunch {per_meal['Lunch']} kcal</span>
        <span class="chip">Dinner {per_meal['Dinner']} kcal</span>
        <span class="chip">Snack {per_meal['Snack']} kcal</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<style>
/* Cardify any Streamlit block/column that CONTAINS our marker element */
.stHorizontalBlock  div[data-testid="stVerticalBlock"]:has(.qbox-start),
.block-container div[data-testid="column"]:has(.qbox-start){
  background:#fff;
  border:1px solid #e9eef4;
  border-radius:14px;
  padding:14px 16px;
  box-shadow:0 4px 14px rgba(18,38,63,0.06);
}

/* Optional: tighten spacing for inputs inside quick cards */
.block-container div[data-testid="stVerticalBlock"]:has(.qbox-start) .stNumberInput,
.block-container div[data-testid="column"]:has(.qbox-start) .stNumberInput { margin-bottom:.35rem; }

.block-container div[data-testid="stVerticalBlock"]:has(.qbox-start) .stButton>button,
.block-container div[data-testid="column"]:has(.qbox-start) .stButton>button{
  width:100%; border-radius:10px; padding:10px 16px; font-weight:700;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Quick actions grid */
.quickgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:6px}
@media (min-width: 1120px){ .quickgrid{grid-template-columns:repeat(3,minmax(0,1fr));} }

.qbtn{
  display:flex;align-items:center;justify-content:space-between;gap:8px;
  border:1px solid #e7edf6;background:#fff;border-radius:12px;padding:10px 12px;
  box-shadow:0 2px 8px rgba(18,38,63,0.04);font-weight:800;cursor:pointer;
}
.qbtn:hover{background:#f6f9ff;border-color:#dbe7fb}
.qbtn .l{display:flex;align-items:center;gap:8px;color:#1a3d7c}
.qbtn .ico{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  background:#eef7ff;border:1px solid #e1ecfb}
.qbtn .badge{font-size:.78rem;font-weight:800;color:#0f2a56;background:#eef2f7;border:1px solid #e4e9f1;
  padding:3px 8px;border-radius:999px}

/* Softer KPI for Today */
.kpi{
  padding:14px 0px;
}
.kpi .head{display:flex;align-items:center;gap:10px;margin-bottom:6px;color:#263244;font-weight:800}
.kpi .ico{width:30px;height:30px;border-radius:10px;background:#f1f6ff;border:1px solid #e3ecff;
  display:flex;align-items:center;justify-content:center}
.kpi .val{font-weight:900;font-size:1.35rem;color:#162a52}
.kpi .sub{font-size:.9rem;color:#5f6b7a}
.row-sep {height: 10px; display: block;}
</style>
""", unsafe_allow_html=True)



# ---- call it once (replace the two banners) ----
energy_banner_compact(daily, per_meal, user_id, today)

st.markdown("---")

# ---------- Today’s logs (card grid) ----------
st.markdown('<div class="hchip"><div class="ico">📒</div><div>Today’s logs</div></div>', unsafe_allow_html=True)
rows = activities_for_day(user_id, today)

if not rows:
    st.info("No activities yet today.")
else:
    st.markdown("""
    <style>
      .log-card{
        background:#fff;
        border:1px solid #e9eef4;
        border-radius:12px;
        padding:12px;
        margin:6px;
        box-shadow:0 2px 8px rgba(18,38,63,0.05);
        font-size:0.88rem;
      }
      .log-head{display:flex;align-items:center;gap:8px;margin-bottom:4px}
      .log-icon{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;
                background:#eef7ff;border:1px solid #e1ecfb;font-size:16px}
      .log-title{font-weight:700;color:#263244}
      .log-meta{color:#5f6b7a;font-size:.82rem;margin-bottom:2px}
    </style>
    """, unsafe_allow_html=True)

    icons = {
        "Walk":"🚶","Run":"🏃","Cycle":"🚴","Swim":"🏊","Strength":"🏋️","Yoga":"🧘","Steps":"👣","Other":"⚡"
    }

    cols_per_row = 5
    for i, r in enumerate(rows):
        kind = r.get("kind","Other")
        icon = icons.get(kind, "⚡")
        intensity = r.get("intensity","")
        details = []
        if r.get("duration_min"): details.append(f"{int(r['duration_min'])} min")
        if r.get("steps"):        details.append(f"{int(r['steps'])} steps")
        kcal = int(float(r.get("calories") or 0))

        if i % cols_per_row == 0:
            cols = st.columns(cols_per_row, gap="small")
        with cols[i % cols_per_row]:
            st.markdown(
                f"""
                <div class="log-card">
                  <div class="log-head">
                    <div class="log-icon">{icon}</div>
                    <div class="log-title">{kind}{f" ({intensity})" if intensity else ""}</div>
                  </div>
                  <div class="log-meta">{", ".join(details) if details else "—"}</div>
                  <div class="log-meta"><b>{kcal} kcal</b></div>
                </div>
                """,
                unsafe_allow_html=True
            )


# ---------- Recommended activities (grid compact cards) ----------
st.markdown("## Recommended activities")

foods = load_day_log(user_id, today) or []
if not foods:
    st.info("Log some meals first to see suggested activities to burn them off.")
else:
    st.markdown("""
    <style>
      .rec-card-btn > button {
        background:#fff !important;
        border:1px solid #e9eef4 !important;
        border-radius:12px !important;
        padding:14px !important;
        margin:6px !important;
        box-shadow:0 2px 6px rgba(18,38,63,0.05) !important;
        font-size:0.9rem !important;
        text-align:left !important;
        height:auto !important;
        height: 100px;
      }
      .rec-title{font-weight:700;color:#263244;margin-bottom:4px}
      .rec-meta{color:#5f6b7a;font-size:.82rem;margin-bottom:2px}
       h2#recommended-activities {
            padding-bottom: 0px;
            margin-bottom: 0px !important;
            margin-top: 20px;
        }

        h2#activities {
            margin-bottom: 0px !important;
            margin-top: 25px;
        }
        .stTooltipHoverTarget {
            /*height: 120px; */
            padding: 0px;
            background: #fff;
            border-radius: 12px;
            margin: 6px;
            box-shadow: 0 2px 8px rgba(18, 38, 63, 0.05);
            font-size: 0.88rem;
        }

        .stTooltipHoverTarget button {
            border: 1px solid #e9eef4 !important;
        } 

        .stTooltipHoverTarget button * {
            color: #000 !important;
        } 

        .stTooltipHoverTarget em {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        align-items: center;
        justify-content: center;
        background: #eef7ff;
        border: 1px solid #e1ecfb;
        font-size: 16px;
        display: inline;
        margin-right: 5px;
        font-style: normal;
    }        
    </style>
    """, unsafe_allow_html=True)

    icons2 = {
        "Walk":"🚶","Run":"🏃","Cycle":"🚴","Swim":"🏊","Strength":"🏋️","Yoga":"🧘","Steps":"👣","Other":"⚡"
    }

    # choose how many cards per row
    cols_per_row = 5
    for i, f in enumerate(foods):
        kind2 = f.get("kind","Other")
        icon2 = icons2.get(kind, "⚡")

        kcal = int(float(f.get("calories_kcal") or 0))
        name = f.get("name","Meal")
        lname = name.lower()
        if any(w in lname for w in ["couscous","pasta","rice","bread"]):
            kind,inten = "Run","Moderate"
        elif any(w in lname for w in ["fish","chicken"]):
            kind,inten = "Walk","Moderate"
        elif any(w in lname for w in ["cake","tart","dessert","sweet"]):
            kind,inten = "Cycle","Moderate"
        else:
            kind,inten = "Walk","Moderate"

        mins = minutes_to_burn(kcal, kind, inten, weight_kg)

        if i % cols_per_row == 0:
            cols = st.columns(cols_per_row, gap="small")
        with cols[i % cols_per_row]:
            if st.button(
                f"*{icon2}* **{name}**\n\n≈ {kcal} kcal\n\n{kind} ({inten}) · {mins} min",
                key=f"log_{f['id']}",
                use_container_width=True,
                help="Click to log this activity",
                type="secondary",
            ):
                insert_activity(
                    user_id=user_id, d=today,
                    kind=kind, intensity=inten,
                    duration_min=mins, calories=kcal,
                    notes=f"Burn-off for {name}"
                )
                st.toast(f"{kind} {mins}m logged ✅")
                st.rerun()

st.markdown("## Activities")

# ---------- Quick actions (styled cards) ----------
qc1, qc2, qc3 = st.columns([1.2, 1.2, 0.8])

with qc1:
    # MARKER — makes this whole column a styled card
    st.markdown('<span class="qbox-start"></span>', unsafe_allow_html=True)
    st.markdown('<div class="hchip"><div class="ico">👣</div><div>Quick add: Steps</div></div>', unsafe_allow_html=True)

    steps = st.number_input("Steps", min_value=0, step=500, value=3000, key="steps_in")
    est = estimate_kcal_steps(steps, weight_kg)
    st.write(f"Estimated: **{int(est)} kcal**")
    kcal_override = st.number_input("Override kcal (optional)", min_value=0, step=10, value=0, key="steps_kc")
    if st.button("Add steps", key="btn_steps"):
        kcal = float(kcal_override or est)
        insert_activity(user_id, today, kind="Steps", intensity="Moderate",
                        steps=int(steps), calories=kcal)
        st.toast("Steps logged ✅")
        st.rerun()

with qc2:
    st.markdown("""
    <style>
    /* Make the parent column a positioned card WHEN it contains a kcal badge */
    .block-container div[data-testid="column"]:has(.qa-badge){
    position: relative;
    background:#fff;
    border:1px solid #e9eef4;
    border-radius:14px;
    padding:12px;
    box-shadow:0 2px 10px rgba(18,38,63,0.05);
    }

    /* Compact pill button */
    .block-container div[data-testid="column"]:has(.qa-badge) .stButton>button{
    width:100%;
    border-radius:12px;
    border:1px solid #e6ebf2;
    background:#fff;
    font-weight:700;
    padding:10px 12px 36px 12px;  /* extra bottom space for the badge */
    box-shadow:0 1px 3px rgba(0,0,0,.04);
    transition:.15s ease;
    }
    .block-container div[data-testid="column"]:has(.qa-badge) .stButton>button p{
        font-size: 12px:
    }
    .block-container div[data-testid="column"]:has(.qa-badge) .stButton>button:hover{
    background:#f7fafc; transform:translateY(-1px)
    }

    /* Badge anchored INSIDE the same column (no extra row height) */
    .qa-badge{
        position: absolute;
        right: calc(50% - 37px);
        bottom: -5px;
        padding: 4px 10px;
        border-radius: 999px;
        background: #ecf8ef;
        border: 1px solid #d8efe0;
        color: #1e7a35;
        font-weight: 800;
        font-size: .80rem;
        pointer-events: none;
    }
                
    .stTooltipIcon p {
        font-size: 14px;
        font-weight: bold;
        color: #666;
    }
                
    #root > div:nth-child(1) > div.withScreencast > div > div > div > section > div.stMainBlockContainer.block-container.st-emotion-cache-zy6yx3.e4man114 > div > div:nth-child(10) > div > div:nth-child(2) > div > div.st-emotion-cache-18kf3ut.e52wr8w3 > div {        
        border: 0px;
        box-shadow: none;
        padding: 0px;
    }           

    /* Title chip for the card */
    .qa-title{display:flex;align-items:center;gap:8px;font-weight:800;font-size:1.05rem;margin-bottom:8px}
    </style>
    """, unsafe_allow_html=True)

    # --- helpers ---
    def _chunks(seq, n):
        for i in range(0, len(seq), n):
            yield seq[i:i+n]

    def est_kcal(met, minutes, weight):
        return int(round(met * float(weight) * (minutes/60.0)))

    def log_quick_activity(kind:str, minutes:int, intensity:str, kcal:int):
        insert_activity(user_id, today, kind=kind, intensity=intensity,
                        duration_min=minutes, calories=float(kcal))
        st.toast(f"{kind} {minutes}m (~{kcal} kcal) logged ✅")
        st.rerun()

    # use your profile weight
    _w = float(weight_kg if "weight_kg" in locals() else st.session_state.get("profile", {}).get("weight_kg", 70.0))

    # icon, label, minutes, MET, intensity
    quick_items = [
        ("🚶", "Walk",     30, 3.5, "Moderate"),
        ("🏃", "Run",      20, 9.8, "Vigorous"),
        ("🚴", "Cycle",    30, 7.0, "Moderate"),
        ("🧘", "Yoga",     20, 2.8, "Light"),
        ("🏋️", "Strength", 20, 6.0, "Moderate"),
        ("🤸", "Stretch",  10, 2.3, "Light"),
    ]

    st.markdown('<span class="qbox-start"></span>', unsafe_allow_html=True)
    st.markdown('<div class="hchip" style="margin-top: -20px; margin-bottom: 25px;"><div class="ico">⚡</div><div>Quick adds</div></div>', unsafe_allow_html=True)

    for row in _chunks(quick_items, 3):
        cols = st.columns(3, gap="small")
        for col, (emoji, kind, mins, met, inten) in zip(cols, row):
            with col:
                kcal = est_kcal(met, mins, _w)
                # one compact card: button + overlay badge inside the same column
                if st.button(f"{emoji}  {kind} · {mins}m", key=f"qa_{kind}_{mins}", use_container_width=True,
                            help=f"Est. ~{kcal} kcal"):
                    log_quick_activity(kind, mins, inten, kcal)
                # overlay badge (absolute; doesn't add extra height)
                st.markdown(f"<span class='qa-badge'>~{kcal} kcal</span>", unsafe_allow_html=True)
        st.markdown('<span class="row-sep"></span>', unsafe_allow_html=True)



with qc3:
    st.markdown('<span class="qbox-start"></span>', unsafe_allow_html=True)
    st.markdown('<div class="hchip"><div class="ico">📊</div><div>Today Activity calories</div></div>', unsafe_allow_html=True)

    act = int(sum_activity_kcal_for_day(user_id, today))
    # Softer KPI card
    st.markdown(
        f"""
        <div class="kpi">
          <div class="val">{act} kcal</div>
          <div class="sub">Auto-summed from your logs</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ---------- Log a workout (kept compact & styled) ----------
st.markdown("""
<style>
/* Cardify the block that contains our workout marker */
.block-container div[data-testid="stVerticalBlock"]:has(.wk-card-start){
  background:#fff;border:1px solid #e9eef4;border-radius:14px;padding:14px 16px;
  box-shadow:0 2px 10px rgba(18,38,63,0.05); margin-top:6px;
}

/* title chip */
.wk-head{display:flex;align-items:center;gap:10px;font-weight:800;font-size:1.05rem;margin-bottom:8px}
.wk-ico{width:34px;height:34px;border-radius:10px;display:flex;align-items:center;justify-content:center;
  background:#f7f9fc;border:1px solid #edf1f7;font-size:18px}

/* live kcal tile */
.miniKPI{background:linear-gradient(135deg,#fff 0%,#f7faff 100%);border:1px solid #e9eef4;border-radius:12px;
  padding:12px 14px;box-shadow:0 1px 6px rgba(18,38,63,0.06);margin-bottom:10px}
.miniKPI .t{font-weight:800;color:#1a3d7c;font-size:.95rem}
.miniKPI .v{font-weight:900;font-size:1.4rem;color:#162a52;margin-top:2px}
.miniKPI .s{color:#5f6b7a;font-size:.88rem}

/* segmented radios */
.seg .stRadio > div{gap:8px}
.seg label{font-weight:700}

/* preset chips */
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 2px}
.chips .stButton>button{
  padding:6px 10px;border-radius:999px;border:1px solid #e6ebf2;background:#fff;font-weight:700;font-size:.88rem;
}
.chips .stButton>button:hover{background:#f7fafc}

/* style the block that has the log button marker, without extra wrappers */
.block-container div[data-testid="stVerticalBlock"]:has(.wk-log-btn-marker) .stButton>button{
  width:100%;border-radius:10px;padding:12px 16px;font-weight:800;
}
            
span.row-sep {
    display: block;
    height: 20px;
    width: 100%;
}

.st-key-wk_log_btn button {
    background: linear-gradient(90deg, #f9ad1a, #ee6a04);
    color: #fff;
    border: 0px;
    padding: 10px !important;
    width: 150px !important;
    float: right;
}

.st-key-wk_log_btn button p {
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# marker to style this block as a card
st.markdown('<span class="wk-card-start"></span>', unsafe_allow_html=True)
st.markdown('<div class="wk-head"><div class="wk-ico">📝</div><div>Log a workout</div></div>', unsafe_allow_html=True)

left, right = st.columns([1.25, 1])

# --- LEFT: inputs (stateful, no form, so estimate updates live) ---
with left:
    # keep state
    _kind = st.session_state.get("wk_kind", "Walk")
    _intensity = st.session_state.get("wk_intensity", "Moderate")
    _duration = int(st.session_state.get("wk_duration", 30))
    _notes = st.session_state.get("wk_notes", "")

    with st.container():  # balanced
        _kind = st.radio("Type", ["Walk","Run","Cycle","Swim","Strength","Yoga","Other"],
                         index=["Walk","Run","Cycle","Swim","Strength","Yoga","Other"].index(_kind),
                         horizontal=True, key="wk_kind")

    with st.container():
        _intensity = st.radio("Intensity", ["Low","Moderate","Vigorous"],
                              index=["Low","Moderate","Vigorous"].index(_intensity),
                              horizontal=True, key="wk_intensity")

    _duration = st.slider("Duration (min)", min_value=5, max_value=180, value=_duration, step=5, key="wk_duration")

    _notes = st.text_input("Notes (optional)", value=_notes, key="wk_notes")

# --- RIGHT: live estimate + override + button (all balanced) ---
with right:
    est_kcal = estimate_kcal(_kind, _intensity, _duration, weight_kg)

    # Entire tile in a single call (open & close inside)
    st.markdown(
        f"""
        <div class="miniKPI">
          <div class="t">Estimated</div>
          <div class="v">~{int(est_kcal)} kcal</div>
          <div class="s">Based on {weight_kg:.1f} kg • {_intensity.lower()} {_kind.lower()} • {_duration} min</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    kcal_override = st.number_input("Override kcal (optional)", min_value=0, value=0, step=10, key="wk_override")

    # marker so CSS can style the button's parent without wrappers
    st.markdown('<span class="wk-log-btn-marker"></span>', unsafe_allow_html=True)
    if st.button("Log workout", use_container_width=True, key="wk_log_btn"):
        kcal = float(kcal_override or est_kcal)
        insert_activity(
            user_id=user_id, d=today, kind=_kind, intensity=_intensity,
            duration_min=int(_duration), calories=kcal, notes=(st.session_state.get("wk_notes") or None)
        )
        st.toast("Workout logged ✅")
        st.rerun()


# --- Danger zone: reset today's activities ---
st.markdown("---")
with st.container(border=True):
    st.markdown('<div class="hchip"><div class="ico">🧨</div><div>Danger zone</div></div>', unsafe_allow_html=True)

    # show the first button or the confirm UI based on a flag
    if not st.session_state.get("__confirm_reset_acts__", False):
        if st.button("🗑️ Reset today’s activities", key="start_reset_acts"):
            st.session_state["__confirm_reset_acts__"] = True
            st.rerun()
    else:
        st.warning("This will permanently delete **all** activity logs for **today**. This cannot be undone.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm delete", key="confirm_delete_acts"):
                ok, err = delete_activities_for_day(user_id, today)
                if ok:
                    st.toast("Cleared today’s activities ✅")
                    st.session_state["__confirm_reset_acts__"] = False
                    st.rerun()
                else:
                    st.error(f"Couldn’t delete: {err}")
        with c2:
            if st.button("Cancel", key="cancel_delete_acts"):
                st.session_state["__confirm_reset_acts__"] = False
                st.rerun()
