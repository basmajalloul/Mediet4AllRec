# utils/ui.py
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components
from typing import Dict, List
from .state import ORDERED_MEALS

# ---------------- CSS once ----------------
def inject_css_and_title():
    st.set_page_config(page_title="MedDiet Recommender", layout="wide")
    st.markdown("""
    <style>                
      section[data-testid="stSidebar"]{width:380px !important;background:#f5f7fa}
      .metriccard{background:linear-gradient(135deg,#fefeff 0%,#f1f6ff 100%);border:1px solid #e9eef4;border-radius:16px;padding:18px 22px;box-shadow:0 1px 5px rgba(0,0,0,.05);margin:8px 0}
      .metricrow{display:flex;gap:12px;align-items:center}
      h1#mediterranean-diet-recommendation-system {
          font-weight: 900;
          text-transform: uppercase;
          font-size: 30px;
          color: #f9ad1a;
          padding-bottom: 0px !important;
          margin-top: 5px;
      }
      .metricicon{font-size:1.3rem;background:#e7efff;border-radius:50%;width:36px;height:36px;display:flex;align-items:center;justify-content:center}
      .metricmain{font-size:1.2rem;font-weight:800;color:#1a3d7c}
      .metricsub{font-size:.95rem;color:#444;margin-top:3px}
      .pill{background:#f4f6fb;color:#333;padding:3px 10px;border-radius:999px;font-size:.78rem;margin-right:6px}
      .badge{display:inline-block;padding:4px 10px;border-radius:999px;background:#e8f3ea;color:#1c6b2a;font-weight:700;font-size:.80rem}
      .divider{height:1px;background:#eef2f7;margin:12px 0}
      .coach-output{padding:16px 20px;border-radius:12px;background:#fafbfc;border-left:4px solid #5ca0f2;font-size:.97rem;line-height:1.55;color:#2a323f;margin-top:12px}
      h1#meddiet{font-weight:900;text-transform:uppercase;font-size:30px;color:#f9ad1a;margin-top:5px}
      .title { font-weight: 700; font-size: 1.05rem; margin: 2px 0 4px; }
      .sub { color:#5b667a; font-size:0.95rem; margin-bottom:12px; }
      .badge {display:inline-block;padding:4px 10px;border-radius:999px;background:#e8f3ea;color:#1c6b2a;font-weight:600;font-size:0.80rem;}
      .pills { display:flex; flex-wrap:wrap; gap:6px; margin:10px 0 0 0; }
      .pill { background:#f4f6fb; color:#333; padding:3px 10px; border-radius:999px; font-size:0.78rem; }
      .divider { height:1px; background:rgba(0,0,0,0.06); margin:12px 0; }

      /* metric bars */
      .metricrow{display:flex;align-items:center;gap:12px;margin:8px 0;}
      .metricrow .label{min-width:140px;font-weight:600;color:#2a2f3a;}
      .metricrow .bar{flex:1;height:10px;background:#eef2f7;border-radius:999px;overflow:hidden}
      .metricrow .bar>span{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#f9ad1a,#ee6a04);}
      .metricrow .pct{color:#6a7485;font-size:0.95rem;min-width:48px;text-align:right}

      /* subtle “why this” bullets */
      .whybox { background:#fbfcfe; border:1px solid #edf2f7; border-radius:12px; padding:10px 14px; }
      .whyline { display:flex; gap:8px; align-items:flex-start; margin:6px 0; color:#2a313d; }
      .whyicon { width:22px; height:22px; display:flex; align-items:center; justify-content:center;
                 border-radius:50%; background:#eef2ff; border:1px solid #e5e9f3; font-size:14px; }
      .whytext { font-size:0.95rem; line-height:1.35rem; }
      .ing { font-size: 13px;}
      .instructions {
          margin-top: 4px;
          font-size: 12px;
          color: #555;
          font-style: italic;
      }
      a.link {
          font-size: 12px;
          float: right;
      }
      .whybox div {
          font-size: 13px !important;
      }
      .whybox {
          margin-bottom: 15px;
          margin-top: 10px;
      }
      
      .stTabs [role="tabpanel"] button {
            float: left;
            background: linear-gradient(90deg, #f9ad1a, #ee6a04);
            color: #fff;
            border: 0px;
            margin-bottom: -45px;
            position: relative;
            z-index: 1000;
        }

        .stTabs [role="tabpanel"] button p {
            font-size: 14px;
            font-weight: bold;
        }
        h2 {
            font-size: 26px !important;
            margin-bottom: 20px !important;
            font-weight: bold !important;
        }
    </style>
    """, unsafe_allow_html=True)

# --- Global styles reused across pages (cards + metric bars + heading) ---

def topbar_logo_and_title():
    c1,c2 = st.columns([1,8])
    with c1: st.image("download.png", width=150)
    with c2:
        st.markdown('<h1 id="meddiet">Mediterranean Diet Recommendation System</h1>', unsafe_allow_html=True)
        st.caption("Profile-based recommendations • Intake logging • Health-aware prioritization")

