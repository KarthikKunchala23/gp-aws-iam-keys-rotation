import boto3
from datetime import datetime, timezone


client = boto3.client("dynamodb")

TABLE_NAME = "iam-key-rotation-state"


def create_rotation_state(
    user_name: str,
    team_name: str,
    email: str,
    old_access_key_id: str,
    new_access_key_id: str,
    secret_arn: str,
    message_id: str
) -> dict:
    """
    Create and persist the initial IAM key rotation state.
    """

    rotation_id = (
        f"{user_name}#"
        f"{old_access_key_id}#"
        f"{new_access_key_id}"
    )

    state = {
        "rotation_id": rotation_id,
        "user_name": user_name,
        "team_name": team_name,
        "email": email,
        "old_access_key_id": old_access_key_id,
        "new_access_key_id": new_access_key_id,
        "secret_arn": secret_arn,
        "status": "HANDOFF_PENDING",
        "notification_sent_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "notification_message_id": message_id,
        "confirmation_received_at": "",
        "old_key_deactivated_at": "",
        "old_key_deleted_at": "",
    }

    item = {
        "rotation_id": {"S": rotation_id},
        "user_name": {"S": user_name},
        "team_name": {"S": team_name},
        "email": {"S": email},
        "old_access_key_id": {"S": old_access_key_id},
        "new_access_key_id": {"S": new_access_key_id},
        "secret_arn": {"S": secret_arn},
        "status": {"S": "HANDOFF_PENDING"},
        "notification_sent_at": {
            "S": state["notification_sent_at"]
        },
        "notification_message_id": {
            "S": message_id
        },
        "confirmation_received_at": {"S": ""},
        "old_key_deactivated_at": {"S": ""},
        "old_key_deleted_at": {"S": ""},
    }

    client.put_item(
        TableName=TABLE_NAME,
        Item=item
    )

    return state

def get_rotation_state(
    user_name: str,
    old_access_key_id: str,
    new_access_key_id: str
) -> dict | None:
    """
    Retrieve an existing rotation state from DynamoDB.
    """

    rotation_id = (
        f"{user_name}#"
        f"{old_access_key_id}#"
        f"{new_access_key_id}"
    )

    response = client.get_item(
        TableName=TABLE_NAME,
        Key={
            "rotation_id": {
                "S": rotation_id
            }
        }
    )

    item = response.get("Item")

    if not item:
        return None

    return {
        key: value["S"]
        for key, value in item.items()
    }


def confirm_handoff(
    rotation_id: str
) -> None:
    """
    Confirm that the application has been updated
    to use the new IAM access key.
    """

    response = client.get_item(
        TableName=TABLE_NAME,
        Key={
            "rotation_id": {
                "S": rotation_id
            }
        }
    )

    item = response.get("Item")

    if not item:
        raise ValueError(
            f"Rotation not found: {rotation_id}"
        )

    current_status = item["status"]["S"]

    if current_status != "HANDOFF_PENDING":
        raise ValueError(
            f"Rotation cannot be confirmed. "
            f"Current status: {current_status}"
        )

    confirmation_time = datetime.now(
        timezone.utc
    ).isoformat()

    client.update_item(
        TableName=TABLE_NAME,
        Key={
            "rotation_id": {
                "S": rotation_id
            }
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
            ":status": {
                "S": "HANDOFF_CONFIRMED"
            },
            ":confirmed_at": {
                "S": confirmation_time
            }
        }
    )



def mark_key_deactivated(
    rotation_id: str
) -> None:
    """
    Mark the old IAM access key as deactivated.
    """

    confirmation = client.get_item(
        TableName=TABLE_NAME,
        Key={
            "rotation_id": {
                "S": rotation_id
            }
        }
    )

    item = confirmation.get("Item")

    if not item:
        raise ValueError(
            f"Rotation not found: {rotation_id}"
        )

    current_status = item["status"]["S"]

    if current_status != "HANDOFF_CONFIRMED":
        raise ValueError(
            f"Cannot deactivate key. "
            f"Current status: {current_status}"
        )

    deactivated_at = datetime.now(
        timezone.utc
    ).isoformat()

    client.update_item(
        TableName=TABLE_NAME,
        Key={
            "rotation_id": {
                "S": rotation_id
            }
        },
        UpdateExpression="""
            SET
                #status = :status,
                old_key_deactivated_at = :deactivated_at
        """,
        ExpressionAttributeNames={
            "#status": "status"
        },
        ExpressionAttributeValues={
            ":status": {
                "S": "OLD_KEY_DEACTIVATED"
            },
            ":deactivated_at": {
                "S": deactivated_at
            }
        }
    )


def mark_key_deleted(
    rotation_id: str
) -> None:
    """
    Mark the old IAM access key as permanently deleted.
    """

    response = client.get_item(
        TableName=TABLE_NAME,
        Key={
            "rotation_id": {
                "S": rotation_id
            }
        }
    )

    item = response.get("Item")

    if not item:
        raise ValueError(
            f"Rotation not found: {rotation_id}"
        )

    current_status = item["status"]["S"]

    if current_status != "OLD_KEY_DEACTIVATED":
        raise ValueError(
            f"Cannot delete key. "
            f"Current status: {current_status}"
        )

    deleted_at = datetime.now(
        timezone.utc
    ).isoformat()

    client.update_item(
        TableName=TABLE_NAME,
        Key={
            "rotation_id": {
                "S": rotation_id
            }
        },
        UpdateExpression="""
            SET
                #status = :status,
                old_key_deleted_at = :deleted_at
        """,
        ExpressionAttributeNames={
            "#status": "status"
        },
        ExpressionAttributeValues={
            ":status": {
                "S": "OLD_KEY_DELETED"
            },
            ":deleted_at": {
                "S": deleted_at
            }
        }
    )