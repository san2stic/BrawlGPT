"""
Tests for the Brawl Stars API client.
"""

import pytest
from unittest.mock import Mock, patch

from brawlstars import BrawlStarsClient
from exceptions import (
    InvalidTagError,
    PlayerNotFoundError,
    RateLimitError,
    BrawlStarsAPIError,
)


class TestTagValidation:
    """Tests for player tag validation."""

    def test_valid_tag_uppercase(self):
        """Valid uppercase tag should pass."""
        result = BrawlStarsClient.validate_tag("9L9GVUC2")
        assert result == "9L9GVUC2"

    def test_valid_tag_lowercase(self):
        """Valid lowercase tag should be converted to uppercase."""
        result = BrawlStarsClient.validate_tag("9l9gvuc2")
        assert result == "9L9GVUC2"

    def test_valid_tag_with_hash(self):
        """Tag with # prefix should be cleaned."""
        result = BrawlStarsClient.validate_tag("#9L9GVUC2")
        assert result == "9L9GVUC2"

    def test_valid_tag_with_spaces(self):
        """Tag with surrounding spaces should be trimmed."""
        result = BrawlStarsClient.validate_tag("  9L9GVUC2  ")
        assert result == "9L9GVUC2"

    def test_empty_tag_raises_error(self):
        """Empty tag should raise InvalidTagError."""
        with pytest.raises(InvalidTagError) as exc_info:
            BrawlStarsClient.validate_tag("")
        assert "cannot be empty" in str(exc_info.value.message)

    def test_whitespace_only_tag_raises_error(self):
        """Whitespace-only tag should raise InvalidTagError."""
        with pytest.raises(InvalidTagError):
            BrawlStarsClient.validate_tag("   ")

    def test_invalid_characters_raise_error(self):
        """Tag with invalid characters should raise InvalidTagError."""
        with pytest.raises(InvalidTagError) as exc_info:
            BrawlStarsClient.validate_tag("INVALID1")
        assert "Invalid tag format" in str(exc_info.value.message)

    def test_tag_too_short_raises_error(self):
        """Tag shorter than 3 characters should raise InvalidTagError."""
        with pytest.raises(InvalidTagError):
            BrawlStarsClient.validate_tag("9L")

    def test_tag_too_long_raises_error(self):
        """Tag longer than 12 characters should raise InvalidTagError."""
        with pytest.raises(InvalidTagError):
            BrawlStarsClient.validate_tag("9L9GVUC29L9GV")


class TestBrawlStarsClient:
    """Tests for the BrawlStarsClient class."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return BrawlStarsClient("test_api_key")

    def test_client_initialization(self, client):
        """Client should be properly initialized."""
        assert client.api_key == "test_api_key"
        assert client.base_url == "https://api.brawlstars.com/v1"
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test_api_key"

    def test_format_tag(self, client):
        """Tag formatting should add %23 prefix."""
        result = client._format_tag("9L9GVUC2")
        assert result == "%239L9GVUC2"

    @patch("brawlstars.requests.get")
    def test_get_player_success(self, mock_get, client):
        """Successful player fetch should return data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tag": "#9L9GVUC2",
            "name": "TestPlayer",
            "trophies": 30000,
        }
        mock_get.return_value = mock_response

        result = client.get_player("9L9GVUC2")

        assert result["name"] == "TestPlayer"
        assert result["trophies"] == 30000
        mock_get.assert_called_once()

    @patch("brawlstars.requests.get")
    def test_get_player_not_found(self, mock_get, client):
        """404 response should raise PlayerNotFoundError."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_get.return_value = mock_response

        with pytest.raises(PlayerNotFoundError):
            client.get_player("9L9GVUC2")

    @patch("brawlstars.requests.get")
    def test_get_player_rate_limited(self, mock_get, client):
        """429 response should raise RateLimitError."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Too many requests"
        mock_get.return_value = mock_response

        with pytest.raises(RateLimitError):
            client.get_player("9L9GVUC2")

    @patch("brawlstars.requests.get")
    def test_get_player_timeout(self, mock_get, client):
        """Timeout should raise BrawlStarsAPIError."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()

        with pytest.raises(BrawlStarsAPIError) as exc_info:
            client.get_player("9L9GVUC2")
        assert "timed out" in str(exc_info.value.message)

    @patch("brawlstars.requests.get")
    def test_get_battle_log_success(self, mock_get, client):
        """Successful battle log fetch should return data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {"battleTime": "20240101T120000.000Z", "event": {"mode": "gemGrab"}}
            ]
        }
        mock_get.return_value = mock_response

        result = client.get_battle_log("9L9GVUC2")

        assert "items" in result
        assert len(result["items"]) == 1


class TestTagFormatValidation:
    """Additional tests for tag format edge cases."""

    @pytest.mark.parametrize(
        "tag",
        [
            "029",
            "PYLQ",
            "GRJCUV",
            "0289PYLQGRJC",  # 12 chars max
        ],
    )
    def test_all_valid_characters(self, tag):
        """All valid Brawl Stars tag characters should be accepted."""
        result = BrawlStarsClient.validate_tag(tag)
        assert result == tag.upper()

    @pytest.mark.parametrize(
        "invalid_tag",
        [
            "ABC",  # A, B, C not valid
            "123",  # 1, 3 not valid
            "XYZ",  # X, Y (but not this Y), Z not valid
            "!!!",  # special characters
        ],
    )
    def test_invalid_character_combinations(self, invalid_tag):
        """Invalid character combinations should be rejected."""
        with pytest.raises(InvalidTagError):
            BrawlStarsClient.validate_tag(invalid_tag)
