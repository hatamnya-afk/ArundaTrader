import io
import unittest
from unittest.mock import patch

import toobit_read_only_transport_v0_1 as transport


class _Response:
    status = 200

    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return self._payload[:size]


class ToobitReadOnlyTransportTests(unittest.TestCase):
    def test_public_exchange_info_get_is_allowed(self):
        payload = b'{"symbols":[],"contracts":[]}'
        with patch.object(transport, "urlopen", return_value=_Response(payload)) as call:
            result = transport.toobit_read_only_transport(
                method="GET",
                path="/api/v1/exchangeInfo",
                params={},
                headers={"X-BB-APIKEY": "must-not-be-forwarded"},
                base_url="https://api.toobit.com",
            )
        self.assertEqual(result, {"symbols": [], "contracts": []})
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.toobit.com/api/v1/exchangeInfo")
        self.assertEqual(request.get_method(), "GET")
        self.assertIsNone(request.get_header("X-bb-apikey"))

    def test_server_time_is_allowed(self):
        with patch.object(
            transport, "urlopen", return_value=_Response(b'{"serverTime":123}')
        ):
            result = transport.toobit_read_only_transport(
                method="GET", path="/api/v1/time", params={}
            )
        self.assertEqual(result, {"serverTime": 123})

    def test_non_get_is_denied_before_network(self):
        with patch.object(transport, "urlopen") as call:
            with self.assertRaisesRegex(RuntimeError, "METHOD_DENIED"):
                transport.toobit_read_only_transport(
                    method="POST", path="/api/v1/order", params={}
                )
        call.assert_not_called()

    def test_unapproved_path_is_denied_before_network(self):
        with patch.object(transport, "urlopen") as call:
            with self.assertRaisesRegex(RuntimeError, "PATH_DENIED"):
                transport.toobit_read_only_transport(
                    method="GET", path="/api/v1/order", params={}
                )
        call.assert_not_called()

    def test_host_override_is_denied_before_network(self):
        with patch.object(transport, "urlopen") as call:
            with self.assertRaisesRegex(RuntimeError, "HOST_DENIED"):
                transport.toobit_read_only_transport(
                    method="GET",
                    path="/api/v1/time",
                    base_url="https://example.com",
                )
        call.assert_not_called()

    def test_query_parameters_are_denied(self):
        with patch.object(transport, "urlopen") as call:
            with self.assertRaisesRegex(RuntimeError, "PARAMS_DENIED"):
                transport.toobit_read_only_transport(
                    method="GET", path="/api/v1/time", params={"symbol": "BTCUSDT"}
                )
        call.assert_not_called()

    def test_invalid_json_is_denied(self):
        with patch.object(transport, "urlopen", return_value=_Response(b"not-json")):
            with self.assertRaisesRegex(RuntimeError, "INVALID_JSON"):
                transport.toobit_read_only_transport(
                    method="GET", path="/api/v1/time", params={}
                )


if __name__ == "__main__":
    unittest.main()
