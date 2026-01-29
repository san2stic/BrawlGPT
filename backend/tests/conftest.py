"""
Pytest configuration and fixtures.
"""

import os
import pytest

# Set test environment variables before any imports
os.environ["BRAWL_API_KEY"] = "test_brawl_api_key"
os.environ["OPENROUTER_API_KEY"] = "test_openrouter_api_key"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000,http://localhost:5173"


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset cache before each test."""
    from cache import cache
    cache.clear_all()
    yield
    cache.clear_all()


@pytest.fixture
def sample_player_data():
    """Sample player data for tests."""
    return {
        "tag": "#9L9GVUC2",
        "name": "TestPlayer",
        "nameColor": "0xff1ba5f5",
        "trophies": 30000,
        "highestTrophies": 35000,
        "expLevel": 150,
        "expPoints": 100000,
        "isQualifiedFromChampionshipChallenge": False,
        "3vs3Victories": 5000,
        "soloVictories": 1000,
        "duoVictories": 800,
        "club": {"tag": "#TEST", "name": "Test Club"},
        "brawlers": [
            {
                "id": 1,
                "name": "Shelly",
                "power": 11,
                "rank": 25,
                "trophies": 750,
                "highestTrophies": 800,
            },
            {
                "id": 2,
                "name": "Colt",
                "power": 10,
                "rank": 22,
                "trophies": 650,
                "highestTrophies": 700,
            },
        ],
    }


@pytest.fixture
def sample_battle_log():
    """Sample battle log for tests."""
    return {
        "items": [
            {
                "battleTime": "20240101T120000.000Z",
                "event": {"id": 1, "mode": "gemGrab", "map": "Hard Rock Mine"},
                "battle": {
                    "mode": "gemGrab",
                    "type": "ranked",
                    "result": "victory",
                    "duration": 120,
                    "trophyChange": 8,
                    "starPlayer": {
                        "tag": "#9L9GVUC2",
                        "name": "TestPlayer",
                        "brawler": {"name": "Shelly"},
                    },
                },
            },
            {
                "battleTime": "20240101T110000.000Z",
                "event": {"id": 2, "mode": "brawlBall", "map": "Backyard Bowl"},
                "battle": {
                    "mode": "brawlBall",
                    "type": "ranked",
                    "result": "defeat",
                    "duration": 90,
                    "trophyChange": -3,
                },
            },
        ]
    }
