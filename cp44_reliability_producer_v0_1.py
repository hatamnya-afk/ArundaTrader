"""CP44 Reliability Producer v0.1 — explicit-input, point-in-time quality boundary."""
from __future__ import annotations
import math
from typing import Any,Mapping
from cp44_reliability_uncertainty_contract_v0_1 import ReliabilityUncertainty
FORBIDDEN={"outcome","future_outcome","label","future_label","realized_return","pnl","exit_price","post_outcome","calibrated_probability"}
def build_reliability_observation(*, observation: Mapping[str,Any])->ReliabilityUncertainty:
    if not isinstance(observation,Mapping): raise ValueError("RELIABILITY_INPUT_MUST_BE_MAPPING")
    if {str(k).strip().lower() for k in observation}&FORBIDDEN: raise ValueError("FUTURE_OUTCOME_LEAKAGE_FORBIDDEN")
    required=("asset","reliability","uncertainty","source","observed_at","provenance")
    missing=[k for k in required if observation.get(k) is None]
    if missing: raise ValueError("MISSING_RELIABILITY_FIELDS:"+",".join(missing))
    values={}
    for field in ("reliability","uncertainty"):
        try:
            value=float(observation[field])
            if not math.isfinite(value) or not 0.0<=value<=1.0: raise ValueError
            values[field]=value
        except (TypeError,ValueError): raise ValueError("INVALID_"+field.upper()) from None
    return ReliabilityUncertainty(asset=str(observation["asset"]),reliability=values["reliability"],uncertainty=values["uncertainty"],source=str(observation["source"]),observed_at=str(observation["observed_at"]),provenance=str(observation["provenance"]),validation="VALID")
def inspect_governance()->dict[str,Any]:
    return {"status":"EXPLICIT_INPUT_BOUNDARY","db_writes":0,"execution":False,"probability_created":False,"future_outcome_used":False,"implicit_mapping":False}
