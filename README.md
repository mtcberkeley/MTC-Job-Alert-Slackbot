# MTC Job Alert — Slack Bot

Checks a set of tech-internship and full-time new-grad sources every
hour, skips anything it's already posted, filters out defense-industry
employers, and drops a concise alert into the right Slack channel with
**role, company, location, posting date, and a direct apply link**.

- **Internships** 
- **Full-time / new-grad tech roles** 

(Both are set in `config.py` as `SLACK_INTERNSHIP_CHANNEL` /
`SLACK_FULLTIME_CHANNEL`, overridable via env vars.)

Default sources (edit in `config.py`):
- Internships: [SimplifyJobs Summer2026-Internships](https://github.com/SimplifyJobs/Summer2026-Internships), [SimplifyJobs Summer2027-Internships](https://github.com/SimplifyJobs/Summer2027-Internships), [vanshb03 Summer2026-Internships](https://github.com/vanshb03/Summer2026-Internships) (off-season list), [RemoteOK](https://remoteok.com/) filtered to "intern" titles
- Full-time: [SimplifyJobs New-Grad-Positions](https://github.com/SimplifyJobs/New-Grad-Positions), RemoteOK filtered to non-"intern" titles

These are actively-maintained, scrape-friendly public lists rather than
scraping LinkedIn/Indeed directly, which is more reliable and avoids ToS
issues. You can add more sources — see "Adding a source" below.

## Defense-industry exclusion

Any listing whose company name matches the blocklist in `config.py`
(`DEFENSE_COMPANY_BLOCKLIST`) is dropped entirely — never posted to
either channel. Currently blocked: Raytheon/RTX, Lockheed Martin,
Northrop Grumman, Boeing, General Dynamics, L3Harris, BAE Systems,
Leonardo, Thales, Anduril, Palantir, Shield AI, Saronic, Skydio, Epirus,
Firestorm Labs, Helsing, Rebellion Defense, Govini, Rocket Lab, and Apex
Space.

Matching is a case-insensitive substring check on the company name, so
it's intentionally broad. A couple of names are generic or dual-use
(e.g. "Boeing" also does commercial aviation, "Leonardo" is a common
name, "Rocket Lab"/"Apex Space" do civil space work too) — that's a
deliberate trade-off toward not letting anything defense-related slip
through, at the cost of occasionally also filtering an unrelated listing
that happens to share the name. To extend the list without touching
code, set `DEFENSE_COMPANY_BLOCKLIST_EXTRA` as a comma-separated env var
(e.g. `"kratos,leidos"`) — it adds to, rather than replaces, the
defaults.

## Configuration

All tunable settings live in `config.py` / environment variables:

| Setting | Purpose | Default |
|---|---|---|
| `SLACK_BOT_TOKEN` | Bot token (required) | — |
| `SLACK_INTERNSHIP_CHANNEL` | Internship channel ID | `C05NY1QR325` |
| `SLACK_FULLTIME_CHANNEL` | Full-time job channel ID | `C0BLES1S753` |
| `MAX_LISTING_AGE_DAYS` | Ignore listings older than this | `14` |
| `ROLE_INCLUDE_KEYWORDS` | Comma-separated; only post if role title matches one | *(none — allow all)* |
| `ROLE_EXCLUDE_KEYWORDS` | Comma-separated; skip if role title matches one | *(none)* |
| `DEFENSE_COMPANY_BLOCKLIST_EXTRA` | Comma-separated; extra companies to block, added to the built-in list | *(none)* |
| `SEEN_STORE_PATH` | Where dedupe state is saved | `seen_listings.json` |

Example: only software/data roles, skip anything requiring an advanced degree:
```bash
export ROLE_INCLUDE_KEYWORDS="software,swe,backend,frontend,full-stack,data,ml,machine learning"
export ROLE_EXCLUDE_KEYWORDS="phd,mba"
```

## How de-duping works

Every listing gets a stable ID (the source's own ID when available,
otherwise a hash of company+role+link). `seen_listings.json` tracks every
ID the bot has ever fetched — not just ones it posted — so a listing that
gets filtered out today (e.g. too old, wrong keyword) won't be
re-evaluated and possibly posted later once it "ages into" being new.
Only truly new IDs trigger a Slack message.

## Message format

Each alert is its own Slack message:

> **Software Engineer Intern** @ **Acme Corp**
> 📍 San Francisco, CA &nbsp;&nbsp; 📅 Posted Aug 05, 2026
> [Apply here](#)
> _Source: SimplifyJobs Summer2027-Internships_

## Adding a source

Most internship-list GitHub repos that follow the SimplifyJobs
`listings.json` format work out of the box — just add a new entry to
`SOURCES` in `config.py` with `"type": "github_json"` and the raw file URL.

For a different shape of source (an RSS feed, a different JSON API, a
company careers page with a public API), write a `fetch_<type>(source)`
function in `sources.py` that returns the normalized listing dict shape
documented at the top of that file, then register it in `FETCHERS`.

## Notes & limits

- Scraping LinkedIn, Handshake, or Indeed directly isn't included here —
  those sites actively block automated scraping and it would violate
  their Terms of Service. The GitHub-list + RemoteOK approach avoids that
  while still surfacing the same roles (Simplify's own bot scrapes
  company career pages hourly and feeds these lists).
- Slack's API rate limits chat.postMessage to roughly 1 message/second
  per channel; `slack_notifier.post_all` paces requests accordingly.
- If a source's format changes upstream, that source will log an error
  and be skipped for that run — it won't crash the whole job.
