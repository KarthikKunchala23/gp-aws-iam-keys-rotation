from config import load_config
from rotation_engine import run_rotation


CONFIG_FILE = "config.yaml"


def lambda_handler(event, context):
    print("Starting IAM access-key rotation")

    config = load_config(CONFIG_FILE)

    results = run_rotation(config)

    print("IAM access-key rotation completed")

    return {
        "statusCode": 200,
        "body": {
            "message": "IAM access-key rotation completed",
            "results": [
                {
                    **result,
                    "create_date": result["create_date"].isoformat()
                }
                for result in results
            ]
        }
    }