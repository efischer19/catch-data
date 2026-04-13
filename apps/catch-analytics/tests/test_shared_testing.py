"""Tests for shared testing fixtures in the analytics app."""


def test_mock_mlb_client_fixture_can_swap_content_variants(mock_mlb_client):
    """Shared MLB mock can switch to alternate frozen content fixtures."""
    mock_mlb_client.set_behavior(
        "content",
        "success",
        fixture_name="content_no_video.json",
    )

    content = mock_mlb_client.get_content(752101)
    epg_titles = [entry["title"] for entry in content["media"]["epg"]]

    assert "Extended Highlights" not in epg_titles
