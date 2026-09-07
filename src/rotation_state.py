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