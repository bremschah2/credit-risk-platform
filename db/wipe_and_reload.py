"""
Wipes all items from credit_risk_table, then reloads the same ~10,000-row
stratified sample as the original Phase 1 load -- this time capturing
sub_grade, and using batch_writer for speed (the original took an hour
writing one item at a time; this should take a few minutes).
"""

import os
import re
import boto3
import pandas as pd
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION"))
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

RAW_PATH = "../data/raw/loan.csv"
SAMPLE_SIZE = 10000

COLUMNS_NEEDED = [
    "loan_amnt", "term", "int_rate", "grade", "sub_grade",
    "home_ownership", "annual_inc", "issue_d", "purpose", "dti",
    "loan_status", "emp_length"
]


def wipe_table():
    print("Scanning table to find all items to delete...")
    items = []
    response = table.scan(ProjectionExpression="PK, SK")
    items.extend(response["Items"])
    while "LastEvaluatedKey" in response:
        response = table.scan(ProjectionExpression="PK, SK", ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response["Items"])

    print(f"Found {len(items)} items. Deleting...")
    with table.batch_writer() as writer:
        for item in items:
            writer.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
    print("Table wiped.")


def parse_term(term_str):
    if pd.isna(term_str):
        return None
    match = re.search(r"(\d+)", str(term_str))
    return int(match.group(1)) if match else None


def parse_issue_date(issue_d_str):
    if pd.isna(issue_d_str):
        return None
    try:
        dt = pd.to_datetime(issue_d_str, format="%b-%Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


def parse_days_past_due(loan_status_str):
    if pd.isna(loan_status_str):
        return 0
    match = re.search(r"\((\d+)-(\d+) days\)", str(loan_status_str))
    if match:
        return int(match.group(2))
    return 0


def reload_sample():
    print(f"Reading and sampling {SAMPLE_SIZE} rows from {RAW_PATH}...")
    df = pd.read_csv(RAW_PATH, usecols=COLUMNS_NEEDED, low_memory=False)
    df = df.dropna(subset=["loan_amnt", "int_rate", "grade", "issue_d", "loan_status"])

    total = len(df)
    samples = []
    for g in df["grade"].unique():
        sub = df[df["grade"] == g]
        n = min(len(sub), max(1, int(SAMPLE_SIZE * len(sub) / total)))
        samples.append(sub.sample(n=n, random_state=42))
    sample = pd.concat(samples)

    print(f"Sampled {len(sample)} rows. Writing to DynamoDB (via batch_writer)...")

    borrower_id_counter = 1
    loan_id_counter = 1

    with table.batch_writer() as writer:
        for _, row in sample.iterrows():
            borrower_id = str(borrower_id_counter)
            loan_id = str(loan_id_counter)
            emp_length = row["emp_length"] if pd.notna(row["emp_length"]) else "Unknown"

            writer.put_item(Item={
                "PK": f"BORROWER#{borrower_id}",
                "SK": "PROFILE",
                "annual_income": Decimal(str(row["annual_inc"])) if pd.notna(row["annual_inc"]) else Decimal("0"),
                "employment_length": emp_length,
                "home_ownership": row["home_ownership"] if pd.notna(row["home_ownership"]) else "Unknown",
                "dti_ratio": Decimal(str(row["dti"])) if pd.notna(row["dti"]) else Decimal("0"),
                "credit_score_band": "N/A",
            })

            writer.put_item(Item={
                "PK": f"BORROWER#{borrower_id}",
                "SK": f"LOAN#{loan_id}",
                "loan_amount": Decimal(str(row["loan_amnt"])),
                "interest_rate": Decimal(str(row["int_rate"])),
                "term_months": parse_term(row["term"]) or 36,
                "grade": row["grade"],
                "sub_grade": row["sub_grade"],
                "issue_date": parse_issue_date(row["issue_d"]) or "unknown",
                "purpose": row["purpose"] if pd.notna(row["purpose"]) else "other",
            })

            writer.put_item(Item={
                "PK": f"LOAN#{loan_id}",
                "SK": f"PAYMENT#{parse_issue_date(row['issue_d']) or 'unknown'}",
                "current_status": row["loan_status"],
                "days_past_due": parse_days_past_due(row["loan_status"]),
            })

            if loan_id_counter % 1000 == 0:
                print(f"  ...loaded {loan_id_counter} loans so far")

            borrower_id_counter += 1
            loan_id_counter += 1

    print(f"Done. Reloaded {loan_id_counter - 1} borrower/loan/payment-status record sets, now including sub_grade.")

    # Reset the ETL watermark since the table was wiped
    table.put_item(Item={
        "PK": "ETL_STATE",
        "SK": "WATERMARK",
        "next_batch_number": 1,
        "last_borrower_id": borrower_id_counter - 1,
        "last_loan_id": loan_id_counter - 1,
    })
    print("ETL watermark reset to batch 1.")


if __name__ == "__main__":
    wipe_table()
    reload_sample()