"""
Brawl Stars API Client.
Handles communication with the official Brawl Stars API.
"""

import re
import logging
from typing import Any

import requests

from exceptions import (
    PlayerNotFoundError,
    InvalidTagError,
    RateLimitError,
    BrawlStarsAPIError,
    MaintenanceError,
)

logger = logging.getLogger(__name__)

# Valid Brawl Stars tag characters
TAG_PATTERN = re.compile(r'^[0289PYLQGRJCUV]{3,12}$', re.IGNORECASE)


class BrawlStarsClient:
    """Client for interacting with the Brawl Stars API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.brawlstars.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        self.timeout = 10  # seconds

    @staticmethod
    def validate_tag(tag: str) -> str:
        """
        Validate and clean a player tag.

        Args:
            tag: The player tag to validate (with or without #)

        Returns:
            The cleaned tag (uppercase, no #)

        Raises:
            InvalidTagError: If the tag format is invalid
        """
        clean_tag = tag.upper().replace("#", "").strip()

        if not clean_tag:
            raise InvalidTagError("Player tag cannot be empty")

        if not TAG_PATTERN.match(clean_tag):
            raise InvalidTagError(
                f"Invalid tag format: '{tag}'. "
                "Tags can only contain: 0, 2, 8, 9, P, Y, L, Q, G, R, J, C, U, V"
            )

        return clean_tag

    def _format_tag(self, tag: str) -> str:
        """
        Format a tag for API URL (URL-encoded with %23 prefix).

        Args:
            tag: The clean tag (already validated)

        Returns:
            URL-encoded tag with %23 prefix
        """
        return f"%23{tag}"

    def _make_request(self, endpoint: str) -> dict[str, Any]:
        """
        Make a GET request to the Brawl Stars API.

        Args:
            endpoint: The API endpoint (e.g., /players/%23TAG)

        Returns:
            The JSON response as a dictionary

        Raises:
            PlayerNotFoundError: If the player doesn't exist
            RateLimitError: If rate limited by the API
            MaintenanceError: If the API is under maintenance
            BrawlStarsAPIError: For other API errors
        """
        url = f"{self.base_url}{endpoint}"

        try:
            logger.debug(f"Making request to: {url}")
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )

            if response.status_code == 200:
                return response.json()

            if response.status_code == 404:
                raise PlayerNotFoundError("Player not found. Check the tag and try again.")

            if response.status_code == 429:
                raise RateLimitError("Brawl Stars API rate limit exceeded")

            if response.status_code == 503:
                raise MaintenanceError()

            if response.status_code == 403:
                logger.error(f"API key invalid or unauthorized: {response.text}")
                raise BrawlStarsAPIError("API authentication failed")

            # Generic error for other status codes
            logger.error(f"API error {response.status_code}: {response.text}")
            raise BrawlStarsAPIError(f"API returned status {response.status_code}")

        except requests.exceptions.Timeout:
            logger.error("Request to Brawl Stars API timed out")
            raise BrawlStarsAPIError("Request timed out")
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to Brawl Stars API")
            raise BrawlStarsAPIError("Failed to connect to Brawl Stars API")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise BrawlStarsAPIError(str(e))

    def get_player(self, tag: str) -> dict[str, Any]:
        """
        Fetch player information by tag.

        Args:
            tag: The player tag (with or without #)

        Returns:
            Player data dictionary

        Raises:
            InvalidTagError: If tag format is invalid
            PlayerNotFoundError: If player doesn't exist
            BrawlStarsAPIError: For API errors
        """
        clean_tag = self.validate_tag(tag)
        formatted_tag = self._format_tag(clean_tag)

        logger.info(f"Fetching player data for tag: {clean_tag}")
        return self._make_request(f"/players/{formatted_tag}")

    def get_battle_log(self, tag: str) -> dict[str, Any]:
        """
        Fetch recent battle log for the player.

        Args:
            tag: The player tag (with or without #)

        Returns:
            Battle log dictionary with 'items' list

        Raises:
            InvalidTagError: If tag format is invalid
            PlayerNotFoundError: If player doesn't exist
            BrawlStarsAPIError: For API errors
        """
        clean_tag = self.validate_tag(tag)
        formatted_tag = self._format_tag(clean_tag)

        logger.info(f"Fetching battle log for tag: {clean_tag}")
        return self._make_request(f"/players/{formatted_tag}/battlelog")

    # =========================================================================
    # CLUB ENDPOINTS
    # =========================================================================

    def get_club(self, club_tag: str) -> dict[str, Any]:
        """
        Fetch club information by tag.

        Args:
            club_tag: The club tag (with or without #)

        Returns:
            Club data dictionary containing:
            - tag, name, description, type
            - badgeId, requiredTrophies
            - trophies, members (list)

        Raises:
            InvalidTagError: If tag format is invalid
            PlayerNotFoundError: If club doesn't exist
            BrawlStarsAPIError: For API errors
        """
        clean_tag = self.validate_tag(club_tag)
        formatted_tag = self._format_tag(clean_tag)

        logger.info(f"Fetching club data for tag: {clean_tag}")
        return self._make_request(f"/clubs/{formatted_tag}")

    def get_club_members(self, club_tag: str) -> dict[str, Any]:
        """
        Fetch club members list.

        Args:
            club_tag: The club tag (with or without #)

        Returns:
            Dictionary with 'items' list of members, each containing:
            - tag, name, nameColor, role
            - trophies, icon

        Raises:
            InvalidTagError: If tag format is invalid
            PlayerNotFoundError: If club doesn't exist
            BrawlStarsAPIError: For API errors
        """
        clean_tag = self.validate_tag(club_tag)
        formatted_tag = self._format_tag(clean_tag)

        logger.info(f"Fetching club members for tag: {clean_tag}")
        return self._make_request(f"/clubs/{formatted_tag}/members")

    # =========================================================================
    # BRAWLERS ENDPOINTS
    # =========================================================================

    def get_all_brawlers(self) -> dict[str, Any]:
        """
        Fetch list of all available brawlers with their stats.

        Returns:
            Dictionary with 'items' list of brawlers, each containing:
            - id, name, starPowers, gadgets
            - Stats can be used for game knowledge

        Raises:
            BrawlStarsAPIError: For API errors
        """
        logger.info("Fetching all brawlers data")
        return self._make_request("/brawlers")

    def get_brawler_details(self, brawler_id: int) -> dict[str, Any]:
        """
        Fetch detailed information about a specific brawler.

        Args:
            brawler_id: The brawler ID (numeric)

        Returns:
            Brawler data dictionary containing:
            - id, name, starPowers, gadgets

        Raises:
            PlayerNotFoundError: If brawler doesn't exist
            BrawlStarsAPIError: For API errors
        """
        logger.info(f"Fetching brawler details for ID: {brawler_id}")
        return self._make_request(f"/brawlers/{brawler_id}")

    # =========================================================================
    # EVENTS ENDPOINT
    # =========================================================================

    def get_event_rotation(self) -> dict[str, Any]:
        """
        Fetch current event rotation (active and upcoming events).

        Returns:
            Dictionary with event rotation data containing:
            - Active events with mode, map, modifiers
            - Scheduled times for rotation

        Raises:
            BrawlStarsAPIError: For API errors
        """
        logger.info("Fetching event rotation")
        return self._make_request("/events/rotation")

    # =========================================================================
    # RANKINGS ENDPOINTS
    # =========================================================================

    def get_player_rankings(
        self,
        country_code: str = "global",
        limit: int = 200
    ) -> dict[str, Any]:
        """
        Fetch top player rankings by country or global.

        Args:
            country_code: Two-letter country code or 'global'
            limit: Number of players to fetch (max 200)

        Returns:
            Dictionary with 'items' list of top players, each containing:
            - tag, name, nameColor, icon
            - trophies, rank, club

        Raises:
            BrawlStarsAPIError: For API errors
        """
        logger.info(f"Fetching player rankings for: {country_code}")
        endpoint = f"/rankings/{country_code}/players"
        if limit and limit < 200:
            endpoint += f"?limit={limit}"
        return self._make_request(endpoint)

    def get_club_rankings(
        self,
        country_code: str = "global",
        limit: int = 200
    ) -> dict[str, Any]:
        """
        Fetch top club rankings by country or global.

        Args:
            country_code: Two-letter country code or 'global'
            limit: Number of clubs to fetch (max 200)

        Returns:
            Dictionary with 'items' list of top clubs, each containing:
            - tag, name, badgeId
            - trophies, rank, memberCount

        Raises:
            BrawlStarsAPIError: For API errors
        """
        logger.info(f"Fetching club rankings for: {country_code}")
        endpoint = f"/rankings/{country_code}/clubs"
        if limit and limit < 200:
            endpoint += f"?limit={limit}"
        return self._make_request(endpoint)

    def get_brawler_rankings(
        self,
        brawler_id: int,
        country_code: str = "global",
        limit: int = 200
    ) -> dict[str, Any]:
        """
        Fetch top players for a specific brawler.

        Args:
            brawler_id: The brawler ID (numeric)
            country_code: Two-letter country code or 'global'
            limit: Number of players to fetch (max 200)

        Returns:
            Dictionary with 'items' list of top players for this brawler,
            each containing:
            - tag, name, nameColor, icon
            - trophies, rank, club

        Raises:
            BrawlStarsAPIError: For API errors
        """
        logger.info(f"Fetching brawler rankings for ID {brawler_id} in {country_code}")
        endpoint = f"/rankings/{country_code}/brawlers/{brawler_id}"
        if limit and limit < 200:
            endpoint += f"?limit={limit}"
        return self._make_request(endpoint)

    def get_powerplay_rankings(
        self,
        country_code: str = "global",
        season_id: str = None,
        limit: int = 200
    ) -> dict[str, Any]:
        """
        Fetch Power Play season rankings.

        Args:
            country_code: Two-letter country code or 'global'
            season_id: Season ID (optional, defaults to current)
            limit: Number of players to fetch (max 200)

        Returns:
            Dictionary with 'items' list of top Power Play players

        Raises:
            BrawlStarsAPIError: For API errors
        """
        logger.info(f"Fetching Power Play rankings for: {country_code}")
        if season_id:
            endpoint = f"/rankings/{country_code}/powerplay/seasons/{season_id}"
        else:
            endpoint = f"/rankings/{country_code}/powerplay/seasons"
        if limit and limit < 200:
            endpoint += f"?limit={limit}"
        return self._make_request(endpoint)
