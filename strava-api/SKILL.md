---
name: strava-api
description: Query Strava athlete and activity data through a safe, normalized JSON wrapper. Use when checking recent activities, weekly run counts, last-run timing, distance/pace summaries, or before sending running reminders that require live Strava context.
---

# Strava API

Use this skill to fetch live Strava data without exposing credentials.

## Requirements

- Keep credentials out of prompts and output.
- Read tokens from a local config file at runtime.
- Refresh access token before API calls.

## Config

The script reads config from:

1. `STRAVA_CONFIG` env var (if set)
2. `~/.strava.json` (default, recommended)

Expected keys in config (not committed):

- `client_id`
- `client_secret`
- `refresh_token`
- `access_token` (updated automatically)
- `expires_at` (updated automatically)

See `references/config-and-security.md` for config + safety rules.

## Commands

Run from this skill folder:

```bash
python3 scripts/strava_api.py athlete
python3 scripts/strava_api.py recent --days 7 --type Run --limit 30
python3 scripts/strava_api.py week --type Run --week-start monday --timezone Europe/London
python3 scripts/strava_api.py last-run --timezone Europe/London
python3 scripts/strava_api.py summary --days 28 --type Run --timezone Europe/London
```

## Output Contract

Return compact JSON only. Do not return raw access tokens.

See `references/output-schema.md` for field definitions.

## Reminder Integration Guidance

Before reminder logic:

1. Call `week` for current run count.
2. Call `last-run` for recency.
3. Apply policy (rest day, target, cooldown) outside this skill.

Keep policy separate from API plumbing.
