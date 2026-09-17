
"""
ARUNDA CONTEXT GOVERNOR v0.1
Deterministic Builder governance gate.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple
import json


class Decision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REDIRECT = "REDIRECT"


class StageStatus(str, Enum):
    BUILT = "BUILT"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"
    CURRENT_FRONTIER = "CURRENT_FRONTIER"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class ArtifactStatus(str, Enum):
    CANONICAL = "CANONICAL"
    VERIFIED = "VERIFIED"
    WRONG_ARTIFACT = "WRONG_ARTIFACT"
    LEGACY = "LEGACY"
    NON_PRODUCTION = "NON_PRODUCTION"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Stage:
    name: str
    status: StageStatus
    notes: str = ""


@dataclass(frozen=True)
class Artifact:
    name: str
    status: ArtifactStatus
    notes: str = ""


@dataclass(frozen=True)
class Contract:
    name: str
    rule: str
    enforced: bool = True


@dataclass(frozen=True)
class ProjectContext:
    project: str
    current_frontier: str
    stages: Tuple[Stage, ...] = ()
    artifacts: Tuple[Artifact, ...] = ()
    contracts: Tuple[Contract, ...] = ()
    version: str = "ARUNDA_CONTEXT_v0.1"


@dataclass(frozen=True)
class ProposedAction:
    action: str
    target: str = ""
    description: str = ""
    writes_production_db: bool = False
    uses_synthetic_data: bool = False
    rebuild: bool = False
    redesign: bool = False
    reset: bool = False
    re_audit: bool = False
    requested_frontier: str = ""


@dataclass(frozen=True)
class GovernanceResult:
    decision: Decision
    reason: str
    required_evidence: str
    next_action: str


class ArundaContextGovernor:

    def __init__(self, context: ProjectContext):
        self.context = context

    @staticmethod
    def _norm(value: str) -> str:
        return " ".join(value.upper().strip().split())

    def _find_stage(self, target: str):
        normalized = self._norm(target)

        for stage in self.context.stages:
            if self._norm(stage.name) == normalized:
                return stage

        return None

    def _find_artifact(self, target: str):
        normalized = self._norm(target)

        for artifact in self.context.artifacts:
            if self._norm(artifact.name) == normalized:
                return artifact

        return None

    def evaluate(self, proposal: ProposedAction) -> GovernanceResult:

        action = self._norm(proposal.action)
        target = self._norm(proposal.target)

        # ============================================================
        # HARD SAFETY
        # ============================================================

        if proposal.uses_synthetic_data:
            return GovernanceResult(
                decision=Decision.BLOCK,
                reason="Synthetic data is forbidden.",
                required_evidence="Real production data source.",
                next_action="Remove synthetic data."
            )

        if proposal.reset:
            return GovernanceResult(
                decision=Decision.BLOCK,
                reason="Project reset is forbidden.",
                required_evidence="Explicit project-level authorization.",
                next_action="Continue from the current frontier."
            )

        if proposal.writes_production_db:
            return GovernanceResult(
                decision=Decision.BLOCK,
                reason="Production DB write detected.",
                required_evidence=(
                    "Explicit production-write contract and boundary."
                ),
                next_action=(
                    "Move the operation behind an approved "
                    "production boundary."
                )
            )

        # ============================================================
        # CLOSED / VERIFIED STAGE PROTECTION
        # ============================================================

        stage = self._find_stage(target)

        if stage is not None:

            protected = (
                StageStatus.CLOSED,
                StageStatus.VERIFIED,
            )

            if stage.status in protected:

                if proposal.rebuild:
                    return GovernanceResult(
                        decision=Decision.BLOCK,
                        reason=(
                            f"Target stage is {stage.status.value}. "
                            "Rebuild prohibited."
                        ),
                        required_evidence=(
                            "Concrete regression evidence invalidating "
                            "the existing verification."
                        ),
                        next_action=(
                            "Do not rebuild the closed/verified stage."
                        )
                    )

                if proposal.redesign:
                    return GovernanceResult(
                        decision=Decision.BLOCK,
                        reason=(
                            f"Target stage is {stage.status.value}. "
                            "Redesign prohibited."
                        ),
                        required_evidence=(
                            "Concrete regression evidence invalidating "
                            "the current architecture."
                        ),
                        next_action=(
                            "Continue from the current frontier."
                        )
                    )

                if proposal.re_audit:
                    return GovernanceResult(
                        decision=Decision.BLOCK,
                        reason=(
                            f"Target stage is {stage.status.value}. "
                            "Re-audit prohibited."
                        ),
                        required_evidence=(
                            "Concrete regression evidence."
                        ),
                        next_action=(
                            "Do not reopen the closed stage."
                        )
                    )

        # ============================================================
        # ARTIFACT PROTECTION
        # ============================================================

        artifact = self._find_artifact(target)

        if artifact is not None:

            if artifact.status == ArtifactStatus.WRONG_ARTIFACT:
                return GovernanceResult(
                    decision=Decision.BLOCK,
                    reason=(
                        "Target artifact is registered as "
                        "WRONG_ARTIFACT."
                    ),
                    required_evidence=(
                        "Evidence that changes its artifact status."
                    ),
                    next_action=(
                        "Do not use this artifact as canonical."
                    )
                )

            if artifact.status == ArtifactStatus.NON_PRODUCTION:
                return GovernanceResult(
                    decision=Decision.BLOCK,
                    reason=(
                        "Target artifact is NON_PRODUCTION."
                    ),
                    required_evidence=(
                        "Explicit production-boundary authorization."
                    ),
                    next_action=(
                        "Keep the artifact outside production execution."
                    )
                )

            if artifact.status == ArtifactStatus.LEGACY:
                return GovernanceResult(
                    decision=Decision.BLOCK,
                    reason=(
                        "Target artifact is LEGACY."
                    ),
                    required_evidence=(
                        "Explicit evidence that it is current canonical."
                    ),
                    next_action=(
                        "Do not propagate legacy code/data."
                    )
                )

        # ============================================================
        # FRONTIER PROTECTION
        # ============================================================

        frontier = self._norm(
            self.context.current_frontier
        )

        if proposal.requested_frontier:

            requested = self._norm(
                proposal.requested_frontier
            )

            if requested != frontier:
                return GovernanceResult(
                    decision=Decision.REDIRECT,
                    reason=(
                        "Requested frontier differs from the "
                        "registered current frontier."
                    ),
                    required_evidence=(
                        "Explicit ledger update changing "
                        "the current frontier."
                    ),
                    next_action=(
                        "Return to current frontier: "
                        f"{self.context.current_frontier}"
                    )
                )

        # ============================================================
        # FORBIDDEN OPERATION DETECTION
        # ============================================================

        forbidden = (
            "REBUILD",
            "REDESIGN",
            "RE-AUDIT",
            "REAUDIT",
        )

        text = self._norm(
            f"{action} {proposal.description} {proposal.target}"
        )

        for word in forbidden:

            if word in text:
                return GovernanceResult(
                    decision=Decision.BLOCK,
                    reason=(
                        f"Forbidden operation detected: {word}"
                    ),
                    required_evidence=(
                        "Concrete regression evidence or "
                        "explicit authorized exception."
                    ),
                    next_action=(
                        "Continue from current frontier: "
                        f"{self.context.current_frontier}"
                    )
                )

        # ============================================================
        # FRONTIER MATCH
        # ============================================================

        if target == frontier:
            return GovernanceResult(
                decision=Decision.ALLOW,
                reason=(
                    "Target matches current project frontier."
                ),
                required_evidence="Normal execution evidence.",
                next_action=(
                    "Execute within the registered contracts."
                )
            )

        # ============================================================
        # DEFAULT ALLOW
        # ============================================================

        return GovernanceResult(
            decision=Decision.ALLOW,
            reason="No governance violation detected.",
            required_evidence=(
                "Maintain all registered contracts and boundaries."
            ),
            next_action=(
                "Remain aligned with: "
                f"{self.context.current_frontier}"
            )
        )

    def explain(self, proposal: ProposedAction) -> dict:

        result = self.evaluate(proposal)

        return {
            "context_version": self.context.version,
            "project": self.context.project,
            "current_frontier": self.context.current_frontier,
            "decision": result.decision.value,
            "reason": result.reason,
            "required_evidence": result.required_evidence,
            "next_action": result.next_action,
        }


# =================================================================
# ARUNDA TRADER CONTEXT
# =================================================================

ARUNDA_CONTEXT = ProjectContext(

    project="ArundaTrader",

    current_frontier=(
        "LAUNCH_DATA_BOUNDARY + "
        "ROLLING_HISTORICAL_CONTEXT_CONTRACT"
    ),

    stages=(

        Stage(
            name="SIGNAL_LAYER",
            status=StageStatus.CLOSED,
            notes="Signal Logic and Signal Engine verified."
        ),

        Stage(
            name="FUSION_RUNTIME",
            status=StageStatus.CLOSED,
            notes="FUSION_v0.5 runtime forensic chain verified."
        ),

        Stage(
            name="FIND_FUTURE_PRICE_FORENSIC",
            status=StageStatus.CLOSED,
            notes="Runtime boundary and tolerance chain verified."
        ),

        Stage(
            name="LIVE_SIGNAL_ORDER_INTENT_RELEASE_PREFLIGHT",
            status=StageStatus.VERIFIED,
            notes="READY_NO_ORDER_INTENTS."
        ),

        Stage(
            name=(
                "LAUNCH_DATA_BOUNDARY + "
                "ROLLING_HISTORICAL_CONTEXT_CONTRACT"
            ),
            status=StageStatus.CURRENT_FRONTIER,
            notes="Active project frontier."
        ),
    ),

    artifacts=(

        Artifact(
            name="runtime_feature_producer.py",
            status=ArtifactStatus.UNKNOWN,
            notes=(
                "Original runtime producer has not been recovered."
            )
        ),

        Artifact(
            name="real_score_producer.py",
            status=ArtifactStatus.WRONG_ARTIFACT,
            notes=(
                "Must not be treated as original "
                "runtime_feature_producer."
            )
        ),

        Artifact(
            name="market_technical",
            status=ArtifactStatus.NON_PRODUCTION,
            notes=(
                "Legacy/test data. Must not influence "
                "production signals."
            )
        ),
    ),

    contracts=(

        Contract(
            name="NO_SYNTHETIC_DATA",
            rule="Production data must be real."
        ),

        Contract(
            name="NO_INTERPOLATION",
            rule="No interpolation."
        ),

        Contract(
            name="NO_FORWARD_BACK_FILL",
            rule="No forward-fill or back-fill."
        ),

        Contract(
            name="NO_PADDING",
            rule="No padding."
        ),

        Contract(
            name="NO_BLENDING",
            rule="One candle = one source."
        ),

        Contract(
            name="PROVENANCE_REQUIRED",
            rule=(
                "Every production market datum requires provenance."
            )
        ),

        Contract(
            name="FAIL_CLOSED",
            rule=(
                "Missing or invalid required data must fail closed."
            )
        ),

        Contract(
            name="LEGACY_DATA_EXCLUDED",
            rule=(
                "Legacy market_technical data is non-production."
            )
        ),
    ],
)


# =================================================================
# BUILDER GATE
# =================================================================

_MANAGER = ArundaContextGovernor(ARUNDA_CONTEXT)


def authorize_builder_action(
    action: str,
    target: str = "",
    description: str = "",
    **flags
) -> dict:

    proposal = ProposedAction(
        action=action,
        target=target,
        description=description,
        **flags
    )

    return _MANAGER.explain(proposal)


def builder_gate(
    action: str,
    target: str = "",
    description: str = "",
    **flags
) -> bool:

    result = authorize_builder_action(
        action=action,
        target=target,
        description=description,
        **flags
    )

    return result["decision"] == Decision.ALLOW.value


# =================================================================
# SELF TEST
# =================================================================

if __name__ == "__main__":

    tests = [
        ProposedAction(
            action="BUILD",
            target=(
                "LAUNCH_DATA_BOUNDARY + "
                "ROLLING_HISTORICAL_CONTEXT_CONTRACT"
            ),
        ),

        ProposedAction(
            action="REBUILD",
            target="SIGNAL_LAYER",
            rebuild=True,
        ),

        ProposedAction(
            action="REDESIGN",
            target="FUSION_RUNTIME",
            redesign=True,
        ),

        ProposedAction(
            action="USE",
            target="real_score_producer.py",
        ),

        ProposedAction(
            action="BUILD",
            target="MARKET DATA",
            uses_synthetic_data=True,
        ),

        ProposedAction(
            action="BUILD",
            target="NEW MODULE",
            writes_production_db=True,
        ),
    ]

    print()
    print("ARUNDA CONTEXT GOVERNOR v0.1")
    print("=" * 72)

    for index, proposal in enumerate(tests, start=1):

        result = _MANAGER.explain(proposal)

        print()
        print(f"TEST {index}")
        print("-" * 72)
        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            )
        )

    print()
    print("=" * 72)
    print("SELF-TEST COMPLETE")