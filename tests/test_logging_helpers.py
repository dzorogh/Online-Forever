import unittest

import main


class LoggingHelpersTest(unittest.TestCase):
    def test_get_env_int_falls_back_for_invalid_values(self):
        self.assertEqual(main.get_env_int({"HEARTBEAT_LOG_INTERVAL": "abc"}, "HEARTBEAT_LOG_INTERVAL", 60), 60)
        self.assertEqual(main.get_env_int({"HEARTBEAT_LOG_INTERVAL": "-5"}, "HEARTBEAT_LOG_INTERVAL", 60), 60)
        self.assertEqual(main.get_env_int({"HEARTBEAT_LOG_INTERVAL": "30"}, "HEARTBEAT_LOG_INTERVAL", 60), 30)

    def test_gateway_health_logger_respects_interval(self):
        logger = main.GatewayHealthLogger(interval_seconds=60)

        self.assertTrue(logger.should_log(now=100, last_ack_at=95))
        logger.mark_logged(now=100)

        self.assertFalse(logger.should_log(now=130, last_ack_at=125))
        self.assertTrue(logger.should_log(now=161, last_ack_at=150))


if __name__ == "__main__":
    unittest.main()
