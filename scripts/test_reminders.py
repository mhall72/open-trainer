"""Tests for the reminder slot-matching logic. Run: python3 -m unittest"""
import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

import send_reminders as sr  # noqa: E402

# Monday 2026-06-08 22:05 UTC.
MON_2205_UTC = datetime(2026, 6, 8, 22, 5, tzinfo=timezone.utc)


class TestDueReminders(unittest.TestCase):
    def _r(self, **kw):
        base = {"id": "1", "enabled": True, "days": ["mon"], "time": "22:00:00",
                "timezone": "UTC", "last_sent_at": None}
        base.update(kw)
        return base

    def test_due_in_window(self):
        self.assertEqual(len(sr.due_reminders([self._r()], MON_2205_UTC)), 1)

    def test_not_due_wrong_day(self):
        self.assertEqual(sr.due_reminders([self._r(days=["tue"])], MON_2205_UTC), [])

    def test_not_due_before_time(self):
        self.assertEqual(sr.due_reminders([self._r(time="23:00:00")], MON_2205_UTC), [])

    def test_not_due_past_window(self):
        self.assertEqual(sr.due_reminders([self._r(time="21:00:00")], MON_2205_UTC), [])

    def test_disabled_skipped(self):
        self.assertEqual(sr.due_reminders([self._r(enabled=False)], MON_2205_UTC), [])

    def test_already_sent_this_slot(self):
        r = self._r(last_sent_at="2026-06-08T22:01:00+00:00")
        self.assertEqual(sr.due_reminders([r], MON_2205_UTC), [])

    def test_sent_yesterday_still_due(self):
        r = self._r(last_sent_at="2026-06-07T22:01:00+00:00")
        self.assertEqual(len(sr.due_reminders([r], MON_2205_UTC)), 1)

    def test_timezone_aware(self):
        # 22:05 UTC == 18:05 in America/Toronto (EDT, -4). A 22:00 *Toronto*
        # reminder is NOT due yet at 18:05 local.
        r = self._r(timezone="America/Toronto")
        self.assertEqual(sr.due_reminders([r], MON_2205_UTC), [])
        # ...but an 18:00 Toronto reminder IS due at 18:05 local.
        r2 = self._r(timezone="America/Toronto", time="18:00:00")
        self.assertEqual(len(sr.due_reminders([r2], MON_2205_UTC)), 1)


if __name__ == "__main__":
    unittest.main()
