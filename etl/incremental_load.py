"""
Incremental ETL: loads the next unprocessed batch file into DynamoDB,
tracking progress with a watermark item stored in the same table.

Watermark item:
    PK = "ETL_STATE"
    SK = "WATERMARK"
    next_batch_number = <int>

Run manually:
    python incremental_load.py
Or via the scheduled GitHub Actions workflow (.github/workflows/etl_schedule.yml)
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

BATCH_DIR = "data"
NUM_BATCHES = 10


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


def get_watermark():
    response = table.get_item(Key={"PK": "ETL_STATE", "SK": "WATERMARK"})
    item = response.get("Item")
    if item:
        return int(item["next_batch_number"])
    return 1  # first run, start at batch 1


def set_watermark(next_batch_number):
    table.put_item(Item={
        "PK": "ETL_STATE",
        "SK": "WATERMARK",
        "next_batch_number": next_batch_number
    })


def get_next_borrower_and_loan_ids():
    """
    Finds the highest existing borrower_id/loan_id already in the table,
    so newly loaded records don't collide with Phase 1's data.
    Simple approach: store running counters in the same watermark item.
    """
    response = table.get_item(Key={"PK": "ETL_STATE", "SK": "WATERMARK"})
    item = response.get("Item")
    if item and "last_borrower_id" in item:
        return int(item["last_borrower_id"]), int(item["last_loan_id"])
    return 10000, 10000  # start above Phase 1's 9,996 records, safely clear of collisions


def run():
    batch_number = get_watermark()

    if batch_number > NUM_BATCHES:
        print(f"All {NUM_BATCHES} batches already processed. Nothing to do.")
        return

    batch_str = str(batch_number).zfill(2)
    batch_path = os.path.join(BATCH_DIR, f"batch_{batch_str}.csv")

    if not os.path.exists(batch_path):
        print(f"Batch file {batch_path} not found. Skipping this run.")
        return

    print(f"Processing batch {batch_number}/{NUM_BATCHES}: {batch_path}")
    df = pd.read_csv(batch_path)

    last_borrower_id, last_loan_id = get_next_borrower_and_loan_ids()

    with table.batch_writer() as writer:
        for _, row in df.iterrows():
            last_borrower_id += 1
            last_loan_id += 1
            borrower_id = str(last_borrower_id)
            loan_id = str(last_loan_id)

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
                "issue_date": parse_issue_date(row["issue_d"]) or "unknown",
                "purpose": row["purpose"] if pd.notna(row["purpose"]) else "other",
            })

            writer.put_item(Item={
                "PK": f"LOAN#{loan_id}",
                "SK": f"PAYMENT#{parse_issue_date(row['issue_d']) or 'unknown'}",
                "current_status": row["loan_status"],
                "days_past_due": parse_days_past_due(row["loan_status"]),
            })

    # Advance the watermark and record the new ID counters
    table.put_item(Item={
        "PK": "ETL_STATE",
        "SK": "WATERMARK",
        "next_batch_number": batch_number + 1,
        "last_borrower_id": last_borrower_id,
        "last_loan_id": last_loan_id,
    })

    print(f"Batch {batch_number} loaded successfully ({len(df)} records). "
          f"Next run will process batch {batch_number + 1}.")


if __name__ == "__main__":
    run()