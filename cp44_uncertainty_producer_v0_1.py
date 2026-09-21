"""CP44 Uncertainty Producer v0.1 — explicit-input, point-in-time boundary."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any,Mapping
FORBIDDEN={"outcome","future_outcome","label","future_label","realized_return","pnl","exit_price","post_outcome","calibrated_probability"}
@dataclass(frozen=True)
class UncertaintyObservation:
    asset:str
    uncertainty:float
    source:str
    observed_at:str
    provenance:str
    validation:str="VALID"
def build_uncertainty_observation(*, observation: Mapping[str,Any])->UncertaintyObservation:
    if not isinstance(observation,Mapping): raise ValueError("UNCERTAINTY_INPUT_MUST_BE_MAPPING")
    if {str(k).strip().lower() for k in observation}&FORBIDDEN: raise ValueError("FUTURE_OUTCOME_LEAKAGE_FORBIDDEN")
    required=("asset","uncertainty","source","observed_at","provenance")
    missing=[k for k in required if observation.get(k) is None]
    if missing: raise ValueError("MISSING_UNCERTAINTY_FIELDS:"+",".join(missing))
    try:
        uncertainty=float(observation["uncertainty"])
        if not math.isfinite(uncertainty) or not 0.0<=uncertainty<=1.0: raise ValueError
    except (TypeError,ValueError): raise ValueError("INVALID_UNCERTAINTY") from None
    return UncertaintyObservation(asset=str(observation["asset"]),uncertainty=uncertainty,source=str(observation["source"]),observed_at=str(observation["observed_at"]),provenance=str(observation["provenance"]))
def inspect_governance()->dict[str,Any]:
    return {"status":"EXPLICIT_INPUT_BOUNDARY","db_writes":0,"execution":False,"probability_created":False,"future_outcome_used":False,"implicit_mapping":False,"reliability_manufactured":False}
