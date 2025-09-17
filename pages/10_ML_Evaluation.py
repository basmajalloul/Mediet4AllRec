# pages/9_ML_Evaluation.py
import streamlit as st
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold, cross_val_score
from utils.state import ensure_session_keys
from meddiet_rules import compute_meal_fit_score

st.set_page_config(page_title="ML Evaluation", layout="wide")
ensure_session_keys()

from utils.auth_ui import auth_gate
user = auth_gate()
user_id = user["id"]
st.session_state["__user_id__"] = user["id"]

st.title("🔬 ML Regressor Evaluation")

df = st.session_state["df"]
st.caption(f"{len(df)} recipes in current dataset")

# Use the same targets & constraints you’re using right now in the app’s sidebar
daily  = st.session_state.get("__daily__", 2000)
per_meal = st.session_state.get("__per_meal__", {"Breakfast":400,"Lunch":700,"Dinner":700,"Snack":200})

diet_prefs = st.session_state.get("__diet_prefs__", {
    "vegan": False, "vegetarian": False, "pescatarian": False,
    "gluten_free": False, "dairy_free": False,
    "prefer_ingredients": "olive oil, chickpeas",
    "avoid_ingredients": "anchovies"
})
health = st.session_state.get("__health__", {
    "hypertension": False, "diabetes": False, "prediabetes": False,
    "hyperlipidemia": False, "celiac": False, "gerd": False, "autoimmune": False
})

# 1) Recompute the *rule* features for every row (exactly what recommend(...) uses)
rows = []
for _, row in df.iterrows():
    meal = str(row["meal_type"])
    kcal_tgt = int(per_meal.get(meal, per_meal.get("Lunch", 600)))
    s, dbg = compute_meal_fit_score(row, kcal_tgt, diet_prefs, health)
    rows.append({
        "fit_score": float(s),
        "fit_calorie": float(dbg["cal_term"]),
        "fit_diet_style": float(dbg["diet_term"]),
        "fit_no_avoids": float(dbg["avoid_term"]),
        "fit_prefer_bonus": float(dbg["prefer_term"]),
        "fit_health_mod": float(dbg["health_mod"]),
        "protein_g": float(row.get("protein_g", 0.0)),
        "carbs_g": float(row.get("carbs_g", 0.0)),
        "fat_g": float(row.get("fat_g", 0.0)),
        "fiber_g": float(row.get("fiber_g", 0.0)),
        "sodium_mg": float(row.get("sodium_mg", 0.0)),
    })
feats = pd.DataFrame(rows)

FEATS = [
    "fit_calorie","fit_diet_style","fit_no_avoids",
    "fit_prefer_bonus","fit_health_mod",
    "protein_g","carbs_g","fat_g","fiber_g","sodium_mg"
]
X = feats[FEATS].values
y = feats["fit_score"].values

# 2) 5-fold CV on the RF regressor (same shape as in your ML build)
rf = RandomForestRegressor(n_estimators=250, max_depth=6, random_state=42)
cv = KFold(n_splits=5, shuffle=True, random_state=42)
r2      = cross_val_score(rf, X, y, cv=cv, scoring="r2")
neg_mae = cross_val_score(rf, X, y, cv=cv, scoring="neg_mean_absolute_error")
neg_rmse= cross_val_score(rf, X, y, cv=cv, scoring="neg_root_mean_squared_error")

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("R² (mean ± sd)", f"{r2.mean():.3f}", f"±{r2.std():.3f}")
with c2:
    st.metric("MAE (mean ± sd)", f"{(-neg_mae).mean():.4f}", f"±{(-neg_mae).std():.4f}")
with c3:
    st.metric("RMSE (mean ± sd)", f"{(-neg_rmse).mean():.4f}", f"±{(-neg_rmse).std():.4f}")

with st.expander("Fold-by-fold scores"):
    per_fold = pd.DataFrame({
        "Fold": np.arange(1, 6),
        "R2": r2,
        "MAE": -neg_mae,
        "RMSE": -neg_rmse
    })
    st.dataframe(per_fold, use_container_width=True)

# 3) Fit once on all data to show feature importances
rf.fit(X, y)
imp = pd.DataFrame({"feature": FEATS, "importance": rf.feature_importances_})\
        .sort_values("importance", ascending=False)
st.subheader("Feature importances")
st.bar_chart(imp.set_index("feature"))

# 4) Optional: quick sanity check plot of predicted vs. rule target
pred = rf.predict(X)
scat = pd.DataFrame({"RuleFit(y)": y, "ModelPred": pred})
with st.expander("Predicted vs. rule fit (sanity check)"):
    st.scatter_chart(scat)

st.caption("Notes: This evaluates how well the learned model re-weights the rule+nutrient features. "
           "For true user-centric eval (e.g., satisfaction), you’d need labeled outcomes.")
