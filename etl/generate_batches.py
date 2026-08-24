"""
One-time script: creates 10 small batch CSV files simulating new loans
arriving over time. These get committed to the repo (small, unlike the
full 1.2GB source file) and consumed one-per-run by the scheduled ETL.

Run this once locally, from inside the etl/ folder:
    python generate_batches.py
"""

import pandas as pd
import os

RAW_PATH = "../data/raw/loan.csv"
OUTPUT_DIR = "data"
NUM_BATCHES = 10
ROWS_PER_BATCH = 300

COLUMNS_NEEDED = [
    "loan_amnt", "term", "int_rate", "grade", "sub_grade",
    "home_ownership", "annual_inc", "issue_d", "purpose", "dti",
    "loan_status", "emp_length"
]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Reading source file (this may take a minute given file size)...")
    df = pd.read_csv(RAW_PATH, usecols=COLUMNS_NEEDED, low_memory=False)
    df = df.dropna(subset=["loan_amnt", "int_rate", "grade", "issue_d", "loan_status"])

    # Sample a different slice than Phase 1's 10,000 -- take rows further
    # into the file so these represent genuinely different "new" records
    total_needed = NUM_BATCHES * ROWS_PER_BATCH
    sample = df.sample(n=total_needed, random_state=99)  # different seed than Phase 1

    for i in range(NUM_BATCHES):
        batch = sample.iloc[i * ROWS_PER_BATCH: (i + 1) * ROWS_PER_BATCH]
        batch_num = str(i + 1).zfill(2)
        out_path = os.path.join(OUTPUT_DIR, f"batch_{batch_num}.csv")
        batch.to_csv(out_path, index=False)
        print(f"Wrote {out_path} ({len(batch)} rows)")

    print(f"\nDone. Created {NUM_BATCHES} batch files in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()