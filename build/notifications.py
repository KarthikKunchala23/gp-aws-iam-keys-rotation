import boto3


client = boto3.client("sns")


def send_rotation_notification(
    topic_arn: str,
    team_name: str,
    email: str,
    iam_user: str,
    old_access_key_id: str,
    new_access_key_id: str,
    confirmation_url: str
) -> str:

    subject = (
        f"AWS IAM Access Key Rotation Required - "
        f"{iam_user}"
    )

    message = f"""
AWS IAM Access Key Rotation Required

Team: {team_name}
IAM User: {iam_user}

Old Access Key:
{old_access_key_id}

New Access Key:
{new_access_key_id}


ACTION REQUIRED
---------------

1. Update your application/service to use the
   new access key.

2. Verify that the application is working correctly.

3. Confirm the key handoff using the HTTPS endpoint:

{confirmation_url}


IMPORTANT
---------

Do NOT manually deactivate or delete the old
access key.

After confirmation, the rotation system will:

1. Wait for the configured observation period.
2. Deactivate the old access key.
3. Wait for the configured deletion retention period.
4. Permanently delete the old access key.


Rotation lifecycle:

HANDOFF_PENDING
       |
       | HTTPS confirmation
       v
HANDOFF_CONFIRMED
       |
       | Observation period
       v
OLD_KEY_DEACTIVATED
       |
       | Deletion retention
       v
OLD_KEY_DELETED
"""

    response = client.publish(
        TopicArn=topic_arn,
        Subject=subject,
        Message=message
    )

    return response["MessageId"]