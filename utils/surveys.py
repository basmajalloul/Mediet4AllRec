# utils/surveys.py
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

# ---------- MEDLIFE ----------
MEDLIFE_ITEMS = [
    # Block 1: food consumption
    ("Sweets ≤2/wk", True),
    ("Red meat <2/wk", True),
    ("Processed meat ≤1/wk", True),
    ("Eggs 2–4/wk", True),
    ("Legumes ≥2/wk", True),
    ("White meat ≈2/wk", True),
    ("Fish/seafood ≥2/wk", True),
    ("Potatoes ≤3/wk", True),
    ("Low-fat dairy ≥2/day", True),
    ("Nuts/olives 1–2/day", True),
    ("Herbs/spices ≥1/day", True),
    ("Fruit 3–6/day", True),
    ("Vegetables ≥2/day", True),
    ("Olive oil ≥3 tbsp/day", True),
    ("Cereals 3–6/day", True),
    # Block 2: habits
    ("Water/infusions 6–8/day or ≥3/wk", True),
    ("Wine 1–2/day", True),
    ("Limit salt", True),
    ("Prefer whole-grain (>25 g fibre/day)", True),
    ("Snacks ≤2/wk", True),
    ("Limit nibbling between meals", True),
    ("Limit sugary drinks", True),
    # Block 3: PA/rest/social
    ("Physical activity >150 min/wk", True),
    ("Weekend siesta", True),
    ("Sleep 6–8 h/day", True),
    ("TV <1 h/day (weekdays)", True),
    ("Socialising ≥2 h/weekend", True),
    ("Collective sports ≥2 h/wk", True),
]

def medlife_score(answers_yes_no: List[bool]) -> Dict:
    """
    answers_yes_no: list of 28 booleans in the order above.
    Returns: total 0..28 + label {Low, Moderate, High}.
    """
    n = min(len(answers_yes_no), len(MEDLIFE_ITEMS))
    total = sum(1 for i in range(n) if answers_yes_no[i])
    # Suggested cutpoints (can switch to cohort tertiles later)
    if total <= 9: label = "Low"
    elif total <= 18: label = "Moderate"
    else: label = "High"
    return {"total": total, "label": label}

# ---------- IPAQ (Short Form) ----------
@dataclass
class IpaqInput:
    walk_days: int; walk_min_per_day: int
    mod_days: int; mod_min_per_day: int
    vig_days: int; vig_min_per_day: int
    sit_hours_per_day: int; sit_min_per_day: int
    use_older_adult_coeffs: bool = False  # if True: 2.5/3.0/5.3

def ipaq_score(ip: IpaqInput) -> Dict:
    w_coef, m_coef, v_coef = (3.3, 4.0, 8.0)
    if ip.use_older_adult_coeffs:
        w_coef, m_coef, v_coef = (2.5, 3.0, 5.3)

    walk_min_week = max(0, ip.walk_days) * max(0, ip.walk_min_per_day)
    mod_min_week  = max(0, ip.mod_days)  * max(0, ip.mod_min_per_day)
    vig_min_week  = max(0, ip.vig_days)  * max(0, ip.vig_min_per_day)

    walk_met = w_coef * walk_min_week
    mod_met  = m_coef * mod_min_week
    vig_met  = v_coef * vig_min_week
    total_met = walk_met + mod_met + vig_met

    if total_met < 1500:
        level = "Low"
    elif total_met < 3000:
        level = "Moderate"
    else:
        level = "High"

    sitting_min_day = ip.sit_hours_per_day * 60 + ip.sit_min_per_day
    return {
        "walking_met_min_week": int(round(walk_met)),
        "moderate_met_min_week": int(round(mod_met)),
        "vigorous_met_min_week": int(round(vig_met)),
        "total_met_min_week": int(round(total_met)),
        "activity_level": level,
        "sitting_min_per_day": max(0, sitting_min_day),
    }