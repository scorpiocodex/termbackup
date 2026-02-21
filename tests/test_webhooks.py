"""Tests for the webhook notifications module."""

from unittest.mock import MagicMock, patch

from termbackup import webhooks


class TestBuildPayload:
    def test_generic_payload(self):
        payload = webhooks._build_payload(
            "https://example.com/webhook",
            "backup_complete",
            "my-profile",
            {"files": 42},
        )
        assert payload["event"] == "backup_complete"
        assert payload["profile"] == "my-profile"
        assert payload["files"] == 42

    def test_slack_payload(self):
        payload = webhooks._build_payload(
            "https://hooks.slack.com/services/T00/B00/xxx",
            "backup_complete",
            "my-profile",
            {"files": 42},
        )
        assert "blocks" in payload
        assert payload["blocks"][0]["type"] == "section"
        text = payload["blocks"][0]["text"]["text"]
        assert "Backup Complete" in text
        assert "my-profile" in text

    def test_discord_payload(self):
        payload = webhooks._build_payload(
            "https://discord.com/api/webhooks/123/abc",
            "backup_complete",
            "my-profile",
            {"files": 42},
        )
        assert "embeds" in payload
        embed = payload["embeds"][0]
        assert "Backup Complete" in embed["title"]
        assert "my-profile" in embed["description"]
        assert embed["color"] == 65280

    def test_no_details(self):
        payload = webhooks._build_payload(
            "https://example.com/hook",
            "backup_complete",
            "prof",
            None,
        )
        assert payload["event"] == "backup_complete"
        assert payload["profile"] == "prof"


class TestSendNotification:
    @patch("termbackup.webhooks.httpx.post")
    def test_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        webhooks.send_notification(
            "https://example.com/hook",
            "backup_complete",
            "prof",
            {"size": 1024},
        )

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://example.com/hook"
        assert call_args[1]["json"]["event"] == "backup_complete"

    @patch("termbackup.webhooks.httpx.post")
    def test_http_error_warns(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        # Should not raise
        webhooks.send_notification("https://example.com/hook", "backup_complete", "prof")

    @patch("termbackup.webhooks.httpx.post", side_effect=Exception("Network error"))
    def test_network_error_warns(self, mock_post):
        # Should not raise
        webhooks.send_notification("https://example.com/hook", "backup_complete", "prof")
