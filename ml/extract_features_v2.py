"""
Extracts a larger, richer training set directly from the raw Lending Club
CSV for model training purposes -- separate from the smaller operational
dataset held in DynamoDB (which stays as the live system's data).

Label definition (same as before):
    default = 1  if loan_status == "Charged Off"
    default = 0  if loan_status == "Fully Paid"

Candidate features (full set -- feature importance will decide what
actually earns a place in the final model):
    Numeric:     loan_amnt, int_rate, term, annual_inc, dti,
                 delinq_2yrs, inq_last_6mths, open_acc, pub_rec,
                 revol_util, mort_acc
    Categorical: sub_grade, purpose, home_ownership, employment_length,
                 verification_status

Output: ml/data/training_data_v2.csv
"""

import re
import pandas as pd
import os

RAW_PATH = "../data/raw/loan.csv"
OUTPUT_DIR = "data"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "training_data_v2.csv")
SAMPLE_SIZE = 40000

COLUMNS_NEEDED = [
    "loan_amnt", "int_rate", "term", "annual_inc", "dti",
    "delinq_2yrs", "inq_last_6mths", "open_acc", "pub_rec",
    "revol_util", "mort_acc",
    "sub_grade", "grade", "purpose", "home_ownership",
    "emp_length", "verification_status", "loan_status"
]

RESOLVED_STATUSES = {
    "Charged Off": 1,
    "Fully Paid": 0,
}


def parse_term(term_str):
    if pd.isna(term_str):
        return None
    match = re.search(r"(\d+)", str(term_str))
    return int(match.group(1)) if match else None


def parse_revol_util(val):
    """'45.3%' -> 45.3"""
    if pd.isna(val):
        return None
    if isinstance(val, str):
        val = val.replace("%", "").strip()
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def main():
    print(f"Reading source file (this will take a couple minutes given file size)...")
    df = pd.read_csv(RAW_PATH, usecols=COLUMNS_NEEDED, low_memory=False)
    print(f"Loaded {len(df)} total rows.")

    df = df[df["loan_status"].isin(RESOLVED_STATUSES.keys())].copy()
    print(f"Filtered to {len(df)} resolved loans (Fully Paid / Charged Off).")

    df["term_months"] = df["term"].apply(parse_term)
    df["revol_util_pct"] = df["revol_util"].apply(parse_revol_util)
    df["default"] = df["loan_status"].map(RESOLVED_STATUSES)

    # Fill manageable gaps rather than dropping rows over them
    df["emp_length"] = df["emp_length"].fillna("Unknown")
    df["mort_acc"] = df["mort_acc"].fillna(0)
    df["revol_util_pct"] = df["revol_util_pct"].fillna(df["revol_util_pct"].median())
    df["delinq_2yrs"] = df["delinq_2yrs"].fillna(0)
    df["inq_last_6mths"] = df["inq_last_6mths"].fillna(0)
    df["open_acc"] = df["open_acc"].fillna(df["open_acc"].median())
    df["pub_rec"] = df["pub_rec"].fillna(0)

    # Drop rows still missing anything essential after fills
    essential = ["loan_amnt", "int_rate", "term_months", "annual_inc", "dti", "sub_grade"]
    before = len(df)
    df = df.dropna(subset=essential)
    print(f"Dropped {before - len(df)} rows missing essential fields. {len(df)} remain.")

    # Stratified sample by sub_grade to keep a realistic risk-tier mix
    total = len(df)
    n_target = min(SAMPLE_SIZE, total)
    samples = []
    for g in df["sub_grade"].unique():
        sub = df[df["sub_grade"] == g]
        n = min(len(sub), max(1, int(n_target * len(sub) / total)))
        samples.append(sub.sample(n=n, random_state=42))
    sample = pd.concat(samples)

    final_columns = [
        "loan_amnt", "int_rate", "term_months", "annual_inc", "dti",
        "delinq_2yrs", "inq_last_6mths", "open_acc", "pub_rec",
        "revol_util_pct", "mort_acc",
        "sub_grade", "purpose", "home_ownership", "emp_length",
        "verification_status", "default"
    ]
    sample = sample[final_columns].rename(columns={
        "loan_amnt": "loan_amount",
        "int_rate": "interest_rate",
        "annual_inc": "annual_income",
        "emp_length": "employment_length",
        "revol_util_pct": "revol_util",
    })

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sample.to_csv(OUTPUT_PATH, index=False)

    print(f"\nFinal training set: {len(sample)} loans")
    print(f"Default rate: {sample['default'].mean():.2%}")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()