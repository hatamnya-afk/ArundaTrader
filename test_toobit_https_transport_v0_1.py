"""Allowlist tests; no network calls are performed."""

import unittest

from toobit_https_transport_v0_1 import toobit_https_transport


class ToobitTransportTests(unittest.TestCase):
    def test_transport_rejects_non_allowlisted_write_route(self):
        with self.assertRaisesRegex(ValueError, "ENDPOINT_NOT_ALLOWLISTED"):
            toobit_https_transport(
                method="DELETE", path="/api/v1/spot/order", params={},
                headers={}, base_url="https://api.toobit.com",
            )

    def test_transport_rejects_untrusted_host(self):
        with self.assertRaisesRegex(ValueError, "HOST_NOT_ALLOWLISTED"):
            toobit_https_transport(
                method="POST", path="/api/v1/spot/order", params={},
                headers={}, base_url="https://example.invalid",
            )


if __name__ == "__main__":
    unittest.main()
