"""Tests for webhook provider classes."""

import base64
from unittest.mock import MagicMock, patch

import pytest

import new_seasons_reminder as nsr
from new_seasons_reminder.config import Config
from new_seasons_reminder.main import get_webhook_provider


class TestWebhookProvider:
    """Tests for the base WebhookProvider class."""

    def test_init(self, generic_config):
        """Test provider initialization."""
        provider = nsr.WebhookProvider(generic_config)
        assert provider.config == generic_config
        assert provider.logger is not None

    def test_validate_config_default(self, generic_config):
        """Test default validate_config returns True."""
        provider = nsr.WebhookProvider(generic_config)
        assert provider.validate_config() is True

    def test_should_send_on_empty_false(self, generic_config):
        """Test should_send_on_empty with default config."""
        provider = nsr.WebhookProvider(generic_config)
        assert provider.should_send_on_empty() is False

    def test_should_send_on_empty_true(self):
        """Test should_send_on_empty with explicit True."""
        config = {"webhook_on_empty": True}
        provider = nsr.WebhookProvider(config)
        assert provider.should_send_on_empty() is True

    def test_get_headers_default(self, generic_config):
        """Test default HTTP headers."""
        provider = nsr.WebhookProvider(generic_config)
        headers = provider.get_headers()
        assert headers["Content-Type"] == "application/json"
        assert "User-Agent" in headers

    def test_format_message_with_seasons(self, sample_seasons):
        """Test message formatting with seasons."""
        config = {
            "message_template": "Found {season_count} new seasons: {show_list}",
            "lookback_days": 7,
        }
        provider = nsr.WebhookProvider(config)
        message = provider.format_message(sample_seasons)

        assert "2" in message  # season_count
        assert "Breaking Bad S3" in message
        assert "The Office S2" in message

    def test_format_message_empty(self, generic_config):
        """Test message formatting with empty seasons."""
        provider = nsr.WebhookProvider(generic_config)
        message = provider.format_message([])

        assert "0" in message or "None" in message

    def test_format_message_custom_template(self, sample_seasons):
        """Test message formatting with custom template."""
        config = {
            "message_template": "Custom: {season_count} - {show_list}",
            "lookback_days": 7,
        }
        provider = nsr.WebhookProvider(config)
        message = provider.format_message(sample_seasons)

        assert message.startswith("Custom:")
        assert "2" in message
        assert "Breaking Bad S3, The Office S2" in message

    def test_build_payload_not_implemented(self, sample_seasons, generic_config):
        """Test that base provider raises NotImplementedError."""
        provider = nsr.WebhookProvider(generic_config)
        with pytest.raises(NotImplementedError):
            provider.build_payload(sample_seasons)


