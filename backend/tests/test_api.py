"""
Tests for the FastAPI endpoints.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# We need to mock environment variables before importing main
import os
os.environ["BRAWL_API_KEY"] = "test_brawl_key"
os.environ["OPENROUTER_API_KEY"] = "test_openrouter_key"

from main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root_endpoint(self, client):
        """Root endpoint should return health status."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_endpoint(self, client):
        """Health endpoint should return detailed status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data
        assert "cache" in data


class TestPlayerEndpoint:
    """Tests for the player stats endpoint."""

    def test_invalid_tag_format(self, client):
        """Invalid tag format should return 400."""
        response = client.get("/api/player/INVALID!")
        assert response.status_code == 400
        assert "Invalid tag format" in response.json()["detail"]

    def test_empty_tag(self, client):
        """Empty tag should return 400."""
        response = client.get("/api/player/   ")
        assert response.status_code == 400

    @patch("main.brawl_client.get_player")
    @patch("main.brawl_client.get_battle_log")
    @patch("main.ai_agent.analyze_profile")
    def test_successful_player_fetch(
        self, mock_analyze, mock_battles, mock_player, client
    ):
        """Successful request should return player data and insights."""
        mock_player.return_value = {
            "tag": "#9L9GVUC2",
            "name": "TestPlayer",
            "trophies": 30000,
            "3vs3Victories": 1000,
            "soloVictories": 500,
            "duoVictories": 300,
            "brawlers": [],
        }
        mock_battles.return_value = {"items": []}
        mock_analyze.return_value = "# AI Insights\n\nGreat player!"

        response = client.get("/api/player/9L9GVUC2")

        assert response.status_code == 200
        data = response.json()
        assert "player" in data
        assert "battles" in data
        assert "insights" in data
        assert data["player"]["name"] == "TestPlayer"

    @patch("main.brawl_client.get_player")
    def test_player_not_found(self, mock_player, client):
        """Player not found should return 404."""
        from exceptions import PlayerNotFoundError
        mock_player.side_effect = PlayerNotFoundError()

        response = client.get("/api/player/9L9GVUC2")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestCacheEndpoints:
    """Tests for cache management endpoints."""

    def test_cache_stats(self, client):
        """Cache stats endpoint should return statistics."""
        response = client.get("/api/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert "player_cache" in data
        assert "insights_cache" in data

    @patch("main.cache.clear_player")
    def test_clear_player_cache(self, mock_clear, client):
        """Clear cache endpoint should work for valid tags."""
        response = client.delete("/api/cache/9L9GVUC2")
        assert response.status_code == 200
        mock_clear.assert_called_once()

    def test_clear_cache_invalid_tag(self, client):
        """Clear cache with invalid tag should return 400."""
        response = client.delete("/api/cache/INVALID!")
        assert response.status_code == 400


class TestAPIVersioning:
    """Tests for API versioning."""

    @patch("main.brawl_client.get_player")
    @patch("main.brawl_client.get_battle_log")
    @patch("main.ai_agent.analyze_profile")
    def test_v1_endpoint_alias(
        self, mock_analyze, mock_battles, mock_player, client
    ):
        """V1 endpoint should work as alias."""
        mock_player.return_value = {
            "tag": "#9L9GVUC2",
            "name": "TestPlayer",
            "trophies": 30000,
            "3vs3Victories": 1000,
            "soloVictories": 500,
            "duoVictories": 300,
            "brawlers": [],
        }
        mock_battles.return_value = {"items": []}
        mock_analyze.return_value = "# AI Insights"

        response = client.get("/api/v1/player/9L9GVUC2")

        assert response.status_code == 200
        assert "player" in response.json()


class TestCORSHeaders:
    """Tests for CORS configuration."""

    def test_cors_preflight(self, client):
        """CORS preflight request should be handled."""
        response = client.options(
            "/api/player/test",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI returns 200 for OPTIONS
        assert response.status_code in [200, 400]
