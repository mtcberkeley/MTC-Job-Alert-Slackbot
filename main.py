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
    """One full check-and-post cycle. Returns number of alerts posted."""
    if not config.SLACK_BOT_TOKEN:
        logger.error(
            "SLACK_BOT_TOKEN is not set. Export it or add it as a repo/CI secret."
        )
        sys.exit(1)

    started_at = datetime.now(timezone.utc).isoformat()
    logger.info("MTC Job Alert run starting at %s", started_at)

    seen_ids = dedupe.load_seen(config.SEEN_STORE_PATH)
    logger.info("Loaded %d previously-seen listing ids", len(seen_ids))

    all_listings = sources.fetch_all(config.SOURCES)
    logger.info("Fetched %d total listings across all sources", len(all_listings))

    new_listings = dedupe.filter_new(all_listings, seen_ids)
    new_listings = [item for item in new_listings if passes_filters(item)]
    # Oldest first, so the channel reads in a sensible chronological order.
    new_listings.sort(key=lambda item: item["date_posted"])

    logger.info("%d new listings pass filters and will be posted", len(new_listings))

    internship_listings = [l for l in new_listings if l["job_type"] == "internship"]
    fulltime_listings = [l for l in new_listings if l["job_type"] == "full_time"]

    posted_count = 0
    if internship_listings:
        posted = slack_notifier.post_all(
            config.SLACK_BOT_TOKEN, config.SLACK_INTERNSHIP_CHANNEL, internship_listings
        )
        logger.info(
            "Posted %d/%d new internships to the internship channel",
            posted,
            len(internship_listings),
        )
        posted_count += posted

    if fulltime_listings:
        posted = slack_notifier.post_all(
            config.SLACK_BOT_TOKEN, config.SLACK_FULLTIME_CHANNEL, fulltime_listings
        )
        logger.info(
            "Posted %d/%d new full-time jobs to the full-time channel",
            posted,
            len(fulltime_listings),
        )
        posted_count += posted

    if not new_listings:
        logger.info("Nothing new this run.")

    # Mark everything we fetched (not just the ones posted) as seen, so a
    # listing that fails a keyword/age filter today doesn't get reconsidered
    # forever — only genuinely new ids show up in future diffs.
    seen_ids.update(item["id"] for item in all_listings)
    dedupe.save_seen(config.SEEN_STORE_PATH, seen_ids)

    return posted_count


if __name__ == "__main__":
    run_once()
