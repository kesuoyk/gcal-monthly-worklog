import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from calendar_worklog import MonthWindow, aggregate_event_seconds


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
        total_seconds, matched = aggregate_event_seconds(events, "案件A", self.window(2026, 2))
        self.assertEqual(matched, 1)
        self.assertEqual(total_seconds, 4 * 3600)

    def test_month_boundary_previous_month_to_target_month(self):
        events = [
            {
                "summary": "案件A",
                "status": "confirmed",
                "start": {"dateTime": "2026-01-31T23:00:00+09:00"},
                "end": {"dateTime": "2026-02-01T02:00:00+09:00"},
            }
        ]
        total_seconds, matched = aggregate_event_seconds(events, "案件A", self.window(2026, 2))
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
        total_seconds, matched = aggregate_event_seconds(events, "案件A", self.window(2026, 2))
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
        total_seconds, matched = aggregate_event_seconds(events, "案件A", self.window(2026, 2))
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
        total_seconds, matched = aggregate_event_seconds(events, "案件A", self.window(2026, 2))
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
        total_seconds, matched = aggregate_event_seconds(events, "案件A", self.window(2026, 2))
        self.assertEqual(matched, 0)
        self.assertEqual(total_seconds, 0)


if __name__ == "__main__":
    unittest.main()
