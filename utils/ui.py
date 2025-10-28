# utils/ui.py
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components
from typing import Dict, List
from utils.state import ORDERED_MEALS
from utils.db import append_logged_meal
from datetime import date
from utils.db import append_logged_meal, sum_activity_kcal_for_day
import pathlib


# ---------------- CSS once ----------------
def inject_css_and_title():
    st.set_page_config(
        page_title="Mediet4All",
        page_icon="download.png",   # relative path to your file
        layout="wide"
    )
    st.set_page_config(page_title="MedDiet Recommender", layout="wide")
   # --- Load external CSS once ---
    css_path = pathlib.Path(__file__).parent / "styles.css"
    if css_path.exists():
        with open(css_path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- Global styles reused across pages (cards + metric bars + heading) ---

def topbar_logo_and_title():
    # c1,c2 = st.columns([1,8])
    # with c1: st.image("download.png", width=150)
    # with c2:
    #     st.markdown('<h1 id="meddiet"><span>Mediterranean</span> Diet Recommendation System</h1>', unsafe_allow_html=True)
    #     st.markdown("<p id='title-caption'>Profile-based recommendations • Intake logging • Health-aware prioritization</p>", unsafe_allow_html=True)

    st.markdown("""<style>
        .app-header {
            display: flex;
            flex-direction: row;
            flex-wrap: nowrap;
            align-content: center;
            align-items: center;
            justify-content: flex-start;
            padding: 20px;
            background: #f9ad1a;
        }

        .app-header img {
            width: 85px;      
            margin-right: 20px;
        }

        .app-header * {
            color: #fff !important;
        }

        h1#welcome-to-mediet4-all {
            font-size: 30px;
        }

         @media (max-width: 768px) {
            .app-header {
                display: none;
            }    
        }                      
        </style>""", unsafe_allow_html=True)

    st.markdown('<div class="app-header"><img style="filter: brightness(0) invert(1);" src="https://www.mediet4all.eu/wp-content/uploads/2023/10/logo-site.svg">'
    '<div class="tagline-holder"><h1 id="meddiet"><span>Mediterranean</span> Diet Recommendation System</h1>'
    '<p id="title-caption">Profile-based recommendations • Intake logging • Health-aware prioritization</p></div></div>', unsafe_allow_html=True)

# ---------------- energy banner (now supports live consumption) ----------------
def energy_banner(total_kcal: int, per: Dict[str, int], df=None):
    """
    Global banner with three cards:
      [ Net / Target + per-meal splits ]  [ Activity today ]  [ Score Today ]
    Signature unchanged so all pages keep working.
    """
    ORDERED_MEALS = ["Breakfast", "Lunch", "Dinner", "Snack"]

    # --- food kcal from today's logged meals (if df + st.session_state["logged"] is used)
    def _consumed_by_meal(_df):
        by = {m: 0 for m in ORDERED_MEALS}
        logged = [str(x) for x in st.session_state.get("logged", [])]
        if _df is None or not logged:
            return by, 0
        ids = _df["recipe_id"].astype(str)
        use = _df[ids.isin(logged)][["meal_type", "calories_kcal"]]
        for m in ORDERED_MEALS:
            by[m] = int(use.loc[use["meal_type"] == m, "calories_kcal"].sum())
        return by, int(sum(by.values()))

    def _status(net:int, target:int):
        if target <= 0: return "good","on track"
        r = net / target
        if r < 0.90:  return "warn","below"
        if r <= 1.10: return "good","within"
        return "bad","above"

    by_meal, consumed = _consumed_by_meal(df)

    # --- activity kcals (DB-backed)
    user_id = st.session_state.get("__user_id__") or st.session_state.get("user_id")
    try:
        activity_kcal = int(sum_activity_kcal_for_day(user_id, date.today())) if user_id else 0
    except Exception:
        activity_kcal = 0

    def _fmt_kcal(v: int) -> str:
        v = int(v)
        return f"-{abs(v)}" if v < 0 else f"{v}"

    def _status(net: int, target: int):
        if net < 0:
            return "warn", "deficit"           # activity > food
        if target <= 0:
            return "good", "on track"
        r = net / target
        if r < 0.90:  return "warn", "below"
        if r <= 1.10: return "good", "within"
        return "bad", "above"

    net = int(consumed) - int(activity_kcal)
    live = (df is not None) and (consumed > 0)

    # ---------- layout: 3 columns (main, activity, score)
    c1, c2, c3 = st.columns([2, 1, 1])

    # MAIN: Net/Target (or Target-only when no logs yet)
    with c1:
        if live:
            pill_cls, pill_txt = _status(net, int(total_kcal))
            per_meal_line = " • ".join([
                f"Breakfast {by_meal.get('Breakfast',0)}/{int(per.get('Breakfast',0) or 0)}",
                f"Lunch {by_meal.get('Lunch',0)}/{int(per.get('Lunch',0) or 0)}",
                f"Dinner {by_meal.get('Dinner',0)}/{int(per.get('Dinner',0) or 0)}",
                f"Snack {by_meal.get('Snack',0)}/{int(per.get('Snack',0) or 0)} kcal",
            ])
            st.markdown(f"""
            <div class="metriccard">
              <div class="metricrow"><div class="metricicon">🔥</div>
                <div>
                    <div class="metricmain">Net today: {_fmt_kcal(net)} / {int(total_kcal)} kcal
                        <span class="pill {pill_cls}" style="margin-left:8px">{pill_txt}</span>
                    </div>
                  <div class="metricsub">{per_meal_line}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="metriccard">
              <div class="metricrow"><div class="metricicon">🔥</div>
                <div>
                  <div class="metricmain">Daily energy target: {int(total_kcal)} kcal</div>
                  <div class="metricsub">
                    Breakfast {per.get('Breakfast',0)} • Lunch {per.get('Lunch',0)}
                    • Dinner {per.get('Dinner',0)} • Snack {per.get('Snack',0)} kcal
                  </div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # NEW MIDDLE CARD: Activity today
    # determine goal-specific text
    goal = st.session_state.get("goal", "").lower()
    activity_target = 0
    activity_line = f"-{int(activity_kcal)} kcal"

    # if fat-loss goal includes exercise, show goal comparison
    if "fat loss" in goal and "exercise" in goal:
        # assume target expenditure ≈ 15 % of total_kcal (tune if you store explicit value)
        activity_target = int(total_kcal * 0.15)
        activity_line = f"{int(activity_kcal)} / {activity_target} kcal"

        # visual pill status
        if activity_kcal >= 0.9 * activity_target:
            pill_cls, pill_txt = "good", "on track"
        elif activity_kcal >= 0.5 * activity_target:
            pill_cls, pill_txt = "warn", "below"
        else:
            pill_cls, pill_txt = "bad", "low"

        pill_html = f"<span class='pill {pill_cls}' style='margin-left:6px'>{pill_txt}</span>"
    else:
        pill_html = ""

        # --- MIDDLE CARD: Activity today ---
    with c2:
        st.markdown(f"""
        <div class="metriccard">
          <div class="metricrow"><div class="metricicon">🏃</div>
            <div>
              <div class="metricmain">Activity today {pill_html}</div>
              <div class="metricsub">{activity_line}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)


    # RIGHT CARD: Score Today (unchanged)
    with c3:
        st.markdown(f"""
        <div class="metriccard">
          <div class="metricrow"><div class="metricicon">✅</div>
            <div>
              <div class="metricmain">Score Today: {int(st.session_state.get('score_today',0))}</div>
              <div class="metricsub">+1 per meal logged</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

# ---------------- recommend card ----------------
def similar_recipe_search_url(name: str, cuisine: str) -> str:
    q = urllib.parse.quote_plus(f"{name} {cuisine} Mediterranean recipe")
    return f"https://www.google.com/search?q={q}"

import urllib.parse

def _pct01(x):
    try:
        return int(round(100*max(0.0,min(1.0,float(x)))))
    except Exception:
        return 0

def _macro_split_pct(row):
    cal_p = 4.0*float(row["protein_g"])
    cal_c = 4.0*float(row["carbs_g"])
    cal_f = 9.0*float(row["fat_g"])
    den   = max(1.0, cal_p+cal_c+cal_f)
    return int(round(100*cal_p/den)), int(round(100*cal_c/den)), int(round(100*cal_f/den))

def _similar_google(name, cuisine):
    q = urllib.parse.quote_plus(f"{name} {cuisine} Mediterranean recipe")
    return f"https://www.google.com/search?q={q}"

def _why_this_html(r, kcal_target, diet_prefs, health):
    # 1) kcal gap
    kcal = float(r["calories_kcal"])
    gap  = int(round(kcal_target - kcal))
    if abs(gap) < 15:
        kcal_line = f"Target matched (±{abs(gap)} kcal)."
    elif gap > 0:
        kcal_line = f"Below target by ~{gap} kcal → consider a small side of whole grains/legumes or a drizzle of olive oil."
    else:
        kcal_line = f"Above target by ~{abs(gap)} kcal → use a lighter side or reduce added fats."

    # 2) diet style line (uses rule-engine outputs)
    diet_ok = bool(r["fit_diet_style"] >= 0.999)
    diet_line = "Matches your chosen diet style." if diet_ok else "Does not fully match your diet style."

    # 3) prefer boost line
    prefer_ok = float(r["fit_prefer_bonus"]) > 1.0
    pref_line = "Includes one of your preferred ingredients." if prefer_ok else "No preferred ingredients detected."

    # 4) health tilt
    health_pct = int(round(100*min(1.0, max(0.0, float(r["fit_health_mod"])) / 1.3)))
    if   health_pct >= 90: health_line = "Favorable for your health profile."
    elif health_pct >= 70: health_line = "Generally supportive of your health profile."
    else:                  health_line = "Neutral or requires tweaks for your health profile."

    # 5) macro split
    p,c,f = _macro_split_pct(r)
    macro_line = f"Macro split ≈ {p}% protein / {c}% carbs / {f}% fat."

    # 6) fiber
    fiber = int(round(float(r.get("fiber_g", 0))))
    fiber_line = "Good fiber content." if fiber >= 6 else "Fiber could be higher."

    return f"""
      <div class="whybox">
        <div class="whyli"><div class="ic">📉</div><div>{kcal_line}</div></div>
        <div class="whyli"><div class="ic">🥗</div><div>{diet_line}</div></div>
        <div class="whyli"><div class="ic">⭐</div><div>{pref_line}</div></div>
        <div class="whyli"><div class="ic">🩺</div><div>{health_line}</div></div>
        <div class="whyli"><div class="ic">🍽️</div><div>{macro_line}</div></div>
        <div class="whyli"><div class="ic">🌿</div><div>{fiber_line}</div></div>
      </div>
    """

def render_why_this(row, kcal_target:int):
    """
    Small, subtle rationale with icons. Put this at the bottom of each recipe card.
    """
    cal   = float(row["calories_kcal"])
    delta = int(round(kcal_target - cal))           # positive => below target by delta
    p = int(round(100*(4*float(row["protein_g"])) / max(1.0, 4*float(row["protein_g"]) + 4*float(row["carbs_g"]) + 9*float(row["fat_g"]))))
    c = int(round(100*(4*float(row["carbs_g"]))   / max(1.0, 4*float(row["protein_g"]) + 4*float(row["carbs_g"]) + 9*float(row["fat_g"]))))
    f = int(round(100*(9*float(row["fat_g"]))     / max(1.0, 4*float(row["protein_g"]) + 4*float(row["carbs_g"]) + 9*float(row["fat_g"]))))

    bullets = []
    # Energy nudge
    # if abs(delta) >= 60:
    #     if delta > 0:
    #         bullets.append(("🧭","Below target by ~{} kcal → consider adding a small whole‑grain/legume side or a drizzle of olive oil.".format(delta)))
    #     else:
    #         bullets.append(("🧭","Above target by ~{} kcal → consider a lighter side or halving added fats.".format(-delta)))
    # Diet style / avoids
    if float(row["fit_diet_style"]) >= 0.99:
        bullets.append(("🥗","Matches your chosen diet style."))
    if float(row["fit_no_avoids"]) >= 0.99:
        bullets.append(("🚫","Respects your ‘avoid’ list."))
    if float(row["fit_prefer_bonus"]) > 1.0:
        bullets.append(("⭐","Includes one of your preferred ingredients."))
    if float(row["fit_health_mod"]) > 1.0:
        bullets.append(("🩺","Favorable for your health profile."))
    bullets.append(("🍽️","Macro split ≈ {}% protein / {}% carbs / {}% fat.".format(p, c, f)))
    if float(row.get("fiber_g", 0)) >= 7:
        bullets.append(("🌿","Good fiber content."))

    # --- Mediterranean compliance ---
    score = float(row.get("fit_med_compliance", 0))
    if score > 0.8:
        bullets.append(("🌿","Mediterranean-compliant meal rich in core Med foods (olive oil, grains, vegetables)."))
    elif score > 0.4:
        bullets.append(("⚖️","Partially Med-compliant meal with some healthy Mediterranean elements."))
    else:
        bullets.append(("🚫","Not Med-compliant; limited Mediterranean ingredients."))

    # Render
    html = ["<div class='whybox'>"]
    for ico, txt in bullets:
        html.append(f"<div class='whyline'><div class='whyicon'>{ico}</div><div class='whytext'>{txt}</div></div>")
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)

def render_recipe_card(r, *, kcal_target, diet_prefs, health, log_key_prefix="rec"):
    # map rule-engine outputs to % for the bars
    overall_pct = _pct01(r["fit_score"])
    #cal_pct     = _pct01(r["fit_calorie"])
    diet_pct    = _pct01(r["fit_diet_style"])
    avoids_pct  = int(round(100*float(r["fit_no_avoids"])))
    pref_pct    = int(round(100*max(0.0, float(r["fit_prefer_bonus"]) - 1.0)/0.15))
    pref_pct    = max(0, min(100, pref_pct))
    health_pct  = int(round(100*min(1.0, max(0.0, float(r["fit_health_mod"])) / 1.3)))

    # tags
    pills = []
    if r.get("diet_tags"):
        pills += [p.strip() for p in str(r["diet_tags"]).split(",") if p.strip()]
    if r.get("med_attributes"):
        for p in [p.strip() for p in str(r["med_attributes"]).split(",") if p.strip()]:
            if p in ("olive_oil","legumes","whole_grains","fish","nuts_seeds","fruits","vegetables","yogurt_cheese"):
                pills.append(p.replace("_"," "))
    pills_html = "".join([f"<span class='pill'>{p}</span>" for p in pills[:10]])

    with st.container(border=True):
        # --- Recipe image on top ---
        if r.get("image_url"):
            st.markdown(
                f"""
                <div style="
                    width: 100%;
                    height: 240px;
                    background-image: url('{r['image_url']}');
                    background-size: cover;
                    background-position: center;
                    border-radius: 12px;
                    margin-bottom: 8px;
                "></div>
                """,
                unsafe_allow_html=True
            )

        # --- Title & subtitle ---
        st.markdown(f"<div class='title'><strong>{r['name']}</strong></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='sub'><b>{int(r['calories_kcal'])} kcal</b> · {r['cuisine']}</div>", unsafe_allow_html=True)

        # utils/ui.py  (inside render_recipe_card, after the "Overall fit" badge line)
        picked = r['recipe_id'] in set(st.session_state.get("optimized_set", set()))
        # --- Overall Fit + Med Compliance + Picked badges on one line ---
        picked_html = " <span class='badge'>🎯 Picked</span>" if picked else ""

        med_badge = ""
        score = float(r.get("fit_med_compliance", 0))
        if score > 0.8:
            med_badge = "<span class='badge green'>🌿 Med-compliant</span>"
        elif score > 0.4:
            med_badge = "<span class='badge yellow'>⚖️ Partially Med</span>"
        else:
            med_badge = "<span class='badge red'>🚫 Non-Med</span>"

        # inline layout
        st.markdown(
            f"<div style='display:flex;gap:6px;align-items:center;'>"
            f"<span class='badge'>Overall fit: {overall_pct}%</span>"
            f"{med_badge}{picked_html}"
            f"</div>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="metricrow"><div class="label">Diet style</div>
              <div class="bar"><span style="width:{diet_pct}%"></span></div><div class="pct">{diet_pct}%</div></div>
            <div class="metricrow"><div class="label">No avoids</div>
              <div class="bar"><span style="width:{avoids_pct}%"></span></div><div class="pct">{avoids_pct}%</div></div>
            <div class="metricrow"><div class="label">Preference boost</div>
              <div class="bar"><span style="width:{pref_pct}%"></span></div><div class="pct">{pref_pct}%</div></div>
            <div class="metricrow"><div class="label">Health mod.</div>
              <div class="bar"><span style="width:{health_pct}%"></span></div><div class="pct">{health_pct}%</div></div>
            """,
            unsafe_allow_html=True
        )

        if pills_html:
            st.markdown(f"<div class='pills'>{pills_html}</div>", unsafe_allow_html=True)

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='ing'><b>Ingredients:</b> {r.get('ingredients','')}</div>", unsafe_allow_html=True)
        if str(r.get("instructions","")).strip():
            st.markdown(f"<div class='instructions'>{r.get('instructions','')}</div>", unsafe_allow_html=True)

        # --- WHY THIS (dynamic explainer) ---
                # --- WHY THIS (dynamic explainer) ---
        render_why_this(r, kcal_target)

        # --- Serving size adjustment ---
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        default_serving = 100  # dataset values per 100g by default
        key_serv = f"{log_key_prefix}_serv_{r['recipe_id']}"
        serving_g = st.number_input(
            "Serving size (g)",
            min_value=50, max_value=1000,
            value=default_serving, step=25,
            key=key_serv
        )

        # Scale nutrients and calories
        scale = serving_g / default_serving
        kcal_scaled   = round(float(r.get("calories_kcal", 0)) * scale)
        protein_scaled = round(float(r.get("protein_g", 0)) * scale, 1)
        carbs_scaled   = round(float(r.get("carbs_g", 0)) * scale, 1)
        fat_scaled     = round(float(r.get("fat_g", 0)) * scale, 1)
        fiber_scaled   = round(float(r.get("fiber_g", 0)) * scale, 1)
        sodium_scaled  = round(float(r.get("sodium_mg", 0)) * scale)

        # Display scaled info summary
        st.markdown(
            f"""
            <div style='background:#f9f9f9;border:1px solid #eee;
                        border-radius:8px;padding:8px 12px;margin-top:5px;
                        font-size:13px; margin-bottom: 5px;'>
                <b>Nutrional values ({serving_g} g):</b><br>
                {kcal_scaled} kcal • Protein {protein_scaled} g • Carbs {carbs_scaled} g • Fat {fat_scaled} g
            </div>
            """,
            unsafe_allow_html=True
        )

        # --- Log button ---
        if st.button("Log this meal", key=f"{log_key_prefix}_log_{r['recipe_id']}"):
            rid = str(r["recipe_id"])

            st.session_state.setdefault("__logged_local__", set())
            st.session_state["__logged_local__"].add(rid)

            uid = st.session_state.get("__user_id__")
            if uid:
                append_logged_meal(uid, {
                    "logged_date": str(date.today()),
                    "recipe_id": rid,
                    "name": r["name"],
                    "meal_type": r.get("meal_type", "Lunch"),
                    "calories_kcal": kcal_scaled,
                    "protein_g":     protein_scaled,
                    "carbs_g":       carbs_scaled,
                    "fat_g":         fat_scaled,
                    "fiber_g":       fiber_scaled,
                    "sodium_mg":     sodium_scaled,
                })

            st.session_state["__log_dirty__"] = True
            st.toast("Logged ✅")
            st.rerun()

# ---------------- logged meals iframe (unchanged behavior) ----------------
def meal_block_html(meal: str, rows: List[dict], logged_kcal: int, target_kcal: int) -> str:
    pct_fill = 0 if target_kcal<=0 else int(round(100*logged_kcal/target_kcal))
    pct_fill = max(2, min(pct_fill, 100))
    accent_map = {"Breakfast":"#2db483","Lunch":"#2a7df0","Dinner":"#7b5cd6","Snack":"#43cea2"}
    accent = accent_map.get(meal, "#2a7df0")
    icon_map = {"Breakfast":"🥞","Lunch":"🥗","Dinner":"🍽️","Snack":"🍎"}
    icon = icon_map.get(meal, "🍽️")
    style = f"""
    <style>
      body{{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1f2530}}
      .wrap{{padding:0 2px}}
      .mealbox{{--accent:{accent};background:linear-gradient(180deg,rgba(42,125,240,0.04) 0%,#fff 55%);border:1px solid #e9eef5;border-left:6px solid var(--accent);border-radius:12px;padding:12px;margin:10px 0 20px}}
      .mealname{{font-weight:900;color:var(--accent)}}
      .mh-bar{{width:220px;height:6px;background:#edf1f6;border-radius:999px;overflow:hidden}}
      .mh-bar>span{{display:block;height:100%;background:var(--accent);opacity:.85;border-radius:999px;min-width:2%}}
      .logged-row{{display:grid;grid-template-columns:1fr .9fr 150px;column-gap:16px;padding:10px 8px;border-top:1px solid #eef1f5}}
      .logged-row span {{font-size: 11px !important;}}
      .mini{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}}
      .lbl{{display:flex;justify-content:space-between;font-size:.74rem;color:#5f6b7a;margin-bottom:2px}}
      .bar{{height:6px;background:#e7eaf0;border-radius:999px;overflow:hidden}}
      .bar>span{{display:block;height:100%;border-radius:999px;min-width:2%}}
      .p>span{{background:#2db483}} .c>span{{background:#2a7df0}} .f>span{{background:#f59e0b}}
      .rm{{border:1px solid #f1c49c;background:#fff;border-radius:8px;padding:6px 10px;color:#9a2a0a; font-size: 12px; font-weight: bold;}}
      .mh-btn{{border: 1px solid #777;border-radius: 10px;padding: 4px 10px;color: #777;background: #fff;font-size: 11px;font-weight: bold;}}
      @media(max-width: 768px) {{.mh-bar{{width: 80px;}}.mealbox > div:nth-child(1)  > div:nth-child(3) > div:nth-child(1){{font-size: 11px;}}  button.mh-btn {{display: none;}} .mealname {{font-weight: 700;}}
      .logged-row {{ display: flex;  flex-direction: column; }} .logged-row>div>div:nth-child(2) {{margin-bottom: 10px;}}  .mini+div>div {{display: none; }}  .mini+div>button {{ margin-top: -15px !important;  font-size: 11px !important;  padding: 4px 5px !important; }} .mini {{ display: none; }} 

      }}  
    </style>
    """
    def row_html(r):
        cal_p=4.0*float(r["protein_g"]); cal_c=4.0*float(r["carbs_g"]); cal_f=9.0*float(r["fat_g"])
        tot=max(1.0,cal_p+cal_c+cal_f)
        p_pct=round(100*cal_p/tot); c_pct=round(100*cal_c/tot); f_pct=round(100*cal_f/tot)
        return f"""
          <div class="logged-row">
            <div><div style="font-weight:750">{r['name']}</div><div style="margin-top:6px">
              <span style="background:#fff3d6;color:#7a5200;font-weight:700;padding:2px 8px;border-radius:999px">{int(r['calories_kcal'])} kcal</span>
              <span style="background:#eef2f7;padding:2px 8px;border-radius:999px;margin-left:6px">{r['meal_type']}</span>
            </div></div>
            <div class="mini">
              <div><div class="lbl">Protein <span>{int(r['protein_g'])} g ({p_pct}%)</span></div><div class="bar p"><span style="width:{p_pct}%"></span></div></div>
              <div><div class="lbl">Carbs <span>{int(r['carbs_g'])} g ({c_pct}%)</span></div><div class="bar c"><span style="width:{c_pct}%"></span></div></div>
              <div><div class="lbl">Fat <span>{int(r['fat_g'])} g ({f_pct}%)</span></div><div class="bar f"><span style="width:{f_pct}%"></span></div></div>
            </div>
            <div style="text-align:right"><div style="font-size:.78rem;color:#5f6b7a;margin-bottom:6px">Fiber: <b>{int(r['fiber_g'])} g</b><br/>Sodium: <b>{int(r['sodium_mg'])} mg</b></div>
              <button class="rm" onclick="rm('{r['rid']}')">🗑️ Remove</button>
            </div>
          </div>"""
    rows_html="\n".join(row_html(r) for r in rows)
    header=f"""
      <div style="display:flex;gap:12px;align-items:center;margin:8px 0 10px">
        <div class="mealname">{icon} {meal}</div>
        <div style="flex:1"></div>
        <div style="display:flex;gap:10px;align-items:center;color:#5f6b7a;font-size:.86rem">
          <div>{int(logged_kcal)} / {int(target_kcal)} kcal</div>
          <div class="mh-bar"><span style="width:{pct_fill}%"></span></div>
          <button class="mh-btn" onclick="clearMeal('{meal}')">Clear meal</button>
        </div>
      </div>
    """
    script = """
    <script>
        function rm(id){
        window.parent.postMessage({type:'removeMeal', rid:id}, '*');
        }
        function clearMeal(meal){
        window.parent.postMessage({type:'clearMeal', meal:meal}, '*');
        }
        </script>
    """
    return f"<!doctype html><html><head><meta charset='utf-8'>{style}</head><body><div class='wrap'><div class='mealbox'>{header}{rows_html}</div></div>{script}</body></html>"

def logged_section(rows: List[dict], per_meal_target: dict):
    """
    rows: list of dicts from Supabase meal_logs (with at least id, recipe_id, name, meal_type,
          calories_kcal, protein_g, carbs_g, fat_g, fiber_g, sodium_mg)
    per_meal_target: dict with kcal target per meal
    """
    from .state import ORDERED_MEALS
    import streamlit.components.v1 as components

    if not rows:
        st.caption("No meals logged yet. Tap **Log this meal** on a card to add it here.")
        return

    # group rows by meal type
    for meal in ORDERED_MEALS:
        g = [r for r in rows if r["meal_type"] == meal]
        if not g: continue
        html = meal_block_html(
            meal,
            g,
            int(sum(float(r["calories_kcal"]) for r in g)),
            int(per_meal_target.get(meal, 0)),
        )
        est_h = 100 + 92 * max(1, len(g)) + 20
        components.html(html, height=est_h, scrolling=False)

def render_recipe_card_compact(r, *, kcal_target, diet_prefs, health, log_key_prefix="rec"):
    overall_pct = _pct01(r["fit_score"])
    st.markdown(f"<div class='compact_card'/>", unsafe_allow_html=True)
   
    # tags
    pills = []
    if r.get("diet_tags"):
        pills += [p.strip() for p in str(r["diet_tags"]).split(",") if p.strip()]
    if r.get("med_attributes"):
        for p in [p.strip() for p in str(r["med_attributes"]).split(",") if p.strip()]:
            if p in ("olive_oil","legumes","whole_grains","fish","nuts_seeds","fruits","vegetables","yogurt_cheese"):
                pills.append(p.replace("_"," "))
    pills_html = "".join([f"<span class='pill'>{p}</span>" for p in pills[:6]])

    with st.container(border=True):
        # image
        if r.get("image_url"):
            st.markdown(
                f"""
                <div style="
                    width: 100%;
                    height: 140px;
                    background-image: url('{r['image_url']}');
                    background-size: cover;
                    background-position: center;
                    border-radius: 10px;
                    margin-bottom: 6px;
                "></div>
                """,
                unsafe_allow_html=True
            )
        # title + kcal
        st.markdown(f"<div class='title'><strong>{r['name']}</strong></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='sub'><b>{int(r['calories_kcal'])} kcal</b> · {r['cuisine']}</div>", unsafe_allow_html=True)

        # fit badge
        # --- Overall Fit + Med Compliance + Picked badges on one line ---
        med_badge = ""
        score = float(r.get("fit_med_compliance", 0))
        if score > 0.8:
            med_badge = "<span class='badge green'>🌿 Med-compliant</span>"
        elif score > 0.4:
            med_badge = "<span class='badge yellow'>⚖️ Partially Med</span>"
        else:
            med_badge = "<span class='badge red'>🚫 Non-Med</span>"

        # inline layout
        st.markdown(
            f"<div style='display:flex;gap:6px;align-items:center;'>"
            f"<span class='badge'>Overall fit: {overall_pct}%</span>"
            f"{med_badge}"
            f"</div>",
            unsafe_allow_html=True
        )


        # tags
        # if pills_html:
        #     st.markdown(f"<div class='pills' style='min-height: 75px; display: flex; flex-direction: row; flex-wrap: wrap; align-content: center; justify-content: center; align-items: center;'>{pills_html}</div>", unsafe_allow_html=True)

        # ingredients (short)
        # if r.get("ingredients"):
        #     st.markdown(f"<div class='ing'><b>Ingredients:</b> {r['ingredients']}</div>", unsafe_allow_html=True)

        # --- Serving size adjustment ---
        default_serving = 100  # base reference (your dataset values are per 100g)
        key_serv = f"{log_key_prefix}_serv_{r['recipe_id']}"
        serving_g = st.number_input(
            "Serving size (g)",
            min_value=50, max_value=1000,
            value=default_serving, step=25,
            key=key_serv
        )

        # Scale calories and macros according to serving size
        scale = serving_g / default_serving
        kcal_scaled   = round(float(r.get("calories_kcal", 0)) * scale)
        protein_scaled = round(float(r.get("protein_g", 0)) * scale, 1)
        carbs_scaled   = round(float(r.get("carbs_g", 0)) * scale, 1)
        fat_scaled     = round(float(r.get("fat_g", 0)) * scale, 1)
        fiber_scaled   = round(float(r.get("fiber_g", 0)) * scale, 1)
        sodium_scaled  = round(float(r.get("sodium_mg", 0)) * scale)

        # Update display so the user sees the scaled kcal
        st.markdown(
            f"<div class='sub'><b>{kcal_scaled} kcal</b> · {r['cuisine']} · {serving_g} g</div>",
            unsafe_allow_html=True
        )

        if st.button("Log this meal", key=f"{log_key_prefix}_log_{r['recipe_id']}"):
            rid = str(r["recipe_id"])
            st.session_state.setdefault("__logged_local__", set())
            st.session_state["__logged_local__"].add(rid)

            uid = st.session_state.get("__user_id__")
            if uid:
                append_logged_meal(uid, {
                    "logged_date": str(date.today()),
                    "recipe_id": rid,
                    "name": r["name"],
                    "meal_type": r.get("meal_type", "Lunch"),
                    "calories_kcal": kcal_scaled,
                    "protein_g": protein_scaled,
                    "carbs_g": carbs_scaled,
                    "fat_g": fat_scaled,
                    "fiber_g": fiber_scaled,
                    "sodium_mg": sodium_scaled,
                })

            st.session_state["__log_dirty__"] = True
            st.toast("Logged ✅")
            st.rerun()
