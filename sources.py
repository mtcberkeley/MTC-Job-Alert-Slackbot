"""
Fetchers for each internship source.

Every fetcher takes a source config dict and returns a list of
*normalized* listing dicts with this shape:

    {
        "id": str,            # stable unique id, used for de-duping
        "role": str,
        "company": str,
        "location": str,
        "date_posted": int,   # unix timestamp, 0 if unknown
        "url": str,
        "source": str,        # human-readable source name
        "job_type": str,      # "internship" or "full_time" -> controls Slack routing
    }

Add a new source type by writing a `fetch_<type>` function and
registering it in FETCHERS at the bottom of this file.
"""

import hashlib
import logging

import requests

logger = logging.getLogger("internship_scout.sources")

REQUEST_TIMEOUT = 20
USER_AGENT = "mtc-job-alert-bot/1.0 (+https://github.com/)"


def _make_id(*parts: str) -> str:
    """Stable id from listing fields, used when a source has no native id."""
    raw = "|".join(p.strip().lower() for p in parts if p)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def fetch_github_json(source: dict) -> list[dict]:
    """
    Fetch listings.json-style feeds used by SimplifyJobs / Pitt CSC /
    forks of that repo format. Only 'active' + 'visible' entries are kept.
    """
    resp = requests.get(
        source["url"], timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}
    )
    resp.raise_for_status()
    raw_listings = resp.json()

    normalized = []
    for item in raw_listings:
        if item.get("active") is False:
            continue
        if item.get("is_visible") is False:
            continue

        company = (item.get("company_name") or "Unknown company").strip()
        role = (item.get("title") or "Unknown role").strip()
        locations = item.get("locations") or []
        location = ", ".join(locations) if locations else "Location not specified"
        url = (item.get("url") or "").strip()
        listing_id = item.get("id") or _make_id(company, role, url)
        date_posted = item.get("date_posted") or item.get("date_updated") or 0

        if not url:
            continue

        normalized.append(
            {
                "id": str(listing_id),
                "role": role,
                "company": company,
                "location": location,
                "date_posted": int(date_posted),
                "url": url,
                "source": source["name"],
                "job_type": source["job_type"],
            }
        )
    return normalized


def fetch_remoteok_json(source: dict) -> list[dict]:
    """
    RemoteOK's public jobs API. The first element is metadata, not a job,
    so it's skipped. The feed isn't internship-specific, so we split it by
    the source's configured job_type: "internship" keeps only postings with
    "intern" in the title, "full_time" keeps everything else.
    """
    resp = requests.get(
        source["url"], timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}
    )
    resp.raise_for_status()
    raw_listings = resp.json()

    want_interns = source["job_type"] == "internship"

    normalized = []
    for item in raw_listings:
        if not isinstance(item, dict) or "id" not in item or "position" not in item:
            continue  # skip the leading metadata object

        role = (item.get("position") or "").strip()
        is_intern_title = "intern" in role.lower()
        if is_intern_title != want_interns:
            continue

        company = (item.get("company") or "Unknown company").strip()
        location = (item.get("location") or "Remote").strip() or "Remote"
        url = (item.get("url") or "").strip()
        date_posted_raw = item.get("epoch") or item.get("date") or 0
        try:
            date_posted = int(date_posted_raw)
        except (TypeError, ValueError):
            date_posted = 0

        if not url:
            continue

        normalized.append(
            {
                "id": f"remoteok-{item['id']}",
                "role": role,
                "company": company,
                "location": location,
                "date_posted": date_posted,
                "url": url,
                "source": source["name"],
                "job_type": source["job_type"],
            }
        )
    return normalized


FETCHERS = {
    "github_json": fetch_github_json,
    "remoteok_json": fetch_remoteok_json,
}


def fetch_all(sources: list[dict]) -> list[dict]:
    """Fetch every configured source, logging and skipping any that fail."""
    all_listings = []
    for source in sources:
        fetcher = FETCHERS.get(source["type"])
        if not fetcher:
            logger.warning("No fetcher registered for type %r, skipping.", source["type"])
            continue
        try:
            listings = fetcher(source)
            logger.info("Fetched %d listings from %s", len(listings), source["name"])
            all_listings.extend(listings)
        except Exception as exc:  # noqa: BLE001 - keep the run alive on one bad source
            logger.error("Failed to fetch %s: %s", source["name"], exc)
    return all_listings
