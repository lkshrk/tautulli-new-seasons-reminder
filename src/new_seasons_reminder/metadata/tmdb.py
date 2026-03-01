"""TMDB (The Movie Database) metadata provider."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime
from urllib.error import HTTPError, URLError

from new_seasons_reminder.http import HTTPClient
from new_seasons_reminder.metadata.base import ExternalMetadataProvider

logger = logging.getLogger(__name__)


class TMDBMetadataProvider(ExternalMetadataProvider):
    """TMDB metadata provider implementation."""

    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(
        self,
        tmdb_apikey: str,
        http_client: HTTPClient | None = None,
    ):
        """Initialize TMDB metadata provider.

        Args:
            tmdb_apikey: TMDB API key
            http_client: Optional HTTP client (for testing)
        """
        self.tmdb_apikey = tmdb_apikey
        self._http_client = http_client or HTTPClient()

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
        tmdb_id = provider_ids.get("tmdb")
        if not tmdb_id:
            logger.debug("No TMDB ID found in provider_ids")
            return None

        logger.debug(
            "Getting expected episode count for TMDB ID=%s season=%s",
            tmdb_id,
            season_number,
        )

        url = f"{self.BASE_URL}/tv/{tmdb_id}/season/{season_number}"
        headers = {"Authorization": f"Bearer {self.tmdb_apikey}"}
        params = {"language": "en-US"}

        try:
            data = self._http_client.get_json(url, headers=headers, params=params)
        except (HTTPError, URLError, ValueError) as e:
            logger.error(
                "Failed to fetch season details from TMDB: %s",
                e,
            )
            return None

        if not data or not isinstance(data, dict):
            logger.warning("Unexpected response format from TMDB")
            return None

        episodes = data.get("episodes", [])
        if not isinstance(episodes, list):
            logger.warning("Unexpected episodes format from TMDB")
            return None

        episode_count = len(episodes)
        logger.debug(
            "Found %d expected episodes for TMDB ID=%s season=%s",
            episode_count,
            tmdb_id,
            season_number,
        )

        return episode_count

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
        tmdb_id = provider_ids.get("tmdb")
        if not tmdb_id:
            logger.debug("No TMDB ID found in provider_ids")
            return None

        logger.debug(
            "Checking if season is fully aired for TMDB ID=%s season=%s",
            tmdb_id,
            season_number,
        )

        url = f"{self.BASE_URL}/tv/{tmdb_id}/season/{season_number}"
        headers = {"Authorization": f"Bearer {self.tmdb_apikey}"}
        params = {"language": "en-US"}

        try:
            data = self._http_client.get_json(url, headers=headers, params=params)
        except (HTTPError, URLError, ValueError) as e:
            logger.error(
                "Failed to fetch season details from TMDB: %s",
                e,
            )
            return None

        if not data or not isinstance(data, dict):
            logger.warning("Unexpected response format from TMDB")
            return None

        episodes = data.get("episodes", [])
        if not isinstance(episodes, list):
            logger.warning("Unexpected episodes format from TMDB")
            return None

        if not episodes:
            logger.debug("No episodes found in season")
            return True  # Empty season is trivially fully aired

        now = datetime.now()

        # Check if all episodes have aired
        for episode in episodes:
            air_date = episode.get("air_date")
            if not air_date:
                logger.debug(
                    "Episode %s has no air_date, assuming not aired",
                    episode.get("episode_number"),
                )
                return False

            try:
                if isinstance(air_date, str):
                    aired_date = datetime.fromisoformat(air_date.replace("Z", "+00:00"))
                else:
                    logger.warning(
                        "Unexpected air_date type: %s",
                        type(air_date).__name__,
                    )
                    return False

                if aired_date > now:
                    logger.debug(
                        "Episode %s has not aired yet (air_date=%s)",
                        episode.get("episode_number"),
                        air_date,
                    )
                    return False
            except (ValueError, AttributeError) as e:
                logger.warning(
                    "Failed to parse air_date for episode %s: %s - %s",
                    episode.get("episode_number"),
                    air_date,
                    e,
                )
                return False

        logger.debug(
            "All episodes have aired for TMDB ID=%s season=%s",
            tmdb_id,
            season_number,
        )
        return True
