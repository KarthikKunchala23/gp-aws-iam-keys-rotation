from config import (
    get_team_config,
    get_rotation_config
)

from validation import key_status, key_age
from iam import get_iam_users, get_access_keys

from notifications import send_rotation_notification

from rotation_state import (
    create_rotation_state,
    get_rotation_state
)

from iam_key_rotation import (
    rotate_access_key,
    deactivate_old_key,
    delete_old_key
)

def collect_rotation_results(config: dict) -> list[dict]:
    """
    Discover IAM users and access keys and determine
    their current rotation status.
    """

    rotation_config = get_rotation_config(config)
    threshold_days = rotation_config["threshold_days"]

    users = get_iam_users()
    results = []

    for user in users:
        user_name = user["UserName"]

        keys = get_access_keys(user_name)

        for key in keys:
            access_key_id = key["AccessKeyId"]
            status = key["Status"]
            create_date = key["CreateDate"]

            key_status_result = key_status(status)

            key_age_result = key_age(
                create_date,
                threshold_days
            )

            results.append({
                "user": user_name,
                "access_key_id": access_key_id,
                "status": key_status_result,
                "create_date": create_date,
                "age_days": key_age_result["age_days"],
                "rotation_status": key_age_result[
                    "rotation_status"
                ],
            })

    return results

def run_rotation(config: dict):
    results = collect_rotation_results(config)

    rotate_old_keys(results, config)

    process_deactivated_keys(results, config)

    return results


def process_deactivated_keys(
    results: list[dict],
    config: dict
):
    """
    Check inactive keys that belong to an existing
    rotation and permanently delete them when the
    configured retention period has elapsed.
    """

    rotation_config = get_rotation_config(config)

    retention_days = rotation_config[
        "deletion_retention_days"
    ]

    users = {}

    for result in results:

        user_name = result["user"]

        if user_name not in users:
            users[user_name] = []

        users[user_name].append(result)

    for user_name, keys in users.items():

        active_keys = [
            key
            for key in keys
            if key["status"] == "Active"
        ]

        inactive_keys = [
            key
            for key in keys
            if key["status"] == "Inactive"
        ]

        if len(active_keys) != 1 or not inactive_keys:
            continue

        new_key = active_keys[0]

        for old_key in inactive_keys:

            rotation_state = get_rotation_state(
                user_name=user_name,
                old_access_key_id=old_key[
                    "access_key_id"
                ],
                new_access_key_id=new_key[
                    "access_key_id"
                ]
            )

            if not rotation_state:
                continue

            print(
                f"\n{user_name}: "
                f"Existing rotation found for inactive key "
                f"{old_key['access_key_id']}"
            )

            print(
                f"  Rotation state : "
                f"{rotation_state['status']}"
            )

            if rotation_state["status"] == "OLD_KEY_DEACTIVATED":

                print(
                    f"  Checking {retention_days}-day "
                    f"deletion retention period..."
                )

                delete_old_key(
                    user_name=user_name,
                    old_access_key_id=old_key[
                        "access_key_id"
                    ],
                    new_access_key_id=new_key[
                        "access_key_id"
                    ],
                    retention_days=retention_days
                )

            elif rotation_state["status"] == "OLD_KEY_DELETED":

                print(
                    "  Old key already deleted."
                )

            else:

                print(
                    "  Old key is not ready for deletion."
                )


