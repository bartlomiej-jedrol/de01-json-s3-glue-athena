import logging
import re
from io import BytesIO
from datetime import datetime, timezone

import boto3
import botocore
import pandas as pd

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TODO  # save the parquet file to temp directory


def list_objects(
    bucket: str, prefix: str, next_continuation_token: str = None
) -> list[dict]:
    if next_continuation_token:
        try:
            return s3.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                ContinuationToken=next_continuation_token,
            )
        except botocore.exceptions.ClientError as error:
            logger.error(
                f'Failed to obtain S3 objects from the bucket: {S3_PROCESSED_BUCKET_NAME} with prefix: {S3_PREFIX_CUSTOMER}: {error}'
            )
    else:
        try:
            return s3.list_objects_v2(
                Bucket=S3_PROCESSED_BUCKET_NAME, Prefix=S3_PREFIX_CUSTOMER
            )
        except botocore.exceptions.ClientError as error:
            logger.error(
                f'Failed to obtain S3 objects from the bucket: {S3_PROCESSED_BUCKET_NAME} with prefix: {S3_PREFIX_CUSTOMER}: {error}'
            )


# Job runs daily at 1:00 AM UTC time (3:00 AM local CET time) and aggregates data from the previous day
current_datetime_utc = datetime.now(tz=timezone.utc)
job_schedule_time = current_datetime_utc  # + timedelta(days=-1)
# print(job_schedule_time)
year = f'{job_schedule_time.year}'
month = f'{job_schedule_time.month:02d}'
day = f'{job_schedule_time.day:02d}'

# AWS S3 bucket details
S3_PROCESSED_BUCKET_NAME = 'de01-processed-data'
S3_AGGREGATED_BUCKET_NAME = 'de01-aggregated-data'
S3_PREFIX_CUSTOMER = f'customer/year={year}/month={month}/day={day}/'
S3_PREFIX_ORDER = f'order/year={year}/month={month}/day={day}/'
S3_PREFIX_PRODUCTS = f'products/year={year}/month={month}/day={day}/'
# print(S3_PREFIX)


# List parquet files from the S3 bucket
s3 = boto3.client('s3')

# Set initial parameters
# is_truncated is set to True to allow entering an initial loop
is_truncated = True
next_continuation_token = None
parquet_files = []

while is_truncated:
    if next_continuation_token:
        response = list_objects(
            bucket=S3_PROCESSED_BUCKET_NAME,
            prefix=S3_PREFIX_CUSTOMER,
            next_continuation_token=next_continuation_token,
        )
    else:
        response = list_objects(
            bucket=S3_PROCESSED_BUCKET_NAME, prefix=S3_PREFIX_CUSTOMER
        )

    is_truncated = response.get('IsTruncated')
    next_continuation_token = response.get('NextContinuationToken')

    parquet_files.extend([obj.get('Key') for obj in response.get('Contents')])
    logger.info(
        f'Successfully obtained S3 objects from the bucket: {S3_PROCESSED_BUCKET_NAME} with prefix: {S3_PREFIX_CUSTOMER}. Number of S3 objects: {len(parquet_files)}'
    )

print(parquet_files[:10])
# print(len(parquet_files))

aggregated_df = pd.DataFrame()

for obj_key in parquet_files:
    obj = s3.get_object(Bucket=S3_PROCESSED_BUCKET_NAME, Key=obj_key)
    df = pd.read_parquet(BytesIO(obj.get('Body').read()))

    aggregated_df = pd.concat([aggregated_df, df], ignore_index=True)

print(aggregated_df)
aggregated_parquet_name = 'aggregated_parquet_file.parquet'
aggregated_df.to_parquet(aggregated_parquet_name)

buffer = BytesIO()
aggregated_df.to_parquet(buffer)

s3.put_object(
    Bucket=S3_AGGREGATED_BUCKET_NAME,
    Key=f'{S3_PREFIX_CUSTOMER}{aggregated_parquet_name}',
    Body=buffer.getvalue(),
)
