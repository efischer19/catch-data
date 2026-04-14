"""Tests for shared testing fixtures in the ingestion app."""

import pytest
import requests


def test_mock_mlb_client_returns_frozen_schedule(mock_mlb_client):
    """Shared mock MLB client returns frozen schedule data by default."""
    schedule = mock_mlb_client.get_schedule(2025)
    assert schedule["dates"][0]["games"][0]["gamePk"] == 751001


@pytest.mark.parametrize("behavior", ["404", "500", "timeout"])
def test_mock_mlb_client_supports_failure_modes(mock_mlb_client, behavior):
    """Shared mock MLB client supports common failure scenarios."""
    mock_mlb_client.set_behavior("boxscore", behavior)

    if behavior == "timeout":
        with pytest.raises(requests.Timeout):
            mock_mlb_client.get_boxscore(752400)
    else:
        with pytest.raises(requests.HTTPError) as exc_info:
            mock_mlb_client.get_boxscore(752400)
        assert exc_info.value.response is not None
        assert exc_info.value.response.status_code == int(behavior)
