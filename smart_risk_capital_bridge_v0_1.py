"""CP38-D provider-neutral bridge: RealCapitalObservation -> Smart Risk input."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from real_capital_observation_contract_v0_1 import RealCapitalObservation


def merge_real_capital_observation(
    observation: Mapping[str, Any],
    capital: RealCapitalObservation,
) -> dict[str, Any]:
    """Return a new Smart Risk observation carrying validated real capital.

    The bridge validates the production-capital contract and copies only its
    provider-neutral fields. It does not mutate the supplied observation or
    invoke runtime/API/database/execution surfaces.
    """
    if not isinstance(observation, Mapping):
        raise TypeError("observation must be a mapping")
    if not isinstance(capital, RealCapitalObservation):
        raise TypeError("capital must be RealCapitalObservation")

    capital.validate()
    merged = dict(observation)
    merged.update(asdict(capital))
    return merged


__all__ = ["merge_real_capital_observation"]
