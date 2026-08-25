"""
Extracts training data by scanning DynamoDB and joining borrower profile,
loan, and payment status items back together.

Label definition:
    default = 1  if loan_status == "Charged Off"
    default = 0  if loan_status == "Fully Paid"
    (all other statuses -- Current, Late, In Grace Period, etc. -- are
    excluded from training since their outcome isn't resolved yet)

Output: ml/data/training_data.csv
"""

import os
import boto3
import pandas as pd
from dotenv import load_dotenv
from boto3.dynamodb.conditions import Key

load_dotenv()

dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION"))
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

OUTPUT_DIR = "data"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "training_data.csv")

RESOLVED_STATUSES = {
    "Charged Off": 1,
    "Fully Paid": 0,
}


def scan_all_items():
    """Scans the full table, handling pagination."""
    items = []
    response = table.scan()
    items.extend(response["Items"])

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response["Items"])

    return items


def extract():
    print("Scanning DynamoDB table (this may take a minute for ~13,000 records)...")
    items = scan_all_items()
    print(f"Retrieved {len(items)} total items from the table.")

    borrowers = {}   # borrower_id -> profile attributes
    loans = {}       # loan_id -> loan attributes (+ borrower_id)
    payment_statuses = {}  # loan_id -> most recent payment status attributes

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
            loans[loan_id] = item

        elif pk.startswith("LOAN#") and sk.startswith("PAYMENT#"):
            loan_id = pk.replace("LOAN#", "")
            # if multiple payment records exist per loan, keep the latest by SK
            if loan_id not in payment_statuses or sk > payment_statuses[loan_id]["SK"]:
                payment_statuses[loan_id] = item

    print(f"Reconstructed: {len(borrowers)} borrowers, {len(loans)} loans, "
          f"{len(payment_statuses)} payment status records.")

    rows = []
    skipped_unresolved = 0
    skipped_missing = 0

    for loan_id, loan in loans.items():
        borrower_id = loan["_borrower_id"]
        borrower = borrowers.get(borrower_id)
        payment = payment_statuses.get(loan_id)

        if not borrower or not payment:
            skipped_missing += 1
            continue

        status = payment.get("current_status", "")
        if status not in RESOLVED_STATUSES:
            skipped_unresolved += 1
            continue

        rows.append({
            "loan_id": loan_id,
            "loan_amount": float(loan.get("loan_amount", 0)),
            "interest_rate": float(loan.get("interest_rate", 0)),
            "term_months": int(loan.get("term_months", 36)),
            "grade": loan.get("grade", "Unknown"),
            "purpose": loan.get("purpose", "other"),
            "annual_income": float(borrower.get("annual_income", 0)),
            "dti_ratio": float(borrower.get("dti_ratio", 0)),
            "home_ownership": borrower.get("home_ownership", "Unknown"),
            "employment_length": borrower.get("employment_length", "Unknown"),
            "default": RESOLVED_STATUSES[status],
        })

    df = pd.DataFrame(rows)

    print(f"\nSkipped {skipped_unresolved} loans with unresolved status "
          f"(Current/Late/etc. -- not usable for training).")
    print(f"Skipped {skipped_missing} loans with missing borrower or payment data.")
    print(f"\nFinal training dataset: {len(df)} resolved loans.")
    print(f"Default rate: {df['default'].mean():.2%}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    extract()