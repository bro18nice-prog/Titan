import unittest

from titan.tools.smart_home import SmartHomeActions


class SmartHomeActionsTests(unittest.TestCase):
    def test_rejects_tuya_error_dictionary(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "nu a răspuns local"):
            SmartHomeActions._assert_tuya_success({"Error": "Timeout", "Err": "914"})

    def test_rejects_missing_tuya_response(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "răspuns valid"):
            SmartHomeActions._assert_tuya_success(None)

    def test_accepts_valid_tuya_response(self) -> None:
        response = {"dps": {"20": True}}
        self.assertEqual(SmartHomeActions._assert_tuya_success(response), response)

    def test_checks_reported_power_state(self) -> None:
        SmartHomeActions._assert_power_state({"dps": {"20": True}}, expected_on=True, power_dps="20")
        with self.assertRaisesRegex(RuntimeError, "încă aprins"):
            SmartHomeActions._assert_power_state({"dps": {"20": True}}, expected_on=False, power_dps="20")
