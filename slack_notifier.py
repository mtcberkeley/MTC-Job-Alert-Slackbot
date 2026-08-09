"""
Posts concise, formatted internship alerts to a Slack channel using the
chat.postMessage Bot API (requires a bot token with the chat:write scope
and the bot invited to the target channel).
"""

import logging
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger("internship_scout.slack")

SLACK_API_URL = "https://slack.com/api/chat.postMessage"


def _format_date(epoch: int) -> str:
    if not epoch:
        return "Date not listed"
    try:
        return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%b %d, %Y")
    except (OSError, OverflowError, ValueError):
        return "Date not listed"


JOB_TYPE_LABELS = {
    "internship": ("Internship", ":student:"),
    "full_time": ("Full-Time", ":briefcase:"),
}


def build_message(listing: dict) -> dict:
    """Build a Slack Block Kit payload (blocks) for one listing."""
    date_str = _format_date(listing["date_posted"])
    label, emoji = JOB_TYPE_LABELS.get(listing.get("job_type"), ("Job", ":briefcase:"))

    text_fallback = (
        f"[{label}] {listing['role']} @ {listing['company']} ({listing['location']}) "
        f"— posted {date_str} — {listing['url']}"
    )
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"{emoji} *{label}*\n"
                    f"*{listing['role']}* @ *{listing['company']}*\n"
                    f":round_pushpin: {listing['location']}   "
                    f":calendar: Posted {date_str}\n"
                    f"<{listing['url']}|Apply here>"
                ),
            },
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"Source: {listing['source']}"}],
        },
    ]
    return {"text": text_fallback, "blocks": blocks}


def post_listing(token: str, channel: str, listing: dict) -> bool:
    """Post a single listing. Returns True on success."""
    payload = build_message(listing)
    payload["channel"] = channel

    resp = requests.post(
        SLACK_API_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json=payload,
        timeout=15,
    )
    data = resp.json()

    if not data.get("ok"):
        logger.error(
            "Slack post failed for %s @ %s: %s",
            listing["role"],
            listing["company"],
            data.get("error"),
        )
        return False
    return True


def post_all(token: str, channel: str, listings: list[dict], delay_seconds: float = 1.1) -> int:
    """
    Post each listing as its own message (most readable in Slack), respecting
    a small delay to stay comfortably under Slack's rate limits.
    Returns the count of successfully posted messages.
    """
    posted = 0
    for listing in listings:
        if post_listing(token, channel, listing):
            posted += 1
        time.sleep(delay_seconds)
    return posted