# ---------------- energy banner ----------------
def energy_banner(total_kcal: int, per: Dict[str,int]):
    c1,c2 = st.columns([2,1])
    with c1:
        st.markdown(f"""
        <div class="metriccard">
         <div class="metricrow"><div class="metricicon">🔥</div>
          <div><div class="metricmain">Daily energy target: {int(total_kcal)} kcal</div>
          <div class="metricsub">Breakfast {per['Breakfast']} • Lunch {per['Lunch']} • Dinner {per['Dinner']} • Snack {per['Snack']} kcal</div>
         </div></div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metriccard">
         <div class="metricrow"><div class="metricicon">✅</div>
          <div><div class="metricmain">Score Today: {int(st.session_state.get('score_today',0))}</div>
          <div class="metricsub">+1 per meal logged</div>
        </div></div></div>""", unsafe_allow_html=True)

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
    if abs(delta) >= 60:
        if delta > 0:
            bullets.append(("🧭","Below target by ~{} kcal → consider adding a small whole‑grain/legume side or a drizzle of olive oil.".format(delta)))
        else:
            bullets.append(("🧭","Above target by ~{} kcal → consider a lighter side or halving added fats.".format(-delta)))
    # Diet style / avoids
    if float(row["fit_diet_style"]) >= 0.99:
        bullets.append(("🥗","Matches your chosen diet style."))
    if float(row["fit_no_avoids"]) >= 0.99:
        bullets.append(("🚫","Respects your ‘avoid’ list."))
    # Preferences
    if float(row["fit_prefer_bonus"]) > 1.0:
        bullets.append(("⭐","Includes one of your preferred ingredients."))
    # Health mod
    if float(row["fit_health_mod"]) > 1.0:
        bullets.append(("🩺","Favorable for your health profile."))
    # Macro
    bullets.append(("🍽️","Macro split ≈ {}% protein / {}% carbs / {}% fat.".format(p, c, f)))
    # Fiber
    if float(row.get("fiber_g", 0)) >= 7:
        bullets.append(("🌿","Good fiber content."))

    # Render
    html = ["<div class='whybox'>"]
    for ico, txt in bullets:
        html.append(f"<div class='whyline'><div class='whyicon'>{ico}</div><div class='whytext'>{txt}</div></div>")
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)

def render_recipe_card(r, *, kcal_target, diet_prefs, health, log_key_prefix="rec"):
    # map rule-engine outputs to % for the bars
    overall_pct = _pct01(r["fit_score"])
    cal_pct     = _pct01(r["fit_calorie"])
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
        st.markdown(f"<div class='title'><strong>{r['name']}</strong></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='sub'><b>{int(r['calories_kcal'])} kcal</b> · {r['cuisine']}</div>", unsafe_allow_html=True)

        # utils/ui.py  (inside render_recipe_card, after the "Overall fit" badge line)
        picked = r['recipe_id'] in set(st.session_state.get("optimized_set", set()))
        picked_html = " <span class='badge'>🎯 Picked</span>" if picked else ""
        st.markdown(f"<span class='badge'>Overall fit: {overall_pct}%</span>{picked_html}", unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="metricrow"><div class="label">Calorie fit</div>
              <div class="bar"><span style="width:{cal_pct}%"></span></div><div class="pct">{cal_pct}%</div></div>
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
        render_why_this(r, kcal_target)


        # --- Log button ---
        if st.button("Log this meal", key=f"{log_key_prefix}_log_{r['recipe_id']}"):
            st.session_state.setdefault("logged", [])
            st.session_state["logged"].append(r["recipe_id"])
            st.session_state["score_today"] = int(st.session_state.get("score_today", 0)) + 1
            st.toast(f"Logged ✅  (score {st.session_state['score_today']})")
            st.rerun()
        
        st.markdown(
            f"<a href='{_similar_google(str(r['name']), str(r['cuisine']))}' target='_blank' class='link'>Find similar recipe ↗︎</a>",
            unsafe_allow_html=True
        )


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
      function rm(id){const u=new URL(window.parent.location);u.searchParams.set('rm',id);window.parent.location=u}
      function clearMeal(meal){const u=new URL(window.parent.location);u.searchParams.set('rm_all',meal);window.parent.location=u}
    </script>"""
    return f"<!doctype html><html><head><meta charset='utf-8'>{style}</head><body><div class='wrap'><div class='mealbox'>{header}{rows_html}</div></div>{script}</body></html>"

def logged_section(df, per_meal_target):
    from .state import ORDERED_MEALS
    if not st.session_state["logged"]:
        st.caption("No meals logged yet. Tap **Log this meal** on a card to add it here.")
        return
    import math
    import pandas as pd
    used = df[df["recipe_id"].isin(st.session_state["logged"])][
        ["recipe_id","name","meal_type","calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sodium_mg","med_attributes"]
    ]
    for meal in ORDERED_MEALS:
        g = used[used["meal_type"] == meal]
        if g.empty: continue
        rows=[]
        for _,row in g.iterrows():
            rows.append({
                "rid":row["recipe_id"],"name":row["name"],"meal_type":row["meal_type"],
                "calories_kcal":row["calories_kcal"],"protein_g":row["protein_g"],
                "carbs_g":row["carbs_g"],"fat_g":row["fat_g"],"fiber_g":row["fiber_g"],"sodium_mg":row["sodium_mg"],
            })
        html = meal_block_html(meal, rows, int(g["calories_kcal"].sum()), int(per_meal_target.get(meal,0)))
        est_h = 100 + 92*max(1,len(rows)) + 20
        components.html(html, height=est_h, scrolling=False)
