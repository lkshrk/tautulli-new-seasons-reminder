from datetime import UTC, datetime, timedelta

from new_seasons_reminder.logic import get_completed_seasons
from new_seasons_reminder.metadata.resolver import MetadataResolver
from new_seasons_reminder.models import CandidateSeason, ExternalIds, SeasonKey, SeasonRef


class StubSource:
    def __init__(self):
        key = SeasonKey(source="tautulli", series_id="show-1", season_number=1)
        ref = SeasonRef(
            season_key=key,
            series_name="Integration Show",
            season_title="Season 1",
            season_id="season-1",
        )
        self._candidate = CandidateSeason(
            season_ref=ref,
            completed_at=datetime.now(tz=UTC) - timedelta(days=1),
            in_library_episode_count=6,
            is_complete_in_source=None,
        )

    def get_candidate_seasons(self, since):
        return [self._candidate]

    def list_seasons(self):
        return [self._candidate.season_ref]

    def get_show_added_at(self, series_id):
        return datetime.now(tz=UTC) - timedelta(days=100)

    def get_provider_ids(self, series_id):
        return ExternalIds(tmdb="12345", tvdb="67890")


class PrimaryProvider:
    def get_expected_episode_count(self, provider_ids, season_number):
        return None

    def is_season_fully_aired(self, provider_ids, season_number):
        return None


class FallbackProvider:
    def get_expected_episode_count(self, provider_ids, season_number):
        return 6

    def is_season_fully_aired(self, provider_ids, season_number):
        return True


def test_end_to_end_with_metadata_fallback():
    source = StubSource()
    metadata = MetadataResolver(primary=PrimaryProvider(), fallback=FallbackProvider())
    result = get_completed_seasons(
        source=source,
        metadata_provider=metadata,
        since=datetime.now(tz=UTC) - timedelta(days=7),
        require_fully_aired=True,
    )
    assert len(result) == 1
    assert result[0]["show"] == "Integration Show"
    assert result[0]["season"] == 1
    assert result[0]["expected_count"] == 6
