"""
Scores every loan in DynamoDB with the trained model, calculates expected
loss, and writes the results back as risk_score items -- closing the loop
on the original schema design.

Expected Loss = P(default) x Exposure x (1 - Recovery Rate)

Recovery rate assumption: 35%, a commonly cited industry-typical figure
for unsecured personal loans.
"""

import os
import boto3
import joblib
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import date
from dotenv import load_dotenv

load_dotenv()

dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION"))
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

MODEL_PATH = "model.pkl"
RECOVERY_RATE = 0.35
TODAY = date.today().isoformat()


def scan_all_items():
    items = []
    response = table.scan()
    items.extend(response["Items"])
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response["Items"])
    return items


def reconstruct_loans_and_borrowers(items):
    borrowers = {}
    loans = {}

    for item in items:
        pk = item.get("PK", "")
        sk = item.get("SK", "")

        if pk.startswith("BORROWER#") and sk == "PROFILE":
            borrower_id = pk.replace("BORROWER#", "")
            borrowers[borrower_id] = item

        elif pk.startswith("BORROWER#") and sk.startswith("LOAN#"):
            borrower_id = pk.replace("BORROWER#", "")
            loan_id = sk.replace("LOAN#", "")
            item["_borrower_id"] = borrower_id
            item["_loan_id"] = loan_id
            loans[loan_id] = item

    return borrowers, loans


def main():
    print("Loading trained model...")
    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]
    model_version = bundle["model_version"]
    numeric_features = bundle["numeric_features"]
    categorical_features = bundle["categorical_features"]

    print("Scanning DynamoDB for all loans...")
    items = scan_all_items()
    borrowers, loans = reconstruct_loans_and_borrowers(items)
    print(f"Found {len(loans)} loans to score.")

    rows = []
    loan_ids = []
    for loan_id, loan in loans.items():
        borrower_id = loan["_borrower_id"]
        borrower = borrowers.get(borrower_id)
        if not borrower:
            continue

        loan_amount = float(loan.get("loan_amount", 0))
        annual_income = float(borrower.get("annual_income", 0))

        rows.append({
            "loan_amount": loan_amount,
            "term_months": int(loan.get("term_months", 36)),
            "grade": loan.get("grade", "Unknown"),
            "sub_grade": loan.get("sub_grade", "Unknown"),
            "purpose": loan.get("purpose", "other"),
            "annual_income": annual_income,
            "dti": float(borrower.get("dti_ratio", 0)),
            "mort_acc": 0,
            "inq_last_6mths": 0,
            "delinq_2yrs": 0,
            "home_ownership": borrower.get("home_ownership", "Unknown"),
            "employment_length": borrower.get("employment_length", "Unknown"),
            "log_annual_income": np.log1p(annual_income),
            "log_loan_amount": np.log1p(loan_amount),
            "loan_to_income_ratio": loan_amount / annual_income if annual_income > 0 else 0,
        })
        loan_ids.append(loan_id)

    X = pd.DataFrame(rows)[numeric_features + categorical_features]

    print("Scoring all loans...")
    probabilities = model.predict_proba(X)[:, 1]

    print("Writing risk scores back to DynamoDB...")
    with table.batch_writer() as writer:
        for loan_id, prob, row in zip(loan_ids, probabilities, rows):
            exposure = row["loan_amount"]
            expected_loss = prob * exposure * (1 - RECOVERY_RATE)

            writer.put_item(Item={
                "PK": f"LOAN#{loan_id}",
                "SK": f"RISKSCORE#{TODAY}",
                "probability_default": Decimal(str(round(prob, 4))),
                "expected_loss": Decimal(str(round(expected_loss, 2))),
                "model_version": model_version,
            })

    total_expected_loss = sum(
        p * r["loan_amount"] * (1 - RECOVERY_RATE)
        for p, r in zip(probabilities, rows)
    )
    total_exposure = sum(r["loan_amount"] for r in rows)

    print(f"\nScored {len(loan_ids)} loans.")
    print(f"Total exposure (sum of loan amounts): ${total_exposure:,.2f}")
    print(f"Total expected loss across portfolio: ${total_expected_loss:,.2f}")
    print(f"Portfolio-level expected loss rate: {total_expected_loss/total_exposure:.2%}")
    print(f"(Recovery rate assumption used: {RECOVERY_RATE:.0%})")


if __name__ == "__main__":
    main()