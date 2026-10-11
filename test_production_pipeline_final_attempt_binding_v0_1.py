from pathlib import Path


def test_production_pipeline_imports_and_calls_final_attempt_dispatcher():
    source = Path(__file__).with_name("arunda_pipeline.py").read_text(
        encoding="utf-8-sig"
    )
    assert (
        "from production_final_execution_attempt_dispatch_v0_1 "
        "import dispatch_final_execution_attempt"
    ) in source

    start = source.index("def verify_execution_boundary_integration(")
    end = source.index("\ndef assert_no_execution_boundary(", start)
    function_source = source[start:end]

    assert "dispatch_final_execution_attempt(" in function_source
    assert "execution_enabled=EXECUTION_ENABLED" in function_source
    assert 'final_attempt_result.error_code != "EXECUTION_DISABLED"' in function_source
    assert 'return "VERIFIED_BLOCKED"' in function_source
