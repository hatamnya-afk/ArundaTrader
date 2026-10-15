import json
import unittest
from unittest.mock import patch
from execution_runtime_policy_source_v0_1 import load_authoritative_execution_runtime_policy

class RuntimePolicyTests(unittest.TestCase):
    def test_missing_source_fails_closed(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "SOURCE_MISSING"):
                load_authoritative_execution_runtime_policy()
    def test_futures_requires_explicit_boolean(self):
        data={"policy_id":"p","policy_version":"v1","venue":"FUTURES","settlement_asset":"USDT","instrument_type":"PERPETUAL"}
        with patch.dict("os.environ", {"ARUNDA_EXECUTION_POLICY_JSON":json.dumps(data)}, clear=True):
            with self.assertRaisesRegex(ValueError, "EXPOSURE_PERMISSION_REQUIRED"):
                load_authoritative_execution_runtime_policy()
    def test_explicit_false_is_preserved(self):
        data={"policy_id":"p","policy_version":"v1","venue":"FUTURES","settlement_asset":"USDC","instrument_type":"PERPETUAL","futures_exposure_allowed":False}
        with patch.dict("os.environ", {"ARUNDA_EXECUTION_POLICY_JSON":json.dumps(data)}, clear=True):
            out=load_authoritative_execution_runtime_policy()
        self.assertIs(out["futures_exposure_allowed"], False)
        self.assertEqual(out["settlement_asset"], "USDC")

if __name__ == "__main__":
    unittest.main()
