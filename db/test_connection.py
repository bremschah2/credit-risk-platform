import os
import boto3
from dotenv import load_dotenv

load_dotenv()

dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION"))
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

print("Connected to table:", table.table_name)
print("Table status:", table.table_status)
print("Item count (approx):", table.item_count)