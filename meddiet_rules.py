import pandas as pd
import numpy as np
import re
from typing import Dict, List, Tuple

def _med_compliance_score(row) -> float:
    """Return a robust Mediterranean compliance score (0–1)."""
    tags = str(row.get("diet_tags", "")).lower()
    attrs = row.get("med_attributes", "")

    # --- Normalize med_attributes ---
    if isinstance(attrs, list):
        items = [a.strip().lower() for a in attrs]
    elif isinstance(attrs, str):
        items = [a.strip().lower() for a in attrs.replace("[","").replace("]","").replace("'","").split(",")]
    else:
        items = []

    # Core Med components
    core = ["olive_oil", "whole_grains", "vegetables", "fruits",
            "fish", "nuts_seeds", "legumes", "yogurt_cheese"]

    n_hits = sum(1 for k in core if k in items)

    # Weighted scoring
    if n_hits >= 4:
        score = 1.0
    elif n_hits >= 2:
        score = 0.8
    elif n_hits == 1:
        score = 0.5
    else:
        score = 0.0

    # Tag-based boost
    if "mediterranean" in tags:
        score = min(1.0, score + 0.1)

    return round(float(score), 2)

def _normalize_list(s: str) -> List[str]:
    if not isinstance(s, str) or not s.strip():
        return []
    parts = re.split(r"[;,]", s)
    return [p.strip().lower() for p in parts if p.strip()]

def derive_daily_calorie_target(age: int, weight_kg: float, height_cm: float, sex: str, activity: str, goal: str) -> int:
    sex = (sex or "female").lower()
    activity = (activity or "sedentary").lower()
    goal = (goal or "maintain").lower()
    if sex == "male":
        bmr = 10*weight_kg + 6.25*height_cm - 5*age + 5
    else:
        bmr = 10*weight_kg + 6.25*height_cm - 5*age - 161
    af_map = {"sedentary":1.2,"light":1.375,"moderate":1.55,"active":1.725,"very active":1.9}
    af = af_map.get(activity, 1.2)
    tdee = bmr * af
    if goal in ("fat loss","weight loss"):
        tdee -= 300
    elif goal in ("muscle gain","weight gain"):
        tdee += 250
    return int(max(1200, round(tdee)))

def split_meal_targets(daily_cals: int, pattern: str = "3_meals_1_snack") -> Dict[str, int]:
    pattern = (pattern or "3_meals_1_snack").lower()
    shares = {"Breakfast":0.20,"Lunch":0.35,"Dinner":0.35,"Snack":0.10} if pattern!="2_meals_2_snacks" else {"Breakfast":0.25,"Lunch":0.35,"Dinner":0.30,"Snack":0.10}
    return {k:int(round(daily_cals*v)) for k,v in shares.items()}

def _health_modifiers(row, health: Dict) -> float:
    """Return multiplicative modifier (0..1.3) based on health conditions."""
    mod = 1.0
    carbs = float(row["carbs_g"]); fat = float(row["fat_g"]); fiber = float(row["fiber_g"])
    sodium = float(row.get("sodium_mg", 350))
    attrs = set([a.strip().lower() for a in str(row.get("med_attributes","")).split(",") if a.strip()])

    # Hypertension
    if health.get("hypertension"):
        if sodium > 500: mod *= 0.85
        if "vegetables" in attrs or "legumes" in attrs: mod *= 1.05

    # Diabetes / Prediabetes
    if health.get("diabetes") or health.get("prediabetes"):
        if carbs > 60: mod *= 0.85
        if fiber >= 8: mod *= 1.08
        if {"whole_grains","legumes","nuts_seeds"} & attrs: mod *= 1.05

    # Hyperlipidemia
    if health.get("hyperlipidemia"):
        if {"fish","olive_oil","nuts_seeds"} & attrs: mod *= 1.05
        if "yogurt_cheese" in attrs: mod *= 0.95

    # Celiac
    if health.get("celiac"):
        if not bool(row["is_gluten_free"]): mod *= 0.0  # hard exclude

    # GERD
    if health.get("gerd"):
        if fat > 25: mod *= 0.9

    # NEW: Rheumatoid Arthritis / Autoimmune (anti-inflammatory tilt)
    # Boost omega-3 fish (salmon, sardines, mackerel), EVOO, nuts/seeds, legumes, fruit/veg, fiber.
    # Slightly de-emphasize cheese-heavy dishes.
    if health.get("autoimmune"):
        if {"fish"} & attrs:                mod *= 1.08
        if {"olive_oil"} & attrs:           mod *= 1.05
        if {"nuts_seeds","legumes"} & attrs:mod *= 1.05
        if {"fruits","vegetables"} & attrs: mod *= 1.05
        if fiber >= 8:                      mod *= 1.05
        if "yogurt_cheese" in attrs:        mod *= 0.97

    return float(np.clip(mod, 0.0, 1.3))

