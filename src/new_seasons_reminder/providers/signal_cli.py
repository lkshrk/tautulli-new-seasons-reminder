"""Signal CLI webhook provider."""

import base64
from datetime import datetime
from typing import Any
from urllib.request import urlopen

from .base import WebhookProvider


class SignalCliProvider(WebhookProvider):
    """Provider for signal-cli-rest-api webhook format."""

    def validate_config(self) -> bool:
        """Validate signal-cli configuration."""
        required = ["signal_number", "signal_recipients"]
        for key in required:
            if not self.config.get(key):
                self.logger.error(f"Missing required config: {key}")
                return False
        return True

    def should_send_on_empty(self) -> bool:
        """Never send Signal messages when there are no new seasons."""
        return False

    def _parse_recipients(self) -> list[str]:
        """Parse comma-separated recipient list."""
        recipients_str = self.config.get("signal_recipients", "")
        if not recipients_str:
            return []
        return [r.strip() for r in recipients_str.split(",") if r.strip()]

    def _get_covers_as_base64(self, seasons: list[dict[str, Any]]) -> list[str]:
        """Download and encode covers as base64."""
        base64_covers = []
        for season in seasons:
            cover_url = season.get("cover_url")
            if not cover_url:
                continue
            try:
                with urlopen(cover_url, timeout=30) as response:
                    image_data = response.read()
                    base64_covers.append(base64.b64encode(image_data).decode("utf-8"))
            except Exception as e:
                self.logger.warning(f"Failed to download cover for {season['show']}: {e}")
        return base64_covers

    def format_message(self, seasons: list[dict[str, Any]]) -> str:
        """Format message with Signal text styling (bold, italic)."""
        count = len(seasons)
        period = self.config.get("lookback_days", 7)

        season_plural = "s" if count > 1 else ""
        lines = [
            f"📺 *{count} new season{season_plural}* completed in the last {period} days!",
            "",
        ]

        for season in seasons:
            show_name = season["show"]
            season_num = season["season"]
            ep_count = season.get("episode_count", 0)
            lines.append(f"• *{show_name}* - Season {season_num} ({ep_count} episodes)")

        lines.append("")
        lines.append(f"_{datetime.now().strftime('%Y-%m-%d %H:%M')}_")

        return "\n".join(lines)

    def build_payload(self, seasons: list[dict[str, Any]]) -> dict[str, Any]:
        """Build signal-cli-rest-api payload."""
        message = self.format_message(seasons)
        recipients = self._parse_recipients()

        payload = {
            "message": message,
            "number": self.config["signal_number"],
            "recipients": recipients,
            "text_mode": self.config.get("signal_text_mode", "styled"),
        }

        if self.config.get("signal_include_covers", False) and seasons:
            base64_covers = self._get_covers_as_base64(seasons)
            if base64_covers:
                payload["base64_attachments"] = base64_covers

        return payload
