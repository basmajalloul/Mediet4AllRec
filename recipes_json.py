import json
from supabase import create_client
import os
import streamlit as st

# --- connect to Supabase ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]  # or anon if you just read public data
supabase = create_client(url, key)

res = supabase.table("recipes").select("*").execute()
rows = res.data or []

with open("medchef_recipes_style.jsonl", "w", encoding="utf-8") as f:
    for r in rows:
        meal = r.get("meal_type", "Meal")
        cuisine = r.get("cuisine", "Mediterranean")
        title = r.get("name", "Recipe")
        ingredients = r.get("ingredients", "")
        instructions = r.get("instructions", "")
        servings = r.get("servings", "")
        kcal = r.get("calories_kcal", "")

        assistant_reply = f"""Title: {title}
Cuisine: {cuisine}
Servings: {servings}
Calories: {kcal} kcal
Ingredients:
{ingredients}
Instructions:
{instructions}
"""

        user_prompt = f"Give me a {meal.lower()} recipe from {cuisine} that fits the Mediterranean Diet."

        ex = {
            "messages": [
                {"role": "system", "content": "You are MedChef, an expert in authentic Mediterranean cooking. Avoid repetitive ingredients, always cook legumes properly, and emphasize balance and realism."},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_reply}
            ]
        }
        f.write(json.dumps(ex, ensure_ascii=False) + "\n")

print("✅ Exported", len(rows), "recipes → medchef_recipes_style.jsonl")
