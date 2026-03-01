"""Tautulli media source adapter."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from new_seasons_reminder.api import (
    get_children_metadata,
    get_libraries,
    get_metadata,
    get_recently_added,
    set_http_client,
)
from new_seasons_reminder.http import HTTPClient
from new_seasons_reminder.models import CandidateSeason, ExternalIds, SeasonKey, SeasonRef
from new_seasons_reminder.sources.base import MediaSource

logger = logging.getLogger(__name__)


class TautulliMediaSource(MediaSource):
    """Tautulli media source adapter."""

    def __init__(
        self,
        tautulli_url: str,
        tautulli_apikey: str,
        http_client: HTTPClient | None = None,
    ):
        """Initialize Tautulli media source.

        Args:
            tautulli_url: URL to the Tautulli instance
            tautulli_apikey: Tautulli API key
            http_client: Optional HTTP client (for testing)
        """
        self.tautulli_url = tautulli_url
        self.tautulli_apikey = tautulli_apikey
        self._http_client = http_client or HTTPClient()
        set_http_client(self._http_client)

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

        # Get recently added seasons from Tautulli
        recent_seasons = get_recently_added(
            media_type="show",
            count=500,  # Get more to filter locally
            tautulli_url=self.tautulli_url,
            tautulli_apikey=self.tautulli_apikey,
        )

        if not recent_seasons:
            libraries = get_libraries(
                tautulli_url=self.tautulli_url,
                tautulli_apikey=self.tautulli_apikey,
            )
            if not libraries:
                logger.warning(
                    "Tautulli returned zero libraries; recently added seasons will be empty. "
                    "Verify the API key and connected Plex server in Tautulli."
                )

        candidates: list[CandidateSeason] = []

        for season_data in recent_seasons:
            try:
                season_key, season_ref = self._parse_season_data(season_data)

                # Get episodes to find completion time
                episodes = get_children_metadata(
                    rating_key=season_ref.season_id,
                    media_type="season",
                    tautulli_url=self.tautulli_url,
                    tautulli_apikey=self.tautulli_apikey,
                )

                if not episodes:
                    logger.debug(
                        "Season %s has no episodes, skipping",
                        season_ref,
                    )
                    continue

                # Find the latest added_at timestamp
                completed_at = self._get_max_episode_added_at(episodes)

                # Filter by since timestamp
                if completed_at < since:
                    logger.debug(
                        "Season %s completed_at %s before since %s, skipping",
                        season_ref,
                        completed_at,
                        since,
                    )
                    continue

                candidate = CandidateSeason(
                    season_ref=season_ref,
                    completed_at=completed_at,
                    in_library_episode_count=len(episodes),
                    is_complete_in_source=None,  # Tautulli doesn't provide this
                )
                candidates.append(candidate)

                logger.debug(
                    "Added candidate: %s with %d episodes completed at %s",
                    season_ref,
                    len(episodes),
                    completed_at,
                )

            except (KeyError, ValueError) as e:
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
        # Get all seasons by fetching recently added with large count
        all_seasons = get_recently_added(
            media_type="show",
            count=10000,  # Large count to get all
            tautulli_url=self.tautulli_url,
            tautulli_apikey=self.tautulli_apikey,
        )

        season_refs: list[SeasonRef] = []

        for season_data in all_seasons:
            try:
                _, season_ref = self._parse_season_data(season_data)
                season_refs.append(season_ref)
            except (KeyError, ValueError) as e:
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

        metadata = get_metadata(
            rating_key=series_id,
            tautulli_url=self.tautulli_url,
            tautulli_apikey=self.tautulli_apikey,
        )

        if not metadata:
            logger.warning("No metadata found for series_id=%s", series_id)
            return None

        added_at = metadata.get("added_at")
        if added_at:
            try:
                if isinstance(added_at, (int, str)):
                    ts = int(added_at)
                    return datetime.fromtimestamp(ts, tz=timezone.utc)
            except (ValueError, OSError, TypeError) as e:
                logger.warning(
                    "Failed to parse added_at=%s for series_id=%s: %s",
                    added_at,
                    series_id,
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

        metadata = get_metadata(
            rating_key=series_id,
            tautulli_url=self.tautulli_url,
            tautulli_apikey=self.tautulli_apikey,
        )

        if not metadata:
            logger.warning("No metadata found for series_id=%s", series_id)
            return ExternalIds()

        # Tautulli provides external IDs under "guid" field
        # Format: "com.plexapp.agents.thetvdb://12345/..."
        guids = metadata.get("guid", "[]")

        if isinstance(guids, str):
            # Single GUID string
            guids = [guids]

        if not isinstance(guids, list):
            guids = []

        tmdb_id: str | None = None
        tvdb_id: str | None = None
        imdb_id: str | None = None

        for guid in guids:
            guid_str = str(guid)

            # Parse TMDB ID
            if "tmdb://" in guid_str:
                with suppress(IndexError, AttributeError):
                    tmdb_id = guid_str.split("tmdb://")[1].split("/")[0]

            # Parse TVDB ID
            if "thetvdb://" in guid_str or "tvdb://" in guid_str:
                with suppress(IndexError, AttributeError):
                    tvdb_id = guid_str.split("//")[1].split("/")[0]

            # Parse IMDB ID
            if "imdb://" in guid_str:
                with suppress(IndexError, AttributeError):
                    imdb_id = guid_str.split("imdb://")[1].split("/")[0]

        return ExternalIds(tmdb=tmdb_id, tvdb=tvdb_id, imdb=imdb_id)

    def _parse_season_data(
        self,
        season_data: dict[str, Any],
    ) -> tuple[SeasonKey, SeasonRef]:
        """Parse season data from Tautulli API response.

        Args:
            season_data: Season data dictionary from Tautulli

        Returns:
            Tuple of (SeasonKey, SeasonRef)

        Raises:
            KeyError: If required fields are missing
        """
        # Get rating_key as the season ID
        season_id = str(season_data["rating_key"])

        # Get season number
        season_number = int(season_data["media_index"])

        # Get parent rating_key as series ID
        series_id = str(season_data["parent_rating_key"])

        # Get series name
        series_name = str(season_data["parent_title"])

        # Get season title (fallback to generated title)
        season_title = season_data.get("title", f"Season {season_number}")

        # Create SeasonKey
        season_key = SeasonKey(
            source="tautulli",
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

    def _get_max_episode_added_at(
        self,
        episodes: list[dict[str, Any]],
    ) -> datetime:
        """Get the maximum added_at timestamp from episodes.

        Args:
            episodes: List of episode dictionaries

        Returns:
            Datetime of the latest episode
        """
        max_timestamp: int | None = None

        for episode in episodes:
            added_at = episode.get("added_at")
            if not added_at:
                continue
            try:
                ts = int(added_at)  # Tautulli returns added_at as int or numeric string
            except ValueError, TypeError:
                continue
            if max_timestamp is None or ts > max_timestamp:
                max_timestamp = ts

        if max_timestamp is None:
            # Fallback: use current UTC time
            logger.warning("No added_at found in episodes, using current time")
            return datetime.now(tz=timezone.utc)

        try:
            return datetime.fromtimestamp(max_timestamp, tz=timezone.utc)
        except (ValueError, OSError) as e:
            logger.warning("Failed to parse timestamp %s: %s", max_timestamp, e)
            return datetime.now(tz=timezone.utc)
