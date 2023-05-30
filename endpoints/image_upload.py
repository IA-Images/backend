import json
import boto3
import uuid
import os
import logging
import base64
from requests_toolbelt.multipart import decoder
from botocore.exceptions import NoCredentialsError

bucket_name = os.getenv('BucketName')
in_review_folder = os.getenv('InReviewImagesFolderName')

s3_client = boto3.client('s3')

if logging.getLogger().hasHandlers():
    # The Lambda environment pre-configures a handler logging to stderr. If a handler is already configured,
    # `.basicConfig` does not execute. Thus, we set the level directly.
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)


def lambda_handler(event, _):
    headers = {
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*"
    }
    try:
        # Get the image from the body of the request
        image = event['body']
        content_type = event['headers']['content-type']
        # Generate a random unique file name

        file_name = str(uuid.uuid4())
        tmp_img_path = f"/tmp/{file_name}.jpeg"
        file_path = f"images/{in_review_folder}/{file_name}.jpeg"
        # Create a temporary file to store the image

        if event['isBase64Encoded']:
            # Decode the image file
            logging.info("The image is Based64 encoded")

            image_multipart_string = base64.b64decode(image)
            image_bytes = decoder.MultipartDecoder(image_multipart_string, content_type).parts[0].content
        else:
            # The image file is not base64 encoded, so just use the content as-is
            logging.info("The image is NOT Based64 encoded")
            image_bytes = decoder.MultipartDecoder(image, content_type).parts[0].content

        with open(tmp_img_path, "wb") as tmp:
            tmp.write(image_bytes)

        # Upload the image to S3
        try:
            s3_client.upload_file(tmp_img_path, bucket_name, file_path)
            logging.info(f'successfully uploaded {file_name}.jpeg to {bucket_name}')

        except NoCredentialsError:
            logging.error('No AWS credentials found')
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'message': 'error: No AWS credentials found'
                })
            }

        # Return a success message
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                    'message': f'successfully uploaded {file_name}.jpeg'
            })
        }

    except Exception as e:
        logging.error(e)
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'message': e
            })
        }
