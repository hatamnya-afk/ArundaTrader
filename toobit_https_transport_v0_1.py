"""Minimal single-attempt HTTPS transport for Toobit signed REST calls.

No retries, no redirects to a different host, and no endpoint discovery.
This module is only invoked when a caller explicitly constructs the opt-in adapter.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any

_ALLOWED_HOST = "api.toobit.com"
_ALLOWED_PATHS = {
    ("GET", "/api/v1/time"),
    ("GET", "/api/v1/exchangeInfo"),
    ("GET", "/api/v1/spot/order"),
    ("GET", "/api/v2/futures/order"),
    ("POST", "/api/v1/spot/order"),
    ("POST", "/api/v2/futures/order"),
}


def toobit_https_transport(
    *,
    method: str,
    path: str,
    params: dict[str, Any],
    headers: dict[str, str],
    base_url: str,
    timeout_seconds: float = 8.0,
) -> Any:
    method = str(method).upper()
    if (method, path) not in _ALLOWED_PATHS:
        raise ValueError("TOOBIT_TRANSPORT_ENDPOINT_NOT_ALLOWLISTED")
    if base_url != "https://" + _ALLOWED_HOST:
        raise ValueError("TOOBIT_TRANSPORT_HOST_NOT_ALLOWLISTED")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
        raise ValueError("TOOBIT_TRANSPORT_TIMEOUT_INVALID")

    query = urlencode(params)
    request_headers = dict(headers)
    if method == "GET":
        url = base_url + path + (("?" + query) if query else "")
        request = Request(url, method=method, headers=request_headers)
    else:
        # Toobit's signed REST examples send POST parameters as an
        # application/x-www-form-urlencoded body, not a URL query string.
        url = base_url + path
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = Request(
            url,
            data=query.encode("utf-8"),
            method=method,
            headers=request_headers,
        )
    try:
        with urlopen(request, timeout=float(timeout_seconds)) as response:
            raw = response.read()
    except HTTPError as exc:
        # Preserve the provider response when available; do not retry POST.
        raw = exc.read()
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            raise RuntimeError(f"TOOBIT_HTTP_ERROR:{exc.code}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"TOOBIT_TRANSPORT_OUTCOME_UNKNOWN:{exc}") from exc

    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("TOOBIT_RESPONSE_JSON_INVALID") from exc
