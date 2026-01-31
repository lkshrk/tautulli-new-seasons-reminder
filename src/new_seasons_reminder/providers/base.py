"""Base webhook provider class."""

import logging
from datetime import datetime
from typing import Any


class WebhookProvider:
    """Base class for webhook providers. Extend this to add new webhook services."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def validate_config(self) -> bool:
        """Validate that required configuration is present."""
        return True

    def should_send_on_empty(self) -> bool:
        """Return True if webhook should be sent even when no seasons found."""
        return bool(self.config.get("webhook_on_empty", False))

    def build_payload(self, seasons: list[dict[str, Any]]) -> dict[str, Any]:
        """Build the webhook payload. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement build_payload()")

    def get_headers(self) -> dict[str, str]:
        """Get HTTP headers for the webhook request."""
        return {
            "Content-Type": "application/json",
            "User-Agent": "Tautulli-NewSeasons-Reminder/1.0",
        }

    def format_message(self, seasons: list[dict[str, Any]]) -> str:
        """Format message using template variables."""
        template = self.config.get(
            "message_template", "📺 {season_count} new season(s) completed this week!"
        )
        show_list = (
            ", ".join([f"{s['show']} S{s['season']}" for s in seasons]) if seasons else "None"
        )
        return str(
            template.format(
                season_count=len(seasons),
                period_days=self.config.get("lookback_days", 7),
                timestamp=datetime.now().isoformat(),
                show_list=show_list,
            )
        )
