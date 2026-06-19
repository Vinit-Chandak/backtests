from __future__ import annotations

import unittest

from backtests_momentum.upstox import api_headers


class UpstoxTests(unittest.TestCase):
    def test_api_headers_include_configurable_user_agent(self) -> None:
        headers = api_headers("test-agent", {"Authorization": "Bearer token"})

        self.assertEqual(headers["Accept"], "application/json")
        self.assertEqual(headers["User-Agent"], "test-agent")
        self.assertEqual(headers["Authorization"], "Bearer token")


if __name__ == "__main__":
    unittest.main()
