import json
import boto3
import botocore
import botocore.exceptions
import os
import logging

if logging.getLogger().hasHandlers():
    # The Lambda environment pre-configures a handler logging to stderr. If a handler is already configured,
    # `.basicConfig` does not execute. Thus, we set the level directly.
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

bucket_name = os.getenv('BucketName')
safe_folder = os.getenv('SafeImagesFolderName')
in_review_folder = os.getenv('InReviewImagesFolderName')
s3_client = boto3.client('s3')


def lambda_handler(event, _):
    headers = {
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*"
    }
    # Get the image ID from the event
    body = json.loads(event['body'])
    image_id = body['id']
    is_safe = body['isSafe']
    # Check if the image exists in the bucket
    object_key = 'images/{}/{}'.format(in_review_folder, image_id)

    logging.info("Image id: {}.".format(image_id))
    logging.info("Is Safe: {}.".format(is_safe))
    logging.info("Image path: {}.".format(object_key))

    not_found_response = {
        'statusCode': 404,
        'headers': headers,
        'body': json.dumps({
            'message': 'image with id {} does not exist'.format(image_id)
        })
    }

    try:
        s3_client.head_object(Bucket=bucket_name, Key=object_key)
    except s3_client.exceptions.NoSuchKey:  # type: ignore
        logging.error("no such image found")
        return not_found_response

    except botocore.exceptions.ClientError as err:
        # NOTE: This case is required because of https://github.com/boto/boto3/issues/2442
        if err.response["Error"]["Code"] == "404":
            logging.error("no such image found")
            return not_found_response

    if is_safe:
        destination_path = f"images/{safe_folder}/{image_id}"

        # Copy the object from the source to the destination
        s3_client.copy_object(Bucket=bucket_name,
                              CopySource={'Bucket': bucket_name, 'Key': object_key},
                              Key=destination_path)

        # Delete the object from the source
        s3_client.delete_object(Bucket=bucket_name, Key=object_key)

        logging.info(f"image with id {image_id} moved to the safe folder.")

        message = f'image with id {image_id} has been successfully approved'
    else:
        # Delete the object
        s3_client.delete_object(Bucket=bucket_name, Key=object_key)

        logging.info(f"Image {image_id} is not safe and has been deleted.")

        message = f'image with id {image_id} has been rejected and deleted'

    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'message': message
        })
    }
