import boto3

S3_PROCESSED_BUCKET = 'de01-processed-data'

s3 = boto3.client('s3')

objects = response = s3.list_objects(
    Bucket=S3_PROCESSED_BUCKET,
    EncodingType='url',
    RequestPayer='requester',
    OptionalObjectAttributes=[
        'RestoreStatus',
    ],
)

print(objects)
