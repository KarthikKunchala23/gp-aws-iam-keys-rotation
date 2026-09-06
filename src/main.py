from iam import get_iam_users, get_access_keys
from validation import key_status, key_age
from iam_key_rotation import rotate_access_key


def main():

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


def rotate_old_keys(results):

    print("\nChecking for keys that require rotation...\n")

    for result in results:

        if (
            result["status"] == "Active"
            and result["rotation_status"] == "ROTATION REQUIRED"
        ):

            user_name = result["user"]
            old_access_key_id = result["access_key_id"]

            print(
                f"Rotating key for user: {user_name}"
            )

            new_key = rotate_access_key(
                user_name,
                old_access_key_id
            )

            print(
                f"New access key created: "
                f"{new_key['AccessKeyId']}"
            )

            print(
                f"Old access key deactivated: "
                f"{old_access_key_id}"
            )

        elif (
            result["status"] == "Inactive"
            and result["rotation_status"] == "ROTATION REQUIRED"
        ):

            print(
                f"Skipping inactive key: "
                f"{result['access_key_id']} "
                f"for user {result['user']}"
            )


if __name__ == "__main__":

    results = main()

    print_table(results)

    rotate_old_keys(results)