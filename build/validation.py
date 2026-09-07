import datetime


def key_status(status: str) -> str:
    """
    Checks the status of an IAM access key.
    """

    if status == "Active":
        return "Active"

    return "Inactive"


def key_age(
    create_date: datetime.datetime,
    threshold_days: int
) -> dict:
    """
    Calculate the age of an IAM access key.
    """

    current_time = datetime.datetime.now(
        datetime.timezone.utc
    )

    age = current_time - create_date
    key_age_days = age.days

    if key_age_days > threshold_days:
        rotation_status = "ROTATION REQUIRED"
    else:
        rotation_status = "KEY IS VALID"

    return {
        "age_days": key_age_days,
        "rotation_status": rotation_status,
    }