"""TVDB (TheTVDB) metadata provider.

Note: TVDB API v4 requires a paid subscription for full functionality.
This provider implements basic functionality with API key authentication.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError

from new_seasons_reminder.http import HTTPClient
from new_seasons_reminder.metadata.base import ExternalMetadataProvider

if TYPE_CHECKING:
    from new_seasons_reminder.metadata.base import ExternalMetadataProvider

logger = logging.getLogger(__name__)


class TVDBMetadataProvider(ExternalMetadataProvider):
    """TVDB metadata provider implementation.

    Note: TheTVDB v4 API now requires a paid subscription for full access.
    Basic API key authentication is available but may have limited functionality.
    """

    BASE_URL = "https://api4.thetvdb.com/v4"

    def __init__(
        self,
        tvdb_apikey: str,
        http_client: HTTPClient | None = None,
    ):
        """Initialize TVDB metadata provider.

        Args:
            tvdb_apikey: TVDB API key
            http_client: Optional HTTP client (for testing)
        """
        self.tvdb_apikey = tvdb_apikey
        self._http_client = http_client or HTTPClient()
        self._auth_token: str | None = None

    def _ensure_auth(self) -> bool:
        """Ensure we have an auth token.

        Returns:
            True if auth successful, False otherwise
        """
        if self._auth_token:
            return True

        logger.debug("Authenticating to TVDB API")

        url = f"{self.BASE_URL}/login"
        data = {"apikey": self.tvdb_apikey}

        try:
            response = self._http_client.post_json(url, data=data)
        except (HTTPError, URLError, ValueError) as e:
            logger.error("Failed to authenticate with TVDB: %s", e)
            return False

        if not response or not isinstance(response, dict):
            logger.warning("Unexpected response format from TVDB login")
            return False

        status = response.get("status")
        if status != "success":
            logger.warning("TVDB authentication failed: %s", response)
            return False

        self._auth_token = response.get("data", {}).get("token")
        if not self._auth_token:
            logger.warning("No token found in TVDB auth response")
            return False

        logger.debug("Successfully authenticated to TVDB API")
        return True

    def get_expected_episode_count(
        self,
        provider_ids: Mapping[str, str],
        season_number: int,
    ) -> int | None:
        """Get expected total episode count for a season.

        Args:
            provider_ids: Mapping of external IDs (tmdb, tvdb, imdb)
            season_number: Season number

        Returns:
            Expected episode count, or None if unavailable
        """
        tvdb_id = provider_ids.get("tvdb")
        if not tvdb_id:
            logger.debug("No TVDB ID found in provider_ids")
            return None

        # Note: TVDB v4 API requires subscription for full episode access
        # This is a placeholder implementation that documents the limitation
        logger.warning(
            "TVDB v4 API requires paid subscription for episode count. "
            "TVDB ID=%s, season=%s. Returning None.",
            tvdb_id,
            season_number,
        )
        return None

    def is_season_fully_aired(
        self,
        provider_ids: Mapping[str, str],
        season_number: int,
    ) -> bool | None:
        """Check if all episodes of a season have aired.

        Args:
            provider_ids: Mapping of external IDs (tmdb, tvdb, imdb)
            season_number: Season number

        Returns:
            True if fully aired, False if not, None if unknown
        """
        tvdb_id = provider_ids.get("tvdb")
        if not tvdb_id:
            logger.debug("No TVDB ID found in provider_ids")
            return None

        # Note: TVDB v4 API requires subscription for full episode access
        # This is a placeholder implementation that documents the limitation
        logger.warning(
            "TVDB v4 API requires paid subscription for airing status. "
            "TVDB ID=%s, season=%s. Returning None.",
            tvdb_id,
            season_number,
        )
        return None
