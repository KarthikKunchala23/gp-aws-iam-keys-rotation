import boto3
import json


client = boto3.client('secretsmanager')

def store_access_key(
        user_name: str,
        access_key: dict
) -> str:

    secret_name = f"iam/{user_name}/access-key"

    secret_value = {
        "AccessKeyId": access_key["AccessKeyId"],
        "SecretAccessKey": access_key["SecretAccessKey"]
    }

    try:
        response = client.put_secret_value(
            SecretId = secret_name,
            SecretString = json.dumps(secret_value)
         )

        return response["ARN"]
    
    except client.exceptions.ResourceNotFoundException:
        response = client.create_secret(
            Name = secret_name,
            SecretString = json.dumps(secret_value)
        )

        return response["ARN"]
