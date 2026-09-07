import os
import boto3
from datetime import datetime, timezone


dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ["TABLE_NAME"]

table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):

    print("Received event:")
    print(event)

    # --------------------------------------------------
    # Get rotation_id from API Gateway path parameter
    # --------------------------------------------------

    path_parameters = event.get(
        "pathParameters"
    ) or {}

    rotation_id = path_parameters.get(
        "rotation_id"
    )

    if not rotation_id:

        return {
            "statusCode": 400,
            "body": "rotation_id is required"
        }

    # --------------------------------------------------
    # Get rotation state
    # --------------------------------------------------

    response = table.get_item(
        Key={
            "rotation_id": rotation_id
        }
    )

    item = response.get("Item")

    if not item:

        return {
            "statusCode": 404,
            "body": "Rotation not found"
        }

    # --------------------------------------------------
    # Validate current state
    # --------------------------------------------------

    if item["status"] != "HANDOFF_PENDING":

        return {
            "statusCode": 409,
            "body": (
                f"Rotation cannot be confirmed. "
                f"Current status: "
                f"{item['status']}"
            )
        }

    # --------------------------------------------------
    # Record confirmation
    # --------------------------------------------------

    confirmation_time = datetime.now(
        timezone.utc
    ).isoformat()

    table.update_item(
        Key={
            "rotation_id": rotation_id
        },
        UpdateExpression="""
            SET
                #status = :status,
                confirmation_received_at = :confirmed_at
        """,
        ExpressionAttributeNames={
            "#status": "status"
        },
        ExpressionAttributeValues={
            ":status": "HANDOFF_CONFIRMED",
            ":confirmed_at": confirmation_time
        }
    )

    print(
        f"Rotation confirmed: {rotation_id}"
    )

    return {
        "statusCode": 200,
        "body": (
            "Access key rotation confirmed successfully. "
            "The observation period has started."
        )
    }