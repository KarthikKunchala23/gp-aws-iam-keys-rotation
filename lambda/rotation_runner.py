from config import load_config
from rotation_engine import run_rotation
from rotation_state import confirm_handoff


CONFIG_FILE = "config.yaml"


def lambda_handler(event, context):

    print("Received event:")
    print(event)

    # --------------------------------------------------
    # API Gateway confirmation request
    # --------------------------------------------------

    route_key = event.get("routeKey", "")

    if route_key == "POST /rotations/{rotation_id}/confirm":

        path_parameters = (
            event.get("pathParameters")
            or {}
        )

        rotation_id = path_parameters.get(
            "rotation_id"
        )

        if not rotation_id:
            return {
                "statusCode": 400,
                "body": "rotation_id is required"
            }

        try:

            confirm_handoff(
                rotation_id
            )

            print(
                f"Rotation confirmed: {rotation_id}"
            )

            return {
                "statusCode": 200,
                "body": (
                    "Access key rotation confirmed "
                    "successfully. "
                    "The observation period has started."
                )
            }

        except ValueError as error:

            print(
                f"Confirmation failed: {error}"
            )

            return {
                "statusCode": 409,
                "body": str(error)
            }

    # --------------------------------------------------
    # Existing IAM key rotation workflow
    # --------------------------------------------------

    print(
        "Starting IAM access-key rotation"
    )

    config = load_config(
        CONFIG_FILE
    )

    results = run_rotation(
        config
    )

    print(
        "IAM access-key rotation completed"
    )

    return {
        "statusCode": 200,
        "body": {
            "message": (
                "IAM access-key rotation completed"
            ),
            "results": [
                {
                    **result,
                    "create_date": (
                        result[
                            "create_date"
                        ].isoformat()
                    )
                }
                for result in results
            ]
        }
    }