class TestSignalCliProvider:
    """Tests for the SignalCliProvider class."""

    def test_validate_config_success(self, signal_config):
        """Test validation with complete config."""
        provider = nsr.SignalCliProvider(signal_config)
        assert provider.validate_config() is True

    def test_validate_config_missing_number(self, signal_config):
        """Test validation fails without signal_number."""
        signal_config["signal_number"] = ""
        provider = nsr.SignalCliProvider(signal_config)
        assert provider.validate_config() is False

    def test_validate_config_missing_recipients(self, signal_config):
        """Test validation fails without signal_recipients."""
        signal_config["signal_recipients"] = ""
        provider = nsr.SignalCliProvider(signal_config)
        assert provider.validate_config() is False

    def test_parse_recipients_single(self, signal_config):
        """Test parsing single recipient."""
        signal_config["signal_recipients"] = "+1234567890"
        provider = nsr.SignalCliProvider(signal_config)
        recipients = provider._parse_recipients()
        assert recipients == ["+1234567890"]

    def test_parse_recipients_multiple(self, signal_config):
        """Test parsing multiple recipients."""
        provider = nsr.SignalCliProvider(signal_config)
        recipients = provider._parse_recipients()
        assert len(recipients) == 2
        assert "+0987654321" in recipients
        assert "+1122334455" in recipients

    def test_parse_recipients_empty(self, signal_config):
        """Test parsing empty recipients."""
        signal_config["signal_recipients"] = ""
        provider = nsr.SignalCliProvider(signal_config)
        recipients = provider._parse_recipients()
        assert recipients == []

    def test_parse_recipients_with_whitespace(self, signal_config):
        """Test parsing recipients with extra whitespace."""
        signal_config["signal_recipients"] = " +123 , +456 , +789 "
        provider = nsr.SignalCliProvider(signal_config)
        recipients = provider._parse_recipients()
        assert recipients == ["+123", "+456", "+789"]

    def test_build_payload_basic(self, sample_seasons, signal_config):
        """Test basic payload building without covers."""
        signal_config["signal_include_covers"] = False
        provider = nsr.SignalCliProvider(signal_config)
        payload = provider.build_payload(sample_seasons)

        assert payload["message"] is not None
        assert payload["number"] == "+1234567890"
        assert payload["recipients"] == ["+0987654321", "+1122334455"]
        assert payload["text_mode"] == "styled"
        assert "base64_attachments" not in payload

    def test_build_payload_empty_seasons(self, signal_config):
        """Test payload building with empty seasons."""
        provider = nsr.SignalCliProvider(signal_config)
        payload = provider.build_payload([])

        assert "message" in payload
        assert payload["number"] == "+1234567890"
        assert "base64_attachments" not in payload

    def test_should_send_on_empty_always_false(self, signal_config):
        """Test that Signal provider never sends on empty."""
        provider = nsr.SignalCliProvider(signal_config)
        assert provider.should_send_on_empty() is False

    def test_build_payload_with_covers_disabled(self, sample_seasons, signal_config):
        """Test that covers are not included when disabled."""
        signal_config["signal_include_covers"] = False
        provider = nsr.SignalCliProvider(signal_config)
        payload = provider.build_payload(sample_seasons)

        assert "base64_attachments" not in payload

    def test_build_payload_with_covers_enabled_no_urls(self, sample_seasons, signal_config):
        """Test cover handling when season has no cover URL."""
        signal_config["signal_include_covers"] = True
        provider = nsr.SignalCliProvider(signal_config)

        # Second season has no cover_url
        seasons_no_cover = [sample_seasons[1]]
        payload = provider.build_payload(seasons_no_cover)

        # Should not have attachments since no covers available
        assert "base64_attachments" not in payload

    @patch("new_seasons_reminder.providers.signal_cli.urlopen")
    def test_get_covers_as_base64_success(self, mock_urlopen, sample_seasons, signal_config):
        """Test successful base64 encoding of covers."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"fake_image_data"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        signal_config["signal_include_covers"] = True
        provider = nsr.SignalCliProvider(signal_config)

        # Only first season has cover_url
        seasons_with_cover = [sample_seasons[0]]
        payload = provider.build_payload(seasons_with_cover)

        assert "base64_attachments" in payload
        assert len(payload["base64_attachments"]) == 1
        # Verify it's valid base64
        decoded = base64.b64decode(payload["base64_attachments"][0])
        assert decoded == b"fake_image_data"

    @patch("new_seasons_reminder.api.urlopen")
    def test_get_covers_as_base64_download_failure(
        self, mock_urlopen, sample_seasons, signal_config
    ):
        """Test handling when cover download fails."""
        mock_urlopen.side_effect = Exception("Download failed")

        signal_config["signal_include_covers"] = True
        provider = nsr.SignalCliProvider(signal_config)

        seasons_with_cover = [sample_seasons[0]]
        payload = provider.build_payload(seasons_with_cover)

        # Should not include attachments if download fails
        assert "base64_attachments" not in payload

    @patch("new_seasons_reminder.providers.signal_cli.urlopen")
    def test_get_covers_as_base64_multiple(self, mock_urlopen, sample_seasons, signal_config):
        """Test encoding multiple covers."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"fake_image_data"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Add cover_url to second season
        sample_seasons[1]["cover_url"] = "http://example.com/cover2.jpg"

        signal_config["signal_include_covers"] = True
        provider = nsr.SignalCliProvider(signal_config)
        payload = provider.build_payload(sample_seasons)

        assert "base64_attachments" in payload
        assert len(payload["base64_attachments"]) == 2


