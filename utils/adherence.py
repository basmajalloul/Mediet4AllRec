# utils/adherence.py
def _clip01(x: float) -> float:
    try:
        x = float(x)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, x))

def _map_ipaq_to_pct(total_met: int, level: str) -> int:
    """
    Map IPAQ to 0..100.
    - <1500 MET-min/wk: Low ≈ 25
    - 1500..2999: Moderate ≈ 60
    - ≥3000: High ≈ 85 (cap at 100 via extra credit up to 5000)
    """
    if total_met is None: return 0
    tm = max(0, int(total_met))
    if tm < 1500: base = 25
    elif tm < 3000: base = 60
    else: base = 85
    # gentle scaling inside band
    if tm >= 3000:
        extra = min(15, int((tm - 3000) / 133))  # +~0..15 by 5k
        val = min(100, base + extra)
    elif tm >= 1500:
        extra = int((tm - 1500) / 50)  # +0..30 up to 3k
        val = min(90, base - 15 + min(30, extra))
    else:
        # lift a bit within 0..1500
        val = int(10 + 15 * (tm / 1500))
    return int(max(0, min(100, val)))

def _sitting_penalty(min_per_day: int) -> int:
    """0..20 penalty: start after 360 min (6h), max at 720 min (12h)."""
    m = max(0, int(min_per_day or 0))
    if m <= 360: return 0
    if m >= 720: return 20
    # linear between 6h and 12h
    return int(round((m - 360) * (20 / 360)))

def compute_general_adherence(
    energy_score: int,         # 0..100 from daily_adherence_from_logs
    variety_score: int,        # 0..100 from daily_adherence_from_logs
    medlife_total: int,        # 0..28
    ipaq_total_met: int,       # MET-min/week
    ipaq_level: str,           # Low/Moderate/High (not strictly needed)
    sitting_min_per_day: int   # minutes
) -> int:
    # Normalize components
    energy = _clip01(energy_score/100.0)      # meal kcal balance (from your function) 
    variety = _clip01(variety_score/100.0)    # Med components coverage (your function) 
    medlife = _clip01((medlife_total or 0)/28.0)
    ipaq_pct = _map_ipaq_to_pct(ipaq_total_met, ipaq_level) / 100.0
    pen = _sitting_penalty(sitting_min_per_day) / 100.0

    # Weights: Nutrition 60% (30 energy + 30 variety), Lifestyle 40% (20 medlife + 20 activity).
    base = (0.30*energy + 0.30*variety + 0.20*medlife + 0.20*ipaq_pct)
    # Sitting penalty (up to -20 points)
    score = max(0.0, base*100.0 - pen*100.0)
    return int(round(min(100.0, score)))
