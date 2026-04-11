"""AWS Lambda handler for example-app.

This module provides the entry point for AWS Lambda invocations.
The handler function is referenced in the Dockerfile CMD instruction
as ``app.lambda_handler.handler``.

See ADR-015 (AWS as Cloud Provider) for context.
"""

import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    """AWS Lambda entry point.

    Parameters
    ----------
    event : dict
        The event payload from the Lambda invocation trigger (e.g.,
        S3 event notification, API Gateway request, CloudWatch
        scheduled event).
    context : LambdaContext
        Runtime information provided by the Lambda service.

    Returns
    -------
    dict
        A response object. Customize the return value based on
        your application's needs.
    """
    logger.info("Received event: %s", json.dumps(event))

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Hello from Lambda!",
                "event": event,
            }
        ),
    }
