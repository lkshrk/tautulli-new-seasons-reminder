"""Tests for TMDB and TVDB metadata providers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from urllib.error import HTTPError, URLError

from new_seasons_reminder.metadata.resolver import MetadataResolver
from new_seasons_reminder.metadata.tmdb import TMDBMetadataProvider
from new_seasons_reminder.metadata.tvdb import TVDBMetadataProvider

UTC = UTC


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_http(return_value=None, side_effect=None):
    mock = MagicMock()
    if side_effect:
        mock.get_json.side_effect = side_effect
        mock.post_json.side_effect = side_effect
    else:
        mock.get_json.return_value = return_value
        mock.post_json.return_value = return_value
    return mock


def _past_date(days: int) -> str:
    """Return an ISO date string N days in the past."""
    dt = datetime.now(tz=UTC) - timedelta(days=days)
    return dt.strftime("%Y-%m-%d")


def _future_date(days: int) -> str:
    """Return an ISO date string N days in the future."""
    dt = datetime.now(tz=UTC) + timedelta(days=days)
    return dt.strftime("%Y-%m-%d")


def _make_episode(number: int, air_date: str | None = None) -> dict:
    return {"episode_number": number, "air_date": air_date or _past_date(30)}


# ---------------------------------------------------------------------------
# TMDBMetadataProvider.get_expected_episode_count
# ---------------------------------------------------------------------------


class TestTMDBGetExpectedEpisodeCount:
    def _provider(self, http_mock):
        return TMDBMetadataProvider(tmdb_apikey="tmdb-key", http_client=http_mock)

    def test_returns_episode_count_from_api(self):
        episodes = [_make_episode(i) for i in range(1, 9)]
        http = _make_http(return_value={"episodes": episodes})
        provider = self._provider(http)

        count = provider.get_expected_episode_count({"tmdb": "1234"}, season_number=2)
        assert count == 8

    def test_returns_none_when_no_tmdb_id(self):
        http = _make_http(return_value={})
        provider = self._provider(http)

        count = provider.get_expected_episode_count({}, season_number=1)
        assert count is None

    def test_returns_none_on_http_error(self):
        http = _make_http(side_effect=HTTPError("http://x", 404, "Not Found", {}, None))
        provider = self._provider(http)

        count = provider.get_expected_episode_count({"tmdb": "1234"}, season_number=1)
        assert count is None

    def test_returns_none_on_url_error(self):
        http = _make_http(side_effect=URLError("connection refused"))
        provider = self._provider(http)

        count = provider.get_expected_episode_count({"tmdb": "1234"}, season_number=1)
        assert count is None

    def test_returns_none_on_non_dict_response(self):
        http = _make_http(return_value=None)
        provider = self._provider(http)

        count = provider.get_expected_episode_count({"tmdb": "1234"}, season_number=1)
        assert count is None

    def test_returns_none_when_episodes_not_list(self):
        http = _make_http(return_value={"episodes": "not-a-list"})
        provider = self._provider(http)

        count = provider.get_expected_episode_count({"tmdb": "1234"}, season_number=1)
        assert count is None

    def test_returns_zero_for_empty_episodes_list(self):
        http = _make_http(return_value={"episodes": []})
        provider = self._provider(http)

        count = provider.get_expected_episode_count({"tmdb": "1234"}, season_number=1)
        assert count == 0

    def test_ignores_non_tmdb_provider_ids(self):
        http = _make_http(return_value={})
        provider = self._provider(http)

        # Only tvdb id, no tmdb
        count = provider.get_expected_episode_count({"tvdb": "9999"}, season_number=1)
        assert count is None


# ---------------------------------------------------------------------------
# TMDBMetadataProvider.is_season_fully_aired
# ---------------------------------------------------------------------------


class TestTMDBIsSeasonFullyAired:
    def _provider(self, http_mock):
        return TMDBMetadataProvider(tmdb_apikey="tmdb-key", http_client=http_mock)

    def test_returns_true_when_all_aired(self):
        episodes = [_make_episode(i, air_date=_past_date(30)) for i in range(1, 4)]
        http = _make_http(return_value={"episodes": episodes})
        provider = self._provider(http)

        result = provider.is_season_fully_aired({"tmdb": "1234"}, season_number=1)
        assert result is True

    def test_returns_false_when_episode_not_yet_aired(self):
        episodes = [
            _make_episode(1, air_date=_past_date(5)),
            _make_episode(2, air_date=_future_date(5)),  # not aired yet
        ]
        http = _make_http(return_value={"episodes": episodes})
        provider = self._provider(http)

        result = provider.is_season_fully_aired({"tmdb": "1234"}, season_number=1)
        assert result is False

    def test_returns_false_when_episode_has_no_air_date(self):
        episodes = [
            _make_episode(1, air_date=_past_date(5)),
            {"episode_number": 2, "air_date": None},
        ]
        http = _make_http(return_value={"episodes": episodes})
        provider = self._provider(http)

        result = provider.is_season_fully_aired({"tmdb": "1234"}, season_number=1)
        assert result is False

    def test_returns_true_for_empty_episodes(self):
        http = _make_http(return_value={"episodes": []})
        provider = self._provider(http)

        result = provider.is_season_fully_aired({"tmdb": "1234"}, season_number=1)
        assert result is True

    def test_returns_none_when_no_tmdb_id(self):
        http = _make_http(return_value={})
        provider = self._provider(http)

        result = provider.is_season_fully_aired({}, season_number=1)
        assert result is None

    def test_returns_none_on_http_error(self):
        http = _make_http(side_effect=HTTPError("http://x", 500, "Err", {}, None))
        provider = self._provider(http)

        result = provider.is_season_fully_aired({"tmdb": "1234"}, season_number=1)
        assert result is None

    def test_returns_none_on_non_dict_response(self):
        http = _make_http(return_value=None)
        provider = self._provider(http)

        result = provider.is_season_fully_aired({"tmdb": "1234"}, season_number=1)
        assert result is None


# ---------------------------------------------------------------------------
# TVDBMetadataProvider (stub — documents API limitation)
# ---------------------------------------------------------------------------


class TestTVDBMetadataProvider:
    def _provider(self):
        return TVDBMetadataProvider(tvdb_apikey="tvdb-key")

    def test_get_expected_episode_count_returns_none_with_tvdb_id(self):
        provider = self._provider()
        result = provider.get_expected_episode_count({"tvdb": "12345"}, season_number=1)
        assert result is None

    def test_get_expected_episode_count_returns_none_without_tvdb_id(self):
        provider = self._provider()
        result = provider.get_expected_episode_count({}, season_number=1)
        assert result is None

    def test_is_season_fully_aired_returns_none_with_tvdb_id(self):
        provider = self._provider()
        result = provider.is_season_fully_aired({"tvdb": "12345"}, season_number=1)
        assert result is None

    def test_is_season_fully_aired_returns_none_without_tvdb_id(self):
        provider = self._provider()
        result = provider.is_season_fully_aired({}, season_number=1)
        assert result is None

    def test_ensure_auth_returns_false_on_http_error(self):
        http = _make_http(side_effect=HTTPError("http://x", 401, "Unauthorized", {}, None))
        provider = TVDBMetadataProvider(tvdb_apikey="tvdb-key", http_client=http)

        result = provider._ensure_auth()
        assert result is False

    def test_ensure_auth_returns_false_on_non_success_status(self):
        http = _make_http(return_value={"status": "failure"})
        provider = TVDBMetadataProvider(tvdb_apikey="tvdb-key", http_client=http)

        result = provider._ensure_auth()
        assert result is False

    def test_ensure_auth_returns_false_when_no_token(self):
        http = _make_http(return_value={"status": "success", "data": {}})
        provider = TVDBMetadataProvider(tvdb_apikey="tvdb-key", http_client=http)

        result = provider._ensure_auth()
        assert result is False

    def test_ensure_auth_returns_true_when_token_found(self):
        http = _make_http(return_value={"status": "success", "data": {"token": "abc123"}})
        provider = TVDBMetadataProvider(tvdb_apikey="tvdb-key", http_client=http)

        result = provider._ensure_auth()
        assert result is True
        assert provider._auth_token == "abc123"

    def test_ensure_auth_skips_login_if_token_cached(self):
        http = _make_http(return_value={})
        provider = TVDBMetadataProvider(tvdb_apikey="tvdb-key", http_client=http)
        provider._auth_token = "cached-token"

        result = provider._ensure_auth()
        assert result is True
        http.post_json.assert_not_called()


# ---------------------------------------------------------------------------
# MetadataResolver (primary + fallback)
# ---------------------------------------------------------------------------


class FakeMetadataProvider:
    """Simple test double for ExternalMetadataProvider."""

    def __init__(self, expected: int | None, aired: bool | None):
        self._expected = expected
        self._aired = aired

    def get_expected_episode_count(self, provider_ids, season_number):
        return self._expected

    def is_season_fully_aired(self, provider_ids, season_number):
        return self._aired


class TestMetadataResolver:
    def test_uses_primary_when_it_returns_count(self):
        primary = FakeMetadataProvider(expected=10, aired=True)
        fallback = FakeMetadataProvider(expected=99, aired=False)
        resolver = MetadataResolver(primary=primary, fallback=fallback)

        count = resolver.get_expected_episode_count({"tmdb": "1"}, season_number=1)
        assert count == 10

    def test_falls_back_when_primary_returns_none(self):
        primary = FakeMetadataProvider(expected=None, aired=None)
        fallback = FakeMetadataProvider(expected=8, aired=True)
        resolver = MetadataResolver(primary=primary, fallback=fallback)

        count = resolver.get_expected_episode_count({"tvdb": "1"}, season_number=1)
        assert count == 8

    def test_returns_none_when_both_return_none(self):
        primary = FakeMetadataProvider(expected=None, aired=None)
        fallback = FakeMetadataProvider(expected=None, aired=None)
        resolver = MetadataResolver(primary=primary, fallback=fallback)

        count = resolver.get_expected_episode_count({}, season_number=1)
        assert count is None

    def test_no_fallback_returns_primary_result(self):
        primary = FakeMetadataProvider(expected=6, aired=True)
        resolver = MetadataResolver(primary=primary, fallback=None)

        count = resolver.get_expected_episode_count({"tmdb": "1"}, season_number=1)
        assert count == 6

    def test_is_season_fully_aired_uses_primary(self):
        primary = FakeMetadataProvider(expected=6, aired=True)
        resolver = MetadataResolver(primary=primary, fallback=None)

        aired = resolver.is_season_fully_aired({"tmdb": "1"}, season_number=1)
        assert aired is True

    def test_is_season_fully_aired_falls_back(self):
        primary = FakeMetadataProvider(expected=None, aired=None)
        fallback = FakeMetadataProvider(expected=6, aired=False)
        resolver = MetadataResolver(primary=primary, fallback=fallback)

        aired = resolver.is_season_fully_aired({"tvdb": "1"}, season_number=1)
        assert aired is False

    def test_caches_result_for_same_key(self):
        call_count = 0

        class CountingProvider:
            def get_expected_episode_count(self, provider_ids, season_number):
                nonlocal call_count
                call_count += 1
                return 10

            def is_season_fully_aired(self, provider_ids, season_number):
                return True

        provider = CountingProvider()
        resolver = MetadataResolver(primary=provider, fallback=None)

        resolver.get_expected_episode_count({"tmdb": "1"}, season_number=1)
        resolver.get_expected_episode_count({"tmdb": "1"}, season_number=1)

        # Should only call the provider once due to caching
        assert call_count == 1

    def test_no_cache_collision_across_seasons(self):
        results = {1: 10, 2: 8}

        class SeasonAwareProvider:
            def get_expected_episode_count(self, provider_ids, season_number):
                return results.get(season_number)

            def is_season_fully_aired(self, provider_ids, season_number):
                return True

        provider = SeasonAwareProvider()
        resolver = MetadataResolver(primary=provider, fallback=None)

        assert resolver.get_expected_episode_count({"tmdb": "1"}, season_number=1) == 10
        assert resolver.get_expected_episode_count({"tmdb": "1"}, season_number=2) == 8
