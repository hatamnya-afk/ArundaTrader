from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from standing_mandate_lifecycle_store_v0_1 import read_lifecycle_events

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ops" / "Activate-ArundaStandingMandate.py"


def _decision_file(path):
    path.write_text(
        json.dumps(
            {
                "management_observation": {
                    "decision": "AUTHORIZED",
                    "mandate_id": "MANAGEMENT_PHASE_ENTRY_DECISION_20261012",
                    "authorized_by": "Project owner / Management",
                    "authorization_source": "MANAGEMENT_PHASE_ENTRY_DECISION_20261012.md",
                    "environment": "REAL_PRODUCTION",
                    "provider": "TOOBIT",
                    "capital_policy": "ZERO_INITIAL_CAPITAL",
                    "allowed_markets": ["SPOT", "FUTURES"],
                    "evidence_required_before": [
                        "Current execution-ready package and readiness validation",
                        "Active durable standing-mandate lifecycle",
                    ],
                    "evidence_required_after": [
                        "Provider outcome evidence",
                        "Append-only execution outcome record",
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def _run(decision, journal, *extra):
    env = os.environ.copy()
    env["ARUNDA_MANDATE_LIFECYCLE_PATH"] = str(journal)
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--decision-json",
            str(decision),
            *extra,
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_activation_cli_defaults_to_read_only_dry_run(tmp_path):
    decision = _decision_file(tmp_path / "decision.json")
    journal = tmp_path / "mandate.jsonl"

    result = _run(decision, journal)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "MANDATE_ACTIVATION=VALIDATED_DRY_RUN" in result.stdout
    assert not journal.exists()


def test_activation_cli_persists_only_after_explicit_confirmation(tmp_path):
    decision = _decision_file(tmp_path / "decision.json")
    journal = tmp_path / "mandate.jsonl"

    result = _run(decision, journal, "--confirm-activate")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "MANDATE_ACTIVATION=PASS" in result.stdout
    events = read_lifecycle_events(journal)
    assert len(events) == 1
    assert events[0]["event_type"] == "ACTIVATE"
    assert events[0]["mandate_id"] == "MANAGEMENT_PHASE_ENTRY_DECISION_20261012"


def test_activation_cli_rejects_non_authorized_decision_without_journal_write(tmp_path):
    decision = _decision_file(tmp_path / "decision.json")
    payload = json.loads(decision.read_text(encoding="utf-8"))
    payload["management_observation"]["decision"] = "DEFERRED"
    decision.write_text(json.dumps(payload), encoding="utf-8")
    journal = tmp_path / "mandate.jsonl"

    result = _run(decision, journal, "--confirm-activate")

    assert result.returncode == 2
    assert "MANAGEMENT_PHASE_ENTRY_NOT_AUTHORIZED" in result.stdout
    assert not journal.exists()
