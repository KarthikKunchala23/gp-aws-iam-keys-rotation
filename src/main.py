import sys

from iam import get_iam_users, get_access_keys
from validation import key_status, key_age
from iam_key_rotation import rotate_access_key
from config import load_config, get_team_config
from notifications import send_rotation_notification
from rotation_state import (
    create_rotation_state,
    get_rotation_state
)


CONFIG_FILE = "config.yaml"


def main(config: dict):

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
            key_age_result = key_age(create_date)

            results.append({
                "user": user_name,
                "access_key_id": access_key_id,
                "status": key_status_result,
                "create_date": create_date,
                "age_days": key_age_result["age_days"],
                "rotation_status": key_age_result["rotation_status"],
            })

    return results


def print_table(results):

    print()

    print(
        f"{'User':<25}"
        f"{'Access Key ID':<25}"
        f"{'Status':<12}"
        f"{'Created':<15}"
        f"{'Age (Days)':<12}"
        f"{'Rotation Status'}"
    )

    print("-" * 115)

    for result in results:

        print(
            f"{result['user']:<25}"
            f"{result['access_key_id']:<25}"
            f"{result['status']:<12}"
            f"{result['create_date'].strftime('%Y-%m-%d'):<15}"
            f"{result['age_days']:<12}"
            f"{result['rotation_status']}"
        )

    print()


def rotate_old_keys(
    results: list[dict],
    config: dict
):

    print("\nChecking for keys that require rotation...\n")

    users = {}

    # --------------------------------------------------
    # Group keys by IAM user
    # --------------------------------------------------

    for result in results:

        user_name = result["user"]

        if user_name not in users:
            users[user_name] = []

        users[user_name].append(result)

    # --------------------------------------------------
    # Process each IAM user
    # --------------------------------------------------

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

                # ------------------------------------------
                # Get team configuration
                # ------------------------------------------

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

                # ------------------------------------------
                # Create replacement key
                # ------------------------------------------

                rotation_result = rotate_access_key(
                    user_name=user_name,
                    old_access_key_id=key["access_key_id"],
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

            # ------------------------------------------
            # Sort oldest -> newest
            # ------------------------------------------

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

            # ------------------------------------------
            # Get team configuration
            # ------------------------------------------

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

            # ------------------------------------------
            # Check DynamoDB rotation state
            # ------------------------------------------

            rotation_state = get_rotation_state(
                user_name=user_name,
                old_access_key_id=old_key["access_key_id"],
                new_access_key_id=new_key["access_key_id"]
            )

            # ------------------------------------------
            # Rotation already exists
            # ------------------------------------------

            if rotation_state:

                print(
                    f"  Rotation state : "
                    f"{rotation_state['status']}"
                )

                print(
                    f"  Notification already sent."
                )

                print(
                    f"  Waiting for team confirmation."
                )

                continue

            # ------------------------------------------
            # No rotation state
            #
            # This can happen when:
            #
            # - A replacement key was created before
            #   DynamoDB state tracking was implemented
            #
            # - The rotation state was lost
            #
            # - This is an externally-created second key
            # ------------------------------------------

            print(
                f"  No rotation state found."
            )

            print(
                f"  Sending handoff notification..."
            )

            # ------------------------------------------
            # Send SNS notification
            # ------------------------------------------

            message_id = send_rotation_notification(
                topic_arn=topic_arn,
                team_name=team_name,
                iam_user=user_name,
                old_access_key_id=old_key["access_key_id"],
                new_access_key_id=new_key["access_key_id"]
            )

            print(
                f"  SNS notification sent: "
                f"{message_id}"
            )

            # ------------------------------------------
            # Create DynamoDB rotation state
            # ------------------------------------------

            rotation_state = create_rotation_state(
                user_name=user_name,
                team_name=team_name,
                email=email,
                old_access_key_id=old_key["access_key_id"],
                new_access_key_id=new_key["access_key_id"],
                secret_arn="",
                message_id=message_id
            )

            print(
                f"  Rotation state created."
            )

            print(
                f"  Status  : "
                f"{rotation_state['status']}"
            )

            print(
                f"  Waiting for application/developer "
                f"to switch to the new key."
            )

            continue

        # --------------------------------------------------
        # CASE 4: Unexpected state
        # --------------------------------------------------

        else:

            print(
                f"{user_name}: "
                f"Unexpected number of active keys: "
                f"{len(active_keys)}"
            )


if __name__ == "__main__":

    # ------------------------------------------------------
    # Load configuration
    # ------------------------------------------------------

    if len(sys.argv) > 1:

        config_file = sys.argv[1]

    else:

        config_file = CONFIG_FILE

    config = load_config(
        config_file
    )

    # ------------------------------------------------------
    # Get current IAM state
    # ------------------------------------------------------

    results = main(
        config
    )

    # ------------------------------------------------------
    # Display current state
    # ------------------------------------------------------

    print_table(
        results
    )

    # ------------------------------------------------------
    # Process rotation
    # ------------------------------------------------------

    rotate_old_keys(
        results,
        config
    )