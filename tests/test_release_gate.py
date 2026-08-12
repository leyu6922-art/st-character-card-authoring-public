import json
from pathlib import Path

from scripts.release_gate import evaluate_manifest_contract, verify_external_head


ROOT = Path(__file__).resolve().parents[1]


def test_release_gate_manifest_contract_is_self_consistent():
    result = evaluate_manifest_contract(ROOT)
    assert result["errors"] == []
    assert "exact_head_github_actions" in result["required_release_gates"]
    assert result["external_release_gates"] == ["exact_head_github_actions"]


def test_release_gate_external_identity_is_explicitly_pending_locally():
    result = verify_external_head(ROOT, env={"GITHUB_ACTIONS": "false"})
    assert result["status"] == "EXTERNAL_REQUIRED"
    assert result["expected_sha"] is None
    assert result["actual_sha"] is None


def test_release_gate_version_split_is_machine_checked():
    manifest = json.loads((ROOT / "public-export-manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifact_profile"] == "workflow-distribution"
    assert manifest["artifact_release_line"] == manifest["release_line"]
    assert manifest["strict_core_release_line"] != manifest["artifact_release_line"]
    assert manifest["release_gate_runner"] == "scripts/release_gate.py"
