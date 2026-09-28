from unittest.mock import patch

from iam_key_rotation import rotate_access_key


@patch("iam_key_rotation.create_rotation_state")
@patch("iam_key_rotation.send_rotation_notification")
@patch("iam_key_rotation.store_access_key")
@patch("iam_key_rotation.create_access_key")
def test_rotate_access_key(
    mock_create_access_key,
    mock_store_access_key,
    mock_send_notification,
    mock_create_rotation_state,
):

    mock_create_access_key.return_value = {
        "AccessKeyId": "NEWKEY123",
        "SecretAccessKey": "SECRET123",
    }

    mock_store_access_key.return_value = (
        "arn:aws:secretsmanager:ap-south-1:123456789012:"
        "secret:iam/test/access-key"
    )

    mock_send_notification.return_value = "sns-message-123"

    mock_create_rotation_state.return_value = {
        "status": "HANDOFF_PENDING"
    }

    result = rotate_access_key(
        user_name="test-user",
        old_access_key_id="OLDKEY123",
        team_name="platform",
        email="test@example.com",
        topic_arn="arn:aws:sns:ap-south-1:123456789012:test-topic",
        confirmation_api_base_url=(
            "https://example.execute-api.ap-south-1.amazonaws.com"
        ),
    )

    expected_rotation_id = (
        "test-user#OLDKEY123#NEWKEY123"
    )

    expected_confirmation_url = (
        "https://example.execute-api.ap-south-1.amazonaws.com"
        f"/rotations/{expected_rotation_id}/confirm"
    )

    mock_create_access_key.assert_called_once_with(
        "test-user"
    )

    mock_store_access_key.assert_called_once_with(
        "test-user",
        {
            "AccessKeyId": "NEWKEY123",
            "SecretAccessKey": "SECRET123",
        },
    )

    mock_send_notification.assert_called_once_with(
        topic_arn=(
            "arn:aws:sns:ap-south-1:123456789012:test-topic"
        ),
        team_name="platform",
        email="test@example.com",
        iam_user="test-user",
        old_access_key_id="OLDKEY123",
        new_access_key_id="NEWKEY123",
        confirmation_url=expected_confirmation_url,
    )

    mock_create_rotation_state.assert_called_once_with(
        user_name="test-user",
        team_name="platform",
        email="test@example.com",
        old_access_key_id="OLDKEY123",
        new_access_key_id="NEWKEY123",
        secret_arn=(
            "arn:aws:secretsmanager:ap-south-1:123456789012:"
            "secret:iam/test/access-key"
        ),
        message_id="sns-message-123",
        rotation_id=expected_rotation_id,
    )