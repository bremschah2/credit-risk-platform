"""
Step 1 of the improved model: train with ALL candidate features, then
run permutation importance to see what actually earns its place.

This does NOT save a final model -- it's a diagnostic run. Once we see
the importance rankings, we'll decide together what to keep and train
the real final model in a follow-up script.
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.inspection import permutation_importance

DATA_PATH = "data/training_data_v2.csv"

NUMERIC_FEATURES = [
    "loan_amount", "interest_rate", "term_months", "annual_income", "dti",
    "delinq_2yrs", "inq_last_6mths", "open_acc", "pub_rec",
    "revol_util", "mort_acc"
]
CATEGORICAL_FEATURES = [
    "sub_grade", "purpose", "home_ownership",
    "employment_length", "verification_status"
]


def main():
    print(f"Loading {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} records.")

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df["default"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    preprocessor = ColumnTransformer(transformers=[
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])

    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced"))
    ])

    print("Training kitchen-sink model (all candidate features)...")
    pipeline.fit(X_train, y_train)

    proba = pipeline.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, proba)
    print(f"\nKitchen-sink model ROC-AUC: {auc:.4f}")
    print("(Compare this to the earlier 0.6904 baseline with the smaller feature set.)")

    print("\nComputing permutation importance (this takes a minute -- "
          "it re-evaluates the model many times with each feature shuffled)...")

    result = permutation_importance(
        pipeline, X_test, y_test,
        n_repeats=10, random_state=42, scoring="roc_auc", n_jobs=-1
    )

    importance_df = pd.DataFrame({
        "feature": X_test.columns,
        "importance_mean": result.importances_mean,
        "importance_std": result.importances_std,
    }).sort_values("importance_mean", ascending=False)

    print("\n=== PERMUTATION IMPORTANCE (drop in ROC-AUC when feature is shuffled) ===")
    print(importance_df.to_string(index=False))

    importance_df.to_csv("data/feature_importance.csv", index=False)
    print("\nSaved to data/feature_importance.csv")


if __name__ == "__main__":
    main()