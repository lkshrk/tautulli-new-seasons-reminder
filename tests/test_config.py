"""Tests for Config dataclass and setup_logging."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from new_seasons_reminder.config import Config, setup_logging
from new_seasons_reminder.metadata.tmdb import TMDBMetadataProvider
from new_seasons_reminder.metadata.tvdb import TVDBMetadataProvider
from new_seasons_reminder.sources.jellyfin import JellyfinMediaSource
from new_seasons_reminder.sources.tautulli import TautulliMediaSource

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env(**overrides: str):
    """Return a minimal valid env dict for Tautulli source."""
    base = {
        "SOURCE_TYPE": "tautulli",
        "TAUTULLI_URL": "http://tautulli:8181",
        "TAUTULLI_APIKEY": "tautulli-key",
        "WEBHOOK_URL": "http://example.com/hook",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Config.from_env — defaults
# ---------------------------------------------------------------------------


class TestConfigFromEnvDefaults:
    def test_source_type_defaults_to_tautulli(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = Config.from_env()
        assert cfg.source_type == "tautulli"

    def test_lookback_days_defaults_to_7(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = Config.from_env()
        assert cfg.lookback_days == 7

    def test_debug_defaults_to_false(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = Config.from_env()
        assert cfg.debug is False

    def test_include_new_shows_defaults_to_false(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = Config.from_env()
        assert cfg.include_new_shows is False

    def test_require_fully_aired_defaults_to_false(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = Config.from_env()
        assert cfg.require_fully_aired is False

    def test_webhook_on_empty_defaults_to_false(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = Config.from_env()
        assert cfg.webhook_on_empty is False

    def test_webhook_mode_defaults_to_default(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = Config.from_env()
        assert cfg.webhook_mode == "default"

    def test_metadata_providers_defaults_to_empty(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = Config.from_env()
        assert cfg.metadata_providers == ()

    def test_disable_ssl_verify_defaults_to_false(self):
        with patch.dict(os.environ, _env(), clear=True):
            cfg = Config.from_env()
        assert cfg.disable_ssl_verify is False


# ---------------------------------------------------------------------------
# Config.from_env — explicit values
# ---------------------------------------------------------------------------


class TestConfigFromEnvExplicit:
    def test_reads_tautulli_url(self):
        with patch.dict(os.environ, _env(TAUTULLI_URL="http://custom:9000"), clear=True):
            cfg = Config.from_env()
        assert cfg.tautulli_url == "http://custom:9000"

    def test_reads_tautulli_apikey(self):
        with patch.dict(os.environ, _env(TAUTULLI_APIKEY="secret123"), clear=True):
            cfg = Config.from_env()
        assert cfg.tautulli_apikey == "secret123"

    def test_reads_lookback_days(self):
        with patch.dict(os.environ, _env(LOOKBACK_DAYS="14"), clear=True):
            cfg = Config.from_env()
        assert cfg.lookback_days == 14

    def test_reads_debug_true(self):
        with patch.dict(os.environ, _env(DEBUG="true"), clear=True):
            cfg = Config.from_env()
        assert cfg.debug is True

    def test_reads_include_new_shows_true(self):
        with patch.dict(os.environ, _env(INCLUDE_NEW_SHOWS="true"), clear=True):
            cfg = Config.from_env()
        assert cfg.include_new_shows is True

    def test_reads_require_fully_aired_true(self):
        with patch.dict(os.environ, _env(REQUIRE_FULLY_AIRED="true"), clear=True):
            cfg = Config.from_env()
        assert cfg.require_fully_aired is True

    def test_reads_webhook_on_empty_true(self):
        with patch.dict(os.environ, _env(WEBHOOK_ON_EMPTY="true"), clear=True):
            cfg = Config.from_env()
        assert cfg.webhook_on_empty is True

    def test_reads_metadata_providers_tmdb(self):
        with patch.dict(os.environ, _env(METADATA_PROVIDERS="tmdb", TMDB_APIKEY="t"), clear=True):
            cfg = Config.from_env()
        assert "tmdb" in cfg.metadata_providers

    def test_reads_metadata_providers_multiple(self):
        with patch.dict(
            os.environ,
            _env(METADATA_PROVIDERS="tmdb,tvdb", TMDB_APIKEY="t", TVDB_APIKEY="v"),
            clear=True,
        ):
            cfg = Config.from_env()
        assert cfg.metadata_providers == ("tmdb", "tvdb")

    def test_reads_tmdb_apikey(self):
        with patch.dict(os.environ, _env(TMDB_APIKEY="tmdb-secret"), clear=True):
            cfg = Config.from_env()
        assert cfg.tmdb_apikey == "tmdb-secret"

    def test_reads_tvdb_apikey(self):
        with patch.dict(os.environ, _env(TVDB_APIKEY="tvdb-secret"), clear=True):
            cfg = Config.from_env()
        assert cfg.tvdb_apikey == "tvdb-secret"

    def test_reads_disable_ssl_verify_true(self):
        with patch.dict(os.environ, _env(DISABLE_SSL_VERIFY="true"), clear=True):
            cfg = Config.from_env()
        assert cfg.disable_ssl_verify is True

    def test_jellyfin_source_type(self):
        env = {
            "SOURCE_TYPE": "jellyfin",
            "JELLYFIN_URL": "http://jellyfin:8096",
            "JELLYFIN_APIKEY": "jf-key",
            "JELLYFIN_USER_ID": "user-42",
            "WEBHOOK_URL": "http://example.com/hook",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = Config.from_env()
        assert cfg.source_type == "jellyfin"
        assert cfg.jellyfin_url == "http://jellyfin:8096"
        assert cfg.jellyfin_apikey == "jf-key"
        assert cfg.jellyfin_user_id == "user-42"


# ---------------------------------------------------------------------------
# Config.from_env — validation / edge cases
# ---------------------------------------------------------------------------


class TestConfigFromEnvEdgeCases:
    def test_invalid_source_type_raises(self):
        with (
            patch.dict(os.environ, _env(SOURCE_TYPE="plex"), clear=True),
            pytest.raises(ValueError, match="SOURCE_TYPE"),
        ):
            Config.from_env()

    def test_lookback_days_too_low_falls_back_to_7(self):
        with patch.dict(os.environ, _env(LOOKBACK_DAYS="0"), clear=True):
            cfg = Config.from_env()
        assert cfg.lookback_days == 7

    def test_lookback_days_too_high_falls_back_to_7(self):
        with patch.dict(os.environ, _env(LOOKBACK_DAYS="400"), clear=True):
            cfg = Config.from_env()
        assert cfg.lookback_days == 7

    def test_lookback_days_not_a_number_falls_back_to_7(self):
        with patch.dict(os.environ, _env(LOOKBACK_DAYS="abc"), clear=True):
            cfg = Config.from_env()
        assert cfg.lookback_days == 7

    def test_webhook_on_empty_case_insensitive(self):
        with patch.dict(os.environ, _env(WEBHOOK_ON_EMPTY="True"), clear=True):
            cfg = Config.from_env()
        assert cfg.webhook_on_empty is True


# ---------------------------------------------------------------------------
# Config.validate
# ---------------------------------------------------------------------------


class TestConfigValidate:
    def test_valid_tautulli_config_passes(self):
        cfg = Config(
            source_type="tautulli",
            tautulli_url="http://tautulli:8181",
            tautulli_apikey="key",
            webhook_url="http://example.com/hook",
        )
        cfg.validate()  # should not raise

    def test_missing_tautulli_url_raises(self):
        cfg = Config(source_type="tautulli", tautulli_url="", webhook_url="http://x.com")
        with pytest.raises(ValueError, match="Tautulli URL"):
            cfg.validate()

    def test_missing_webhook_url_raises(self):
        cfg = Config(
            source_type="tautulli",
            tautulli_url="http://tautulli",
            tautulli_apikey="k",
            webhook_url="",
        )
        with pytest.raises(ValueError, match="WEBHOOK_URL"):
            cfg.validate()

    def test_jellyfin_missing_url_raises(self):
        cfg = Config(
            source_type="jellyfin",
            jellyfin_url="",
            jellyfin_apikey="key",
            jellyfin_user_id="uid",
            webhook_url="http://x.com",
        )
        with pytest.raises(ValueError, match="Jellyfin URL"):
            cfg.validate()

    def test_jellyfin_missing_apikey_raises(self):
        cfg = Config(
            source_type="jellyfin",
            jellyfin_url="http://jf",
            jellyfin_apikey="",
            jellyfin_user_id="uid",
            webhook_url="http://x.com",
        )
        with pytest.raises(ValueError, match="API key"):
            cfg.validate()

    def test_jellyfin_missing_user_id_raises(self):
        cfg = Config(
            source_type="jellyfin",
            jellyfin_url="http://jf",
            jellyfin_apikey="key",
            jellyfin_user_id="",
            webhook_url="http://x.com",
        )
        with pytest.raises(ValueError, match="user ID"):
            cfg.validate()

    def test_tmdb_missing_apikey_raises(self):
        cfg = Config(
            source_type="tautulli",
            tautulli_url="http://t",
            tautulli_apikey="k",
            webhook_url="http://x.com",
            metadata_providers=("tmdb",),
            tmdb_apikey="",
        )
        with pytest.raises(ValueError, match="TMDB_APIKEY"):
            cfg.validate()

    def test_tvdb_missing_apikey_raises(self):
        cfg = Config(
            source_type="tautulli",
            tautulli_url="http://t",
            tautulli_apikey="k",
            webhook_url="http://x.com",
            metadata_providers=("tvdb",),
            tvdb_apikey="",
        )
        with pytest.raises(ValueError, match="TVDB_APIKEY"):
            cfg.validate()


# ---------------------------------------------------------------------------
# Config.create_media_source
# ---------------------------------------------------------------------------


class TestCreateMediaSource:
    def test_creates_tautulli_source(self):
        cfg = Config(
            source_type="tautulli",
            tautulli_url="http://tautulli:8181",
            tautulli_apikey="key",
        )
        source = cfg.create_media_source()
        assert isinstance(source, TautulliMediaSource)

    def test_creates_jellyfin_source(self):
        cfg = Config(
            source_type="jellyfin",
            jellyfin_url="http://jellyfin:8096",
            jellyfin_apikey="key",
            jellyfin_user_id="uid",
        )
        source = cfg.create_media_source()
        assert isinstance(source, JellyfinMediaSource)

    def test_tautulli_missing_url_raises(self):
        cfg = Config(source_type="tautulli", tautulli_url="", tautulli_apikey="key")
        with pytest.raises(ValueError):
            cfg.create_media_source()

    def test_jellyfin_missing_user_id_raises(self):
        cfg = Config(
            source_type="jellyfin",
            jellyfin_url="http://jf",
            jellyfin_apikey="key",
            jellyfin_user_id="",
        )
        with pytest.raises(ValueError):
            cfg.create_media_source()

    def test_unknown_source_type_raises(self):
        cfg = Config(source_type="plex")
        with pytest.raises(ValueError, match="Unknown source type"):
            cfg.create_media_source()

    def test_create_http_client_disables_ssl_verification(self):
        cfg = Config(disable_ssl_verify=True)
        client = cfg.create_http_client()
        assert client.verify_ssl is False

    def test_tautulli_source_uses_ssl_setting_in_http_client(self):
        cfg = Config(
            source_type="tautulli",
            tautulli_url="http://tautulli:8181",
            tautulli_apikey="key",
            disable_ssl_verify=True,
        )
        source = cfg.create_media_source()
        assert isinstance(source, TautulliMediaSource)
        assert source._http_client.verify_ssl is False


# ---------------------------------------------------------------------------
# Config.create_metadata_providers
# ---------------------------------------------------------------------------


class TestCreateMetadataProviders:
    def test_empty_providers_returns_empty_list(self):
        cfg = Config()
        providers = cfg.create_metadata_providers()
        assert providers == []

    def test_tmdb_provider_created(self):
        cfg = Config(metadata_providers=("tmdb",), tmdb_apikey="tmdb-key")
        providers = cfg.create_metadata_providers()
        assert len(providers) == 1
        assert isinstance(providers[0], TMDBMetadataProvider)

    def test_tvdb_provider_created(self):
        cfg = Config(metadata_providers=("tvdb",), tvdb_apikey="tvdb-key")
        providers = cfg.create_metadata_providers()
        assert len(providers) == 1
        assert isinstance(providers[0], TVDBMetadataProvider)

    def test_both_providers_created_in_order(self):
        cfg = Config(
            metadata_providers=("tmdb", "tvdb"),
            tmdb_apikey="tmdb-key",
            tvdb_apikey="tvdb-key",
        )
        providers = cfg.create_metadata_providers()
        assert len(providers) == 2
        assert isinstance(providers[0], TMDBMetadataProvider)
        assert isinstance(providers[1], TVDBMetadataProvider)

    def test_tmdb_skipped_if_no_apikey(self):
        cfg = Config(metadata_providers=("tmdb",), tmdb_apikey="")
        providers = cfg.create_metadata_providers()
        assert providers == []

    def test_tvdb_skipped_if_no_apikey(self):
        cfg = Config(metadata_providers=("tvdb",), tvdb_apikey="")
        providers = cfg.create_metadata_providers()
        assert providers == []


# ---------------------------------------------------------------------------
# Config.get_provider_config
# ---------------------------------------------------------------------------


class TestGetProviderConfig:
    def test_returns_dict_with_webhook_url(self):
        cfg = Config(webhook_url="http://example.com/hook")
        pc = cfg.get_provider_config()
        assert pc["webhook_url"] == "http://example.com/hook"

    def test_returns_dict_with_lookback_days(self):
        cfg = Config(lookback_days=14)
        pc = cfg.get_provider_config()
        assert pc["lookback_days"] == 14

    def test_returns_dict_with_signal_settings(self):
        cfg = Config(signal_number="+1234", signal_recipients="+5678", signal_text_mode="normal")
        pc = cfg.get_provider_config()
        assert pc["signal_number"] == "+1234"
        assert pc["signal_recipients"] == "+5678"
        assert pc["signal_text_mode"] == "normal"


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------


class TestSetupLogging:
    def test_returns_logger(self):
        import logging

        result = setup_logging(debug=False)
        assert isinstance(result, logging.Logger)

    def test_debug_mode_returns_logger_without_error(self):
        import logging

        result = setup_logging(debug=True)
        assert isinstance(result, logging.Logger)

    def test_info_mode_returns_logger_without_error(self):
        import logging

        result = setup_logging(debug=False)
        assert isinstance(result, logging.Logger)
