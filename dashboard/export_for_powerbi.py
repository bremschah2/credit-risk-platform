"""
Exports DynamoDB data into a single flat, wide CSV file for Power BI --
one row per loan, with borrower info, payment status, and the latest
risk score all joined together.
"""

import os
import boto3
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION"))
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

OUTPUT_DIR = "exports"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "loans_flat.csv")


def scan_all_items():
    items = []
    response = table.scan()
    items.extend(response["Items"])
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response["Items"])
    return items


def main():
    print("Scanning DynamoDB table...")
    items = scan_all_items()
    print(f"Retrieved {len(items)} total items.")

    borrowers = {}
    loans = {}
    payment_statuses = {}
    risk_scores = {}

    for item in items:
        pk = item.get("PK", "")
        sk = item.get("SK", "")

        if pk.startswith("BORROWER#") and sk == "PROFILE":
            borrowers[pk.replace("BORROWER#", "")] = item

        elif pk.startswith("BORROWER#") and sk.startswith("LOAN#"):
            borrower_id = pk.replace("BORROWER#", "")
            loan_id = sk.replace("LOAN#", "")
            item["_borrower_id"] = borrower_id
            loans[loan_id] = item

        elif pk.startswith("LOAN#") and sk.startswith("PAYMENT#"):
            loan_id = pk.replace("LOAN#", "")
            if loan_id not in payment_statuses or sk > payment_statuses[loan_id]["_sk"]:
                item["_sk"] = sk
                payment_statuses[loan_id] = item

        elif pk.startswith("LOAN#") and sk.startswith("RISKSCORE#"):
            loan_id = pk.replace("LOAN#", "")
            if loan_id not in risk_scores or sk > risk_scores[loan_id]["_sk"]:
                item["_sk"] = sk
                risk_scores[loan_id] = item

    print(f"Borrowers: {len(borrowers)} | Loans: {len(loans)} | "
          f"Payment statuses: {len(payment_statuses)} | Risk scores: {len(risk_scores)}")

    rows = []
    for loan_id, loan in loans.items():
        borrower_id = loan["_borrower_id"]
        borrower = borrowers.get(borrower_id, {})
        payment = payment_statuses.get(loan_id, {})
        risk = risk_scores.get(loan_id, {})

        rows.append({
            "loan_id": loan_id,
            "borrower_id": borrower_id,
            "loan_amount": float(loan.get("loan_amount", 0)),
            "interest_rate": float(loan.get("interest_rate", 0)),
            "term_months": int(loan.get("term_months", 0)),
            "grade": loan.get("grade", ""),
            "sub_grade": loan.get("sub_grade", ""),
            "purpose": loan.get("purpose", ""),
            "issue_date": loan.get("issue_date", ""),
            "annual_income": float(borrower.get("annual_income", 0)),
            "dti_ratio": float(borrower.get("dti_ratio", 0)),
            "home_ownership": borrower.get("home_ownership", ""),
            "employment_length": borrower.get("employment_length", ""),
            "current_status": payment.get("current_status", "Unknown"),
            "days_past_due": int(payment.get("days_past_due", 0)),
            "probability_default": float(risk.get("probability_default", 0)) if risk else None,
            "expected_loss": float(risk.get("expected_loss", 0)) if risk else None,
            "model_version": risk.get("model_version", ""),
            "risk_score_date": risk.get("_sk", "").replace("RISKSCORE#", "") if risk else "",
        })

    df = pd.DataFrame(rows)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"\nExported {len(df)} loans to {OUTPUT_PATH}")
    print(f"Loans with a risk score: {df['probability_default'].notna().sum()}")
    print(f"Loans missing a risk score: {df['probability_default'].isna().sum()}")


if __name__ == "__main__":
    main()