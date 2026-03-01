"""Resolver for external metadata providers.

Uses TMDB as primary, TVDB as fallback, with per-run caching.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from new_seasons_reminder.metadata.base import ExternalMetadataProvider

logger = logging.getLogger(__name__)


class MetadataResolver:
    """Resolves metadata from multiple providers (TMDB primary, TVDB fallback)."""

    def __init__(
        self,
        primary: ExternalMetadataProvider,
        fallback: ExternalMetadataProvider | None = None,
    ) -> None:
        """Initialize metadata resolver.

        Args:
            primary: Primary metadata provider (e.g., TMDB)
            fallback: Fallback provider (e.g., TVDB), used if primary fails
        """
        self.primary = primary
        self.fallback = fallback
        self._cache: dict[tuple[str, int], int] = {}  # Cache episode counts

    def get_expected_episode_count(
        self,
        provider_ids: Mapping[str, str],
        season_number: int,
    ) -> int | None:
        """Get expected episode count from available providers.

        Tries primary first, then fallback if configured.
        Caches results per run to reduce API calls.

        Args:
            provider_ids: Mapping of external IDs (tmdb, tvdb, imdb)
            season_number: Season number

        Returns:
            Expected episode count, or None if unavailable from any provider
        """
        cache_key = self._make_cache_key(provider_ids, season_number)

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try primary provider
        count = self.primary.get_expected_episode_count(provider_ids, season_number)

        # Try fallback if primary failed and fallback exists
        if count is None and self.fallback:
            logger.debug("Primary provider returned None, trying fallback")
            count = self.fallback.get_expected_episode_count(provider_ids, season_number)

        if count is not None:
            self._cache[cache_key] = count
            logger.debug("Cached episode count: %s S%d = %d", cache_key[0], cache_key[1], count)

        return count

    def is_season_fully_aired(
        self,
        provider_ids: Mapping[str, str],
        season_number: int,
    ) -> bool | None:
        """Check if season is fully aired from available providers.

        Tries primary first, then fallback if configured.

        Args:
            provider_ids: Mapping of external IDs (tmdb, tvdb, imdb)
            season_number: Season number

        Returns:
            True if fully aired, False if not, None if unknown
        """
        # Try primary provider
        result = self.primary.is_season_fully_aired(provider_ids, season_number)

        # Try fallback if primary failed and fallback exists
        if result is None and self.fallback:
            result = self.fallback.is_season_fully_aired(provider_ids, season_number)

        return result

    def _make_cache_key(
        self,
        provider_ids: Mapping[str, str],
        season_number: int,
    ) -> tuple[str, int]:
        """Create a cache key from provider IDs.

        Uses the first available ID in preference order: tmdb, tvdb, imdb.

        Args:
            provider_ids: Mapping of external IDs
            season_number: Season number

        Returns:
            Tuple of (provider_id_str, season_number)
        """
        for key in ["tmdb", "tvdb", "imdb"]:
            if key in provider_ids:
                return (f"{key}:{provider_ids[key]}", season_number)

        # Fallback: use string representation of all IDs
        id_str = ":".join(f"{k}={v}" for k, v in sorted(provider_ids.items()))
        return (id_str, season_number)