class TestGenericProvider:
    """Tests for the GenericProvider class."""

    def test_build_payload_default_template(self, sample_seasons, generic_config):
        """Test building payload with default template."""
        provider = nsr.GenericProvider(generic_config)
        payload = provider.build_payload(sample_seasons)

        assert "timestamp" in payload
        assert payload["period_days"] == 7
        assert payload["season_count"] == 2
        assert "message" in payload
        assert len(payload["seasons"]) == 2
        assert payload["seasons"][0]["show"] == "Breaking Bad"

    def test_build_payload_empty_seasons(self, generic_config):
        """Test building payload with empty seasons."""
        provider = nsr.GenericProvider(generic_config)
        payload = provider.build_payload([])

        assert payload["season_count"] == 0
        assert payload["seasons"] == []
        assert "message" in payload

    def test_build_payload_custom_template(self, sample_seasons, custom_config):
        """Test building payload with custom template."""
        provider = nsr.GenericProvider(custom_config)
        payload = provider.build_payload(sample_seasons)

        assert "custom_msg" in payload
        assert payload["count"] == 2
        assert "shows" in payload
        assert "Breaking Bad S3, The Office S2" in str(payload["shows"])

    def test_build_payload_custom_with_all_variables(self, sample_seasons):
        """Test custom template with all available variables."""
        config = {
            "webhook_payload_template": (
                '{"msg": {message}, "count": {season_count}, '
                '"days": {period_days}, "time": {timestamp}, '
                '"list": {show_list}, "data": {seasons}}'
            ),
            "lookback_days": 7,
            "message_template": "Test: {season_count}",
        }
        provider = nsr.GenericProvider(config)
        payload = provider.build_payload(sample_seasons)

        assert "msg" in payload
        assert payload["count"] == 2
        assert payload["days"] == 7
        assert "time" in payload
        assert "list" in payload
        assert "data" in payload
        assert len(payload["data"]) == 2

    def test_build_payload_custom_json_escaping(self):
        """Test that JSON strings in templates are properly escaped."""
        config = {
            "payload_template": '{"message": {message}}',
            "message_template": 'Line1\nLine2 with "quotes"',
        }
        provider = nsr.GenericProvider(config)
        payload = provider.build_payload([])

        # Should be valid JSON with properly escaped newlines and quotes
        assert "message" in payload
        assert isinstance(payload["message"], str)

    def test_format_message_included_in_payload(self, sample_seasons, generic_config):
        """Test that format_message result is included in payload."""
        provider = nsr.GenericProvider(generic_config)
        payload = provider.build_payload(sample_seasons)

        expected_message = provider.format_message(sample_seasons)
        assert payload["message"] == expected_message

    def test_inherits_webhook_provider_methods(self, generic_config):
        """Test that GenericProvider inherits base class methods."""
        provider = nsr.GenericProvider(generic_config)

        # Should have access to base class methods
        assert hasattr(provider, "validate_config")
        assert hasattr(provider, "get_headers")
        assert hasattr(provider, "format_message")
        assert hasattr(provider, "should_send_on_empty")


class TestGetWebhookProvider:
    """Tests for the get_webhook_provider factory function."""

    def test_get_signal_cli_provider(self, signal_config):
        """Test factory returns SignalCliProvider."""
        config = Config(
            tautulli_url="http://localhost:8181",
            tautulli_apikey="test",
            webhook_url=signal_config["webhook_url"],
            webhook_mode="signal-cli",
            signal_number=signal_config["signal_number"],
            signal_recipients=signal_config["signal_recipients"],
            signal_text_mode=signal_config["signal_text_mode"],
            signal_include_covers=signal_config["signal_include_covers"],
            lookback_days=signal_config["lookback_days"],
        )
        provider = get_webhook_provider(config)
        assert isinstance(provider, nsr.SignalCliProvider)

    def test_get_generic_provider_default(self, generic_config):
        """Test factory returns GenericProvider for default mode."""
        config = Config(
            tautulli_url="http://localhost:8181",
            tautulli_apikey="test",
            webhook_url=generic_config["webhook_url"],
            webhook_mode="default",
            lookback_days=generic_config["lookback_days"],
        )
        provider = get_webhook_provider(config)
        assert isinstance(provider, nsr.GenericProvider)

    def test_get_generic_provider_custom(self, custom_config):
        """Test factory returns GenericProvider for custom mode."""
        config = Config(
            tautulli_url="http://localhost:8181",
            tautulli_apikey="test",
            webhook_url=custom_config["webhook_url"],
            webhook_mode="custom",
            webhook_on_empty=custom_config["webhook_on_empty"],
            webhook_message_template=custom_config["message_template"],
            webhook_payload_template=custom_config["webhook_payload_template"],
            lookback_days=custom_config["lookback_days"],
        )
        provider = get_webhook_provider(config)
        assert isinstance(provider, nsr.GenericProvider)

    def test_invalid_config_raises_error(self):
        """Test that invalid config raises ValueError."""
        config = Config(
            tautulli_url="http://localhost:8181",
            tautulli_apikey="test",
            webhook_url="http://test.com",
            webhook_mode="signal-cli",
            signal_number="",  # Missing required field
            signal_recipients="",
        )
        with pytest.raises(ValueError) as exc_info:
            get_webhook_provider(config)
        assert "Invalid configuration" in str(exc_info.value)

    def test_unknown_mode_raises_error(self, generic_config):
        """Test that unknown mode raises ValueError."""
        config = Config(
            tautulli_url="http://localhost:8181",
            tautulli_apikey="test",
            webhook_url=generic_config["webhook_url"],
            webhook_mode="unknown",
            lookback_days=generic_config["lookback_days"],
        )
        with pytest.raises(ValueError) as exc_info:
            get_webhook_provider(config)
        assert "Unsupported webhook_mode" in str(exc_info.value)
