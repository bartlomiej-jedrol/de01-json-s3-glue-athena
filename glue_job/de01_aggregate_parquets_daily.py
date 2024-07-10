import logging
from io import BytesIO
from datetime import datetime, timezone, timedelta

import boto3
import botocore
import pandas as pd

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def list_objects(
    bucket: str, prefix: str, next_continuation_token: str = None
) -> list[dict]:
    """
    Lists objects from S3 bucket for a specific prefix.

    Args:
        bucket (str): S3 bucket.
        prefix (str): S3 object prefix.
        next_continuation_token (str, optional): Lists a continuation of objects from a previous API call. Defaults to None.

    Returns:
        list[dict]: List of S3 objects.
    """
    if next_continuation_token:
        try:
            return s3.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                ContinuationToken=next_continuation_token,
            )
        except botocore.exceptions.ClientError as error:
            logger.error(
                f'Failed to obtain S3 objects from the bucket: {bucket} with prefix: {prefix}: {error}'
            )
    else:
        try:
            return s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        except botocore.exceptions.ClientError as error:
            logger.error(
                f'Failed to obtain S3 objects from the bucket: {bucket} with prefix: {prefix}: {error}'
            )


def get_parquet_keys(
    bucket: str, prefix: str, is_truncated: bool, next_continuation_token: str = None
) -> list[str]:
    """
    Returns list of parquet files' S3 object keys for a specific bucket and prefix.

    Args:
        bucket (str): S3 bucket.
        prefix (str): S3 object prefix.
        is_truncated (bool): True if an initial API call returns 1000 objects (api limit) and there if more to get. Should be set to True to enter the loop.
        next_continuation_token (str): Lists a continuation of objects from a previous API call.

    Returns:
        list[str]: List of of parquet files S3 object keys.
    """
    parquet_keys = []
    while is_truncated:
        if next_continuation_token:
            response = list_objects(
                bucket=bucket,
                prefix=prefix,
                next_continuation_token=next_continuation_token,
            )
        else:
            response = list_objects(bucket=bucket, prefix=prefix)

        is_truncated = response.get('IsTruncated')
        next_continuation_token = response.get('NextContinuationToken')
        # print(response.get('Contents'))

        parquet_keys.extend([obj.get('Key') for obj in response.get('Contents')])
        logger.info(
            f'Successfully obtained S3 objects from the bucket: {bucket} with prefix: {prefix}. Number of S3 objects: {len(parquet_keys)}'
        )
    return parquet_keys


# Set job schedule time.
# Job runs daily at 1:00 AM UTC time (3:00 AM local CET time) and aggregates data from the previous day.
current_datetime_utc = datetime.now(tz=timezone.utc)
job_schedule_time = current_datetime_utc  # + timedelta(days=-1)

# Date parts of the job schedule date.
year = f'{job_schedule_time.year}'
month = f'{job_schedule_time.month:02d}'
day = f'{job_schedule_time.day:02d}'

# AWS S3 bucket details.
S3_PROCESSED_BUCKET_NAME = 'de01-processed-data'
S3_AGGREGATED_BUCKET_NAME = 'de01-aggregated-data'
PREFIX_CUSTOMER = 'customer'
PREFIX_ORDER = 'order'
PREFIX_PRODUCTS = 'products'
S3_PREFIXES = (
    f'{PREFIX_CUSTOMER}/year={year}/month={month}/day={day}/',
    f'{PREFIX_ORDER}/year={year}/month={month}/day={day}/',
    f'{PREFIX_PRODUCTS}/year={year}/month={month}/day={day}/',
)

s3 = boto3.client('s3')
# Set initial parameter - is_truncated is set to True to allow entering an initial loop.
is_truncated = True
# Loop over all S3 prefixes to get parquet keys for customer, order, and products.
for prefix in S3_PREFIXES:
    parquet_keys = []
    parquet_keys = get_parquet_keys(
        bucket=S3_PROCESSED_BUCKET_NAME,
        prefix=prefix,
        is_truncated=True,
    )

    aggregated_df = pd.DataFrame()
    for obj_key in parquet_keys:
        obj = s3.get_object(Bucket=S3_PROCESSED_BUCKET_NAME, Key=obj_key)
        # Create Data Frame for each parquet file.
        df = pd.read_parquet(BytesIO(obj.get('Body').read()))
        # print(f'obj: {obj}\n')
        # print(f'obj.get("Body"): {obj.get("Body")}\n')
        # print(f'obj.get("Body").read(): {obj.get("Body").read()}\n')
        # print(f'BytesIO(obj.get("Body").read(): {BytesIO(obj.get("Body").read())}\n')

        # Merge current Data Frame of parquet file to the aggregated Data Frame.
        aggregated_df = pd.concat([aggregated_df, df], ignore_index=True)

    # print(aggregated_df)

    # Map prefix to suffix for the parquet file name.
    prefix_to_suffix_map = {
        S3_PREFIXES[0]: PREFIX_CUSTOMER,
        S3_PREFIXES[1]: PREFIX_ORDER,
        S3_PREFIXES[2]: PREFIX_PRODUCTS,
    }
    suffix = prefix_to_suffix_map.get(prefix, '')
    parquet_file_name = f'{prefix}{year}_{month}_{day}_{suffix}_aggregated.parquet'

    # Convert an aggregated Data Frame buffer to parquet file.
    buffer = BytesIO()
    aggregated_df.to_parquet(buffer)

    # Put the aggregated parquet file to S3 bucket.
    s3.put_object(
        Bucket=S3_AGGREGATED_BUCKET_NAME,
        Key=parquet_file_name,
        Body=buffer.getvalue(),
    )
