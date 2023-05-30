import json
import boto3
import os
import logging

if logging.getLogger().hasHandlers():
    # The Lambda environment pre-configures a handler logging to stderr. If a handler is already configured,
    # `.basicConfig` does not execute. Thus, we set the level directly.
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

bucket_name = os.getenv('BucketName')
in_review_folder = os.getenv('InReviewImagesFolderName')
s3_client = boto3.client('s3')


def lambda_handler(_, __):
    headers = {
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*"
    }
    # Check if the image exists in the bucket
    in_review_folder_path = 'images/{}'.format(in_review_folder)

    logging.info("Review folder path: {}.".format(in_review_folder_path))

    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=in_review_folder_path)

    # Check if any objects are found in the safe folder
    if 'Contents' in response:
        # Get the first object from the response
        object_key = response['Contents'][0]['Key']
        object_name = object_key.split('/')[-1]  # Extract the object name

        # Generate a pre-signed URL for the object
        url = s3_client.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': object_key})

        # Create the JSON response
        response_data = {'id': object_name, 'url': url}
    else:
        response_data = {'message': 'no images available for review'}

    # Return the JSON response
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response_data)
    }
