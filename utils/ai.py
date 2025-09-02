# utils/ai.py
import json, os
import streamlit as st

def _model_name():
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def call_llm(messages, temperature=0.6, max_tokens=900):
    """Minimal OpenAI Chat Completions wrapper. Expects OPENAI_API_KEY in env.
       Returns string content. Falls back to a stub if no key is present."""
    
    OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

    api_key = OPENAI_API_KEY

    if not api_key:
        # --- fallback stub for dev ---
        return json.dumps({
            "title": "Chickpea–Tomato Skillet with Spinach",
            "servings": 2,
            "cuisine": "Mediterranean",
            "med_tags": ["olive_oil","legumes","vegetables","whole_grains(optional)"],
            "ingredients": [
                {"item":"olive oil","qty":1.5,"unit":"tbsp"},
                {"item":"onion","qty":0.5,"unit":"medium"},
                {"item":"garlic","qty":2,"unit":"clove"},
                {"item":"chickpeas (cooked)","qty":240,"unit":"g"},
                {"item":"tomato passata","qty":200,"unit":"g"},
                {"item":"baby spinach","qty":80,"unit":"g"},
                {"item":"lemon","qty":0.5,"unit":"unit"},
                {"item":"oregano","qty":0.5,"unit":"tsp"},
                {"item":"black pepper","qty":0.25,"unit":"tsp"},
                {"item":"salt","qty":0.25,"unit":"tsp"}
            ],
            "steps":[
                "Sauté onion in olive oil 3–4 min; add garlic 30 s.",
                "Stir in chickpeas, passata, oregano; simmer 7–8 min.",
                "Fold in spinach to wilt; season with pepper, a pinch of salt; finish with lemon."
            ],
            "nutrition": {
                "calories_kcal": 480, "protein_g": 20, "carbs_g": 50,
                "fat_g": 18, "fiber_g": 14, "sodium_mg": 520
            },
            "rationale":"Legumes + vegetables + EVOO; moderate sodium; plant protein."
        })
    # --- real call ---
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=_model_name(),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "text"}
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return json.dumps({"error": str(e)})
