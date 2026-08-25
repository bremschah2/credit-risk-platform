"""
Final model: trains logistic regression and XGBoost on the larger
(~40,000 loan) dataset, using the 10-feature set selected via
permutation importance (features dropped: verification_status,
purpose, open_acc, pub_rec, interest_rate, revol_util -- all showed
importance indistinguishable from noise in the diagnostic run).

Saves the better-performing model to model.pkl, replacing the earlier
smaller-dataset version.
"""

import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    roc_auc_score, accuracy_score, precision_score,
    recall_score, confusion_matrix
)
from xgboost import XGBClassifier

DATA_PATH = "data/training_data_v2.csv"
MODEL_PATH = "model.pkl"

NUMERIC_FEATURES = [
    "term_months", "mort_acc", "dti", "annual_income",
    "loan_amount", "inq_last_6mths", "delinq_2yrs"
]
CATEGORICAL_FEATURES = ["sub_grade", "home_ownership", "employment_length"]


def build_preprocessor():
    return ColumnTransformer(transformers=[
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])


def evaluate(name, model, X_test, y_test):
    proba = model.predict_proba(X_test)[:, 1]
    preds = model.predict(X_test)

    auc = roc_auc_score(y_test, proba)
    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds)
    rec = recall_score(y_test, preds)
    cm = confusion_matrix(y_test, preds)

    print(f"\n=== {name} ===")
    print(f"ROC-AUC:   {auc:.4f}")
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f}")
    print("Confusion matrix (rows=actual, cols=predicted):")
    print(f"                Predicted: No-Default  Predicted: Default")
    print(f"Actual No-Default    {cm[0][0]:>10}          {cm[0][1]:>10}")
    print(f"Actual Default       {cm[1][0]:>10}          {cm[1][1]:>10}")

    return auc


def main():
    print(f"Loading {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} records.")

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df["default"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train set: {len(X_train)} loans | Test set: {len(X_test)} loans")
    print(f"Train default rate: {y_train.mean():.2%} | Test default rate: {y_test.mean():.2%}")

    preprocessor = build_preprocessor()

    # --- Logistic Regression ---
    logreg_pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced"))
    ])
    logreg_pipeline.fit(X_train, y_train)
    logreg_auc = evaluate("Logistic Regression (v2, larger data + pruned features)",
                           logreg_pipeline, X_test, y_test)

    # --- XGBoost ---
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    xgb_pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=42
        ))
    ])
    xgb_pipeline.fit(X_train, y_train)
    xgb_auc = evaluate("XGBoost (v2, larger data + pruned features)",
                        xgb_pipeline, X_test, y_test)

    print("\n" + "=" * 60)
    print("MODEL COMPARISON (v2)")
    print("=" * 60)
    print(f"Logistic Regression ROC-AUC: {logreg_auc:.4f}  (v1 baseline was 0.6904)")
    print(f"XGBoost ROC-AUC:             {xgb_auc:.4f}  (v1 baseline was 0.6707)")

    if xgb_auc >= logreg_auc:
        best_model, best_name, best_auc = xgb_pipeline, "xgboost_v2", xgb_auc
    else:
        best_model, best_name, best_auc = logreg_pipeline, "logreg_v2", logreg_auc

    print(f"\nSelected model: {best_name} (ROC-AUC: {best_auc:.4f})")

    joblib.dump({
        "model": best_model,
        "model_version": best_name,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
    }, MODEL_PATH)

    print(f"Saved model to {MODEL_PATH} (replaces the earlier v1 model)")


if __name__ == "__main__":
    main()