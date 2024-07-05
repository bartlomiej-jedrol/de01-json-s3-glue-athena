import json
import random
import string
import os
from dotenv import load_dotenv

import boto3

load_dotenv()

S3_SOURCE_BUCKET = os.getenv("S3_SOURCE_BUCKET")

# Define a mapping of product IDs to fixed prices
product_prices = {"P001": 50.00, "P002": 30.00, "P003": 20.00, "P004": 40.00}


# Function to generate random data for a JSON file
def generate_random_data():
    order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    order_date = f"2024-{random.randint(1,5):02}-{random.randint(1, 31):02}"
    customer_id = ''.join(random.choices(string.digits, k=1))
    customer_name = ''.join(random.choices(string.ascii_letters, k=8))
    customer_email = f"{customer_name}@example.com"
    street = f"{random.randint(1, 100)} {random.choice(string.ascii_uppercase)} St"
    city = random.choice(["Anytown", "Sometown", "Othertown"])
    state = random.choice(["CA", "NY", "TX"])
    zip_code = ''.join(random.choices(string.digits, k=5))
    products = [
        {
            "product_id": product_id,
            "price": product_prices.get(
                product_id, round(random.uniform(10.0, 100.0), 2)
            ),
            "quantity": random.randint(1, 5),
        }
        for i, product_id in enumerate(product_prices.keys())
    ]
    total_amount = sum(product["price"] * product["quantity"] for product in products)

    data = {
        "order_id": order_id,
        "order_date": order_date,
        "customer": {
            "customer_id": customer_id,
            "name": customer_name,
            "email": customer_email,
            "address": {
                "street": street,
                "city": city,
                "state": state,
                "zip_code": zip_code,
            },
        },
        "products": products,
        "total_amount": total_amount,
    }

    return data


# Generate and upload a specified number of JSON files to AWS S3
num_files = 50
# s3_prefix = 'data/'

s3_client = boto3.client('s3')

for i in range(num_files):
    data = generate_random_data()
    file_name = f"data_{data['order_date'].replace('-', '_')}.json"
    file_path = f"sample_files/{file_name}"

    with open(file_path, 'w') as file:
        json.dump(data, file)

    s3_client.upload_file(file_path, S3_SOURCE_BUCKET, f"{file_name}")

    print(f"Uploaded {file_name} to S3 bucket {S3_SOURCE_BUCKET}")

    # os.remove(f"sample_files/{file_name}")
