"""Offline tests for the Stripe→Telegram linking helpers. Run: python3 -m unittest"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import linking  # noqa: E402


class TestCode(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(linking.normalize_code(" 9f3a2c "), "9F3A2C")
        self.assertEqual(linking.normalize_code("/start 9f3a2c"), "9F3A2C")
        self.assertEqual(linking.normalize_code("/start"), "")

    def test_valid(self):
        self.assertTrue(linking.is_valid_code("9F3A2C"))
        self.assertTrue(linking.is_valid_code("/start 9f3a2c"))
        self.assertFalse(linking.is_valid_code("ZZZZZZ"))   # not hex
        self.assertFalse(linking.is_valid_code("9F3A2"))     # too short
        self.assertFalse(linking.is_valid_code(""))


class TestStatusMap(unittest.TestCase):
    def test_known(self):
        self.assertEqual(linking.subscription_status_from_stripe("active"), "active")
        self.assertEqual(linking.subscription_status_from_stripe("trialing"), "trial")
        self.assertEqual(linking.subscription_status_from_stripe("past_due"), "past_due")
        self.assertEqual(linking.subscription_status_from_stripe("canceled"), "canceled")

    def test_unknown_defaults_inactive(self):
        self.assertEqual(linking.subscription_status_from_stripe("weird"), "inactive")
        self.assertEqual(linking.subscription_status_from_stripe(""), "inactive")


class TestDeepLink(unittest.TestCase):
    def test_build(self):
        self.assertEqual(linking.build_deep_link("OpenTrainerBot", "9F3A2C"),
                         "https://t.me/OpenTrainerBot?start=9F3A2C")
        self.assertEqual(linking.build_deep_link("@OpenTrainerBot", "9F3A2C"),
                         "https://t.me/OpenTrainerBot?start=9F3A2C")
        self.assertEqual(linking.build_deep_link("", "9F3A2C"), "")

    def test_message_contains_code_and_link(self):
        msg = linking.verification_message("9F3A2C", "OpenTrainerBot")
        self.assertIn("9F3A2C", msg)
        self.assertIn("t.me/OpenTrainerBot?start=9F3A2C", msg)


if __name__ == "__main__":
    unittest.main()
