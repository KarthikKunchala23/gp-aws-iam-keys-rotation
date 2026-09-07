import boto3
from secretsManager import store_access_key
from rotation_state import create_rotation_state
from notifications import send_rotation_notification


client = boto3.client("iam")


def create_access_key(user_name: str) -> dict:
    """
    Create a new IAM access key.
    """

    response = client.create_access_key(
        UserName=user_name
    )

    return response["AccessKey"]

def rotate_access_key(
    user_name: str,
    old_access_key_id: str,
    team_name: str,
    email: str,
    topic_arn: str
) -> dict:

    # --------------------------------------------------
    # 1. Create new access key
    # --------------------------------------------------

    new_key = create_access_key(
        user_name
    )

    new_access_key_id = new_key["AccessKeyId"]

    # --------------------------------------------------
    # 2. Store credentials in Secrets Manager
    # --------------------------------------------------

    secret_arn = store_access_key(
        user_name,
        new_key
    )

    # --------------------------------------------------
    # 3. Send SNS notification
    # --------------------------------------------------

    message_id = send_rotation_notification(
        topic_arn=topic_arn,
        team_name=team_name,
        email=email,
        iam_user=user_name,
        old_access_key_id=old_access_key_id,
        new_access_key_id=new_access_key_id
    )

    # --------------------------------------------------
    # 4. Store rotation state in DynamoDB
    # --------------------------------------------------

    rotation_state = create_rotation_state(
        user_name=user_name,
        team_name=team_name,
        email=email,
        old_access_key_id=old_access_key_id,
        new_access_key_id=new_access_key_id,
        secret_arn=secret_arn,
        message_id=message_id
    )

    # --------------------------------------------------
    # 5. Report
    # --------------------------------------------------

    print(
        f"New access key created for {user_name}: "
        f"{new_access_key_id}"
    )

    print(
        f"Credentials stored in Secrets Manager: "
        f"{secret_arn}"
    )

    print(
        f"SNS notification sent: "
        f"{message_id}"
    )

    print(
        f"Rotation state: "
        f"{rotation_state['status']}"
    )

    print(
        f"Old access key remains ACTIVE: "
        f"{old_access_key_id}"
    )

    return {
        "new_key": new_key,
        "secret_arn": secret_arn,
        "rotation_state": rotation_state,
        "message_id": message_id,
    }