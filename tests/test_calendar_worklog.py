import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from calendar_worklog import (
    MatchedEventDetail,
    MonthWindow,
    aggregate_event_seconds,
    format_event_detail_line,
    resolve_aggregation_window,
)


class AggregateEventSecondsTests(unittest.TestCase):
    def setUp(self):
        self.tz = ZoneInfo("Asia/Tokyo")

    def window(self, year: int, month: int) -> MonthWindow:
        start = datetime(year, month, 1, 0, 0, 0, tzinfo=self.tz)
        if month == 12:
            end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=self.tz)
        else:
            end = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=self.tz)
        return MonthWindow(start=start, end=end)

    def test_overnight_same_month_counts_full_duration(self):
        events = [
            {
                "summary": "案件A",
                "status": "confirmed",
                "start": {"dateTime": "2026-02-10T22:00:00+09:00"},
                "end": {"dateTime": "2026-02-11T02:00:00+09:00"},
            }
        ]
        total_seconds, matched, details = aggregate_event_seconds(events, "案件A", self.window(2026, 2))
        self.assertEqual(matched, 1)
        self.assertEqual(total_seconds, 4 * 3600)
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0].counted_seconds, 4 * 3600)

    def test_month_boundary_previous_month_to_target_month(self):
        events = [
            {
                "summary": "案件A",
                "status": "confirmed",
                "start": {"dateTime": "2026-01-31T23:00:00+09:00"},
                "end": {"dateTime": "2026-02-01T02:00:00+09:00"},
            }
        ]
        total_seconds, matched, _ = aggregate_event_seconds(events, "案件A", self.window(2026, 2))
        self.assertEqual(matched, 1)
        self.assertEqual(total_seconds, 2 * 3600)

    def test_month_boundary_target_month_to_next_month(self):
        events = [
            {
                "summary": "案件A",
                "status": "confirmed",
                "start": {"dateTime": "2026-02-28T23:00:00+09:00"},
                "end": {"dateTime": "2026-03-01T02:00:00+09:00"},
            }
        ]
        total_seconds, matched, _ = aggregate_event_seconds(events, "案件A", self.window(2026, 2))
        self.assertEqual(matched, 1)
        self.assertEqual(total_seconds, 3600)

    def test_exact_match_only(self):
        events = [
            {
                "summary": "案件A",
                "status": "confirmed",
                "start": {"dateTime": "2026-02-05T10:00:00+09:00"},
                "end": {"dateTime": "2026-02-05T11:00:00+09:00"},
            },
            {
                "summary": "案件A-打ち合わせ",
                "status": "confirmed",
                "start": {"dateTime": "2026-02-05T12:00:00+09:00"},
                "end": {"dateTime": "2026-02-05T13:00:00+09:00"},
            },
        ]
        total_seconds, matched, _ = aggregate_event_seconds(events, "案件A", self.window(2026, 2))
        self.assertEqual(matched, 1)
        self.assertEqual(total_seconds, 3600)

    def test_all_day_events_are_excluded(self):
        events = [
            {
                "summary": "案件A",
                "status": "confirmed",
                "start": {"date": "2026-02-03"},
                "end": {"date": "2026-02-04"},
            }
        ]
        total_seconds, matched, _ = aggregate_event_seconds(events, "案件A", self.window(2026, 2))
        self.assertEqual(matched, 0)
        self.assertEqual(total_seconds, 0)

    def test_zero_when_no_matching_events(self):
        events = [
            {
                "summary": "案件B",
                "status": "confirmed",
                "start": {"dateTime": "2026-02-01T09:00:00+09:00"},
                "end": {"dateTime": "2026-02-01T10:00:00+09:00"},
            }
        ]
        total_seconds, matched, _ = aggregate_event_seconds(events, "案件A", self.window(2026, 2))
        self.assertEqual(matched, 0)
        self.assertEqual(total_seconds, 0)

    def test_format_event_detail_line(self):
        detail = MatchedEventDetail(
            title="案件A",
            start=datetime(2026, 2, 4, 20, 0, 0, tzinfo=self.tz),
            end=datetime(2026, 2, 4, 22, 30, 0, tzinfo=self.tz),
            counted_seconds=2.5 * 3600,
        )
        line = format_event_detail_line(1, detail, self.tz)
        self.assertEqual(line, "1. 2026-02-04 20:00 -> 2026-02-04 22:30 (2.50h)")

    def test_resolve_aggregation_window_caps_to_now_by_default(self):
        month_window = self.window(2026, 2)
        now = datetime(2026, 2, 10, 12, 0, 0, tzinfo=self.tz)
        resolved = resolve_aggregation_window(
            month_window=month_window,
            include_through_month_end=False,
            now=now,
        )
        self.assertEqual(resolved.start, month_window.start)
        self.assertEqual(resolved.end, now)

    def test_resolve_aggregation_window_keeps_month_end_when_flag_enabled(self):
        month_window = self.window(2026, 2)
        now = datetime(2026, 2, 10, 12, 0, 0, tzinfo=self.tz)
        resolved = resolve_aggregation_window(
            month_window=month_window,
            include_through_month_end=True,
            now=now,
        )
        self.assertEqual(resolved, month_window)


if __name__ == "__main__":
    unittest.main()
