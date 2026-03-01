"""Base protocol for external metadata providers."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class ExternalMetadataProvider(Protocol):
    """Protocol for external metadata providers (TMDB, TVDB)."""

    @abstractmethod
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

    @abstractmethod
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
