"""
Tracks which listing IDs have already been posted, so re-running the
scout every hour doesn't repost the same internship.

State is a flat JSON file: {"seen_ids": [...], "last_run": "<iso ts>"}
Kept deliberately simple so it can be committed back to a git repo by
the GitHub Actions workflow (see .github/workflows/hourly.yml) and give
the bot persistent memory without a database.
"""

import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger("internship_scout.dedupe")


def load_seen(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("seen_ids", []))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read %s (%s); starting with empty state.", path, exc)
        return set()


def save_seen(path: str, seen_ids: set[str], max_keep: int = 5000) -> None:
    """
    Persist seen IDs. Caps the stored set so the file doesn't grow forever;
    oldest entries (by insertion order isn't tracked, so this is a simple
    size cap, not strict LRU) are trimmed once the cap is exceeded.
    """
    ids_list = list(seen_ids)
    if len(ids_list) > max_keep:
        ids_list = ids_list[-max_keep:]

    payload = {
        "seen_ids": ids_list,
        "last_run": datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def filter_new(listings: list[dict], seen_ids: set[str]) -> list[dict]:
    """Return only listings whose id hasn't been seen before."""
    return [item for item in listings if item["id"] not in seen_ids]
