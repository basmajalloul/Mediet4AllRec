# utils/compose.py
# utils/compose.py
import json, re, random   # add random
import pandas as pd
from meddiet_rules import compute_meal_fit_score

DISH_STYLES = {
    "Breakfast": ["frittata", "omelette", "savory pancakes", "toasts", "yogurt parfait"],
    "Lunch":     ["wrap", "pasta", "soup", "tray bake", "skewers", "stuffed vegetables"],
    "Dinner":    ["stew/tagine", "bake", "pasta", "grill", "skewers", "sheet-pan"],
    "Snack":     ["mezze plate", "dip + crudités", "mini skewers", "toast", "smoothie"]
}
LEGUME_WORDS = ("chickpea", "chick-pea", "garbanzo", "lentil", "bean")

SCHEMA = """
Return ONLY valid minified JSON with keys:
{
  "title": str,
  "servings": int,
  "cuisine": str,
  "med_tags": [str,...],
  "ingredients": [{"item": str, "qty": number, "unit": str, "notes": str|optional}, ...],
  "steps": [str, ...],
  "nutrition": {
    "calories_kcal": number, "protein_g": number, "carbs_g": number,
    "fat_g": number, "fiber_g": number, "sodium_mg": number
  },
  "rationale": str
}
"""

def _json_from_text(txt: str):
    # Grab first {...} block and parse.
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("No JSON object found in model output.")
    return json.loads(m.group(0))

def build_system_prompt():
    return (
        "You are a Mediterranean Diet recipe composer. Create coherent, practical recipes "
        "aligned with MedDiet principles (EVOO, vegetables, legumes, whole grains, fish, nuts; "
        "limited red/processed meats; moderate dairy). Quantities in metric. No brands. "
        "Avoid repeating the same format ('salad'/'bowl') across requests; prefer varied forms "
        "such as stew/tagine, pasta, wrap, tray bake/sheet-pan, skewers, stuffed vegetables, frittata/omelette, soup. "
        "LEGUME RULE: if legumes appear they MUST be cooked (canned or pre-cooked). NEVER raw. "
        "Include a step to 'rinse and drain canned legumes' or 'cook until tender' with an indicative time. "
        "If grains are used (rice, quinoa, pasta), include the cooking step and time."
    )

def build_user_prompt(meal, kcal_target, diet_prefs, health, pantry, servings, strict_pantry):
    prefs = []
    if diet_prefs.get("vegan"): prefs.append("vegan")
    elif diet_prefs.get("vegetarian"): prefs.append("vegetarian")
    elif diet_prefs.get("pescatarian"): prefs.append("pescatarian")
    if diet_prefs.get("gluten_free"): prefs.append("gluten-free")
    if diet_prefs.get("dairy_free"):  prefs.append("dairy-free")
    prefs_str = ", ".join(prefs) if prefs else "no special diet"
    avoid = diet_prefs.get("avoid_ingredients","")
    prefer = diet_prefs.get("prefer_ingredients","")
    health_flags = [k for k,v in health.items() if v]
    health_str = ", ".join(health_flags) if health_flags else "none"

    pantry = [p.strip() for p in pantry if p and p.strip()]
    ptxt = "; ".join(pantry) if pantry else "none"

    # Pick a varied dish style for this meal to reduce salad/bowl bias
    style = random.choice(DISH_STYLES.get(meal, ["chef's choice"]))

    if strict_pantry:
        pantry_line = (
            "HARD CONSTRAINT: Use ONLY the listed pantry items. Do not add anything else. "
            "If impossible, keep ingredients within the list and adapt portions."
        )
        legume_bias_line = "Do NOT introduce legumes unless they are listed in the pantry."
    else:
        pantry_line = "Pantry-first: you may add common basics like onion, garlic, herbs, lemon."
        legume_bias_line = "Legumes are optional; do not force them if not appropriate."

    return f"""
Compose a {meal.lower()} recipe for {servings} serving(s), ~{int(kcal_target)} kcal per serving.
Diet style: {prefs_str}. Avoid: {avoid or 'none'}. Prefer: {prefer or 'none'}.
Health constraints: {health_str}.
Pantry items: {ptxt}. {pantry_line}
Dish format: favor a {style} (avoid defaulting to 'salad' or 'bowl' unless explicitly asked).
{legume_bias_line}
Follow MedDiet style, balance macros, and keep sodium moderate (<700 mg/serving if possible).
{SCHEMA}
"""

def compute_fit_for_recipe(recipe_dict, kcal_target, diet_prefs, health):
    nut = recipe_dict.get("nutrition") or {}
    required = ["calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sodium_mg"]
    if any(k not in nut for k in required):
        return None, {"warning": "nutrition_missing"}
    # Build a 'row-like' dict for compute_meal_fit_score
    row = {
        "calories_kcal": nut["calories_kcal"],
        "protein_g": nut["protein_g"],
        "carbs_g": nut["carbs_g"],
        "fat_g": nut["fat_g"],
        "fiber_g": nut["fiber_g"],
        "sodium_mg": nut["sodium_mg"],
        "is_vegan": "vegan" in (recipe_dict.get("med_tags") or []),
        "is_vegetarian": "vegetarian" in (recipe_dict.get("med_tags") or []) or "vegan" in (recipe_dict.get("med_tags") or []),
        "is_pescatarian": "fish" in " ".join(recipe_dict.get("med_tags") or []),
        "is_gluten_free": "gluten_free" in (recipe_dict.get("med_tags") or []),
        "is_dairy_free": "dairy_free" in (recipe_dict.get("med_tags") or []),
        "med_attributes": ",".join(recipe_dict.get("med_tags") or []),
        "ingredients": "; ".join(i["item"] for i in recipe_dict.get("ingredients", [])),
    }
    score, dbg = compute_meal_fit_score(row, int(kcal_target), diet_prefs, health)
    return float(score), dbg

def _needs_legume_prep(recipe_dict):
    txt_ing = " ".join(i.get("item","").lower() for i in recipe_dict.get("ingredients", []))
    has_legume = any(w in txt_ing for w in LEGUME_WORDS)
    if not has_legume:
        return False
    steps_txt = " ".join(map(str, recipe_dict.get("steps", []))).lower()
    good = any(w in steps_txt for w in ("rinse", "drain", "boil", "simmer", "cook", "pressure"))
    return not good

def critique_message(score, dbg, recipe_dict=None):
    if score is None:
        return "Nutrition missing; add per-serving calories, protein, carbs, fat, fiber, and sodium."
    tips = []
    if dbg["cal_term"] < 0.7: tips.append("adjust portion sizes to hit the calorie target more closely")
    if dbg["health_mod"] < 0.95: tips.append("lower sodium and/or saturated-fat sources (avoid processed meats/cheese)")
    if dbg["diet_term"] < 1.0: tips.append("ensure the diet style flags (vegan/vegetarian/gluten-free) are truly respected")
    if dbg["avoid_term"] < 1.0: tips.append("remove any ingredients on the avoid list")
    if dbg["prefer_term"] < 1.1: tips.append("incorporate at least one preferred ingredient")
    if recipe_dict is not None and _needs_legume_prep(recipe_dict):
        tips.append("legumes must be canned/cooked; add 'rinse and drain' or 'cook until tender' with an indicative time (never raw legumes)")
    return " ; ".join(tips) or "Looks good—minor wording polish only."

def refine_prompt(prev_json, critique):
    return (
        "Revise the previous recipe to address the issues:\n"
        f"{critique}\n"
        "Return ONLY the full recipe JSON again (same schema)."
        f"\nPrevious recipe:\n{json.dumps(prev_json, ensure_ascii=False)}"
    )
