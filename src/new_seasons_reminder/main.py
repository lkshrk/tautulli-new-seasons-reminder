"""Main entry point for the new_seasons_reminder application."""

import json
import logging
import sys
from functools import partial
from typing import Any

from .api import (
    get_children_metadata,
    get_metadata,
    get_recently_added,
    get_show_cover,
)
from .config import Config, setup_logging
from .logic import get_new_finished_seasons, is_new_show, is_season_finished
from .providers import GenericProvider, SignalCliProvider, WebhookProvider


def get_webhook_provider(config: Config) -> WebhookProvider:
    """Get the appropriate webhook provider based on configuration.

    Args:
        config: Application configuration.

    Returns:
        Configured webhook provider instance.

    Raises:
        ValueError: If configuration is invalid or mode is unsupported.
    """
    provider_config = config.get_provider_config()
    mode = config.webhook_mode.lower()

    provider: WebhookProvider
    if mode == "signal-cli":
        provider = SignalCliProvider(provider_config)
    elif mode == "default" or mode == "custom":
        provider = GenericProvider(provider_config)
    else:
        raise ValueError(f"Unsupported webhook_mode: {config.webhook_mode}")

    if not provider.validate_config():
        raise ValueError(f"Invalid configuration for {mode} provider")

    return provider


def send_webhook(seasons: list[dict[str, Any]], provider: WebhookProvider, config: Config) -> bool:
    """Send webhook notification with new seasons data.

    Args:
        seasons: List of new finished seasons.
        provider: Configured webhook provider.
        config: Application configuration.

    Returns:
        True if webhook was sent successfully, False otherwise.
    """
    if not seasons and not provider.should_send_on_empty():
        logging.info("No new seasons found, skipping webhook")
        return True

    if not config.webhook_url:
        logging.warning("WEBHOOK_URL not set, skipping webhook send")
        return False

    try:
        payload = provider.build_payload(seasons)
        headers = provider.get_headers()

        import urllib.request

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            config.webhook_url, data=data, headers=headers, method="POST"
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status in (200, 201, 202, 204):
                logging.info(f"Webhook sent successfully to {config.webhook_url}")
                return True
            else:
                logging.warning(f"Webhook returned status {response.status}")
                return False

    except Exception as e:
        logging.error(f"Failed to send webhook: {e}")
        return False


def main() -> int:
    """Main entry point for the application.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    try:
        config = Config.from_env()
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        return 1

    logger = setup_logging(config.debug)

    if not config.tautulli_url or not config.tautulli_apikey:
        logger.error("TAUTULLI_URL and TAUTULLI_APIKEY must be set")
        return 1

    try:
        provider = get_webhook_provider(config)
    except ValueError as e:
        logger.error(f"Invalid webhook configuration: {e}")
        return 1

    try:
        get_recently_added_func = partial(
            get_recently_added,
            tautulli_url=config.tautulli_url,
            tautulli_apikey=config.tautulli_apikey,
        )

        get_metadata_func = partial(
            get_metadata,
            tautulli_url=config.tautulli_url,
            tautulli_apikey=config.tautulli_apikey,
        )

        get_children_func = partial(
            get_children_metadata,
            tautulli_url=config.tautulli_url,
            tautulli_apikey=config.tautulli_apikey,
        )

        get_show_cover_func = partial(
            get_show_cover,
            plex_url=config.plex_url,
            plex_token=config.plex_token,
            tautulli_url=config.tautulli_url,
            tautulli_apikey=config.tautulli_apikey,
        )

        is_new_show_func = partial(is_new_show, get_metadata_func=get_metadata_func)

        is_season_finished_func = partial(is_season_finished, get_children_func=get_children_func)

        seasons = get_new_finished_seasons(
            lookback_days=config.lookback_days,
            get_recently_added_func=get_recently_added_func,
            is_new_show_func=is_new_show_func,
            is_season_finished_func=is_season_finished_func,
            get_show_cover_func=get_show_cover_func,
            get_children_func=get_children_func,
        )

        logger.info(f"Found {len(seasons)} new finished season(s)")
        for season in seasons:
            logger.info(
                f"  - {season['show']} Season {season['season']} "
                f"({season['episode_count']} episodes)"
            )

        if config.webhook_url:
            success = send_webhook(seasons, provider, config)
            if not success:
                logger.error("Failed to send webhook notification")
                return 1
        else:
            logger.warning("WEBHOOK_URL not set, skipping webhook send (useful for testing)")
            if seasons:
                print(json.dumps(seasons, indent=2))

        return 0

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if config.debug:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
