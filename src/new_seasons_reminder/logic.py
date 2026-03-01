"""Core logic for season completion detection."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from new_seasons_reminder.metadata.base import ExternalMetadataProvider
from new_seasons_reminder.models import CompletionDecision
from new_seasons_reminder.sources.base import MediaSource

logger = logging.getLogger(__name__)


def is_new_show(
    series_id: str,
    show_added_at: datetime | None,
    cutoff_date: datetime,
) -> bool | None:
    """Check if a show was recently added (i.e. is "new").

    Args:
        series_id: Source-native series ID
        show_added_at: Datetime when show was first added to library
        cutoff_date: Cutoff date to consider shows as "new"

    Returns:
        True if new, False if existing, None if timestamp unavailable
    """
    if not show_added_at:
        logger.debug("Show %s missing added_at timestamp", series_id)
        return None

    logger.debug(
        "Show %s added at %s compared to cutoff %s",
        series_id,
        show_added_at,
        cutoff_date,
    )

    try:
        show_date = show_added_at
        logger.debug(
            "Show %s added at %s - this is a %sSHOW",
            series_id,
            show_date,
            "NEW" if show_date >= cutoff_date else "EXISTING",
        )
        return show_date >= cutoff_date
    except (ValueError, TypeError) as e:
        logger.warning(
            "Error parsing added_at for show %s: %s",
            series_id,
            e,
        )
        return None


def get_completed_seasons(
    source: MediaSource,
    metadata_provider: ExternalMetadataProvider | None,
    since: datetime,
    require_fully_aired: bool = False,
    include_new_shows: bool = False,
) -> list[dict[str, Any]]:
    """Get seasons that are completed with strict episode count validation.

    This function:
    1. Gets candidate seasons from the media source
    2. Validates each season against external metadata for expected episode count
    3. Optionally checks if all episodes have aired (if require_fully_aired=True)
    4. Optionally filters out new shows (if include_new_shows=False)

    Args:
        source: Media source adapter (Tautulli or Jellyfin)
        metadata_provider: External metadata provider (TMDB or TVDB)
        since: Only consider seasons completed at or after this datetime
        require_fully_aired: If True, only include seasons where all episodes have aired
        include_new_shows: If False (default), skip shows first added within the since window

    Returns:
        List of completed seasons with completion details
    """
    logger.debug(
        "Getting completed seasons from %s since %s",
        source.__class__.__name__,
        since,
    )
    logger.debug("Require fully aired: %s", require_fully_aired)

    # Get candidate seasons from media source
    candidates = source.get_candidate_seasons(since)

    if not candidates:
        logger.info("No candidate seasons found")
        return []

    completed_seasons: list[dict[str, Any]] = []

    for candidate in candidates:
        season_ref = candidate.season_ref
        season_key = season_ref.season_key
        series_id = season_key.series_id
        season_number = season_key.season_number

        logger.debug(
            "Processing %s (S%s) with %d episodes, completed at %s",
            season_ref.series_name,
            season_number,
            candidate.in_library_episode_count,
            candidate.completed_at,
        )

        # Get external provider IDs for this show
        provider_ids = source.get_provider_ids(series_id)

        # Validate with external metadata
        decision = validate_season_completion(
            provider_ids=provider_ids.to_dict() if provider_ids else {},
            season_number=season_number,
            in_library_count=candidate.in_library_episode_count,
            source_complete=candidate.is_complete_in_source,
            metadata_provider=metadata_provider,
            require_fully_aired=require_fully_aired,
        )

        if decision.is_complete:
            # Optionally filter out new shows (first added within the since window)
            if not include_new_shows:
                show_added_at = source.get_show_added_at(series_id)
                if is_new_show(series_id, show_added_at, since) is True:
                    logger.debug(
                        "Skipping new show: %s (S%s)",
                        season_ref.series_name,
                        season_number,
                    )
                    continue

            season_dict: dict[str, Any] = {
                "show": season_ref.series_name,
                "season": season_number,
                "season_title": season_ref.season_title,
                "added_at": candidate.completed_at.isoformat(),
                "episode_count": candidate.in_library_episode_count,
                "rating_key": season_ref.season_id,
                "reason": decision.reason,
                "expected_count": decision.expected_episode_count,
            }
            completed_seasons.append(season_dict)

            logger.info(
                "Completed: %s (S%s) - %s",
                season_ref.series_name,
                season_number,
                decision.reason,
            )
        else:
            logger.debug(
                "Not complete: %s (S%s) - %s",
                season_ref.series_name,
                season_number,
                decision.reason,
            )

    logger.info("Found %d completed seasons", len(completed_seasons))
    return completed_seasons


def validate_season_completion(
    provider_ids: Mapping[str, str],
    season_number: int,
    in_library_count: int,
    source_complete: bool | None,
    metadata_provider: ExternalMetadataProvider | None,
    require_fully_aired: bool,
) -> CompletionDecision:
    """Validate season completion using external metadata.

    This implements strict season completion detection:
    1. If source provides is_complete_in_source (e.g., Jellyfin), use that
    2. Otherwise, validate against external metadata:
       a. Check if in_library_count matches expected_count
       b. If require_fully_aired, also check airing status

    Args:
        provider_ids: Mapping of external IDs (tmdb, tvdb, imdb)
        season_number: Season number
        in_library_count: Number of episodes currently in library
        source_complete: Source-specific completeness flag (may be None for Tautulli)
        metadata_provider: External metadata provider to query
        require_fully_aired: Whether to check if all episodes have aired

    Returns:
        CompletionDecision with completion status and reason
    """
    # Case 1: Source provides completion status (e.g., Jellyfin)
    if source_complete is not None:
        if source_complete:
            return CompletionDecision(
                is_complete=True,
                reason="Source reports season as complete",
                expected_episode_count=in_library_count,
            )
        else:
            return CompletionDecision(
                is_complete=False,
                reason="Source reports season as incomplete",
                expected_episode_count=in_library_count,
            )

    # Case 2: Use external metadata provider
    if metadata_provider is None:
        return CompletionDecision(
            is_complete=in_library_count > 0,
            reason="No metadata provider configured - assuming complete if episodes exist",
            expected_episode_count=None,
        )

    # Get expected episode count from metadata provider
    expected_count = metadata_provider.get_expected_episode_count(
        provider_ids=provider_ids,
        season_number=season_number,
    )

    if expected_count is None:
        logger.debug(
            "No expected episode count from metadata provider for S%s",
            season_number,
        )
        return CompletionDecision(
            is_complete=in_library_count > 0,
            reason="Could not determine expected episode count",
            expected_episode_count=None,
        )

    logger.debug(
        "Season S%s: library=%d, expected=%d",
        season_number,
        in_library_count,
        expected_count,
    )

    # Check if counts match
    counts_match = in_library_count == expected_count

    if not counts_match:
        return CompletionDecision(
            is_complete=False,
            reason=f"Incomplete: {in_library_count}/{expected_count} episodes in library",
            expected_episode_count=expected_count,
        )

    # Check airing status if required
    if require_fully_aired:
        is_fully_aired = metadata_provider.is_season_fully_aired(
            provider_ids=provider_ids,
            season_number=season_number,
        )

        if is_fully_aired is None:
            logger.debug("Could not determine airing status")
            # If we can't determine airing status, assume it's complete
            return CompletionDecision(
                is_complete=True,
                reason=(
                    f"Complete: {in_library_count}/{expected_count} episodes (airs status unknown)"
                ),
                expected_episode_count=expected_count,
            )
        elif not is_fully_aired:
            return CompletionDecision(
                is_complete=False,
                reason="Incomplete: Not all episodes have aired yet",
                expected_episode_count=expected_count,
            )

    # Counts match and (no airing check or all aired)
    return CompletionDecision(
        is_complete=True,
        reason=f"Complete: {in_library_count}/{expected_count} episodes in library",
        expected_episode_count=expected_count,
    )
