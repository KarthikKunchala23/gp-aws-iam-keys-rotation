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