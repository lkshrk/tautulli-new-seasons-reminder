"""Domain models for season detection.

This module defines typed dataclasses representing the core domain entities
for season completion detection across multiple media sources.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SeasonKey:
    """Unique identifier for a season across all sources."""

    source: str  # e.g., "tautulli", "jellyfin"
    series_id: str  # Source-native series ID
    season_number: int  # Season number (1-indexed, 0 = specials)

    def __str__(self) -> str:
        return f"{self.source}:{self.series_id}:S{self.season_number}"


@dataclass(frozen=True, slots=True)
class SeasonRef:
    """Reference to a season from a media source."""

    season_key: SeasonKey
    series_name: str  # Show title
    season_title: str  # Season display name (e.g., "Season 1")
    season_id: str  # Source-native season ID (rating_key or SeasonId)

    def __str__(self) -> str:
        return f"{self.series_name} S{self.season_key.season_number}"


@dataclass(frozen=True, slots=True)
class CandidateSeason:
    """A season candidate for completion detection."""

    season_ref: SeasonRef
    completed_at: datetime  # Time when last episode was added (max episode.added_at)
    in_library_episode_count: int  # Episodes currently in library
    is_complete_in_source: bool | None  # Source-specific completeness (Jellyfin) or None (Tautulli)


@dataclass(frozen=True, slots=True)
class CompletionDecision:
    """Decision about whether a season is complete."""

    is_complete: bool
    reason: str
    expected_episode_count: int | None


@dataclass(frozen=True, slots=True)
class CompletedSeasonPayload:
    """Payload sent to webhooks for completed seasons."""

    show: str  # Show title
    season: int  # Season number
    season_title: str  # Season display name
    completed_at: str  # ISO 8601 timestamp
    episode_count: int  # Actual episodes in library
    rating_key: str  # season_id string for backward compatibility


@dataclass(frozen=True, slots=True)
class ExternalIds:
    """External provider IDs for a show."""

    tmdb: str | None = None
    tvdb: str | None = None
    imdb: str | None = None

    def to_dict(self) -> Mapping[str, str]:
        """Convert to a non-None mapping.

        Returns:
            Mapping containing only non-None IDs
        """
        pairs = [("tmdb", self.tmdb), ("tvdb", self.tvdb), ("imdb", self.imdb)]
        return {k: v for k, v in pairs if v is not None}