def compute_meal_fit_score(row, kcal_target: int, diet_prefs: Dict, health: Dict) -> Tuple[float, Dict]:
    cal = float(row["calories_kcal"]); dev = abs(cal - kcal_target)
    #cal_term = np.exp(-(dev**2) / (2 * (0.2 * max(200, kcal_target))**2))
    cal_term = 1.0
    
    diet_ok = True
    if diet_prefs.get("vegan"): diet_ok = bool(row["is_vegan"])
    elif diet_prefs.get("vegetarian"): diet_ok = bool(row["is_vegetarian"])
    elif diet_prefs.get("pescatarian"): diet_ok = bool(row["is_pescatarian"])
    if diet_ok and diet_prefs.get("gluten_free"): diet_ok = bool(row["is_gluten_free"])
    if diet_ok and diet_prefs.get("dairy_free"):  diet_ok = bool(row["is_dairy_free"])
    diet_term = 1.0 if diet_ok else 0.0

    avoid = set([a.lower() for a in _normalize_list(diet_prefs.get("avoid_ingredients",""))])
    ing   = set([a.lower() for a in _normalize_list(row.get("ingredients",""))])
    avoid_term = 0.0 if (avoid and (avoid & ing)) else 1.0

    # --- Preference boost: set match + attributes + light synonyms
    prefer = set([a.lower() for a in _normalize_list(diet_prefs.get("prefer_ingredients",""))])

    ing   = set([a.lower() for a in _normalize_list(row.get("ingredients",""))])
    attrs = set([a.strip().lower() for a in _normalize_list(row.get("med_attributes",""))])

    # Map attribute tags to phrases a user might put in preferences
    ATTR_TO_PREF = {
        "olive_oil": {"olive oil", "extra virgin olive oil", "evoo"},
        "whole_grains": {"whole grains", "whole-wheat", "whole wheat", "bulgur",
                        "brown rice", "oats", "barley", "farro", "quinoa"},
        "legumes": {"legumes", "beans", "lentils", "chickpeas", "peas"},
        "nuts_seeds": {"nuts", "seeds", "almonds", "walnuts", "sesame"},
        # add more if you like
    }

    # If user prefers “olive oil” and the recipe has med_attribute 'olive_oil',
    # count it as a hit even if the ingredient line is messy.
    attr_hit = any(prefer & ATTR_TO_PREF.get(a, set()) for a in attrs)

    ing_hit  = bool(prefer & ing)

    prefer_term = 1.0 + (0.15 if (ing_hit or attr_hit) else 0.0)
    health_mod = _health_modifiers(row, health)
    med_compliance = _med_compliance_score(row)

    # Penalize non-Med foods: 0.5× if non-compliant, 0.8× if partial
    med_term = 0.5 + 0.5 * med_compliance

    total = cal_term * diet_term * avoid_term * prefer_term * health_mod * med_term
    dbg = {
        "cal_term":float(cal_term),"diet_term":float(diet_term),"avoid_term":float(avoid_term),
        "prefer_term":float(prefer_term),"health_mod":float(health_mod),
        "med_term":float(med_term),"total":float(total)
    }
    return total, dbg


def recommend(df: pd.DataFrame, meal_type: str, kcal_target: int, diet_prefs: Dict, health: Dict, k: int = 5, exclude_recipe_ids: List[str] = None) -> pd.DataFrame:
    mt = (
        df.get("meal_type")
        .astype(str)              # coerce non-strings/NaN
        .str.strip()
        .str.lower()
    )
    subset = df[mt == str(meal_type).strip().lower()].copy()
    if exclude_recipe_ids:
        subset = subset[~subset["recipe_id"].isin(exclude_recipe_ids)]
    scores=[]; cals=[]; diets=[]; avoids=[]; prefers=[]; healths=[]
    for _, row in subset.iterrows():
        s, dbg = compute_meal_fit_score(row, kcal_target, diet_prefs, health)
        scores.append(s)
        cals.append(dbg["cal_term"]); diets.append(dbg["diet_term"]); avoids.append(dbg["avoid_term"])
        prefers.append(dbg["prefer_term"]); healths.append(dbg["health_mod"])
    subset["fit_score"]        = scores
    subset["fit_calorie"]      = cals
    subset["fit_diet_style"]   = diets
    subset["fit_no_avoids"]    = avoids
    subset["fit_prefer_bonus"] = prefers
    subset["fit_health_mod"]   = healths
    subset = subset.sort_values("fit_score", ascending=False)
    return subset.head(k)

def daily_adherence_from_logs(df: pd.DataFrame, logged_ids: List[str]) -> dict:
    if not logged_ids:
        return {"energy_score": 0, "component_score": 0, "total": 0}
    used = df[df["recipe_id"].isin(logged_ids)].copy()
    comp_set = set()
    for _, r in used.iterrows():
        attrs = [a.strip().lower() for a in str(r.get("med_attributes","")).split(",") if a.strip()]
        comp_set.update(attrs)
    core = ["olive_oil","legumes","whole_grains","fish","nuts_seeds","fruits","vegetables","yogurt_cheese","herbs_spices"]
    comp_score = len(set(core) & comp_set) / len(core)
    cal = used["calories_kcal"].values.astype(float)
    if len(cal) > 1:
        cv = np.std(cal) / max(1.0, np.mean(cal))
        energy = np.clip(1.0 - cv, 0.0, 1.0)
    else:
        energy = 0.7
    total = int(round((0.5*energy + 0.5*comp_score) * 100))
    return {"energy_score": int(round(energy*100)), "component_score": int(round(comp_score*100)), "total": total}