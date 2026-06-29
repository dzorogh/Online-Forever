from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

import main


class ScheduleTest(unittest.TestCase):
    def test_parse_clock_accepts_hh_mm(self):
        parsed = main.parse_clock("09:30")

        self.assertEqual(parsed.hour, 9)
        self.assertEqual(parsed.minute, 30)

    def test_online_window_for_same_day_schedule(self):
        tz = ZoneInfo("Europe/Moscow")
        start = main.parse_clock("09:30")
        end = main.parse_clock("22:30")

        self.assertFalse(main.is_online_window(datetime(2026, 6, 29, 9, 29, tzinfo=tz), start, end))
        self.assertTrue(main.is_online_window(datetime(2026, 6, 29, 9, 30, tzinfo=tz), start, end))
        self.assertTrue(main.is_online_window(datetime(2026, 6, 29, 22, 29, tzinfo=tz), start, end))
        self.assertFalse(main.is_online_window(datetime(2026, 6, 29, 22, 30, tzinfo=tz), start, end))

    def test_seconds_until_next_transition(self):
        tz = ZoneInfo("Europe/Moscow")
        start = main.parse_clock("09:30")
        end = main.parse_clock("22:30")

        self.assertEqual(
            main.seconds_until_next_transition(datetime(2026, 6, 29, 8, 30, tzinfo=tz), start, end),
            60 * 60,
        )
        self.assertEqual(
            main.seconds_until_next_transition(datetime(2026, 6, 29, 22, 0, tzinfo=tz), start, end),
            30 * 60,
        )
        self.assertEqual(
            main.seconds_until_next_transition(datetime(2026, 6, 29, 23, 0, tzinfo=tz), start, end),
            10 * 60 * 60 + 30 * 60,
        )


if __name__ == "__main__":
    unittest.main()
