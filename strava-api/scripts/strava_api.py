#!/usr/bin/env python3
import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib import parse, request, error

API_BASE = "https://www.strava.com/api/v3"
OAUTH_URL = "https://www.strava.com/oauth/token"
DEFAULT_CFG = Path.home() / ".openclaw" / "workspace" / ".strava.json"


@dataclass
class StravaConfig:
    path: Path
    data: dict


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def load_config() -> StravaConfig:
    cfg_path = Path(os.environ.get("STRAVA_CONFIG", str(DEFAULT_CFG))).expanduser()
    if not cfg_path.exists():
        raise FileNotFoundError(f"Missing Strava config: {cfg_path}")
    data = json.loads(cfg_path.read_text())
    required = ["client_id", "client_secret", "refresh_token"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        raise ValueError(f"Missing required keys in config: {', '.join(missing)}")
    return StravaConfig(path=cfg_path, data=data)


def save_config(cfg: StravaConfig) -> None:
    cfg.path.write_text(json.dumps(cfg.data, indent=2) + "\n")


def refresh_access_token(cfg: StravaConfig) -> None:
    payload = parse.urlencode(
        {
            "client_id": str(cfg.data["client_id"]),
            "client_secret": str(cfg.data["client_secret"]),
            "grant_type": "refresh_token",
            "refresh_token": cfg.data["refresh_token"],
        }
    ).encode()
    req = request.Request(OAUTH_URL, data=payload, method="POST")
    with request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode())
    cfg.data["access_token"] = body["access_token"]
    cfg.data["refresh_token"] = body.get("refresh_token", cfg.data["refresh_token"])
    cfg.data["expires_at"] = body.get("expires_at")
    save_config(cfg)


def ensure_fresh_token(cfg: StravaConfig) -> None:
    expires_at = cfg.data.get("expires_at")
    token = cfg.data.get("access_token")
    # Refresh when missing or expiring in next 120s
    if not token or not expires_at or int(expires_at) <= int(utc_now().timestamp()) + 120:
        refresh_access_token(cfg)


def api_get(cfg: StravaConfig, path: str, query: dict | None = None):
    ensure_fresh_token(cfg)
    qs = f"?{parse.urlencode(query)}" if query else ""
    url = f"{API_BASE}{path}{qs}"
    req = request.Request(url, headers={"Authorization": f"Bearer {cfg.data['access_token']}"})
    try:
        with request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except error.HTTPError as e:
        detail = e.read().decode(errors="ignore")[:400]
        raise RuntimeError(f"Strava API error {e.code}: {detail}")


def pace_min_per_km(distance_m: float, moving_s: float):
    if not distance_m or not moving_s:
        return None
    km = distance_m / 1000.0
    return round((moving_s / 60.0) / km, 2)


def normalize_activity(a: dict) -> dict:
    distance_m = float(a.get("distance", 0) or 0)
    moving_s = float(a.get("moving_time", 0) or 0)
    elapsed_s = float(a.get("elapsed_time", 0) or 0)
    return {
        "id": a.get("id"),
        "name": a.get("name"),
        "type": a.get("type"),
        "sport_type": a.get("sport_type"),
        "start_date": a.get("start_date"),
        "start_date_local": a.get("start_date_local"),
        "timezone": a.get("timezone"),
        "distance_km": round(distance_m / 1000.0, 2),
        "moving_time_min": round(moving_s / 60.0, 2),
        "elapsed_time_min": round(elapsed_s / 60.0, 2),
        "average_speed_mps": a.get("average_speed"),
        "pace_min_per_km": pace_min_per_km(distance_m, moving_s),
        "total_elevation_gain_m": a.get("total_elevation_gain"),
        "trainer": bool(a.get("trainer", False)),
    }


def parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def filter_activities(items: list[dict], days: int, typ: str | None) -> list[dict]:
    cutoff = utc_now() - timedelta(days=days)
    out = []
    for a in items:
        try:
            dt = parse_dt(a["start_date"])
        except Exception:
            continue
        if dt < cutoff:
            continue
        if typ and (a.get("sport_type") != typ and a.get("type") != typ):
            continue
        out.append(a)
    return out


def cmd_athlete(cfg: StravaConfig, _args):
    athlete = api_get(cfg, "/athlete")
    return {
        "generated_at": iso_now(),
        "athlete": {
            "id": athlete.get("id"),
            "firstname": athlete.get("firstname"),
            "lastname": athlete.get("lastname"),
        },
    }


def fetch_recent_raw(cfg: StravaConfig, per_page: int = 100, page: int = 1):
    return api_get(cfg, "/athlete/activities", {"per_page": per_page, "page": page})


