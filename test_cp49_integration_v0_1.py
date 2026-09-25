from cp49_first_execution_contract_v0_1 import AttemptState, ExecutionSafetyGate
from cp49_autonomous_decision_boundary_v0_1 import AutonomousDecisionInput, build_autonomous_decision_boundary
from cp49_provider_preflight_v0_1 import ProviderPreflightEvidence, evaluate_provider_preflight
from cp49_execution_lifecycle_v0_1 import prepare_first_attempt, finalize_attempt


def decision():
    return AutonomousDecisionInput(
        "D1","S1",1000,900,"BTC/USDT","LONG",100,90,1.0,"RISK_POSITION_SIZE",
        "SPOT","I1",
        (("decision","D1"),("risk","R1"),("allocation","A1"),
         ("position_size","P1"),("quantity","RISK_POSITION_SIZE"))
    )


def intent():
    return build_autonomous_decision_boundary(decision()).order_intent


def evidence():
    return ProviderPreflightEvidence(
        "SPOT","BTC/USDT",True,True,True,True,True,True,True,True
    )


def safety(authorized=True):
    return ExecutionSafetyGate(authorized,True,False,True,True,True,False)


def test_autonomous_boundary_requires_upstream_provenance():
    d=decision()
    bad=AutonomousDecisionInput(**{**d.__dict__,"provenance":(("decision","D1"),)})
    assert build_autonomous_decision_boundary(bad).status=="BLOCK"


def test_autonomous_boundary_passes_canonical_data():
    r=build_autonomous_decision_boundary(decision())
    assert r.status=="PASS"
    assert r.order_intent is not None


def test_preflight_fails_closed_on_each_safety_condition():
    base=evidence()
    fields=("authenticated","account_state_fresh","symbol_valid","constraints_resolved",
            "balance_consistent","position_state_consistent","timestamp_valid","safety_consistent")
    for field in fields:
        bad=ProviderPreflightEvidence(
            **{**base.__dict__,field:False}
        )
        assert evaluate_provider_preflight(intent(),bad).status=="BLOCK"


def test_preflight_identity_mismatch_blocks():
    bad=ProviderPreflightEvidence("SPOT","ETH/USDT",True,True,True,True,True,True,True,True)
    assert evaluate_provider_preflight(intent(),bad).status=="BLOCK"


def test_prepare_requires_human_authorization():
    r=prepare_first_attempt(safety(False),intent(),evaluate_provider_preflight(intent(),evidence()),
                            attempt_id="A1",started_at_ms=1100)
    assert r.status is AttemptState.BLOCKED


def test_prepare_accepts_one_ready_attempt():
    r=prepare_first_attempt(safety(),intent(),evaluate_provider_preflight(intent(),evidence()),
                            attempt_id="A1",started_at_ms=1100)
    assert r.status is AttemptState.READY


def test_prepare_blocks_prior_attempt():
    s=ExecutionSafetyGate(True,True,True,True,True,True,False)
    r=prepare_first_attempt(s,intent(),evaluate_provider_preflight(intent(),evidence()),
                            attempt_id="A2",started_at_ms=1100)
    assert r.status is AttemptState.BLOCKED


def test_finalize_is_one_way():
    p=prepare_first_attempt(safety(),intent(),evaluate_provider_preflight(intent(),evidence()),
                            attempt_id="A1",started_at_ms=1100)
    r=finalize_attempt(p.attempt,decision_timestamp_ms=1000,knowledge_cutoff_ms=900,
                       execution_attempt_timestamp_ms=1101,snapshot_id="S1",
                       market="BTC/USDT",venue="SPOT",response_status="REJECTED",
                       outcome=AttemptState.REJECTED,latency_ms=20,request_id="REQ1",
                       rejection_code="INSUFFICIENT_BALANCE")
    assert r.status is AttemptState.REJECTED
    again=finalize_attempt(r.attempt,decision_timestamp_ms=1000,knowledge_cutoff_ms=900,
                       execution_attempt_timestamp_ms=1101,snapshot_id="S1",
                       market="BTC/USDT",venue="SPOT",response_status="REJECTED",
                       outcome=AttemptState.REJECTED,latency_ms=20,request_id="REQ1")
    assert again.status is AttemptState.BLOCKED


def test_finalize_preserves_time_separation():
    p=prepare_first_attempt(safety(),intent(),evaluate_provider_preflight(intent(),evidence()),
                            attempt_id="A1",started_at_ms=1100)
    r=finalize_attempt(p.attempt,decision_timestamp_ms=1000,knowledge_cutoff_ms=900,
                       execution_attempt_timestamp_ms=1101,snapshot_id="S1",
                       market="BTC/USDT",venue="SPOT",response_status="ACCEPTED",
                       outcome=AttemptState.ACCEPTED,latency_ms=20,request_id="REQ1")
    assert r.observation.knowledge_cutoff_ms==900
    assert r.observation.execution_attempt_timestamp_ms==1101
