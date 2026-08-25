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

DATA_PATH = "training_data.csv"
MODEL_PATH = "model.pkl"

NUMERIC_FEATURES = ["loan_amount", "interest_rate", "term_months", "annual_income", "dti_ratio"]
CATEGORICAL_FEATURES = ["grade", "purpose", "home_ownership", "employment_length"]


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
    print(f"Loaded {len(df)} total records.")

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df["default"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train set: {len(X_train)} loans | Test set: {len(X_test)} loans")
    print(f"Train default rate: {y_train.mean():.2%} | Test default rate: {y_test.mean():.2%}")

    preprocessor = build_preprocessor()

    logreg_pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced"))
    ])
    logreg_pipeline.fit(X_train, y_train)
    logreg_auc = evaluate("Logistic Regression (baseline)", logreg_pipeline, X_test, y_test)

    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    xgb_pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.1,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=42
        ))
    ])
    xgb_pipeline.fit(X_train, y_train)
    xgb_auc = evaluate("XGBoost", xgb_pipeline, X_test, y_test)

    print("\n" + "=" * 50)
    print("MODEL COMPARISON")
    print("=" * 50)
    print(f"Logistic Regression ROC-AUC: {logreg_auc:.4f}")
    print(f"XGBoost ROC-AUC:             {xgb_auc:.4f}")

    if xgb_auc >= logreg_auc:
        best_model, best_name, best_auc = xgb_pipeline, "xgboost_v1", xgb_auc
    else:
        best_model, best_name, best_auc = logreg_pipeline, "logreg_v1", logreg_auc

    print(f"\nSelected model: {best_name} (ROC-AUC: {best_auc:.4f})")

    joblib.dump({
        "model": best_model,
        "model_version": best_name,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
    }, MODEL_PATH)

    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()