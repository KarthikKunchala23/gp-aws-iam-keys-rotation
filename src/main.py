import sys

from config import load_config
from rotation_engine import run_rotation


CONFIG_FILE = "config.yaml"


def print_table(results):
    print(
        "\nUser                     Access Key ID            "
        "Status      Created        Age (Days)  Rotation Status"
    )

    print("-" * 115)

    for result in results:
        print(
            f"{result['user']:<24}"
            f"{result['access_key_id']:<25}"
            f"{result['status']:<12}"
            f"{result['create_date'].strftime('%Y-%m-%d'):<15}"
            f"{result['age_days']:<12}"
            f"{result['rotation_status']}"
        )


if __name__ == "__main__":

    config_file = (
        sys.argv[1]
        if len(sys.argv) > 1
        else CONFIG_FILE
    )

    config = load_config(config_file)

    results = run_rotation(config)
    print_table(results)