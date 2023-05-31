import json
import boto3
import botocore
import botocore.exceptions
import uuid
import os
import logging
import tempfile

if logging.getLogger().hasHandlers():
    # The Lambda environment pre-configures a handler logging to stderr. If a handler is already configured,
    # `.basicConfig` does not execute. Thus, we set the level directly.
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

bucket_name = os.getenv('BucketName')
safe_folder = os.getenv('SafeImagesFolderName')
s3_client = boto3.client('s3')


def lambda_handler(event, _):
    # Get the image ID from the event
    headers = {
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*"
    }
    body = json.loads(event['body'])
    image_id = body['id']
    # Check if the image exists in the bucket
    object_key = 'images/{}/{}'.format(safe_folder, image_id)

    logging.info("Image id: {}".format(image_id))
    logging.info("Bucket: {}".format(bucket_name))
    logging.info("Image path: {}".format(object_key))

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

    # The image exists, save the JSON file
    with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf8') as temp_file:
        temp_file_name = temp_file.name
        json.dump(body, temp_file, ensure_ascii=False)

    annotation_id = str(uuid.uuid4())
    annotations_path = 'annotations/{}/{}.json'.format(image_id, annotation_id)

    try:
        with open(temp_file_name, 'rb') as data:
            s3_client.upload_fileobj(data, bucket_name, annotations_path)
    except Exception as e:
        logging.error("error occurred while uploading to S3", e)
        return
    finally:
        # Make sure we remove the temporary file.
        os.remove(temp_file_name)

    # Return 201
    return {
        'statusCode': 201,
        'headers': headers,
        'body': json.dumps(json.dumps({
                'message': f'annotation has been successfully saved with id: {annotation_id}'
        }))
    }
