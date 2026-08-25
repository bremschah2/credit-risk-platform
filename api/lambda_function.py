"""
Lambda handler for real-time credit risk scoring.
Expects a JSON POST body with loan/borrower features and returns
a probability of default plus expected loss.
"""

import json
import joblib
import numpy as np
import pandas as pd

MODEL_PATH = "model.pkl"
RECOVERY_RATE = 0.35

bundle = joblib.load(MODEL_PATH)
model = bundle["model"]
model_version = bundle["model_version"]
numeric_features = bundle["numeric_features"]
categorical_features = bundle["categorical_features"]


def engineer_features(data):
    annual_income = float(data.get("annual_income", 0))
    loan_amount = float(data.get("loan_amount", 0))
    return {
        "term_months": int(data.get("term_months", 36)),
        "mort_acc": float(data.get("mort_acc", 0)),
        "dti": float(data.get("dti", 0)),
        "inq_last_6mths": float(data.get("inq_last_6mths", 0)),
        "delinq_2yrs": float(data.get("delinq_2yrs", 0)),
        "log_annual_income": np.log1p(annual_income),
        "log_loan_amount": np.log1p(loan_amount),
        "loan_to_income_ratio": loan_amount / annual_income if annual_income > 0 else 0,
        "sub_grade": data.get("sub_grade", "C1"),
        "home_ownership": data.get("home_ownership", "RENT"),
        "employment_length": data.get("employment_length", "Unknown"),
        "loan_amount": loan_amount,
    }


def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event

        features = engineer_features(body)
        X = pd.DataFrame([features])[numeric_features + categorical_features]

        probability = float(model.predict_proba(X)[:, 1][0])
        exposure = features["loan_amount"]
        expected_loss = probability * exposure * (1 - RECOVERY_RATE)

        result = {
            "probability_default": round(probability, 4),
            "expected_loss": round(expected_loss, 2),
            "exposure": exposure,
            "recovery_rate_assumption": RECOVERY_RATE,
            "model_version": model_version,
        }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result),
        }

    except Exception as e:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)}),
        }