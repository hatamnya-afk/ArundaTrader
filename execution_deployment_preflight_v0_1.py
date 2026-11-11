"""Read-only preflight for explicit execution deployment configuration.

This module performs no network calls, adapter construction, database creation,
or order actions. A PASS means only that static configuration fields are
present and syntactically plausible; it never authorizes or attempts execution.
"""
from __future__ import annotations

import base64
import binascii
import json
import os
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit


def inspect_execution_deployment_config(
    *,
    production_database_path: str | Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Inspect deployment settings without changing state or disclosing secrets."""
    env = os.environ if environ is None else environ
    issues: list[str] = []
    checks: dict[str, str] = {}

    provider_on = env.get("ARUNDA_ENABLE_PROVIDER_ORDER_ATTEMPT") == "1"
    venue_on = env.get("ARUNDA_ENABLE_TOOBIT_ORDER_SUBMISSION") == "1"
    if provider_on != venue_on:
        issues.append("EXECUTION_OPT_IN_SWITCHES_INCOMPLETE")
        checks["opt_in"] = "BLOCKED"
    elif not provider_on:
        checks["opt_in"] = "OFF"
    else:
        checks["opt_in"] = "ON_EXPLICITLY_CONFIGURED"

    raw_url = env.get("ARUNDA_MANDATE_STATUS_URL", "").strip()
    parsed = urlsplit(raw_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        issues.append("MANDATE_STATUS_URL_INVALID_OR_MISSING")
        checks["mandate_status_url"] = "MISSING_OR_INVALID"
    else:
        checks["mandate_status_url"] = "PRESENT_SYNTAX_ONLY"

    if not env.get("ARUNDA_MANDATE_STATUS_SOURCE_ID", "").strip():
        issues.append("MANDATE_STATUS_SOURCE_ID_MISSING")
        checks["mandate_status_source_id"] = "MISSING"
    else:
        checks["mandate_status_source_id"] = "PRESENT"

    key_text = env.get("ARUNDA_MANDATE_STATUS_PUBLIC_KEY_B64", "").strip()
    try:
        key_bytes = base64.b64decode(key_text, validate=True)
    except (binascii.Error, ValueError):
        key_bytes = b""
    if len(key_bytes) != 32:
        issues.append("MANDATE_STATUS_PUBLIC_KEY_INVALID_OR_MISSING")
        checks["mandate_status_public_key"] = "MISSING_OR_INVALID"
    else:
        checks["mandate_status_public_key"] = "PRESENT_SHAPE_ONLY"

    claim_text = env.get("ARUNDA_EXECUTION_CLAIM_DB", "").strip()
    claim_path = Path(claim_text).expanduser() if claim_text else None
    try:
        production_path = Path(production_database_path).expanduser().resolve()
    except (OSError, RuntimeError):
        production_path = None
    if claim_path is None:
        issues.append("ISOLATED_EXECUTION_CLAIM_DB_PATH_REQUIRED")
        checks["claim_store_path"] = "MISSING"
    elif not claim_path.is_absolute():
        issues.append("EXECUTION_CLAIM_DB_PATH_MUST_BE_ABSOLUTE")
        checks["claim_store_path"] = "NOT_ABSOLUTE"
    else:
        try:
            resolved_claim = claim_path.resolve()
            if production_path is not None and resolved_claim == production_path:
                issues.append("CLAIM_STORE_MUST_NOT_USE_PRODUCTION_DATABASE")
                checks["claim_store_path"] = "PRODUCTION_DB_COLLISION"
            elif not resolved_claim.parent.is_dir():
                issues.append("CLAIM_STORE_PARENT_DIRECTORY_MISSING")
                checks["claim_store_path"] = "PARENT_MISSING"
            else:
                checks["claim_store_path"] = "PATH_SHAPE_ONLY"
        except (OSError, RuntimeError):
            issues.append("EXECUTION_CLAIM_DB_PATH_UNRESOLVABLE")
            checks["claim_store_path"] = "UNRESOLVABLE"

    if not env.get("TOOBIT_API_KEY", "").strip():
        issues.append("TOOBIT_API_KEY_MISSING")
        checks["provider_credentials"] = "INCOMPLETE"
    elif not env.get("TOOBIT_API_SECRET", "").strip():
        issues.append("TOOBIT_API_SECRET_MISSING")
        checks["provider_credentials"] = "INCOMPLETE"
    else:
        checks["provider_credentials"] = "PRESENT_NOT_AUTHENTICATED"

    return {
        "schema_version": "arunda.execution_deployment_preflight.v1",
        "status": "CONFIGURATION_ISSUES_FOUND" if issues else "STATIC_CONFIGURATION_SHAPE_PASS",
        "issues": issues,
        "checks": checks,
        "authorization_granted": False,
        "provider_contacted": False,
        "database_written": False,
        "order_attempted": False,
        "meaning": "Static configuration inspection only; no policy, mandate, runtime, exchange, or order readiness is proven.",
    }


def main() -> int:
    import os

    database_path = os.environ.get("ARUNDA_PRODUCTION_DB_PATH", "").strip()
    if not database_path:
        result = {
            "schema_version": "arunda.execution_deployment_preflight.v1",
            "status": "CONFIGURATION_ISSUES_FOUND",
            "issues": ["ARUNDA_PRODUCTION_DB_PATH_MISSING"],
            "checks": {},
            "authorization_granted": False,
            "provider_contacted": False,
            "database_written": False,
            "order_attempted": False,
            "meaning": "Static configuration inspection only; no policy, mandate, runtime, exchange, or order readiness is proven.",
        }
    else:
        result = inspect_execution_deployment_config(production_database_path=database_path)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["status"] == "STATIC_CONFIGURATION_SHAPE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
