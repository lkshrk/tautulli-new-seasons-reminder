"""Tests for Tautulli API functions."""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import new_seasons_reminder.api as api


class TestMakeTautulliRequest:
    """Tests for the API helper functions."""

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_make_tautulli_request_success(self, mock_get_json):
        """Test successful API request."""
        mock_get_json.return_value = {"response": {"result": "success", "data": {"test": "data"}}}

        result = api.make_tautulli_request(
            "get_recently_added",
            {"count": 10},
            "http://localhost:8181",
            "test-api-key",
        )

        assert result == {"test": "data"}

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_make_tautulli_request_unauthorized(self, mock_get_json):
        """Test unauthorized response."""
        mock_get_json.return_value = {"response": {"result": "error", "error": "Unauthorized"}}

        result = api.make_tautulli_request(
            "get_metadata",
            {},
            "http://localhost:8181",
            "test-api-key",
        )

        assert result is None

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_make_tautulli_request_missing_config(self, mock_get_json):
        """Test missing configuration."""
        mock_get_json.return_value = None

        result = api.make_tautulli_request(
            "get_metadata",
            {},
            "",
            "test-api-key",
        )

        assert result is None

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_make_tautulli_request_http_error(self, mock_get_json):
        """Test HTTP error."""
        # Mock get_json to raise Exception
        mock_get_json.side_effect = Exception("HTTP error occurred")

        result = api.make_tautulli_request(
            "get_recently_added",
            {"count": 10},
            "http://localhost:8181",
            "test-api-key",
        )

        assert result is None

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_make_tautulli_request_url_error(self, mock_get_json):
        """Test URL error."""
        # Mock get_json to raise Exception
        mock_get_json.side_effect = Exception("URL error occurred")

        result = api.make_tautulli_request(
            "get_recently_added",
            {"count": 10},
            "http://localhost:8181",
            "test-api-key",
        )

        assert result is None

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_make_tautulli_request_invalid_json(self, mock_get_json):
        """Test invalid JSON response."""
        mock_get_json.return_value = "not json"

        result = api.make_tautulli_request(
            "get_recently_added",
            {"count": 10},
            "http://localhost:8181",
            "test-api-key",
        )

        assert result is None

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_make_tautulli_request_empty_response(self, mock_get_json):
        """Test empty response."""
        mock_get_json.return_value = {}

        result = api.make_tautulli_request(
            "get_recently_added",
            {"count": 10},
            "http://localhost:8181",
            "test-api-key",
        )

        assert result == []

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_make_tautulli_request_raw_recently_added_dict(self, mock_get_json):
        mock_get_json.return_value = {"recently_added": [{"rating_key": "season_1"}]}

        result = api.make_tautulli_request(
            "get_recently_added",
            {"count": 10},
            "http://localhost:8181",
            "test-api-key",
        )

        assert isinstance(result, dict)
        assert result["recently_added"][0]["rating_key"] == "season_1"

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_get_recently_added_success(self, mock_get_json):
        """Test get_recently_added success."""
        recent_data = [
            {
                "rating_key": "season_1",
                "title": "Season 1",
                "media_type": "season",
                "added_at": "1234567890",
            },
            {
                "rating_key": "season_2",
                "title": "Season 2",
                "media_type": "season",
                "added_at": "1234567891",
            },
        ]

        mock_get_json.return_value = {
            "response": {"result": "success", "data": {"recently_added": recent_data}}
        }

        result = api.get_recently_added("show", 10, "http://localhost:8181", "test-api-key")

        assert len(result) == 2
        assert result[0]["rating_key"] == "season_1"

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_get_recently_added_no_items(self, mock_get_json):
        """Test get_recently_added with no items."""
        mock_get_json.return_value = {
            "response": {"result": "success", "data": {"recently_added": []}}
        }

        result = api.get_recently_added("show", 10, "http://localhost:8181", "test-api-key")

        assert result == []

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_get_recently_added_missing_response(self, mock_get_json):
        """Test get_recently_added with missing response."""
        mock_get_json.return_value = {"response": {"result": "success"}}

        result = api.get_recently_added("show", 10, "http://localhost:8181", "test-api-key")

        assert result == []

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_get_metadata_success(self, mock_get_json):
        """Test get_metadata success."""
        metadata_data = {
            "rating_key": "show_1",
            "title": "Test Show",
            "media_type": "show",
            "added_at": "1234567890",
        }

        mock_get_json.return_value = {"response": {"result": "success", "data": metadata_data}}

        result = api.get_metadata("show_1", "http://localhost:8181", "test-api-key")

        assert result is not None
        assert result["rating_key"] == "show_1"

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_get_metadata_missing_response(self, mock_get_json):
        """Test get_metadata with missing response."""
        mock_get_json.return_value = {"response": {"result": "success"}}

        result = api.get_metadata("show_1", "http://localhost:8181", "test-api-key")

        assert result is None

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_get_children_metadata_success(self, mock_get_json):
        """Test get_children_metadata success."""
        children_data = [
            {
                "rating_key": "episode_1",
                "title": "Episode 1",
                "media_type": "episode",
            },
            {
                "rating_key": "episode_2",
                "title": "Episode 2",
                "media_type": "episode",
            },
        ]

        mock_get_json.return_value = {
            "response": {"result": "success", "data": {"children_list": children_data}}
        }

        result = api.get_children_metadata("season_1", "http://localhost:8181", "test-api-key")

        assert len(result) == 2
        assert result[0]["rating_key"] == "episode_1"
        params = mock_get_json.call_args.kwargs["params"]
        assert params["cmd"] == "get_children_metadata"
        assert params["rating_key"] == "season_1"
        assert params["media_type"] == "season"

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_get_children_metadata_custom_media_type(self, mock_get_json):
        mock_get_json.return_value = {
            "response": {"result": "success", "data": {"children_list": []}}
        }

        result = api.get_children_metadata(
            "show_1",
            media_type="show",
            tautulli_url="http://localhost:8181",
            tautulli_apikey="test-api-key",
        )

        assert result == []
        params = mock_get_json.call_args.kwargs["params"]
        assert params["media_type"] == "show"

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_get_children_metadata_no_items(self, mock_get_json):
        """Test get_children_metadata with no items."""
        mock_get_json.return_value = {
            "response": {"result": "success", "data": {"children_list": []}}
        }

        result = api.get_children_metadata("season_1", "http://localhost:8181", "test-api-key")

        assert result == []

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_get_children_metadata_missing_response(self, mock_get_json):
        """Test get_children_metadata with missing response."""
        mock_get_json.return_value = {"response": {"result": "success"}}

        result = api.get_children_metadata("season_1", "http://localhost:8181", "test-api-key")

        assert result == []

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_get_libraries_success(self, mock_get_json):
        mock_get_json.return_value = {
            "response": {
                "result": "success",
                "data": [{"section_id": "1", "section_name": "TV Shows"}],
            }
        }

        result = api.get_libraries("http://localhost:8181", "test-api-key")

        assert len(result) == 1
        assert result[0]["section_id"] == "1"

    @patch("new_seasons_reminder.http.HTTPClient.get_json")
    def test_get_libraries_non_list_response(self, mock_get_json):
        mock_get_json.return_value = {
            "response": {"result": "success", "data": {"unexpected": True}}
        }

        result = api.get_libraries("http://localhost:8181", "test-api-key")

        assert result == []
