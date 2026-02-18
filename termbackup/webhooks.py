"""Post-backup webhook notifications."""

import httpx

from termbackup import ui


def send_notification(
    webhook_url: str,
    event: str,
    profile: str,
    details: dict | None = None,
) -> None:
    """Sends a webhook notification. Auto-detects format by URL.

    Args:
        webhook_url: The webhook endpoint URL.
        event: Event type (e.g., 'backup_complete').
        profile: Profile name.
        details: Optional extra data.
    """
    try:
        payload = _build_payload(webhook_url, event, profile, details)
        response = httpx.post(webhook_url, json=payload, timeout=10.0)
        if response.status_code >= 400:
            ui.warning(f"Webhook returned HTTP {response.status_code}")
    except Exception as e:
        ui.warning(f"Webhook notification failed: {e}")


def _build_payload(
    url: str,
    event: str,
    profile: str,
    details: dict | None,
) -> dict:
    """Builds the webhook payload based on URL pattern."""
    base = {
        "event": event,
        "profile": profile,
        **(details or {}),
    }

    if "hooks.slack.com" in url:
        # Slack blocks format
        text_parts = [f"*{event.replace('_', ' ').title()}*", f"Profile: `{profile}`"]
        if details:
            for k, v in details.items():
                text_parts.append(f"{k}: `{v}`")
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "\n".join(text_parts)},
                }
            ]
        }

    if "discord.com/api/webhooks" in url:
        # Discord embeds format
        fields = []
        if details:
            for k, v in details.items():
                fields.append({"name": k, "value": str(v), "inline": True})
        return {
            "embeds": [
                {
                    "title": event.replace("_", " ").title(),
                    "description": f"Profile: {profile}",
                    "fields": fields,
                    "color": 65280,  # Green
                }
            ]
        }

    # Generic JSON POST
    return base
