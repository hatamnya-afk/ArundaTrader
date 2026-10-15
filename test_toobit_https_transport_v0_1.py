"""Allowlist tests; no network calls are performed."""

import unittest
from io import BytesIO
from unittest.mock import patch

from toobit_https_transport_v0_1 import toobit_https_transport


class ToobitTransportTests(unittest.TestCase):
    def test_read_only_order_query_routes_are_allowlisted_without_network(self):
        routes = (
            "/api/v1/spot/order",
            "/api/v2/futures/order",
        )
        for path in routes:
            with self.subTest(path=path):
                with patch(
                    "toobit_https_transport_v0_1.urlopen",
                    return_value=BytesIO(b'{"code":200,"data":{}}'),
                ) as mocked_urlopen:
                    result = toobit_https_transport(
                        method="GET",
                        path=path,
                        params={"origClientOrderId": "A-test"},
                        headers={"X-BB-APIKEY": "test-key"},
                        base_url="https://api.toobit.com",
                    )
                self.assertEqual(result, {"code": 200, "data": {}})
                mocked_urlopen.assert_called_once()

    def test_post_sends_signed_form_body_not_url_query(self):
        with patch(
            "toobit_https_transport_v0_1.urlopen",
            return_value=BytesIO(b'{"code":200,"data":{"orderId":"fixture"}}'),
        ) as mocked_urlopen:
            result = toobit_https_transport(
                method="POST",
                path="/api/v1/spot/order",
                params={
                    "symbol": "BTCUSDT",
                    "newClientOrderId": "A-fixture",
                    "timestamp": 123456789,
                    "recvWindow": 5000,
                    "signature": "fixture-signature",
                },
                headers={"X-BB-APIKEY": "test-key"},
                base_url="https://api.toobit.com",
            )
        self.assertEqual(result, {"code": 200, "data": {"orderId": "fixture"}})
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.toobit.com/api/v1/spot/order")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Content-type"), "application/x-www-form-urlencoded")
        body = request.data.decode("utf-8")
        self.assertIn("newClientOrderId=A-fixture", body)
        self.assertIn("signature=fixture-signature", body)
        self.assertNotIn("signature=", request.full_url)

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
