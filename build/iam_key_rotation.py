import boto3
from secretsManager import store_access_key
from notifications import send_rotation_notification
from datetime import datetime, timezone, timedelta

from iam import (
    deactivate_access_key,
    delete_access_key
)

from rotation_state import (
    create_rotation_state,
    get_rotation_state,
    mark_key_deactivated,
    mark_key_deleted
)

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


def deactivate_old_key(
    user_name: str,
    old_access_key_id: str,
    new_access_key_id: str,
    observation_days: int
) -> None:
    """
    Deactivate the old IAM access key after the
    configured observation period has elapsed.
    """

    rotation_id = (
        f"{user_name}#"
        f"{old_access_key_id}#"
        f"{new_access_key_id}"
    )

    rotation_state = get_rotation_state(
        user_name=user_name,
        old_access_key_id=old_access_key_id,
        new_access_key_id=new_access_key_id
    )

    if not rotation_state:
        raise ValueError(
            f"Rotation not found: {rotation_id}"
        )

    if rotation_state["status"] != "HANDOFF_CONFIRMED":
        raise ValueError(
            f"Cannot deactivate old key. "
            f"Current status: "
            f"{rotation_state['status']}"
        )

    confirmed_at = rotation_state.get(
        "confirmation_received_at"
    )

    if not confirmed_at:
        raise ValueError(
            f"Missing confirmation timestamp "
            f"for rotation: {rotation_id}"
        )

    if not is_observation_period_complete(
        confirmed_at=confirmed_at,
        observation_days=observation_days
    ):
        print(
            f"Observation period has not elapsed "
            f"for {old_access_key_id}. "
            f"Waiting {observation_days} days."
        )
        return

    print(
        f"Deactivating old access key: "
        f"{old_access_key_id}"
    )

    deactivate_access_key(
        user_name=user_name,
        access_key_id=old_access_key_id
    )

    mark_key_deactivated(
        rotation_id=rotation_id
    )

    print(
        f"Old access key deactivated successfully: "
        f"{old_access_key_id}"
    )

def is_deletion_retention_complete(
    deactivated_at: str,
    retention_days: int
) -> bool:
    """
    Check whether the old access key has completed
    the configured deletion retention period.
    """

    deactivated_time = datetime.fromisoformat(
        deactivated_at
    )

    if deactivated_time.tzinfo is None:
        deactivated_time = deactivated_time.replace(
            tzinfo=timezone.utc
        )

    deletion_time = (
        deactivated_time
        + timedelta(days=retention_days)
    )

    current_time = datetime.now(timezone.utc)

    return current_time >= deletion_time

def delete_old_key(
    user_name: str,
    old_access_key_id: str,
    new_access_key_id: str,
    retention_days: int
) -> None:
    """
    Permanently delete the old IAM access key after
    the configured retention period has elapsed.
    """

    rotation_id = (
        f"{user_name}#"
        f"{old_access_key_id}#"
        f"{new_access_key_id}"
    )

    rotation_state = get_rotation_state(
        user_name=user_name,
        old_access_key_id=old_access_key_id,
        new_access_key_id=new_access_key_id
    )

    if not rotation_state:
        raise ValueError(
            f"Rotation not found: {rotation_id}"
        )

    if rotation_state["status"] != "OLD_KEY_DEACTIVATED":
        raise ValueError(
            f"Cannot delete old key. "
            f"Current status: "
            f"{rotation_state['status']}"
        )

    deactivated_at = rotation_state.get(
        "old_key_deactivated_at"
    )

    if not deactivated_at:
        raise ValueError(
            f"Missing old_key_deactivated_at "
            f"for rotation: {rotation_id}"
        )

    if not is_deletion_retention_complete(
        deactivated_at=deactivated_at,
        retention_days=retention_days
    ):
        print(
            f"Deletion retention period has not elapsed "
            f"for {old_access_key_id}. "
            f"Waiting {retention_days} days."
        )
        return

    access_keys = get_access_keys(user_name)

    old_key = next(
        (
            key
            for key in access_keys
            if key["AccessKeyId"] == old_access_key_id
        ),
        None
    )

    new_key = next(
        (
            key
            for key in access_keys
            if key["AccessKeyId"] == new_access_key_id
        ),
        None
    )

    if not old_key:
        raise ValueError(
            f"Old access key not found: "
            f"{old_access_key_id}"
        )

    if not new_key:
        raise ValueError(
            f"New access key not found: "
            f"{new_access_key_id}"
        )

    if old_key["Status"] != "Inactive":
        raise ValueError(
            f"Old access key is not inactive: "
            f"{old_access_key_id}"
        )

    if new_key["Status"] != "Active":
        raise ValueError(
            f"New access key is not active: "
            f"{new_access_key_id}"
        )

    print(
        f"Deleting old access key: "
        f"{old_access_key_id}"
    )

    delete_access_key(
        user_name=user_name,
        access_key_id=old_access_key_id
    )

    mark_key_deleted(
        rotation_id=rotation_id
    )

    print(
        f"Old access key deleted successfully: "
        f"{old_access_key_id}"
    )

def is_observation_period_complete(
    confirmed_at: str,
    observation_days: int
) -> bool:
    """
    Check whether the configured observation period
    has elapsed since handoff confirmation.
    """

    confirmed_time = datetime.fromisoformat(
        confirmed_at
    )

    if confirmed_time.tzinfo is None:
        confirmed_time = confirmed_time.replace(
            tzinfo=timezone.utc
        )

    deactivation_time = (
        confirmed_time
        + timedelta(days=observation_days)
    )

    current_time = datetime.now(timezone.utc)

    return current_time >= deactivation_time