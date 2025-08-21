# MedDiet4All — Food Recommender & Coach

A Streamlit, multi‑page Mediterranean‑diet app that helps you plan meals, log what you ate, check daily adherence, get AI‑powered coaching, and **compose new recipes** that respect your profile (diet style, health flags, calorie targets, pantry).

> **Heads‑up on secrets:** Keep your OpenAI key **out of the repo**. Use Streamlit **Secrets Manager** (cloud) and a local `.streamlit/secrets.toml` that’s ignored by git. See **[Secrets & Security](#secrets--security)**.

---

## Features

- **Rule‑based recommender** (kcal fit, diet style, avoids & prefers, health modifiers)
- **Daily logging** with per‑meal targets & **adherence rings**
- **AI Coach** (LLM) gives plain‑English feedback and concrete swaps
- **Recipe Composer (AI + rules)**: coherent, MedDiet‑aligned recipes; auto‑critique with your rules; one‑click tweaks; log to today
- Optional **ML re‑scorer** (RandomForest) + **evaluation (R² / MAE / RMSE)** via a debug page
- Clean, modern UI with compact recipe cards and rationale lines

---

## Quick Start

```bash
# 1) Python 3.10+ recommended
python -V

# 2) Create & activate a virtual environment
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 3) Install deps
pip install -U pip
pip install streamlit pandas numpy scikit-learn openai

# 4) (Optional) Enable AI features
# Cloud: use Streamlit Secrets (see below)
# Local:
mkdir -p .streamlit
printf 'OPENAI_API_KEY = "sk-..."\nOPENAI_MODEL = "gpt-4o-mini"\n' > .streamlit/secrets.toml

# 5) Run the app
streamlit run Home.py
```

The app expects `meddiet_recipes.csv` and uses `meddiet_rules.py` in the repo root.

---

## App Structure

```
Home.py                         # Entry page (title + shared state)
1_Recommendations.py            # Rule-based recommendations (cards + log buttons)
2_Logged_Today.py               # Logged meals, per-meal kcal bands, macros/fiber/sodium
3_Coach_and_Insights.py         # AI Coach: day summary + actionable swaps
4_Recipe_Composer.py            # AI recipe composer + rule-based critique & fix
9_Debug_Context.py              # Debug/testing (can include ML evaluation page)
state.py                        # Session helpers (ensure keys, shared values)
ui.py                           # UI utilities (badges, bars, card rendering)
meddiet_rules.py                # Rule engine for fit scoring & adherence
meddiet_recipes.csv             # Recipe dataset (kcal, macros, tags/flags)

# (Convenience single-file app)
meddiet_recommender_app_with_coach_patch_2_bars.py
```

> If you want a single‑file experience:
>
> ```bash
> streamlit run meddiet_recommender_app_with_coach_patch_2_bars.py
> ```

---

## How It Works (Brief)

### Rule‑based scoring
Each recipe receives an overall **fit score** \[0–1] based on:
- **Calorie fit** to the meal’s target
- **Diet style**: vegan/vegetarian/pescatarian, gluten‑/dairy‑free
- **Avoids / Prefers**: ingredient checks
- **Health modifiers**: hypertension, diabetes/prediabetes, hyperlipidemia, celiac, GERD, autoimmune

These are implemented in `meddiet_rules.py` and reused by the coach & composer (for critique).

### AI Coach
Explains how your day aligns with targets, calls out kcal/macro/fiber/sodium issues, considers health flags, and offers **concrete swaps** (e.g., “Replace X with Y”). Requires `OPENAI_API_KEY`.

### Recipe Composer (AI + rules)
Generates a recipe conditioned on **meal type**, **calorie target**, **diet style**, **health flags**, and **pantry**. The result is auto‑**critiqued** with the rule engine; if needed, the app asks the model to **revise** once. You can **tweak** (e.g., “more protein”) and **log** the recipe to today.

### Optional ML re‑scorer
A small RandomForest trained on rule components + nutrients can be used to blend scores or just evaluated for R²/MAE/RMSE. The debug page shows cross‑validation metrics and feature importances.

---

## Secrets & Security

### Streamlit Cloud (recommended)
1. Open your deployed app → **⋯ → Settings → Secrets** and add:
   ```
   OPENAI_API_KEY = sk-xxxx
   OPENAI_MODEL   = gpt-4o-mini
   ```
2. In code, read secrets safely:
   ```python
   import os, streamlit as st
   OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
   OPENAI_MODEL   = st.secrets.get("OPENAI_MODEL")   or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
   ```
3. **Do not** commit `.streamlit/secrets.toml` to the repo. Cloud secrets are stored server‑side.

### Local dev
Create `.streamlit/secrets.toml` (ignored by git):
```toml
OPENAI_API_KEY = "sk-your-local-key"
OPENAI_MODEL   = "gpt-4o-mini"
```
Add to `.gitignore`:
```
.streamlit/secrets.toml
.env
```

### If a key leaked in git history
- **Rotate** the key (generate a new one; disable the old).  
- **Scrub history** so the old key isn’t recoverable:

**PowerShell (Windows):**
```powershell
@'
regex:sk-[A-Za-z0-9]{20,}==>sk-***REDACTED***
'@ | Set-Content -Encoding UTF8 .\replacements.txt

git filter-repo --force --replace-text .\replacements.txt
git push --force origin --all
git push --force origin --tags
```

**bash (macOS/Linux):**
```bash
printf 'regex:sk-[A-Za-z0-9]{20,}==>sk-***REDACTED***\n' > replacements.txt
git filter-repo --force --replace-text replacements.txt
git push -f origin --all && git push -f origin --tags
```

Notify collaborators to **re‑clone** (history was rewritten).

---

## Deployment on Streamlit Cloud

1. Push this repo to GitHub (no secrets committed).  
2. On share.streamlit.io, create a new app from your repo.  
3. In the app’s **Secrets**, add `OPENAI_API_KEY` and (optionally) `OPENAI_MODEL`.  
4. The app boots by running `Home.py`.

---

## Troubleshooting

- **Buttons look like they do nothing**: Streamlit re‑runs scripts on each click. We persist outputs in `st.session_state` and call `st.rerun()`; confirm your session keys exist (see `state.py`).  
- **Empty recommendations**: Filters too strict; relax diet style/avoid lists or switch meal type.  
- **No AI output**: Make sure `OPENAI_API_KEY` is available via secrets or env.  
- **Dataset schema**: Your CSV should include at least:  
  `recipe_id, name, meal_type, calories_kcal, protein_g, carbs_g, fat_g, fiber_g, sodium_mg, med_attributes, is_vegan, is_vegetarian, is_pescatarian, is_gluten_free, is_dairy_free, ingredients, instructions, cuisine`.

---

## Contributing

- Create a feature branch: `git checkout -b feature/ai-composer`  
- Commit small, focused changes with clear messages  
- Open a PR to `main`

---

## License

Choose a license (MIT/Apache‑2.0) before publishing publicly. For now, this is provided **as‑is** for research & prototyping.
