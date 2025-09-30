# utils/ml.py
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import RandomForestRegressor

from meddiet_rules import compute_meal_fit_score


# ---------- Embedding index (TF-IDF + SVD + nutrients) ----------
@st.cache_resource(show_spinner=False)
def build_recipe_index(df: pd.DataFrame):
    # 0) Early exit on empty DF
    if df is None or len(df) == 0:
        return {"emb": np.zeros((0, 8), dtype=np.float32), "rid2pos": {}}

    # 1) Build text exactly once (coerce to str)
    text = (
        df.get("ingredients", "").fillna("").astype(str) + " " +
        df.get("med_attributes", "").fillna("").astype(str) + " " +
        df.get("cuisine", "").fillna("").astype(str) + " " +
        df.get("diet_tags", "").fillna("").astype(str)
    ).str.lower().str.replace(r"\s+", " ", regex=True)

    # 2) Numeric features (always available)
    num_cols = ["calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sodium_mg"]
    X_num = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).to_numpy(dtype=np.float32)
    # normalize rows
    Xn = X_num / (np.linalg.norm(X_num, axis=1, keepdims=True) + 1e-8)

    # 3) Try TF-IDF text → SVD; relax min_df if needed
    X_text_lat = None
    nonempty = text.str.strip().str.len() > 0
    docs = text[nonempty].tolist()
    try:
        if len(docs) > 0:
            # pick min_df so we always get a vocabulary
            # (at least 1% of docs, but ≥1 and ≤5)
            md = max(1, min(5, int(round(0.01 * len(docs)))))
            tfidf = TfidfVectorizer(
                stop_words="english",
                min_df=md,
                max_df=0.9,
                ngram_range=(1, 2),
                token_pattern=r"(?u)\b\w\w+\b"   # words with ≥2 letters
            )
            X = tfidf.fit_transform(docs)
            # guard against tiny vocab
            n_comp = int(min(64, max(2, X.shape[1]-1)))
            if n_comp >= 2:
                svd = TruncatedSVD(n_components=n_comp, random_state=3)
                X_text_lat = svd.fit_transform(X).astype(np.float32)
    except Exception:
        X_text_lat = None

    # 4) Combine (fallback to numeric-only if needed)
    if X_text_lat is None:
        X = Xn
    else:
        # pad rows that were empty docs with zeros so shapes align
        out = np.zeros((len(df), X_text_lat.shape[1]), dtype=np.float32)
        out[nonempty.values, :] = X_text_lat
        Xt = out / (np.linalg.norm(out, axis=1, keepdims=True) + 1e-8)
        X = np.hstack([Xt, Xn])

    # final row-norm
    X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-8)

    rid2pos = {rid: i for i, rid in enumerate(df["recipe_id"].astype(str).tolist())}
    return {"emb": X, "rid2pos": rid2pos}

# ---------- Train a tiny learned re-scorer over rule features ----------
@st.cache_resource(show_spinner=False)
def train_rescorer(df: pd.DataFrame, per_meal_target: dict, diet_prefs: dict, health: dict):
    FEATS = ["fit_diet_style","fit_no_avoids","fit_prefer_bonus","fit_health_mod",
             "protein_g","carbs_g","fat_g","fiber_g","sodium_mg"]
    df_all = df.copy()
    cal_list=diet_list=avoids_list=prefer_list=health_list=score_list=[]

    cal_list, diet_list, avoids_list, prefer_list, health_list, score_list = [], [], [], [], [], []
    for _, row in df_all.iterrows():
        meal = str(row["meal_type"])
        kcal_tgt = int(per_meal_target.get(meal, per_meal_target.get("Lunch", 600)))
        s, dbg = compute_meal_fit_score(row, kcal_tgt, diet_prefs, health)
        score_list.append(s)
        cal_list.append(dbg["cal_term"]); diet_list.append(dbg["diet_term"])
        avoids_list.append(dbg["avoid_term"]); prefer_list.append(dbg["prefer_term"])
        health_list.append(dbg["health_mod"])

    df_all["fit_score"]        = score_list
    df_all["fit_diet_style"]   = diet_list
    df_all["fit_no_avoids"]    = avoids_list
    df_all["fit_prefer_bonus"] = prefer_list
    df_all["fit_health_mod"]   = health_list

    X = df_all[FEATS].fillna(0.0).astype(float).values
    y = df_all["fit_score"].fillna(0.0).astype(float).values

    model = RandomForestRegressor(n_estimators=200, max_depth=6, random_state=3)
    model.fit(X, y)
    return model

def apply_rescorer_blend(df_in: pd.DataFrame, model, alpha: float = 0.6):
    FEATS = ["fit_diet_style","fit_no_avoids","fit_prefer_bonus","fit_health_mod",
             "protein_g","carbs_g","fat_g","fiber_g","sodium_mg"]
    X = df_in[FEATS].fillna(0.0).astype(float).values
    out = df_in.copy()
    out["fit_learned"] = model.predict(X)
    base = out.get("fit_score", pd.Series(np.zeros(len(out)), index=out.index)).astype(float)
    out["fit_blend"] = alpha*out["fit_learned"] + (1-alpha)*base
    return out

# ---------- Diversity MMR ----------
def mmr_rerank(candidates_df: pd.DataFrame, embed_matrix: np.ndarray, k=6, lambda_tradeoff=0.8, rel_col="fit_blend"):
    chosen, remaining = [], list(range(len(candidates_df)))
    rel = candidates_df[rel_col].to_numpy().astype(float)
    E = embed_matrix
    while remaining and len(chosen) < k:
        if not chosen:
            j = int(max(remaining, key=lambda i: rel[i]))
        else:
            sims = cosine_similarity(E[remaining], E[chosen]).max(axis=1)
            mmr = lambda_tradeoff * rel[remaining] - (1 - lambda_tradeoff) * sims
            j = remaining[int(np.argmax(mmr))]
        chosen.append(j); remaining.remove(j)
    return candidates_df.iloc[chosen]

# ---------- Day optimizer (auto-pick) ----------
from itertools import product
def optimize_day(dfB, dfL, dfD, dfS, targets, budget=None):
    N = 10
    sets = [dfB.head(N), dfL.head(N), dfD.head(N), dfS.head(N)]
    best_ids, best_obj = None, 1e9
    for i, j, k, l in product(*[range(len(s)) for s in sets]):
        picks = [sets[0].iloc[i], sets[1].iloc[j], sets[2].iloc[k], sets[3].iloc[l]]
        tot = {
            "cal": sum(float(p["calories_kcal"]) for p in picks),
            "p":   sum(float(p["protein_g"])      for p in picks),
            "c":   sum(float(p["carbs_g"])        for p in picks),
            "f":   sum(float(p["fat_g"])          for p in picks),
        }
        if budget is not None and "cost_eur" in sets[0].columns:
            if sum(float(p["cost_eur"]) for p in picks) > budget:
                continue
        obj = (abs(tot["cal"]-targets["kcal"]) +
               4*abs(tot["p"]-targets["protein_g"]) +
               2*abs(tot["c"]-targets["carb_g"]) +
               2*abs(tot["f"]-targets["fat_g"]))
        if obj < best_obj:
            best_obj, best_ids = obj, [p["recipe_id"] for p in picks]
    return best_ids or []
