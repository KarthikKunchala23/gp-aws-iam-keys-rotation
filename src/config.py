import yaml


def load_config(config_file: str) -> dict:

    with open(config_file, "r") as file:
        return yaml.safe_load(file)


def get_team_config(
    config: dict,
    iam_user: str
) -> dict:

    for team in config["teams"]:

        if team["iam_user"] == iam_user:
            return team

    raise ValueError(
        f"No team configuration found for IAM user: {iam_user}"
    )