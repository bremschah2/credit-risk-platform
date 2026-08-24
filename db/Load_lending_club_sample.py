"""
Loads a stratified sample of the Lending Club dataset into DynamoDB,
following the single-table design from db/schema.py.
"""

import re
import pandas as pd
from schema import put_borrower, put_loan, put_payment_status

SAMPLE_SIZE = 10000
RAW_PATH = "../data/raw/loan.csv"

COLUMNS_NEEDED = [
    "loan_amnt", "term", "int_rate", "grade", "sub_grade",
    "home_ownership", "annual_inc", "issue_d", "purpose", "dti",
    "loan_status", "emp_length"
]


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


def load_sample():
    print(f"Reading a stratified sample of {SAMPLE_SIZE} rows from {RAW_PATH}...")
    print("(This still requires one pass over the file -- expect a minute or two.)")

    df = pd.read_csv(RAW_PATH, usecols=COLUMNS_NEEDED, low_memory=False)
    df = df.dropna(subset=["loan_amnt", "int_rate", "grade", "issue_d", "loan_status"])

    # Stratified sample built manually per grade (avoids the pandas 3.0
    # groupby().apply() behavior change that drops the grouping column)
    total = len(df)
    samples = []
    for g in df["grade"].unique():
        sub = df[df["grade"] == g]
        n = min(len(sub), max(1, int(SAMPLE_SIZE * len(sub) / total)))
        samples.append(sub.sample(n=n, random_state=42))

    sample = pd.concat(samples)
    print(f"Sampled {len(sample)} rows. Loading into DynamoDB...")

    borrower_id_counter = 1
    loan_id_counter = 1

    for _, row in sample.iterrows():
        borrower_id = str(borrower_id_counter)
        loan_id = str(loan_id_counter)

        emp_length = row["emp_length"] if pd.notna(row["emp_length"]) else "Unknown"

        put_borrower(
            borrower_id=borrower_id,
            annual_income=row["annual_inc"] if pd.notna(row["annual_inc"]) else 0,
            employment_length=emp_length,
            home_ownership=row["home_ownership"] if pd.notna(row["home_ownership"]) else "Unknown",
            dti_ratio=row["dti"] if pd.notna(row["dti"]) else 0,
            credit_score_band="N/A"
        )

        put_loan(
            borrower_id=borrower_id,
            loan_id=loan_id,
            loan_amount=row["loan_amnt"],
            interest_rate=row["int_rate"],
            term_months=parse_term(row["term"]) or 36,
            grade=row["grade"],
            issue_date=parse_issue_date(row["issue_d"]) or "unknown",
            purpose=row["purpose"] if pd.notna(row["purpose"]) else "other"
        )

        put_payment_status(
            loan_id=loan_id,
            status_date=parse_issue_date(row["issue_d"]) or "unknown",
            current_status=row["loan_status"],
            days_past_due=parse_days_past_due(row["loan_status"])
        )

        if loan_id_counter % 500 == 0:
            print(f"  ...loaded {loan_id_counter} loans so far")

        borrower_id_counter += 1
        loan_id_counter += 1

    print(f"Done. Loaded {loan_id_counter - 1} borrower/loan/payment-status record sets.")


if __name__ == "__main__":
    load_sample()