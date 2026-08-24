import os
import boto3
from dotenv import load_dotenv
from decimal import Decimal

load_dotenv()

dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION"))
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))


def put_borrower(borrower_id, annual_income, employment_length,
                  home_ownership, dti_ratio, credit_score_band):
    table.put_item(Item={
        "PK": f"BORROWER#{borrower_id}",
        "SK": "PROFILE",
        "annual_income": Decimal(str(annual_income)),
        "employment_length": employment_length,
        "home_ownership": home_ownership,
        "dti_ratio": Decimal(str(dti_ratio)),
        "credit_score_band": credit_score_band,
    })


def put_loan(borrower_id, loan_id, loan_amount, interest_rate,
             term_months, grade, issue_date, purpose):
    table.put_item(Item={
        "PK": f"BORROWER#{borrower_id}",
        "SK": f"LOAN#{loan_id}",
        "loan_amount": Decimal(str(loan_amount)),
        "interest_rate": Decimal(str(interest_rate)),
        "term_months": term_months,
        "grade": grade,
        "issue_date": issue_date,
        "purpose": purpose,
    })


def put_payment_status(loan_id, status_date, current_status, days_past_due):
    table.put_item(Item={
        "PK": f"LOAN#{loan_id}",
        "SK": f"PAYMENT#{status_date}",
        "current_status": current_status,
        "days_past_due": days_past_due,
    })


def put_risk_score(loan_id, score_date, probability_default,
                    expected_loss, model_version):
    table.put_item(Item={
        "PK": f"LOAN#{loan_id}",
        "SK": f"RISKSCORE#{score_date}",
        "probability_default": Decimal(str(probability_default)),
        "expected_loss": Decimal(str(expected_loss)),
        "model_version": model_version,
    })