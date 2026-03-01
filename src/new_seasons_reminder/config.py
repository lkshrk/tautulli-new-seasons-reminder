"""Configuration management for new_seasons_reminder."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from new_seasons_reminder.http import HTTPClient
from new_seasons_reminder.metadata.base import ExternalMetadataProvider
from new_seasons_reminder.metadata.tmdb import TMDBMetadataProvider
from new_seasons_reminder.metadata.tvdb import TVDBMetadataProvider
from new_seasons_reminder.sources.base import MediaSource

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    # Media source configuration
    source_type: str = "tautulli"  # "tautulli" or "jellyfin"

    # Tautulli settings
    tautulli_url: str = ""
    tautulli_apikey: str = ""

    # Jellyfin settings
    jellyfin_url: str = ""
    jellyfin_apikey: str = ""
    jellyfin_user_id: str = ""

    # Metadata providers
    metadata_providers: tuple[str, ...] = ()
    tmdb_apikey: str = ""
    tvdb_apikey: str = ""

    # Webhook settings
    webhook_url: str = ""
    webhook_mode: str = "default"
    webhook_message_template: str = "📺 {season_count} new season(s) completed this week!"
    webhook_on_empty: bool = False
    webhook_payload_template: str = "default"

    # Signal CLI settings
    signal_number: str = ""
    signal_recipients: str = ""
    signal_text_mode: str = "styled"

    # Application settings
    lookback_days: int = 7
    debug: bool = False
    include_new_shows: bool = False
    require_fully_aired: bool = False
    disable_ssl_verify: bool = False

    @classmethod
    def from_env(cls) -> Config:
        """Create configuration from environment variables."""
        config = cls()

        # Media source type
        config.source_type = os.environ.get("SOURCE_TYPE", "tautulli").lower()
        if config.source_type not in ("tautulli", "jellyfin"):
            raise ValueError("SOURCE_TYPE must be 'tautulli' or 'jellyfin'")

        # Tautulli settings
        config.tautulli_url = os.environ.get("TAUTULLI_URL", "")
        config.tautulli_apikey = os.environ.get("TAUTULLI_APIKEY", "")
        logger.debug("Loaded TAUTULLI_URL=%s", config.tautulli_url)
        logger.debug("Loaded TAUTULLI_APIKEY=%s", config._mask_value(config.tautulli_apikey))

        # Jellyfin settings (required if source_type is jellyfin)
        config.jellyfin_url = os.environ.get("JELLYFIN_URL", "")
        config.jellyfin_apikey = os.environ.get("JELLYFIN_APIKEY", "")
        config.jellyfin_user_id = os.environ.get("JELLYFIN_USER_ID", "")
        if config.source_type == "jellyfin":
            logger.debug("Loaded JELLYFIN_URL=%s", config.jellyfin_url)
            logger.debug("Loaded JELLYFIN_APIKEY=%s", config._mask_value(config.jellyfin_apikey))
            logger.debug("Loaded JELLYFIN_USER_ID=%s", config.jellyfin_user_id)

        # Metadata providers
        providers_env = os.environ.get("METADATA_PROVIDERS", "")
        if providers_env:
            config.metadata_providers = tuple(p.strip().lower() for p in providers_env.split(","))
            logger.debug("Loaded METADATA_PROVIDERS=%s", config.metadata_providers)
            for provider in config.metadata_providers:
                if provider not in ("tmdb", "tvdb"):
                    logger.warning(
                        f"Unsupported metadata provider: {provider}. Must be 'tmdb' or 'tvdb'"
                    )

        config.tmdb_apikey = os.environ.get("TMDB_APIKEY", "")
        config.tvdb_apikey = os.environ.get("TVDB_APIKEY", "")
        if config.tmdb_apikey:
            logger.debug("Loaded TMDB_APIKEY=%s", config._mask_value(config.tmdb_apikey))
        if config.tvdb_apikey:
            logger.debug("Loaded TVDB_APIKEY=%s", config._mask_value(config.tvdb_apikey))

        # Webhook
        config.webhook_url = os.environ.get("WEBHOOK_URL", "")
        logger.debug("Loaded WEBHOOK_URL=%s", config.webhook_url)

        config.webhook_mode = os.environ.get("WEBHOOK_MODE", "default")
        logger.debug("Loaded WEBHOOK_MODE=%s", config.webhook_mode)

        config.webhook_message_template = os.environ.get(
            "WEBHOOK_MESSAGE_TEMPLATE",
            "📺 {season_count} new season(s) completed this week!",
        )
        logger.debug(
            "Loaded WEBHOOK_MESSAGE_TEMPLATE=%s",
            config.webhook_message_template,
        )

        config.webhook_on_empty = os.environ.get("WEBHOOK_ON_EMPTY", "false").lower() == "true"
        logger.debug("Loaded WEBHOOK_ON_EMPTY=%s", config.webhook_on_empty)

        config.webhook_payload_template = os.environ.get("WEBHOOK_PAYLOAD_TEMPLATE", "default")
        logger.debug("Loaded WEBHOOK_PAYLOAD_TEMPLATE=%s", config.webhook_payload_template)

        # Signal CLI
        config.signal_number = os.environ.get("SIGNAL_NUMBER", "")
        logger.debug("Loaded SIGNAL_NUMBER=%s", config._mask_value(config.signal_number))

        config.signal_recipients = os.environ.get("SIGNAL_RECIPIENTS", "")
        logger.debug("Loaded SIGNAL_RECIPIENTS=%s", config._mask_value(config.signal_recipients))

        config.signal_text_mode = os.environ.get("SIGNAL_TEXT_MODE", "styled")
        logger.debug("Loaded SIGNAL_TEXT_MODE=%s", config.signal_text_mode)

        # Application
        config.lookback_days = cls._get_lookback_days()
        logger.debug("Loaded LOOKBACK_DAYS=%s", config.lookback_days)

        config.debug = os.environ.get("DEBUG", "false").lower() == "true"
        logger.debug("Loaded DEBUG=%s", config.debug)

        config.include_new_shows = os.environ.get("INCLUDE_NEW_SHOWS", "false").lower() == "true"
        logger.debug("Loaded INCLUDE_NEW_SHOWS=%s", config.include_new_shows)

        config.require_fully_aired = (
            os.environ.get("REQUIRE_FULLY_AIRED", "false").lower() == "true"
        )
        logger.debug("Loaded REQUIRE_FULLY_AIRED=%s", config.require_fully_aired)

        config.disable_ssl_verify = os.environ.get("DISABLE_SSL_VERIFY", "false").lower() == "true"
        logger.debug("Loaded DISABLE_SSL_VERIFY=%s", config.disable_ssl_verify)

        return config

    @staticmethod
    def _mask_value(value: str, prefix: int = 4) -> str:
        """Mask sensitive values for logging.

        Args:
            value: Value to mask
            prefix: Number of characters to show

        Returns:
            Masked value or empty string
        """
        if not value:
            return ""
        visible = value[:prefix]
        return f"{visible}***"

    @staticmethod
    def _get_lookback_days() -> int:
        """Get and validate LOOKBACK_DAYS from environment."""
        try:
            days = int(os.environ.get("LOOKBACK_DAYS", "7"))
            if days < 1 or days > 365:
                raise ValueError("LOOKBACK_DAYS must be between 1 and 365")
            logger.debug("Parsed LOOKBACK_DAYS=%s", days)
            return days
        except ValueError as e:
            logger.warning(f"Invalid LOOKBACK_DAYS: {e}. Using default of 7.")
            return 7

    def create_http_client(self) -> HTTPClient:
        """Create HTTP client for API requests."""
        return HTTPClient(verify_ssl=not self.disable_ssl_verify)

    def get_provider_config(self) -> dict[str, Any]:
        return {
            "webhook_url": self.webhook_url,
            "webhook_on_empty": self.webhook_on_empty,
            "message_template": self.webhook_message_template,
            "webhook_payload_template": self.webhook_payload_template,
            "payload_template": self.webhook_payload_template,
            "lookback_days": self.lookback_days,
            "signal_number": self.signal_number,
            "signal_recipients": self.signal_recipients,
            "signal_text_mode": self.signal_text_mode,
        }

    def create_media_source(self) -> MediaSource:
        """Create media source instance based on configuration."""
        from new_seasons_reminder.sources.jellyfin import JellyfinMediaSource
        from new_seasons_reminder.sources.tautulli import TautulliMediaSource

        if self.source_type == "tautulli":
            if not self.tautulli_url or not self.tautulli_apikey:
                raise ValueError("Tautulli URL and API key are required")
            return TautulliMediaSource(
                tautulli_url=self.tautulli_url,
                tautulli_apikey=self.tautulli_apikey,
                http_client=self.create_http_client(),
            )
        elif self.source_type == "jellyfin":
            if not self.jellyfin_url or not self.jellyfin_apikey or not self.jellyfin_user_id:
                raise ValueError("Jellyfin URL, API key, and user ID are required")
            return JellyfinMediaSource(
                jellyfin_url=self.jellyfin_url,
                jellyfin_apikey=self.jellyfin_apikey,
                user_id=self.jellyfin_user_id,
                http_client=self.create_http_client(),
            )
        else:
            raise ValueError(f"Unknown source type: {self.source_type}")

    def create_metadata_providers(self) -> list[ExternalMetadataProvider]:
        """Create metadata provider instances based on configuration.

        Returns:
            List of configured metadata providers
        """
        providers: list[ExternalMetadataProvider] = []

        for provider in self.metadata_providers:
            if provider == "tmdb":
                if not self.tmdb_apikey:
                    logger.warning("TMDB configured but no API key provided, skipping")
                    continue
                providers.append(
                    TMDBMetadataProvider(
                        tmdb_apikey=self.tmdb_apikey,
                        http_client=self.create_http_client(),
                    )
                )
            elif provider == "tvdb":
                if not self.tvdb_apikey:
                    logger.warning("TVDB configured but no API key provided, skipping")
                    continue
                providers.append(
                    TVDBMetadataProvider(
                        tvdb_apikey=self.tvdb_apikey,
                        http_client=self.create_http_client(),
                    )
                )

        logger.info(f"Created {len(providers)} metadata provider(s)")
        return providers

    def validate(self) -> None:
        """Validate configuration and raise errors for invalid settings."""
        if not self.tautulli_url and self.source_type == "tautulli":
            raise ValueError("Tautulli URL is required when SOURCE_TYPE=tautulli")

        if self.source_type == "jellyfin":
            if not self.jellyfin_url:
                raise ValueError("Jellyfin URL is required when SOURCE_TYPE=jellyfin")
            if not self.jellyfin_apikey:
                raise ValueError("Jellyfin API key is required when SOURCE_TYPE=jellyfin")
            if not self.jellyfin_user_id:
                raise ValueError("Jellyfin user ID is required when SOURCE_TYPE=jellyfin")

        if not self.webhook_url:
            raise ValueError("WEBHOOK_URL is required")

        # Validate metadata providers have API keys
        for provider in self.metadata_providers:
            if provider == "tmdb" and not self.tmdb_apikey:
                raise ValueError("TMDB_APIKEY is required when TMDB is in METADATA_PROVIDERS")
            if provider == "tvdb" and not self.tvdb_apikey:
                raise ValueError("TVDB_APIKEY is required when TVDB is in METADATA_PROVIDERS")

        logger.info("Configuration validation passed")


def setup_logging(debug: bool = False) -> logging.Logger:
    """Setup application logging with appropriate verbosity.

    Args:
        debug: If True, set logging level to DEBUG. Otherwise, use INFO (default).

    Returns:
        Configured logger instance.
    """
    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at {logging.getLevelName(level)} level")

    if debug:
        logger.debug("Debug mode enabled - verbose logging active")

    logger.debug(
        "Configured log levels: root=%s, %s=%s",
        logging.getLevelName(logging.getLogger().getEffectiveLevel()),
        __name__,
        logging.getLevelName(logger.getEffectiveLevel()),
    )

    return logger
