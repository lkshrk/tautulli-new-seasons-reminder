"""Jellyfin media source adapter."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError

from new_seasons_reminder.http import HTTPClient
from new_seasons_reminder.models import CandidateSeason, ExternalIds, SeasonKey, SeasonRef
from new_seasons_reminder.sources.base import MediaSource

logger = logging.getLogger(__name__)


class JellyfinMediaSource(MediaSource):
    """Jellyfin media source adapter."""

    def __init__(
        self,
        jellyfin_url: str,
        jellyfin_apikey: str,
        user_id: str,
        http_client: HTTPClient | None = None,
    ):
        """Initialize Jellyfin media source.

        Args:
            jellyfin_url: URL to the Jellyfin instance
            jellyfin_apikey: Jellyfin API key
            user_id: Jellyfin user ID (required for most API calls)
            http_client: Optional HTTP client (for testing)
        """
        self.jellyfin_url = jellyfin_url.rstrip("/")
        self.jellyfin_apikey = jellyfin_apikey
        self.user_id = user_id
        self._http_client = http_client or HTTPClient()

    def get_candidate_seasons(
        self,
        since: datetime,
    ) -> Sequence[CandidateSeason]:
        """Get seasons that became candidates since the given timestamp.

        Args:
            since: Only return seasons with completed_at >= this timestamp

        Returns:
            Sequence of candidate seasons
        """
        logger.debug("Getting candidate seasons since %s", since)

        # Get recently added seasons from Jellyfin
        params = {
            "userId": self.user_id,
            "IncludeItemTypes": "Season",
            "enableUserData": "true",
            "enableImages": "false",
            "Fields": "ProviderIds,DateCreated,ProductionYear",
            "limit": "500",
        }

        url = f"{self.jellyfin_url}/Items/Latest"
        headers = {"X-MediaBrowser-Token": self.jellyfin_apikey}

        try:
            data = self._http_client.get_json(url, params=params, headers=headers)
        except (HTTPError, URLError, ValueError) as e:
            logger.error("Failed to fetch latest items from Jellyfin: %s", e)
            return []

        if not data or not isinstance(data, list):
            logger.warning("Unexpected response format from /Items/Latest")
            return []

        candidates: list[CandidateSeason] = []

        for season_data in data:
            try:
                season_key, season_ref = self._parse_season_data(season_data)

                # Jellyfin provides DateCreated for seasons
                date_created = season_data.get("DateCreated")
                if not date_created:
                    logger.debug("Season %s has no DateCreated, skipping", season_ref)
                    continue

                # Parse ISO 8601 datetime
                try:
                    if isinstance(date_created, str):
                        completed_at = datetime.fromisoformat(date_created.replace("Z", "+00:00"))
                    else:
                        logger.warning(
                            "Unexpected DateCreated type for %s: %s",
                            season_ref,
                            type(date_created).__name__,
                        )
                        continue
                except (ValueError, AttributeError) as e:
                    logger.warning(
                        "Failed to parse DateCreated for %s: %s - %s",
                        season_ref,
                        date_created,
                        e,
                    )
                    continue

                # Filter by since timestamp
                if completed_at < since:
                    logger.debug(
                        "Season %s completed_at %s before since %s, skipping",
                        season_ref,
                        completed_at,
                        since,
                    )
                    continue

                # Get episode count from season data
                location_type = season_data.get("LocationType")
                if location_type == "Virtual":
                    # Virtual season - episodes are virtual, get actual count
                    # We can query episodes for this season
                    episode_count = self._get_season_episode_count(season_ref.season_id)
                else:
                    # Physical season - episodes are real files
                    episode_count = season_data.get("ChildCount", 0)

                # Get is_complete_in_source from UserData
                user_data = season_data.get("UserData", {})
                is_complete = user_data.get("Played", False)
                # Jellyfin marks seasons as played when all episodes are played
                is_complete_in_source = bool(is_complete)

                candidate = CandidateSeason(
                    season_ref=season_ref,
                    completed_at=completed_at,
                    in_library_episode_count=episode_count,
                    is_complete_in_source=is_complete_in_source,
                )
                candidates.append(candidate)

                logger.debug(
                    "Added candidate: %s with %d episodes completed at %s",
                    season_ref,
                    episode_count,
                    completed_at,
                )

            except (KeyError, ValueError, AttributeError) as e:
                logger.warning(
                    "Failed to parse season data: %s - %s",
                    season_data,
                    e,
                )
                continue

        logger.info(
            "Found %d candidate seasons since %s",
            len(candidates),
            since,
        )
        return candidates

    def list_seasons(self) -> Sequence[SeasonRef]:
        """List all seasons available in the media source.

        Returns:
            Sequence of all seasons
        """
        logger.debug("Listing all seasons")

        # Get all seasons from library
        params = {
            "userId": self.user_id,
            "IncludeItemTypes": "Season",
            "enableUserData": "false",
            "enableImages": "false",
            "Recursive": "true",
            "limit": "10000",
        }

        url = f"{self.jellyfin_url}/Users/{self.user_id}/Items"
        headers = {"X-MediaBrowser-Token": self.jellyfin_apikey}

        try:
            response = self._http_client.get_json(url, params=params, headers=headers)
        except (HTTPError, URLError, ValueError) as e:
            logger.error("Failed to fetch seasons from Jellyfin: %s", e)
            return []

        if not response or not isinstance(response, dict):
            logger.warning("Unexpected response format from /Items")
            return []

        items = response.get("Items", [])
        season_refs: list[SeasonRef] = []

        for season_data in items:
            try:
                _, season_ref = self._parse_season_data(season_data)
                season_refs.append(season_ref)
            except (KeyError, ValueError, AttributeError) as e:
                logger.warning(
                    "Failed to parse season data: %s - %s",
                    season_data,
                    e,
                )
                continue

        logger.debug("Listed %d total seasons", len(season_refs))
        return season_refs

    def get_show_added_at(
        self,
        series_id: str,
    ) -> datetime | None:
        """Get the date when the show was first added to the library.

        Args:
            series_id: Source-native series ID

        Returns:
            Datetime when show was added, or None if unknown
        """
        logger.debug("Getting show added_at for series_id=%s", series_id)

        url = f"{self.jellyfin_url}/Users/{self.user_id}/Items/{series_id}"
        headers = {"X-MediaBrowser-Token": self.jellyfin_apikey}

        try:
            metadata = self._http_client.get_json(url, headers=headers)
        except (HTTPError, URLError, ValueError) as e:
            logger.error("Failed to fetch metadata for series_id=%s: %s", series_id, e)
            return None

        if not metadata or not isinstance(metadata, dict):
            logger.warning("No metadata found for series_id=%s", series_id)
            return None

        date_created = metadata.get("DateCreated")
        if not date_created:
            logger.debug("No DateCreated found for series_id=%s", series_id)
            return None

        try:
            if isinstance(date_created, str):
                return datetime.fromisoformat(date_created.replace("Z", "+00:00"))
            else:
                logger.warning(
                    "Unexpected DateCreated type for series_id=%s: %s",
                    series_id,
                    type(date_created).__name__,
                )
                return None
        except (ValueError, AttributeError) as e:
            logger.warning(
                "Failed to parse DateCreated for series_id=%s: %s - %s",
                series_id,
                date_created,
                e,
            )
            return None

    def get_provider_ids(
        self,
        series_id: str,
    ) -> ExternalIds:
        """Get external provider IDs for a show.

        Args:
            series_id: Source-native series ID

        Returns:
            ExternalIds with tmdb/tvdb/imdb IDs
        """
        logger.debug("Getting provider IDs for series_id=%s", series_id)

        url = f"{self.jellyfin_url}/Users/{self.user_id}/Items/{series_id}"
        headers = {"X-MediaBrowser-Token": self.jellyfin_apikey}

        try:
            metadata = self._http_client.get_json(url, headers=headers)
        except (HTTPError, URLError, ValueError) as e:
            logger.error("Failed to fetch metadata for series_id=%s: %s", series_id, e)
            return ExternalIds()

        if not metadata or not isinstance(metadata, dict):
            logger.warning("No metadata found for series_id=%s", series_id)
            return ExternalIds()

        # Jellyfin provides ProviderIds as a dictionary
        provider_ids = metadata.get("ProviderIds", {})
        if not isinstance(provider_ids, dict):
            logger.warning("Unexpected ProviderIds format for series_id=%s", series_id)
            return ExternalIds()

        tmdb_id: str | None = provider_ids.get("Tmdb")
        tvdb_id: str | None = provider_ids.get("Tvdb")
        imdb_id: str | None = provider_ids.get("Imdb")

        return ExternalIds(tmdb=tmdb_id, tvdb=tvdb_id, imdb=imdb_id)

    def _parse_season_data(
        self,
        season_data: dict[str, Any],
    ) -> tuple[SeasonKey, SeasonRef]:
        """Parse season data from Jellyfin API response.

        Args:
            season_data: Season data dictionary from Jellyfin

        Returns:
            Tuple of (SeasonKey, SeasonRef)

        Raises:
            KeyError: If required fields are missing
        """
        # Get item ID as the season ID
        season_id = str(season_data["Id"])

        # Get season number
        season_number = int(season_data.get("IndexNumber", 0))

        # Get parent series ID
        series_id = str(season_data.get("SeriesId") or season_data.get("ParentId"))

        # Get series name
        series_name = str(
            season_data.get("SeriesName") or season_data.get("SeriesTitle", "Unknown")
        )

        # Get season title
        season_title = season_data.get("Name", f"Season {season_number}")

        # Create SeasonKey
        season_key = SeasonKey(
            source="jellyfin",
            series_id=series_id,
            season_number=season_number,
        )

        # Create SeasonRef
        season_ref = SeasonRef(
            season_key=season_key,
            series_name=series_name,
            season_title=season_title,
            season_id=season_id,
        )

        return season_key, season_ref

    def _get_season_episode_count(
        self,
        season_id: str,
    ) -> int:
        """Get the number of episodes in a season.

        Args:
            season_id: Season ID

        Returns:
            Number of episodes
        """
        url = f"{self.jellyfin_url}/Users/{self.user_id}/Items"
        headers = {"X-MediaBrowser-Token": self.jellyfin_apikey}

        params = {
            "ParentId": season_id,
            "IncludeItemTypes": "Episode",
            "Recursive": "false",
            "limit": "1000",
        }

        try:
            response = self._http_client.get_json(url, params=params, headers=headers)
        except (HTTPError, URLError, ValueError) as e:
            logger.error("Failed to fetch episodes for season_id=%s: %s", season_id, e)
            return 0

        if not response or not isinstance(response, dict):
            logger.warning("Unexpected response format for season episodes")
            return 0

        items = response.get("Items", [])
        return len(items) if isinstance(items, list) else 0