def rotate_old_keys(
    results: list[dict],
    config: dict
):
    """
    Process IAM users and execute the appropriate
    access-key rotation lifecycle.
    """

    print(
        "\nChecking for keys that require rotation...\n"
    )

    rotation_config = get_rotation_config(config)

    observation_days = rotation_config[
        "observation_days"
    ]

    users = {}

    for result in results:

        user_name = result["user"]

        if user_name not in users:
            users[user_name] = []

        users[user_name].append(result)

    for user_name, keys in users.items():

        active_keys = [
            key
            for key in keys
            if key["status"] == "Active"
        ]

        # --------------------------------------------------
        # CASE 1: No active keys
        # --------------------------------------------------

        if len(active_keys) == 0:

            print(
                f"{user_name}: "
                f"No active access keys found."
            )

            continue

        # --------------------------------------------------
        # CASE 2: One active key
        # --------------------------------------------------

        if len(active_keys) == 1:

            key = active_keys[0]

            if key["rotation_status"] == "ROTATION REQUIRED":

                print(
                    f"{user_name}: "
                    f"Access key {key['access_key_id']} "
                    f"is older than the rotation threshold."
                )

                try:

                    team_config = get_team_config(
                        config,
                        user_name
                    )

                except ValueError as error:

                    print(
                        f"ERROR: {error}"
                    )

                    continue

                team_name = team_config["name"]
                email = team_config["email"]

                topic_arn = config[
                    "notification"
                ][
                    "sns_topic_arn"
                ]

                print(
                    f"{user_name}: "
                    f"Team = {team_name}"
                )

                print(
                    f"{user_name}: "
                    f"Notification email = {email}"
                )

                print(
                    f"{user_name}: "
                    f"Creating replacement access key..."
                )

                rotation_result = rotate_access_key(
                    user_name=user_name,
                    old_access_key_id=key[
                        "access_key_id"
                    ],
                    team_name=team_name,
                    email=email,
                    topic_arn=topic_arn
                )

                new_key = rotation_result["new_key"]

                print(
                    f"{user_name}: "
                    f"New access key created: "
                    f"{new_key['AccessKeyId']}"
                )

            else:

                print(
                    f"{user_name}: "
                    f"Access key is within rotation period."
                )

            continue

        # --------------------------------------------------
        # CASE 3: Two active keys
        # --------------------------------------------------

        if len(active_keys) == 2:

            active_keys.sort(
                key=lambda key: key["create_date"]
            )

            old_key = active_keys[0]
            new_key = active_keys[1]

            print(
                f"\nUser: {user_name}"
            )

            print(
                f"  Old key : "
                f"{old_key['access_key_id']} "
                f"({old_key['age_days']} days)"
            )

            print(
                f"  New key : "
                f"{new_key['access_key_id']} "
                f"({new_key['age_days']} days)"
            )

            try:

                team_config = get_team_config(
                    config,
                    user_name
                )

                team_name = team_config["name"]
                email = team_config["email"]

                print(
                    f"  Team    : "
                    f"{team_name}"
                )

                print(
                    f"  Email   : "
                    f"{email}"
                )

            except ValueError as error:

                print(
                    f"  WARNING : {error}"
                )

                continue

            topic_arn = config[
                "notification"
            ][
                "sns_topic_arn"
            ]

            rotation_state = get_rotation_state(
                user_name=user_name,
                old_access_key_id=old_key[
                    "access_key_id"
                ],
                new_access_key_id=new_key[
                    "access_key_id"
                ]
            )

            # ------------------------------------------
            # Existing rotation
            # ------------------------------------------

            if rotation_state:

                status = rotation_state["status"]

                print(
                    f"  Rotation state : "
                    f"{status}"
                )

                if status == "HANDOFF_PENDING":

                    print(
                        "  Notification already sent."
                    )

                    print(
                        "  Waiting for team confirmation."
                    )

                    continue

                if status == "HANDOFF_CONFIRMED":

                    print(
                        "  Handoff confirmed."
                    )

                    print(
                        f"  Checking {observation_days}-day "
                        f"observation period..."
                    )

                    deactivate_old_key(
                        user_name=user_name,
                        old_access_key_id=old_key[
                            "access_key_id"
                        ],
                        new_access_key_id=new_key[
                            "access_key_id"
                        ],
                        observation_days=observation_days
                    )

                    continue

                if status == "OLD_KEY_DEACTIVATED":

                    print(
                        "  Old key already deactivated."
                    )

                    print(
                        "  Deletion will occur after the "
                        "configured retention period."
                    )

                    continue

                if status == "OLD_KEY_DELETED":

                    print(
                        "  Old key already deleted."
                    )

                    continue

                print(
                    f"  WARNING: Unknown rotation state: "
                    f"{status}"
                )

                continue

            # ------------------------------------------
            # No rotation state
            # ------------------------------------------

            print(
                "  No rotation state found."
            )

            print(
                "  Sending handoff notification..."
            )

            message_id = send_rotation_notification(
                topic_arn=topic_arn,
                team_name=team_name,
                email=email,
                iam_user=user_name,
                old_access_key_id=old_key[
                    "access_key_id"
                ],
                new_access_key_id=new_key[
                    "access_key_id"
                ]
            )

            print(
                f"  SNS notification sent: "
                f"{message_id}"
            )

            rotation_state = create_rotation_state(
                user_name=user_name,
                team_name=team_name,
                email=email,
                old_access_key_id=old_key[
                    "access_key_id"
                ],
                new_access_key_id=new_key[
                    "access_key_id"
                ],
                secret_arn="",
                message_id=message_id
            )

            print(
                "  Rotation state created."
            )

            print(
                f"  Status  : "
                f"{rotation_state['status']}"
            )

            print(
                "  Waiting for application/developer "
                "to switch to the new key."
            )

            continue

        # --------------------------------------------------
        # CASE 4: Unexpected state
        # --------------------------------------------------

        print(
            f"{user_name}: "
            f"Unexpected number of active keys: "
            f"{len(active_keys)}"
        )