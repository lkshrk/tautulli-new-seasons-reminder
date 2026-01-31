"""Generic webhook provider class."""

import json
from datetime import datetime
from typing import Any

from .base import WebhookProvider


class GenericProvider(WebhookProvider):
    """Generic webhook provider supporting default and custom templates."""

    def build_payload(self, seasons: list[dict[str, Any]]) -> dict[str, Any]:
        """Build the webhook payload.

        Supports both default template and custom template via WEBHOOK_PAYLOAD_TEMPLATE.
        """
        message = self.format_message(seasons)

        payload_template = self.config.get("webhook_payload_template")

        if payload_template:
            # Custom template with variable substitution
            show_list = (
                ", ".join([f"{s['show']} S{s['season']}" for s in seasons]) if seasons else "None"
            )

            # Replace template variables
            template_str = payload_template
            template_str = template_str.replace(
                "{timestamp}", json.dumps(datetime.now().isoformat())
            )
            template_str = template_str.replace(
                "{period_days}", json.dumps(self.config.get("lookback_days", 7))
            )
            template_str = template_str.replace("{season_count}", json.dumps(len(seasons)))
            template_str = template_str.replace("{message}", json.dumps(message))
            template_str = template_str.replace("{show_list}", json.dumps(show_list))
            template_str = template_str.replace("{seasons}", json.dumps(seasons))

            try:
                return dict(json.loads(template_str))
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse custom payload template: {e}")
                # Fall back to default template

        # Default template
        return {
            "timestamp": datetime.now().isoformat(),
            "period_days": self.config.get("lookback_days", 7),
            "season_count": len(seasons),
            "seasons": seasons,
            "message": message,
        }
