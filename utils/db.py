# utils/db.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import date

import streamlit as st
from supabase import create_client, Client

# -------- client --------
@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

# -------- auth (used by auth_gate) --------
def sign_up_password(email: str, password: str) -> Dict[str, Any]:
    res = get_client().auth.sign_up({"email": email, "password": password})
    return {"user": res.user.model_dump() if res.user else None}

def sign_in_password(email: str, password: str) -> Dict[str, Any]:
    res = get_client().auth.sign_in_with_password({"email": email, "password": password})
    return {"user": res.user.model_dump() if res.user else None}

def send_otp(email: str) -> None:
    get_client().auth.sign_in_with_otp({"email": email})

def verify_otp(email: str, token: str) -> Dict[str, Any]:
    res = get_client().auth.verify_otp({"email": email, "token": token, "type": "email"})
    return {"user": res.user.model_dump() if res and res.user else None}

def sign_out() -> None:
    get_client().auth.sign_out()

def current_user() -> Optional[dict]:
    res = get_client().auth.get_user()
    return None if not res or not res.user else res.user.model_dump()

# -------- profiles --------
@st.cache_data(ttl=60)
def list_profiles(user_id: str) -> List[str]:
    r = (
        get_client()
        .table("profiles")
        .select("name")
        .eq("user_id", user_id)
        .order("name")
        .execute()
    )
    return [row["name"] for row in (r.data or [])]

@st.cache_data(ttl=60)
def load_profile(user_id: str, name: str) -> Dict[str, Any]:
    # tolerate 0 rows (first-time users)
    r = (
        get_client()
        .table("profiles")
        .select("data")
        .eq("user_id", user_id)
        .eq("name", name)
        .limit(1)
        .execute()
    )
    rows = r.data or []
    return rows[0]["data"] if rows else {}

def upsert_profile(user_id: str, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    r = (
        get_client()
        .table("profiles")
        .upsert(
            {"user_id": user_id, "name": name, "data": data},
            on_conflict="user_id,name",
            returning="representation"  # supabase-py v2: no .select() after upsert
        )
        .execute()
    )
    try:
        list_profiles.clear()  # type: ignore
        load_profile.clear()   # type: ignore
    except Exception:
        pass
    return (r.data or [{}])[0]

# -------- meal logs --------
@st.cache_data(ttl=60)
def load_day_log(user_id: str, day: date) -> List[Dict[str, Any]]:
    r = (
        get_client()
        .table("meal_logs")
        .select(
            "id, logged_date, recipe_id, name, meal_type, "
            "calories_kcal, protein_g, carbs_g, fat_g, fiber_g, sodium_mg, created_at"
        )
        .eq("user_id", user_id)
        .eq("logged_date", str(day))
        .order("created_at")
        .execute()
    )
    return r.data or []

def append_logged_meal(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    r = (
        get_client()
        .table("meal_logs")
        .insert({**payload, "user_id": user_id}, returning="representation")
        .execute()
    )
    try:
        load_day_log.clear()  # type: ignore
    except Exception:
        pass
    return (r.data or [{}])[0]

def remove_log_by_id(user_id: str, log_id: int) -> int:
    r = (
        get_client()
        .table("meal_logs")
        .delete()
        .eq("user_id", user_id)
        .eq("id", log_id)
        .execute()
    )
    try:
        load_day_log.clear()  # type: ignore
    except Exception:
        pass
    return r.count or 0

def clear_meal(user_id: str, day: date, meal_type: str) -> int:
    r = (
        get_client()
        .table("meal_logs")
        .delete()
        .eq("user_id", user_id)
        .eq("logged_date", str(day))
        .eq("meal_type", meal_type)
        .execute()
    )
    try:
        load_day_log.clear()  # type: ignore
    except Exception:
        pass
    return r.count or 0

# add this next to your other meal log helpers
def remove_log_by_recipe(user_id: str, day: date, recipe_id: str) -> int:
    r = (
        get_client()
        .table("meal_logs")
        .delete()
        .eq("user_id", user_id)
        .eq("logged_date", str(day))
        .eq("recipe_id", recipe_id)
        .execute()
    )
    try: load_day_log.clear()  # type: ignore
    except: pass
    return r.count or 0

# --- replace your current activities helpers with this set ---

from typing import List, Dict, Optional
from datetime import date

# list day activities
def activities_for_day(user_id: str, d: date) -> List[Dict]:
    r = (
        get_client()
        .table("activities")
        .select("*")
        .eq("user_id", user_id)
        .eq("d", d.isoformat())
        .order("created_at")
        .execute()
    )
    return r.data or []

# sum kcal for day
def sum_activity_kcal_for_day(user_id: str, d: date) -> float:
    rows = activities_for_day(user_id, d)
    return float(sum((r.get("calories") or 0) for r in rows))

# insert one activity
def insert_activity(
    user_id: str,
    d: date,
    kind: str,
    intensity: str = "Moderate",
    duration_min: Optional[int] = None,
    steps: Optional[int] = None,
    calories: Optional[float] = None,
    notes: Optional[str] = None,
):
    payload = {
        "user_id": user_id,          # user_id is UUID string; Postgres will accept cast
        "d": d.isoformat(),
        "kind": kind,
        "intensity": intensity,
        "duration_min": duration_min,
        "steps": steps,
        "calories": calories,
        "notes": notes,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    return get_client().table("activities").insert(payload).execute()
