"""Configuration management for new_seasons_reminder."""

import logging
import os
from dataclasses import dataclass
from typing import Any


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    # Tautulli settings
    tautulli_url: str = ""
    tautulli_apikey: str = ""

    # Plex settings (for cover images)
    plex_url: str = ""
    plex_token: str = ""

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
    signal_include_covers: bool = False

    # Application settings
    lookback_days: int = 7
    debug: bool = False

    @classmethod
    def from_env(cls) -> Config:
        """Create configuration from environment variables."""
        config = cls()

        # Tautulli
        config.tautulli_url = os.environ.get("TAUTULLI_URL", "")
        config.tautulli_apikey = os.environ.get("TAUTULLI_APIKEY", "")

        # Plex
        config.plex_url = os.environ.get("PLEX_URL", "")
        config.plex_token = os.environ.get("PLEX_TOKEN", "")

        # Webhook
        config.webhook_url = os.environ.get("WEBHOOK_URL", "")
        config.webhook_mode = os.environ.get("WEBHOOK_MODE", "default")
        config.webhook_message_template = os.environ.get(
            "WEBHOOK_MESSAGE_TEMPLATE", "📺 {season_count} new season(s) completed this week!"
        )
        config.webhook_on_empty = os.environ.get("WEBHOOK_ON_EMPTY", "false").lower() == "true"
        config.webhook_payload_template = os.environ.get("WEBHOOK_PAYLOAD_TEMPLATE", "default")

        # Signal CLI
        config.signal_number = os.environ.get("SIGNAL_NUMBER", "")
        config.signal_recipients = os.environ.get("SIGNAL_RECIPIENTS", "")
        config.signal_text_mode = os.environ.get("SIGNAL_TEXT_MODE", "styled")
        config.signal_include_covers = (
            os.environ.get("SIGNAL_INCLUDE_COVERS", "false").lower() == "true"
        )

        # Application settings
        config.lookback_days = cls._get_lookback_days()
        config.debug = os.environ.get("DEBUG", "false").lower() == "true"

        return config

    @staticmethod
    def _get_lookback_days() -> int:
        """Get and validate LOOKBACK_DAYS from environment."""
        try:
            days = int(os.environ.get("LOOKBACK_DAYS", "7"))
            if days < 1 or days > 365:
                raise ValueError("LOOKBACK_DAYS must be between 1 and 365")
            return days
        except ValueError as e:
            logging.warning(f"Invalid LOOKBACK_DAYS: {e}. Using default of 7.")
            return 7

    def get_provider_config(self) -> dict[str, Any]:
        """Get configuration dictionary for webhook providers."""
        return {
            "webhook_url": self.webhook_url,
            "webhook_on_empty": self.webhook_on_empty,
            "message_template": self.webhook_message_template,
            "payload_template": self.webhook_payload_template,
            "lookback_days": self.lookback_days,
            "signal_number": self.signal_number,
            "signal_recipients": self.signal_recipients,
            "signal_text_mode": self.signal_text_mode,
            "signal_include_covers": self.signal_include_covers,
        }


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

    # Log the startup with appropriate level
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at {logging.getLevelName(level)} level")
    if debug:
        logger.debug("Debug mode enabled - verbose logging active")

    return logger
