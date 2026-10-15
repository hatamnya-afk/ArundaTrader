"""Allowlist tests; no network calls are performed."""

import pytest

from toobit_https_transport_v0_1 import toobit_https_transport


def test_transport_rejects_non_allowlisted_write_route():
    with pytest.raises(ValueError, match="ENDPOINT_NOT_ALLOWLISTED"):
        toobit_https_transport(
            method="DELETE", path="/api/v1/spot/order", params={},
            headers={}, base_url="https://api.toobit.com",
        )


def test_transport_rejects_untrusted_host():
    with pytest.raises(ValueError, match="HOST_NOT_ALLOWLISTED"):
        toobit_https_transport(
            method="POST", path="/api/v1/spot/order", params={},
            headers={}, base_url="https://example.invalid",
        )
