#!/usr/bin/env python3
"""Aggregate monthly work hours from Google Calendar events by exact title."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
DEFAULT_TIMEZONE = "Asia/Tokyo"


class WorklogError(Exception):
    """User-facing execution error."""


@dataclass(frozen=True)
class MonthWindow:
    start: datetime
    end: datetime


def parse_month_window(month: str, timezone_name: str) -> MonthWindow:
    parts = month.split("-")
    if len(parts) != 2:
        raise WorklogError("--month must be in YYYY-MM format.")
    try:
        year = int(parts[0])
        month_value = int(parts[1])
    except ValueError as exc:
        raise WorklogError("--month must be in YYYY-MM format.") from exc
    if month_value < 1 or month_value > 12:
        raise WorklogError("--month must be in YYYY-MM format.")

    try:
        tz = ZoneInfo(timezone_name)
    except Exception as exc:  # pragma: no cover - platform tz db issue
        raise WorklogError(f"Invalid timezone: {timezone_name}") from exc

    start = datetime(year, month_value, 1, 0, 0, 0, tzinfo=tz)
    if month_value == 12:
        end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=tz)
    else:
        end = datetime(year, month_value + 1, 1, 0, 0, 0, tzinfo=tz)
    return MonthWindow(start=start, end=end)


def is_all_day_event(event: dict) -> bool:
    return "date" in event.get("start", {}) or "date" in event.get("end", {})


def parse_event_datetime(value: str) -> datetime:
    # Google may return a trailing "Z", which datetime.fromisoformat does not parse directly.
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def overlap_seconds(event_start: datetime, event_end: datetime, window: MonthWindow) -> float:
    effective_start = max(event_start, window.start)
    effective_end = min(event_end, window.end)
    if effective_end <= effective_start:
        return 0.0
    return (effective_end - effective_start).total_seconds()


def aggregate_event_seconds(events: list[dict], target_title: str, window: MonthWindow) -> tuple[float, int]:
    total_seconds = 0.0
    matched_count = 0

    for event in events:
        if event.get("status") == "cancelled":
            continue
        if event.get("summary") != target_title:
            continue
        if is_all_day_event(event):
            continue

        start_raw = event.get("start", {}).get("dateTime")
        end_raw = event.get("end", {}).get("dateTime")
        if not start_raw or not end_raw:
            continue

        try:
            event_start = parse_event_datetime(start_raw)
            event_end = parse_event_datetime(end_raw)
        except ValueError:
            continue

        seconds = overlap_seconds(event_start, event_end, window)
        if seconds > 0:
            matched_count += 1
            total_seconds += seconds

    return total_seconds, matched_count


def build_calendar_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise WorklogError(
            "Missing dependencies. Run: pip install -r requirements.txt"
        ) from exc

    creds = None
    token_path = "token.json"
    credentials_path = "credentials.json"

    if Credentials and token_path:
        try:
            creds = Credentials.from_authorized_user_file(token_path, [READONLY_SCOPE])
        except FileNotFoundError:
            creds = None
        except ValueError:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:
                raise WorklogError(f"Failed to refresh OAuth token: {exc}") from exc
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, [READONLY_SCOPE]
                )
            except FileNotFoundError as exc:
                raise WorklogError(
                    "credentials.json not found. Download OAuth client credentials first."
                ) from exc
            creds = flow.run_local_server(port=0)

        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def fetch_events_for_window(service, window: MonthWindow) -> list[dict]:
    events: list[dict] = []
    page_token = None

    while True:
        response = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=window.start.isoformat(),
                timeMax=window.end.isoformat(),
                singleEvents=True,
                showDeleted=False,
                pageToken=page_token,
                maxResults=2500,
            )
            .execute()
        )
        events.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return events


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sum monthly work hours from Google Calendar by exact event title."
    )
    parser.add_argument("--month", required=True, help="Target month in YYYY-MM")
    parser.add_argument("--title", required=True, help="Exact event title to match")
    parser.add_argument(
        "--timezone",
        default=DEFAULT_TIMEZONE,
        help=f"IANA timezone name (default: {DEFAULT_TIMEZONE})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        window = parse_month_window(args.month, args.timezone)
        service = build_calendar_service()
        events = fetch_events_for_window(service, window)
        total_seconds, matched_count = aggregate_event_seconds(events, args.title, window)
    except WorklogError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: Google Calendar API request failed: {exc}", file=sys.stderr)
        return 1

    total_hours = total_seconds / 3600.0
    print(f"Month: {args.month}")
    print(f"Title (exact): {args.title}")
    print(f"Matched events: {matched_count}")
    print(f"Total hours: {total_hours:.2f}h")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
