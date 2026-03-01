"""Tests for Tautulli and Jellyfin media source adapters."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from email.message import Message
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from new_seasons_reminder.models import ExternalIds, SeasonRef
from new_seasons_reminder.sources.jellyfin import JellyfinMediaSource
from new_seasons_reminder.sources.tautulli import TautulliMediaSource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _recent_ts(days_ago: int = 1) -> int:
    """Return a UNIX timestamp from N days ago."""
    return int((_now() - timedelta(days=days_ago)).timestamp())


def _make_http(return_value=None, side_effect=None):
    mock = MagicMock()
    if side_effect:
        mock.get_json.side_effect = side_effect
        mock.post_json.side_effect = side_effect
    else:
        mock.get_json.return_value = return_value
        mock.post_json.return_value = return_value
    return mock


# ---------------------------------------------------------------------------
# TautulliMediaSource
# ---------------------------------------------------------------------------


class TestTautulliGetCandidateSeasons:
    def test_sets_api_http_client_on_init(self):
        with patch("new_seasons_reminder.sources.tautulli.set_http_client") as mock_set_client:
            source = TautulliMediaSource("http://t:8181", "k")

        mock_set_client.assert_called_once_with(source._http_client)

    def test_returns_empty_when_no_recent_seasons(self):
        since = _now() - timedelta(days=7)
        with (
            patch("new_seasons_reminder.sources.tautulli.get_recently_added", return_value=[]),
            patch("new_seasons_reminder.sources.tautulli.get_children_metadata", return_value=[]),
        ):
            source = TautulliMediaSource("http://t:8181", "k")
            result = source.get_candidate_seasons(since)
        assert list(result) == []

    def test_returns_candidate_for_recent_season(self):
        since = _now() - timedelta(days=7)
        recent_ts = _recent_ts(1)

        season_data = [
            {
                "rating_key": "100",
                "title": "Season 2",
                "parent_title": "Breaking Bad",
                "parent_rating_key": "10",
                "media_index": 2,
            }
        ]
        episodes = [
            {"rating_key": "ep1", "added_at": recent_ts},
            {"rating_key": "ep2", "added_at": recent_ts},
        ]

        with (
            patch(
                "new_seasons_reminder.sources.tautulli.get_recently_added", return_value=season_data
            ),
            patch(
                "new_seasons_reminder.sources.tautulli.get_children_metadata", return_value=episodes
            ),
        ):
            source = TautulliMediaSource("http://t:8181", "k")
            candidates = list(source.get_candidate_seasons(since))

        assert len(candidates) == 1
        assert candidates[0].season_ref.series_name == "Breaking Bad"
        assert candidates[0].season_ref.season_key.season_number == 2
        assert candidates[0].in_library_episode_count == 2
        assert candidates[0].is_complete_in_source is None  # Tautulli never provides this

    def test_skips_season_older_than_since(self):
        since = _now() - timedelta(days=1)
        old_ts = _recent_ts(10)  # 10 days ago

        season_data = [
            {
                "rating_key": "100",
                "title": "Season 1",
                "parent_title": "The Office",
                "parent_rating_key": "20",
                "media_index": 1,
            }
        ]
        episodes = [{"rating_key": "ep1", "added_at": old_ts}]

        with (
            patch(
                "new_seasons_reminder.sources.tautulli.get_recently_added", return_value=season_data
            ),
            patch(
                "new_seasons_reminder.sources.tautulli.get_children_metadata", return_value=episodes
            ),
        ):
            source = TautulliMediaSource("http://t:8181", "k")
            candidates = list(source.get_candidate_seasons(since))

        assert candidates == []

    def test_skips_season_with_no_episodes(self):
        since = _now() - timedelta(days=7)
        season_data = [
            {
                "rating_key": "100",
                "title": "Season 1",
                "parent_title": "Show",
                "parent_rating_key": "20",
                "media_index": 1,
            }
        ]

        with (
            patch(
                "new_seasons_reminder.sources.tautulli.get_recently_added", return_value=season_data
            ),
            patch("new_seasons_reminder.sources.tautulli.get_children_metadata", return_value=[]),
        ):
            source = TautulliMediaSource("http://t:8181", "k")
            candidates = list(source.get_candidate_seasons(since))

        assert candidates == []

    def test_skips_malformed_season_data(self):
        since = _now() - timedelta(days=7)
        season_data = [{"missing_required_fields": True}]

        with patch(
            "new_seasons_reminder.sources.tautulli.get_recently_added", return_value=season_data
        ):
            source = TautulliMediaSource("http://t:8181", "k")
            candidates = list(source.get_candidate_seasons(since))

        assert candidates == []

    def test_uses_documented_tautulli_media_type_params(self):
        since = _now() - timedelta(days=7)
        season_data = [
            {
                "rating_key": "100",
                "title": "Season 1",
                "parent_title": "Show",
                "parent_rating_key": "20",
                "media_index": 1,
            }
        ]
        episodes = [{"rating_key": "ep1", "added_at": _recent_ts(1)}]

        with (
            patch(
                "new_seasons_reminder.sources.tautulli.get_recently_added", return_value=season_data
            ) as mock_recently_added,
            patch(
                "new_seasons_reminder.sources.tautulli.get_children_metadata", return_value=episodes
            ) as mock_children,
        ):
            source = TautulliMediaSource("http://t:8181", "k")
            candidates = list(source.get_candidate_seasons(since))

        assert len(candidates) == 1
        assert mock_recently_added.call_args.kwargs["media_type"] == "show"
        assert mock_children.call_args.kwargs["media_type"] == "season"

    def test_warns_when_no_recent_items_and_no_libraries(self, caplog):
        since = _now() - timedelta(days=7)

        with (
            patch("new_seasons_reminder.sources.tautulli.get_recently_added", return_value=[]),
            patch("new_seasons_reminder.sources.tautulli.get_libraries", return_value=[]),
            caplog.at_level(logging.WARNING),
        ):
            source = TautulliMediaSource("http://t:8181", "k")
            candidates = list(source.get_candidate_seasons(since))

        assert candidates == []
        assert "Tautulli returned zero libraries" in caplog.text


class TestTautulliGetShowAddedAt:
    def test_returns_datetime_from_int_timestamp(self):
        ts = _recent_ts(365)
        with patch(
            "new_seasons_reminder.sources.tautulli.get_metadata",
            return_value={"added_at": ts},
        ):
            source = TautulliMediaSource("http://t:8181", "k")
            result = source.get_show_added_at("series-1")

        assert isinstance(result, datetime)

    def test_returns_none_when_no_metadata(self):
        with patch("new_seasons_reminder.sources.tautulli.get_metadata", return_value=None):
            source = TautulliMediaSource("http://t:8181", "k")
            result = source.get_show_added_at("series-1")
        assert result is None

    def test_returns_none_when_no_added_at(self):
        with patch(
            "new_seasons_reminder.sources.tautulli.get_metadata", return_value={"title": "Show"}
        ):
            source = TautulliMediaSource("http://t:8181", "k")
            result = source.get_show_added_at("series-1")
        assert result is None


class TestTautulliGetProviderIds:
    def test_parses_tmdb_guid(self):
        with patch(
            "new_seasons_reminder.sources.tautulli.get_metadata",
            return_value={"guid": ["tmdb://12345/1"]},
        ):
            source = TautulliMediaSource("http://t:8181", "k")
            ids = source.get_provider_ids("series-1")

        assert ids.tmdb == "12345"
        assert ids.tvdb is None

    def test_parses_tvdb_guid(self):
        with patch(
            "new_seasons_reminder.sources.tautulli.get_metadata",
            return_value={"guid": ["thetvdb://67890/1"]},
        ):
            source = TautulliMediaSource("http://t:8181", "k")
            ids = source.get_provider_ids("series-1")

        assert ids.tvdb == "67890"

    def test_parses_imdb_guid(self):
        with patch(
            "new_seasons_reminder.sources.tautulli.get_metadata",
            return_value={"guid": ["imdb://tt1234567/1"]},
        ):
            source = TautulliMediaSource("http://t:8181", "k")
            ids = source.get_provider_ids("series-1")

        assert ids.imdb == "tt1234567"

    def test_returns_empty_external_ids_when_no_metadata(self):
        with patch("new_seasons_reminder.sources.tautulli.get_metadata", return_value=None):
            source = TautulliMediaSource("http://t:8181", "k")
            ids = source.get_provider_ids("series-1")
        assert ids == ExternalIds()

    def test_returns_empty_when_no_guids(self):
        with patch(
            "new_seasons_reminder.sources.tautulli.get_metadata",
            return_value={"guid": []},
        ):
            source = TautulliMediaSource("http://t:8181", "k")
            ids = source.get_provider_ids("series-1")
        assert ids == ExternalIds()


class TestTautulliListSeasons:
    def test_returns_season_refs(self):
        season_data = [
            {
                "rating_key": "100",
                "title": "Season 1",
                "parent_title": "Show A",
                "parent_rating_key": "10",
                "media_index": 1,
            }
        ]
        with patch(
            "new_seasons_reminder.sources.tautulli.get_recently_added", return_value=season_data
        ):
            source = TautulliMediaSource("http://t:8181", "k")
            seasons = list(source.list_seasons())

        assert len(seasons) == 1
        assert isinstance(seasons[0], SeasonRef)
        assert seasons[0].series_name == "Show A"


# ---------------------------------------------------------------------------
# JellyfinMediaSource
# ---------------------------------------------------------------------------


def _jf_season_item(
    season_id="s1",
    series_id="series1",
    season_number=1,
    series_name="Show",
    date_created=None,
    child_count=5,
    played=False,
):
    if date_created is None:
        date_created = (_now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.0000000Z")
    return {
        "Id": season_id,
        "SeriesId": series_id,
        "IndexNumber": season_number,
        "SeriesName": series_name,
        "Name": f"Season {season_number}",
        "DateCreated": date_created,
        "ChildCount": child_count,
        "LocationType": "FileSystem",
        "UserData": {"Played": played},
    }


class TestJellyfinGetCandidateSeasons:
    def _source(self, http_mock):
        return JellyfinMediaSource(
            jellyfin_url="http://jf:8096",
            jellyfin_apikey="jf-key",
            user_id="user-1",
            http_client=http_mock,
        )

    def test_returns_candidate_for_recent_season(self):
        since = _now() - timedelta(days=7)
        item = _jf_season_item()
        http = _make_http(return_value=[item])
        source = self._source(http)

        candidates = list(source.get_candidate_seasons(since))
        assert len(candidates) == 1
        assert candidates[0].season_ref.series_name == "Show"
        assert candidates[0].in_library_episode_count == 5
        assert candidates[0].is_complete_in_source is False  # Played=False

    def test_returns_complete_when_played_true(self):
        since = _now() - timedelta(days=7)
        item = _jf_season_item(played=True)
        http = _make_http(return_value=[item])
        source = self._source(http)

        candidates = list(source.get_candidate_seasons(since))
        assert candidates[0].is_complete_in_source is True

    def test_skips_season_older_than_since(self):
        since = _now() - timedelta(hours=1)
        old_date = (_now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S.0000000Z")
        item = _jf_season_item(date_created=old_date)
        http = _make_http(return_value=[item])
        source = self._source(http)

        candidates = list(source.get_candidate_seasons(since))
        assert candidates == []

    def test_skips_season_with_no_date_created(self):
        since = _now() - timedelta(days=7)
        item = _jf_season_item()
        item.pop("DateCreated")
        http = _make_http(return_value=[item])
        source = self._source(http)

        candidates = list(source.get_candidate_seasons(since))
        assert candidates == []

    def test_returns_empty_on_http_error(self):
        since = _now() - timedelta(days=7)
        http = _make_http(side_effect=HTTPError("http://x", 500, "Err", Message(), None))
        source = self._source(http)

        candidates = list(source.get_candidate_seasons(since))
        assert candidates == []

    def test_returns_empty_on_url_error(self):
        since = _now() - timedelta(days=7)
        http = _make_http(side_effect=URLError("connection refused"))
        source = self._source(http)

        candidates = list(source.get_candidate_seasons(since))
        assert candidates == []

    def test_returns_empty_on_non_list_response(self):
        since = _now() - timedelta(days=7)
        http = _make_http(return_value={"unexpected": "dict"})
        source = self._source(http)

        candidates = list(source.get_candidate_seasons(since))
        assert candidates == []


class TestJellyfinGetShowAddedAt:
    def _source(self, http_mock):
        return JellyfinMediaSource(
            jellyfin_url="http://jf:8096",
            jellyfin_apikey="jf-key",
            user_id="user-1",
            http_client=http_mock,
        )

    def test_returns_datetime_from_iso_string(self):
        date_str = "2025-01-01T12:00:00.0000000Z"
        http = _make_http(return_value={"DateCreated": date_str})
        source = self._source(http)

        result = source.get_show_added_at("series-1")
        assert isinstance(result, datetime)

    def test_returns_none_on_http_error(self):
        http = _make_http(side_effect=HTTPError("http://x", 404, "Not Found", Message(), None))
        source = self._source(http)

        result = source.get_show_added_at("series-1")
        assert result is None

    def test_returns_none_when_no_date_created(self):
        http = _make_http(return_value={"Name": "Show"})
        source = self._source(http)

        result = source.get_show_added_at("series-1")
        assert result is None

    def test_returns_none_on_non_dict_response(self):
        http = _make_http(return_value=None)
        source = self._source(http)

        result = source.get_show_added_at("series-1")
        assert result is None


class TestJellyfinGetProviderIds:
    def _source(self, http_mock):
        return JellyfinMediaSource(
            jellyfin_url="http://jf:8096",
            jellyfin_apikey="jf-key",
            user_id="user-1",
            http_client=http_mock,
        )

    def test_parses_tmdb_id(self):
        http = _make_http(return_value={"ProviderIds": {"Tmdb": "42", "Tvdb": "99"}})
        source = self._source(http)

        ids = source.get_provider_ids("series-1")
        assert ids.tmdb == "42"
        assert ids.tvdb == "99"

    def test_returns_empty_on_http_error(self):
        http = _make_http(side_effect=HTTPError("http://x", 500, "Err", Message(), None))
        source = self._source(http)

        ids = source.get_provider_ids("series-1")
        assert ids == ExternalIds()

    def test_returns_empty_when_no_provider_ids(self):
        http = _make_http(return_value={"Name": "Show"})
        source = self._source(http)

        ids = source.get_provider_ids("series-1")
        assert ids == ExternalIds()

    def test_returns_empty_on_none_response(self):
        http = _make_http(return_value=None)
        source = self._source(http)

        ids = source.get_provider_ids("series-1")
        assert ids == ExternalIds()


class TestJellyfinListSeasons:
    def _source(self, http_mock):
        return JellyfinMediaSource(
            jellyfin_url="http://jf:8096",
            jellyfin_apikey="jf-key",
            user_id="user-1",
            http_client=http_mock,
        )

    def test_returns_season_refs(self):
        items = [_jf_season_item(season_id="s1", series_name="Show A")]
        http = _make_http(return_value={"Items": items})
        source = self._source(http)

        seasons = list(source.list_seasons())
        assert len(seasons) == 1
        assert isinstance(seasons[0], SeasonRef)
        assert seasons[0].series_name == "Show A"

    def test_returns_empty_on_http_error(self):
        http = _make_http(side_effect=HTTPError("http://x", 500, "Err", Message(), None))
        source = self._source(http)

        seasons = list(source.list_seasons())
        assert seasons == []

    def test_returns_empty_on_non_dict_response(self):
        http = _make_http(return_value=None)
        source = self._source(http)

        seasons = list(source.list_seasons())
        assert seasons == []
