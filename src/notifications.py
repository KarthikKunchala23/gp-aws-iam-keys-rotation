import boto3


client = boto3.client("sns")


def send_rotation_notification(
    topic_arn: str,
    team_name: str,
    iam_user: str,
    old_access_key_id: str,
    new_access_key_id: str
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

Action Required:

Please update your application/service to use
the new access key.

Do NOT delete or deactivate the old key yet.

Once the application has been updated,
confirm the handoff through the provided
rotation confirmation process.

The old access key will only be retired
after the handoff has been confirmed.

"""

    response = client.publish(
        TopicArn=topic_arn,
        Subject=subject,
        Message=message
    )

    return response["MessageId"]