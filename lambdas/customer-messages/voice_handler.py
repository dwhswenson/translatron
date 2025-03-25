import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Voice handler invoked")
    logger.info(event)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Voice placeholder OK"})
    }
