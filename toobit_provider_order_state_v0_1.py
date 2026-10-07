"""ARUNDA TRADER — TOOBIT PROVIDER ORDER STATE PRODUCER v0.1

Authoritative read-only owner for CP46-A6 ProviderOrderState.

No order submission, cancellation, database write, retry, synthesis,
interpolation, or fallback is performed.
"""

from __future__ import annotations

from provider_preflight_v0_1 import ProviderOrderState


def build_toobit_provider_order_state(
    adapter,
    asset: str,
    *,
    venue: str = "SPOT",
) -> ProviderOrderState:
    """Build ProviderOrderState from Toobit's authenticated USER_DATA reads."""
    if adapter is None or not isinstance(asset, str) or not asset.strip():
        raise RuntimeError("Provider order-state input is invalid")

    if venue == "FUTURES":
        result = adapter.futures_duplicate_check(asset.strip().upper())
    else:
        result = adapter.duplicate_check(asset.strip().upper(), "LONG")
    if getattr(result, "allowed", False) is not True:
        raise RuntimeError(
            "Authoritative Toobit order state unavailable: "
            f"{getattr(result, 'reason', 'unknown')}"
        )

    data = getattr(result, "data", None)
    if not isinstance(data, dict) or data.get("state_known") is not True:
        raise RuntimeError("Authoritative provider order state is unknown")

    open_ids = data.get("open_order_client_ids")
    recent_ids = data.get("recent_order_client_ids")

    if not isinstance(open_ids, frozenset) or not isinstance(recent_ids, frozenset):
        raise RuntimeError("Provider order-state IDs are invalid")

    return ProviderOrderState(
        state_known=True,
        open_order_client_ids=open_ids,
        recent_order_client_ids=recent_ids,
    )