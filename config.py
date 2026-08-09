"""
Configuration for the MTC Job Alert bot.

Everything here is either a plain constant (safe to edit directly) or
pulled from environment variables (so secrets never live in the code).
"""

import os

# --- Slack settings -------------------------------------------------------

# Bot token (starts with xoxb-...). Create a Slack app, add the
# `chat:write` bot scope, install it to your workspace, and invite the
# bot to both target channels with `/invite @YourBotName`.
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

# Two separate channels: internships go to one, full-time new-grad tech
# jobs go to the other. Use channel IDs (most reliable for CI/cron use).
SLACK_INTERNSHIP_CHANNEL = os.environ.get("SLACK_INTERNSHIP_CHANNEL", "C05NY1QR325")
SLACK_FULLTIME_CHANNEL = os.environ.get("SLACK_FULLTIME_CHANNEL", "C0BLES1S753")

# --- Filtering --------------------------------------------------------------

# Only alert on listings posted within this many days, so a first-ever
# run doesn't dump hundreds of old postings into the channel.
MAX_LISTING_AGE_DAYS = int(os.environ.get("MAX_LISTING_AGE_DAYS", "14"))

# Optional keyword filters. Leave empty to allow everything.
# Example: ["software", "swe", "backend", "data", "ml"]
ROLE_INCLUDE_KEYWORDS = [
    k.strip().lower()
    for k in os.environ.get("ROLE_INCLUDE_KEYWORDS", "").split(",")
    if k.strip()
]
# Example: ["mba", "phd"]
ROLE_EXCLUDE_KEYWORDS = [
    k.strip().lower()
    for k in os.environ.get("ROLE_EXCLUDE_KEYWORDS", "").split(",")
    if k.strip()
]

# --- Defense-industry blocklist --------------------------------------------
#
# Listings whose company name matches (case-insensitive, substring) any of
# these are dropped entirely — never posted to either channel. Add more
# names/aliases as a comma-separated env var to extend without editing code;
# the env var is *added to*, not a replacement for, the defaults below.
#
# Note: some entries (e.g. "Boeing", "Leonardo", "Rocket Lab") are dual-use
# or have ambiguous/generic names. Matching is intentionally broad per an
# explicit request to exclude these companies, which means it may also catch
# a non-defense listing that happens to share the name (e.g. a commercial
# Boeing internship, or an unrelated company literally named "Leonardo").
# Tighten individual entries in the list below if that turns out to be noisy.
DEFENSE_COMPANY_BLOCKLIST = [
    "raytheon",
    "rtx",
    "lockheed martin",
    "northrop grumman",
    "boeing",
    "general dynamics",
    "l3harris",
    "l3 harris",
    "bae systems",
    "leonardo",
    "thales",
    "anduril",
    "palantir",
    "shield ai",
    "saronic",
    "skydio",
    "epirus",
    "firestorm labs",
    "helsing",
    "rebellion defense",
    "govini",
    "rocket lab",
    "apex space",
] + [
    k.strip().lower()
    for k in os.environ.get("DEFENSE_COMPANY_BLOCKLIST_EXTRA", "").split(",")
    if k.strip()
]

# --- Storage ------------------------------------------------------------

# Where "already posted" listing IDs are tracked between runs.
SEEN_STORE_PATH = os.environ.get("SEEN_STORE_PATH", "seen_listings.json")

# --- Sources --------------------------------------------------------------
# Each source is fetched and normalized independently in sources.py.
# Add / remove / comment out entries here to change what gets scouted.
#
# "job_type" controls routing: "internship" -> SLACK_INTERNSHIP_CHANNEL,
# "full_time" -> SLACK_FULLTIME_CHANNEL.

SOURCES = [
    # --- Internship sources ---
    {
        "name": "SimplifyJobs Summer2026-Internships",
        "type": "github_json",
        "job_type": "internship",
        "url": "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json",
    },
    {
        "name": "SimplifyJobs Summer2027-Internships",
        "type": "github_json",
        "job_type": "internship",
        "url": "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/.github/scripts/listings.json",
    },
    {
        "name": "Vansh Off-Season Tech Internships",
        "type": "github_json",
        "job_type": "internship",
        "url": "https://raw.githubusercontent.com/vanshb03/Summer2026-Internships/dev/.github/scripts/listings.json",
    },
    {
        # RemoteOK's public API, filtered client-side for "intern" in the title.
        "name": "RemoteOK (internships)",
        "type": "remoteok_json",
        "job_type": "internship",
        "url": "https://remoteok.com/api",
    },
    # --- Full-time / new-grad sources ---
    {
        "name": "SimplifyJobs New-Grad-Positions",
        "type": "github_json",
        "job_type": "full_time",
        "url": "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json",
    },
    {
        # Same RemoteOK feed, this time excluding anything with "intern" in the title.
        "name": "RemoteOK (full-time)",
        "type": "remoteok_json",
        "job_type": "full_time",
        "url": "https://remoteok.com/api",
    },
]