def cmd_recent(cfg: StravaConfig, args):
    raw = fetch_recent_raw(cfg, per_page=min(max(args.limit, 1), 200), page=1)
    filt = filter_activities(raw, args.days, args.type)
    activities = [normalize_activity(a) for a in filt[: args.limit]]
    return {
        "generated_at": iso_now(),
        "filters": {"days": args.days, "type": args.type, "limit": args.limit},
        "activities": activities,
    }


def week_bounds_local(tz_name: str, week_start: str):
    tz = ZoneInfo(tz_name)
    now_local = datetime.now(tz)
    weekday = now_local.weekday()  # Mon=0
    start_index = 0 if week_start.lower() == "monday" else 6
    delta_days = (weekday - start_index) % 7
    start = (now_local - timedelta(days=delta_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return start, end


def cmd_week(cfg: StravaConfig, args):
    start_local, end_local = week_bounds_local(args.timezone, args.week_start)
    # Pull enough recent activities to cover the week
    raw = fetch_recent_raw(cfg, per_page=100, page=1)
    acts = []
    for a in raw:
        if args.type and (a.get("sport_type") != args.type and a.get("type") != args.type):
            continue
        dt_local = parse_dt(a["start_date_local"]).astimezone(ZoneInfo(args.timezone))
        if start_local <= dt_local < end_local:
            acts.append(a)
    norm = [normalize_activity(a) for a in acts]
    return {
        "generated_at": iso_now(),
        "timezone": args.timezone,
        "week_start": start_local.date().isoformat(),
        "week_end_exclusive": end_local.date().isoformat(),
        "type": args.type,
        "count": len(norm),
        "distance_km": round(sum(a["distance_km"] for a in norm), 2),
        "moving_time_min": round(sum(a["moving_time_min"] for a in norm), 2),
        "activities": norm,
    }


def cmd_last_run(cfg: StravaConfig, args):
    raw = fetch_recent_raw(cfg, per_page=50, page=1)
    run = None
    for a in raw:
        if a.get("sport_type") == "Run" or a.get("type") == "Run":
            run = a
            break
    if not run:
        return {
            "generated_at": iso_now(),
            "timezone": args.timezone,
            "last_activity": None,
            "hours_since": None,
        }
    dt = parse_dt(run["start_date"])
    hours = round((utc_now() - dt).total_seconds() / 3600.0, 2)
    n = normalize_activity(run)
    return {
        "generated_at": iso_now(),
        "timezone": args.timezone,
        "last_activity": {
            "id": n["id"],
            "start_date_local": n["start_date_local"],
            "distance_km": n["distance_km"],
            "moving_time_min": n["moving_time_min"],
            "pace_min_per_km": n["pace_min_per_km"],
        },
        "hours_since": hours,
    }


def cmd_summary(cfg: StravaConfig, args):
    raw = fetch_recent_raw(cfg, per_page=100, page=1)
    filt = filter_activities(raw, args.days, args.type)
    norm = [normalize_activity(a) for a in filt]
    count = len(norm)
    distance_km = round(sum(a["distance_km"] for a in norm), 2)
    moving_min = round(sum(a["moving_time_min"] for a in norm), 2)
    avg_distance = round(distance_km / count, 2) if count else 0
    paces = [a["pace_min_per_km"] for a in norm if a["pace_min_per_km"]]
    avg_pace = round(sum(paces) / len(paces), 2) if paces else None
    return {
        "generated_at": iso_now(),
        "timezone": args.timezone,
        "window_days": args.days,
        "type": args.type,
        "count": count,
        "distance_km": distance_km,
        "moving_time_min": moving_min,
        "avg_distance_km": avg_distance,
        "avg_pace_min_per_km": avg_pace,
    }


def main():
    p = argparse.ArgumentParser(description="Strava API normalized wrapper")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("athlete")

    recent = sub.add_parser("recent")
    recent.add_argument("--days", type=int, default=7)
    recent.add_argument("--type", default="Run")
    recent.add_argument("--limit", type=int, default=30)

    week = sub.add_parser("week")
    week.add_argument("--type", default="Run")
    week.add_argument("--week-start", choices=["monday", "sunday"], default="monday")
    week.add_argument("--timezone", default="Europe/London")

    last = sub.add_parser("last-run")
    last.add_argument("--timezone", default="Europe/London")

    summary = sub.add_parser("summary")
    summary.add_argument("--days", type=int, default=28)
    summary.add_argument("--type", default="Run")
    summary.add_argument("--timezone", default="Europe/London")

    args = p.parse_args()
    cfg = load_config()

    handlers = {
        "athlete": cmd_athlete,
        "recent": cmd_recent,
        "week": cmd_week,
        "last-run": cmd_last_run,
        "summary": cmd_summary,
    }

    out = handlers[args.cmd](cfg, args)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
