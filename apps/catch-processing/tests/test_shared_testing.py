"""Tests for shared testing fixtures in the processing app."""

from testing.conftest import TEST_BUCKET


def test_mock_s3_client_supports_bucket_operations(mock_s3_client):
    """Shared moto-backed S3 fixture behaves like a real boto3 client."""
    mock_s3_client.put_object(
        Bucket=TEST_BUCKET,
        Key="silver/items/2026-01-15/boxscore.json",
        Body=b'{"ok": true}',
    )

    objects = mock_s3_client.list_objects_v2(Bucket=TEST_BUCKET)
    assert objects["KeyCount"] == 1
    assert objects["Contents"][0]["Key"] == "silver/items/2026-01-15/boxscore.json"
