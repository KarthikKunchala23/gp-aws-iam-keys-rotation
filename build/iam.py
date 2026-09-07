import boto3

client = boto3.client("iam")


def get_iam_users() -> list[dict]:
    """
    Lists all IAM users.

    Returns:
        list[dict]: List of IAM user objects.
    """
    response = client.list_users()

    return response["Users"]

def get_access_keys(user: str) -> list[dict]:
    """
    Args:
        user: IAM username

    Returns:
        list[dict]: List of IAM access key details
    """

    paginator = client.get_paginator("list_access_keys")

    keys = []

    for page in paginator.paginate(UserName=user):
        keys.extend(page["AccessKeyMetadata"])

    return keys

def deactivate_access_key(
    user_name: str,
    access_key_id: str
) -> None:

    client.update_access_key(
        UserName=user_name,
        AccessKeyId=access_key_id,
        Status="Inactive"
    )

def delete_access_key(
    user_name: str,
    access_key_id: str
) -> None:
    """
    Permanently delete an IAM access key.
    """

    client.delete_access_key(
        UserName=user_name,
        AccessKeyId=access_key_id
    )