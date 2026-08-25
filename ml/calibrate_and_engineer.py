"""
Checks whether the model's predicted probabilities are well-calibrated
(i.e., among loans predicted at ~30% default risk, do roughly 30% of
them actually default?) -- distinct from ROC-AUC, which only measures
ranking, not the accuracy of the probability values themselves.

This matters specifically because expected loss = P(default) x exposure
x (1 - recovery rate) uses the raw probability directly, so a
miscalibrated model produces misleading dollar figures even if its
AUC/ranking is fine.

Also applies feature engineering (log-transform skewed numerics, adds
loan-to-income ratio) before checking calibration and applying
isotonic calibration if needed.
"""

import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import roc_auc_score, brier_score_loss

DATA_PATH = "data/training_data_v2.csv"
MODEL_PATH = "model.pkl"

CATEGORICAL_FEATURES = ["sub_grade", "home_ownership", "employment_length"]

ENGINEERED_NUMERIC = [
    "term_months", "mort_acc", "dti", "inq_last_6mths", "delinq_2yrs",
    "log_annual_income", "log_loan_amount", "loan_to_income_ratio"
]


def engineer_features(df):
    df = df.copy()
    df["log_annual_income"] = np.log1p(df["annual_income"])
    df["log_loan_amount"] = np.log1p(df["loan_amount"])
    df["loan_to_income_ratio"] = df["loan_amount"] / df["annual_income"].replace(0, 1)
    return df


def build_preprocessor():
    return ColumnTransformer(transformers=[
        ("num", StandardScaler(), ENGINEERED_NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])


def print_calibration_table(y_true, y_prob, label, n_bins=10):
    fraction_of_positives, mean_predicted_value = calibration_curve(
        y_true, y_prob, n_bins=n_bins, strategy="quantile"
    )
    print(f"\n--- Calibration check: {label} ---")
    print(f"{'Predicted avg':>15} {'Actual default rate':>22} {'Gap':>10}")
    for pred, actual in zip(mean_predicted_value, fraction_of_positives):
        gap = actual - pred
        flag = "  <-- off by 5+ pts" if abs(gap) > 0.05 else ""
        print(f"{pred:>15.3f} {actual:>22.3f} {gap:>+10.3f}{flag}")

    brier = brier_score_loss(y_true, y_prob)
    print(f"Brier score: {brier:.4f} (lower is better; 0 = perfect, 0.25 = naive baseline for ~20% base rate)")


def main():
    print(f"Loading {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH)
    df = engineer_features(df)

    X = df[ENGINEERED_NUMERIC + CATEGORICAL_FEATURES]
    y = df["default"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    preprocessor = build_preprocessor()

    # --- Uncalibrated model (with engineered features) ---
    base_pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced"))
    ])
    base_pipeline.fit(X_train, y_train)
    proba_uncalibrated = base_pipeline.predict_proba(X_test)[:, 1]

    auc = roc_auc_score(y_test, proba_uncalibrated)
    print(f"\nROC-AUC with engineered features: {auc:.4f}")
    print("(Compare to v2's 0.6954 -- this isolates the effect of feature engineering alone.)")
    print_calibration_table(y_test, proba_uncalibrated, "Uncalibrated (with engineered features)")

    # --- Calibrated model ---
    print("\nApplying isotonic calibration...")
    calibrated_pipeline = CalibratedClassifierCV(
        base_pipeline, method="isotonic", cv=5
    )
    calibrated_pipeline.fit(X_train, y_train)
    proba_calibrated = calibrated_pipeline.predict_proba(X_test)[:, 1]

    auc_calibrated = roc_auc_score(y_test, proba_calibrated)
    print(f"\nROC-AUC after calibration: {auc_calibrated:.4f} (ranking should stay similar)")
    print_calibration_table(y_test, proba_calibrated, "Calibrated (isotonic)")

    joblib.dump({
        "model": calibrated_pipeline,
        "model_version": "logreg_v3_calibrated",
        "numeric_features": ENGINEERED_NUMERIC,
        "categorical_features": CATEGORICAL_FEATURES,
        "feature_engineering": "log1p on income/loan_amount, loan_to_income_ratio added",
    }, MODEL_PATH)

    print(f"\nSaved calibrated model to {MODEL_PATH}")


if __name__ == "__main__":
    main()