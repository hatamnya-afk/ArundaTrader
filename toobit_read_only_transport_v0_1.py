"""Production-safe public read-only HTTP transport for Toobit metadata.

This transport deliberately supports only unauthenticated GET requests to the
provider's server-time and exchange-information endpoints. It cannot submit,
cancel, or modify orders and never reads credentials.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from typing import Any, Mapping

TOOBIT_BASE_URL = "https://api.toobit.com"
READ_ONLY_PATHS = frozenset({"/api/v1/time", "/api/v1/exchangeInfo"})
DEFAULT_TIMEOUT_SECONDS = 8
MAX_RESPONSE_BYTES = 2_000_000


def toobit_read_only_transport(
    *,
    method: str,
    path: str,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    base_url: str = TOOBIT_BASE_URL,
) -> Any:
    """Fetch public Toobit metadata; fail closed for every other request."""
    if not isinstance(method, str) or method.strip().upper() != "GET":
        raise RuntimeError("TOOBIT_READ_ONLY_TRANSPORT_METHOD_DENIED")
    if not isinstance(path, str) or path not in READ_ONLY_PATHS:
        raise RuntimeError("TOOBIT_READ_ONLY_TRANSPORT_PATH_DENIED")
    parsed_base = urlsplit(base_url)
    if (
        parsed_base.scheme != "https"
        or parsed_base.netloc.lower() != "api.toobit.com"
        or parsed_base.path not in {"", "/"}
        or parsed_base.query
        or parsed_base.fragment
    ):
        raise RuntimeError("TOOBIT_READ_ONLY_TRANSPORT_HOST_DENIED")
    if params not in (None, {}):
        raise RuntimeError("TOOBIT_READ_ONLY_TRANSPORT_PARAMS_DENIED")
    # Caller-supplied headers are intentionally ignored: this surface is public
    # metadata-only and must never send credentials or signatures.
    url = TOOBIT_BASE_URL + path
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise RuntimeError(f"TOOBIT_READ_ONLY_HTTP_STATUS:{status}")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise RuntimeError(f"TOOBIT_READ_ONLY_HTTP_STATUS:{exc.code}") from exc
    except URLError as exc:
        raise RuntimeError("TOOBIT_READ_ONLY_NETWORK_ERROR") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise RuntimeError("TOOBIT_READ_ONLY_RESPONSE_TOO_LARGE")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("TOOBIT_READ_ONLY_RESPONSE_INVALID_JSON") from exc


__all__ = [
    "TOOBIT_BASE_URL",
    "READ_ONLY_PATHS",
    "toobit_read_only_transport",
]
