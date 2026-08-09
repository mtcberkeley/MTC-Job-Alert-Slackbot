"""
MTC Job Alert — entry point.

Run this on a schedule (hourly via cron / GitHub Actions / a simple
sleep-loop) to check configured sources for new tech internships and
post concise alerts to a Slack channel.

    python main.py

Required environment variable: SLACK_BOT_TOKEN
See README.md for full setup instructions.
"""

import logging
import sys
import time
from datetime import datetime, timezone

import config
import dedupe
import slack_notifier
import sources

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("internship_scout.main")


def is_defense_company(listing: dict) -> bool:
    company_lower = listing["company"].lower()
    return any(name in company_lower for name in config.DEFENSE_COMPANY_BLOCKLIST)


def passes_filters(listing: dict) -> bool:
    if is_defense_company(listing):
        return False

    role_lower = listing["role"].lower()

    if config.ROLE_INCLUDE_KEYWORDS and not any(
        kw in role_lower for kw in config.ROLE_INCLUDE_KEYWORDS
    ):
        return False

    if config.ROLE_EXCLUDE_KEYWORDS and any(
        kw in role_lower for kw in config.ROLE_EXCLUDE_KEYWORDS
    ):
        return False

    if listing["date_posted"]:
        age_days = (time.time() - listing["date_posted"]) / 86400
        if age_days > config.MAX_LISTING_AGE_DAYS:
            return False

    return True


def run_once() -> int:
    """One full check-and-post cycle. Returns number of alerts posted (or
    would-post count, in dry-run mode)."""
    if not config.SLACK_BOT_TOKEN and not config.DRY_RUN:
        logger.error(
            "SLACK_BOT_TOKEN is not set. Export it, add it as a repo/CI secret, "
            "or set DRY_RUN=true to test without a token."
        )
        sys.exit(1)

    started_at = datetime.now(timezone.utc).isoformat()
    mode = " [DRY RUN]" if config.DRY_RUN else ""
    logger.info("MTC Job Alert run starting at %s%s", started_at, mode)

    seen_ids = dedupe.load_seen(config.SEEN_STORE_PATH)
    logger.info("Loaded %d previously-seen listing ids", len(seen_ids))

    all_listings = sources.fetch_all(config.SOURCES)
    logger.info("Fetched %d total listings across all sources", len(all_listings))

    new_listings = dedupe.filter_new(all_listings, seen_ids)
    new_listings = [item for item in new_listings if passes_filters(item)]
    # Oldest first, so the channel reads in a sensible chronological order.
    new_listings.sort(key=lambda item: item["date_posted"])

    logger.info("%d new listings pass filters and will be posted", len(new_listings))

    if config.DRY_RUN:
        logger.info(
            "DRY RUN — not posting to Slack, not saving seen-ids state. "
            "Listing details below."
        )
        for item in new_listings:
            logger.info(
                "  [%s] %s @ %s | %s | %s",
                item["job_type"].upper(),
                item["role"],
                item["company"],
                item["location"],
                item["url"],
            )
        return len(new_listings)

    posted_count = 0
    if new_listings:
        posted_count = slack_notifier.post_all(
            config.SLACK_BOT_TOKEN, config.SLACK_CHANNEL, new_listings
        )
        logger.info("Posted %d/%d new listings to Slack", posted_count, len(new_listings))
    else:
        logger.info("Nothing new this run.")

    # Mark everything we fetched (not just the ones posted) as seen, so a
    # listing that fails a keyword/age filter today doesn't get reconsidered
    # forever — only genuinely new ids show up in future diffs.
    seen_ids.update(item["id"] for item in all_listings)
    dedupe.save_seen(config.SEEN_STORE_PATH, seen_ids)

    return posted_count


if __name__ == "__main__":
    run_once()