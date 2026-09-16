"""CP38-C — Smart Risk Engine deterministic and fail-closed tests."""
from smart_risk_engine_v0_1 import build_smart_risk

def obs():
    return {"asset":"BTC/USDT","direction":"LONG","entry_price":100.0,"stop_distance":2.0,"capital_state":"REAL_CAPITAL","portfolio_capital":10000.0,"usable_capital":10000.0,"allocated_risk":0.0,"concurrent_positions":0}

def policy():
    return {"policy_validation":"VALID","policy_version":"CP38-POLICY-0.1","risk_per_trade":0.005,"max_portfolio_risk":0.01,"max_concurrent_positions":2}

def test_calculation():
    r=build_smart_risk(obs(),policy()); assert r.risk_state=="APPROVED"; assert r.risk_budget==50.0; assert r.position_size==25.0; assert r.exposure==2500.0; assert r.remaining_portfolio_risk==100.0

def test_portfolio_cap():
    x=obs(); x["allocated_risk"]=80.0; r=build_smart_risk(x,policy()); assert r.risk_budget==20.0; assert r.position_size==10.0

def test_requires_real_capital():
    x=obs(); x["capital_state"]="UNAVAILABLE_CAPITAL"; r=build_smart_risk(x,policy()); assert r.risk_state=="BLOCKED"; assert r.reason=="REAL_CAPITAL_NOT_AVAILABLE"

def test_requires_valid_policy():
    p=policy(); p["policy_validation"]="UNVALIDATED"; r=build_smart_risk(obs(),p); assert r.reason=="RISK_POLICY_UNVALIDATED"

def test_requires_explicit_stop():
    x=obs(); x.pop("stop_distance"); r=build_smart_risk(x,policy()); assert r.reason=="STOP_DISTANCE_NOT_EXPLICIT"

def test_invalid_adjustment_blocks():
    x=obs(); x["liquidity_adjustment"]=1.5; r=build_smart_risk(x,policy()); assert r.reason=="LIQUIDITY_ADJUSTMENT_INVALID"

def test_adjustments_only_reduce_risk():
    x=obs(); x["correlation_adjustment"]=0.5; x["liquidity_adjustment"]=0.8; r=build_smart_risk(x,policy()); assert r.risk_budget==20.0

def test_position_limit():
    x=obs(); x["concurrent_positions"]=2; r=build_smart_risk(x,policy()); assert r.reason=="MAX_CONCURRENT_POSITIONS_REACHED"

def test_usable_capital_limit():
    x=obs(); x["usable_capital"]=10.0; r=build_smart_risk(x,policy()); assert r.reason=="USABLE_CAPITAL_EXCEEDED"

def test_no_execution_fields():
    r=build_smart_risk(obs(),policy()); assert not ({"order_intent","execution","exchange","order_id"} & set(vars(r)))
