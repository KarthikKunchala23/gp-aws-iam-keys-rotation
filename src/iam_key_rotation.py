import boto3


client = boto3.client("iam")


def create_access_key(user_name: str) -> dict:

    response = client.create_access_key(
        UserName=user_name
    )

    return response["AccessKey"]


def deactivate_access_key(
    user_name: str,
    access_key_id: str
) -> None:

    client.update_access_key(
        UserName=user_name,
        AccessKeyId=access_key_id,
        Status="Inactive"
    )


def rotate_access_key(
    user_name: str,
    old_access_key_id: str
) -> dict:

    new_key = create_access_key(user_name)

    deactivate_access_key(
        user_name,
        old_access_key_id
    )

    return new_key