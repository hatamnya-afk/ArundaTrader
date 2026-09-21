"""CP44 Predictive Evidence Producer v0.1 — explicit-input, point-in-time boundary."""
from __future__ import annotations
import math
from typing import Any, Mapping
from cp44_predictive_evidence_contract_v0_1 import PredictiveEvidence
FORBIDDEN={"outcome","future_outcome","label","future_label","realized_return","pnl","exit_price","post_outcome","calibrated_probability"}
def build_predictive_evidence(*, observation: Mapping[str,Any])->PredictiveEvidence:
    if not isinstance(observation,Mapping): raise ValueError("EVIDENCE_INPUT_MUST_BE_MAPPING")
    if {str(k).strip().lower() for k in observation}&FORBIDDEN: raise ValueError("FUTURE_OUTCOME_LEAKAGE_FORBIDDEN")
    required=("asset","direction","evidence","source","observed_at","provenance")
    missing=[k for k in required if observation.get(k) is None]
    if missing: raise ValueError("MISSING_EVIDENCE_FIELDS:"+",".join(missing))
    direction=str(observation["direction"]).upper()
    if direction not in {"LONG","SHORT"}: raise ValueError("INVALID_DIRECTION")
    try:
        evidence=float(observation["evidence"])
        if not math.isfinite(evidence): raise ValueError
    except (TypeError,ValueError): raise ValueError("INVALID_EVIDENCE") from None
    return PredictiveEvidence(asset=str(observation["asset"]),direction=direction,evidence=evidence,source=str(observation["source"]),observed_at=str(observation["observed_at"]),provenance=str(observation["provenance"]),validation="VALID")
def inspect_governance()->dict[str,Any]:
    return {"status":"EXPLICIT_INPUT_BOUNDARY","db_writes":0,"execution":False,"probability_created":False,"future_outcome_used":False,"score_reinterpreted":False}
