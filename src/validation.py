import datetime


ROTATION_THRESHOLD = 15


def key_status(status: str) -> str:
    """
    Checks the status of an IAM access key.

    Args:
        status: Access key status returned by AWS.

    Returns:
        str: Status of the access key.
    """

    if status == "Active":
        return "Active"

    return "Inactive"


def key_age(create_date: datetime.datetime) -> dict:
    """
    Calculate the age of an IAM access key.

    Args:
        create_date: Access key creation date returned by AWS.

    Returns:
        dict: Key age and rotation status.
    """

    current_time = datetime.datetime.now(datetime.timezone.utc)

    age = current_time - create_date
    key_age_days = age.days

    if key_age_days > ROTATION_THRESHOLD:
        rotation_status = "ROTATION REQUIRED"
    else:
        rotation_status = "KEY IS VALID"

    return {
        "age_days": key_age_days,
        "rotation_status": rotation_status,
    }