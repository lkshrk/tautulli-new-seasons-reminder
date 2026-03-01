from datetime import UTC, datetime, timedelta

from new_seasons_reminder.logic import (
    get_completed_seasons,
    is_new_show,
    validate_season_completion,
)
from new_seasons_reminder.models import (
    CandidateSeason,
    CompletionDecision,
    ExternalIds,
    SeasonKey,
    SeasonRef,
)


class FakeSource:
    def __init__(self, candidates, provider_ids):
        self._candidates = candidates
        self._provider_ids = provider_ids

    def get_candidate_seasons(self, since):
        return self._candidates

    def list_seasons(self):
        return []

    def get_show_added_at(self, series_id):
        return None

    def get_provider_ids(self, series_id):
        return self._provider_ids.get(series_id, ExternalIds())


class FakeMetadataProvider:
    def __init__(self, expected, aired):
        self._expected = expected
        self._aired = aired

    def get_expected_episode_count(self, provider_ids, season_number):
        return self._expected.get(season_number)

    def is_season_fully_aired(self, provider_ids, season_number):
        return self._aired.get(season_number)


def _candidate(
    series_id: str, series_name: str, season_number: int, episode_count: int
) -> CandidateSeason:
    season_key = SeasonKey(source="tautulli", series_id=series_id, season_number=season_number)
    season_ref = SeasonRef(
        season_key=season_key,
        series_name=series_name,
        season_title=f"Season {season_number}",
        season_id=f"{series_id}-s{season_number}",
    )
    return CandidateSeason(
        season_ref=season_ref,
        completed_at=datetime.now(tz=UTC),
        in_library_episode_count=episode_count,
        is_complete_in_source=None,
    )


class TestIsNewShow:
    def test_returns_true_for_recent_show(self):
        cutoff = datetime.now(tz=UTC) - timedelta(days=7)
        assert is_new_show("series-1", datetime.now(tz=UTC) - timedelta(days=1), cutoff) is True

    def test_returns_false_for_old_show(self):
        cutoff = datetime.now(tz=UTC) - timedelta(days=7)
        assert is_new_show("series-1", datetime.now(tz=UTC) - timedelta(days=30), cutoff) is False

    def test_returns_none_for_missing_timestamp(self):
        cutoff = datetime.now(tz=UTC) - timedelta(days=7)
        assert is_new_show("series-1", None, cutoff) is None


class TestValidateSeasonCompletion:
    def test_uses_source_complete_true(self):
        decision = validate_season_completion(
            provider_ids={},
            season_number=1,
            in_library_count=10,
            source_complete=True,
            metadata_provider=None,
            require_fully_aired=False,
        )
        assert isinstance(decision, CompletionDecision)
        assert decision.is_complete is True

    def test_uses_source_complete_false(self):
        decision = validate_season_completion(
            provider_ids={},
            season_number=1,
            in_library_count=10,
            source_complete=False,
            metadata_provider=None,
            require_fully_aired=False,
        )
        assert decision.is_complete is False

    def test_count_mismatch_is_incomplete(self):
        provider = FakeMetadataProvider(expected={1: 12}, aired={1: True})
        decision = validate_season_completion(
            provider_ids={"tmdb": "123"},
            season_number=1,
            in_library_count=10,
            source_complete=None,
            metadata_provider=provider,
            require_fully_aired=False,
        )
        assert decision.is_complete is False
        assert decision.expected_episode_count == 12

    def test_counts_match_and_fully_aired_is_complete(self):
        provider = FakeMetadataProvider(expected={1: 10}, aired={1: True})
        decision = validate_season_completion(
            provider_ids={"tmdb": "123"},
            season_number=1,
            in_library_count=10,
            source_complete=None,
            metadata_provider=provider,
            require_fully_aired=True,
        )
        assert decision.is_complete is True


class TestGetCompletedSeasons:
    def test_returns_empty_when_no_candidates(self):
        source = FakeSource(candidates=[], provider_ids={})
        result = get_completed_seasons(source, None, since=datetime.now(tz=UTC))
        assert result == []

    def test_returns_completed_season_with_metadata(self):
        source = FakeSource(
            candidates=[_candidate("series-1", "Show One", 2, 8)],
            provider_ids={"series-1": ExternalIds(tmdb="42")},
        )
        provider = FakeMetadataProvider(expected={2: 8}, aired={2: True})
        result = get_completed_seasons(
            source=source,
            metadata_provider=provider,
            since=datetime.now(tz=UTC) - timedelta(days=14),
            require_fully_aired=True,
        )
        assert len(result) == 1
        assert result[0]["show"] == "Show One"
        assert result[0]["season"] == 2
        assert result[0]["episode_count"] == 8
        assert result[0]["expected_count"] == 8

    def test_filters_not_fully_aired_when_required(self):
        source = FakeSource(
            candidates=[_candidate("series-2", "Show Two", 1, 10)],
            provider_ids={"series-2": ExternalIds(tmdb="99")},
        )
        provider = FakeMetadataProvider(expected={1: 10}, aired={1: False})
        result = get_completed_seasons(
            source=source,
            metadata_provider=provider,
            since=datetime.now(tz=UTC) - timedelta(days=14),
            require_fully_aired=True,
        )
        assert result == []
