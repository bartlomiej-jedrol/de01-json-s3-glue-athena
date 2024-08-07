import os
import json
import re
import logging
from urllib.parse import unquote_plus

import boto3
import pandas as pd

S3_CLIENT = boto3.client('s3')
TARGET_BUCKET_NAME = os.getenv('S3_TARGET_BUCKET')

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def read_json(bucket: str, key: str) -> dict[str, str | float]:
    """
    Function to read JSON from source S3 bucket and return dictionary.

    Args:
        bucket (str): S3 bucket.
        key (str): S3 object key.

    Returns:
        dict[str, str | float]: Dumped JSON file.
    """
    try:
        s3_object = S3_CLIENT.get_object(Bucket=bucket, Key=key)
        logger.info(
            f'Successfully obtained the S3 object with key: {key} from the bucket: {bucket}'
        )
        s3_object_bytes = s3_object['Body'].read()
        data = json.loads(s3_object_bytes)
        # print(f'Data: {data}\n')
        return data
    except Exception as e:
        logger.error(
            f'Failed to obtain the S3 object with key: {key} from the bucket: {bucket}: {e}'
        )
        return None


def matches_pattern(s: str) -> bool:
    """
    Function to check if provided string matches pattern.

    Args:
        s (str): The input string to process.

    Returns:
        bool: The flag indicating if the string matches pattern.
    """
    pattern = r'\d{4}_\d{2}_\d{2}'
    return bool(re.match(pattern, s))


def create_data_frames(data: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Function to create Data Frames for the customer, products, and order.

    Args:
        data (dict): JSON data.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: Three Data Frames for customer, products, and order.
    """
    df_customer = pd.json_normalize(data['customer'])
    df_products = pd.json_normalize(data['products'])
    df_order = pd.json_normalize(data)[
        ['order_id', 'order_date', 'total_amount', 'customer.customer_id']
    ]
    # Normalize the 'products' part of the JSON and include 'order_id' as a meta field
    df_order_products = pd.json_normalize(
        data, record_path=['products'], meta=['order_id'], errors='ignore'
    )
    # Select only the 'order_id' and 'product_id' columns
    df_order_products = df_order_products[['order_id', 'product_id']]

    # Adding the 'created_on' timestamp with the current data and time
    current_timestamp = pd.Timestamp.now()
    df_customer['created_on'] = current_timestamp
    df_products['created_on'] = current_timestamp
    df_order['created_on'] = current_timestamp
    df_order_products['created_on'] = current_timestamp

    print(f'DF customer:\n {df_customer}\n')
    print(f'DF products:\n {df_products}\n')
    print(f'DF order:\n {df_order}\n')
    print(f'DF product_order:\n {df_order_products}\n')
    return df_customer, df_products, df_order, df_order_products


def upload_object(file_name: str, bucket: str, key: str):
    """
    Function to upload Parquet file to the target S3 bucket.

    Args:
        file_name (str): File name.
        bucket (str): S3 bucket.
        key (str): S3 object key.
    """
    try:
        S3_CLIENT.upload_file(Filename=file_name, Bucket=bucket, Key=key)
        logger.info(
            f'Successfully uploaded the S3 object with key: {key} to the bucket: {bucket}'
        )
    except Exception as e:
        logger.error(
            f'Failed to upload the S3 object with key: {key} to the bucket: {bucket}: {e}'
        )


def parse_date(date: str) -> tuple[str, str, str]:
    """
    Function to extract date parts from a string.

    Args:
        date (str): Date in the string format (YYYY-MM-DD).

    Returns:
        tuple[str, str, str]: Year, month, day.
    """
    if matches_pattern(s=date):
        year = date[:4]
        month = date[5:7]
        day = date[8:]
        return year, month, day


def lambda_handler(event, context):
    """
    Event listener for S3 bucket events.
    Processes source JSON file and uploads it to target S3 bucket in a Parquet format.

    Args:
        event (dict): Lambda event.
        context (LambdaContext): Lambda context.
    """
    logger.info(f'Received event: {event}\n')

    source_bucket_name = event['Records'][0]['s3']['bucket']['name']
    raw_object_key = unquote_plus(
        event['Records'][0]['s3']['object']['key'], encoding='utf-8'
    )

    # Create Data Frame from the source JSON file
    data = read_json(bucket=source_bucket_name, key=raw_object_key)
    data_frames = create_data_frames(data=data)

    # Extract date from the source file name
    file_datetime = raw_object_key.replace('data_', '').replace(
        '.json', ''
    )  # data_2024_07_08T09:18:06.954.json -> 2024_07_08
    file_date = file_datetime.split(' ')[0]
    year, month, day = parse_date(date=file_date)

    # Upload each Data Frame as the Parquet file to the target S3 bucket
    for df in data_frames:
        if 'customer_id' in df.columns:
            file_name_prefix = 'customer'
        elif all(column in df.columns for column in ['order_id', 'product_id']):
            file_name_prefix = 'order_products'
        elif 'product_id' in df.columns:
            file_name_prefix = 'products'
        elif 'order_id' in df.columns:
            file_name_prefix = 'order'

        print(df.columns)
        print(file_name_prefix)

        # Convert Data Frame to the Parquet format
        parquet_file_name = f'{file_datetime}_{file_name_prefix}.parquet'
        lambda_path = f'/tmp/{parquet_file_name}'
        df.to_parquet(path=lambda_path, compression='snappy')

        # Upload Parquet file from the temporary Lambda path to the target S3 bucket
        target_object_key = f'{file_name_prefix}/year={year}/month={month}/day={day}/{parquet_file_name}'
        upload_object(
            file_name=lambda_path, bucket=TARGET_BUCKET_NAME, key=target_object_key
        )
