import json
from pathlib import Path

from scripts.audit_docs import audit_docs
from scripts.audit_public_release import audit_tree
from scripts.doctor import inspect_environment


ROOT = Path(__file__).resolve().parents[1]


def test_public_contract_manifests_parse_and_point_to_each_other():
    export_manifest = json.loads((ROOT / "public-export-manifest.json").read_text(encoding="utf-8"))
    skill_manifest = json.loads((ROOT / "skill-manifest.json").read_text(encoding="utf-8"))
    assert export_manifest["contract_sources"]["skill_capability_manifest"] == "skill-manifest.json"
    assert skill_manifest["single_source_policy"]["public_export_scope_and_redaction"] == "public-export-manifest.json"
    assert skill_manifest["status"] == "candidate"
    assert skill_manifest["release_version"] == "0.1.0"
    assert skill_manifest["capability_level"] == "L2"
    assert skill_manifest["distribution"]["profile"] == "leyu-workflow"
    profiles = skill_manifest["profiles"]
    assert profiles["leyu-workflow"]["kind"] == "opinionated_personal_workflow"
    assert profiles["leyu-workflow"]["status"] == "existing"
    assert "authoring_workflow" in profiles["leyu-workflow"]["default_for"]
    assert profiles["leyu-production"]["kind"] == "validation_profile"
    assert profiles["leyu-production"]["status"] == "existing"
    assert "alias_of" not in profiles["leyu-production"]
    capabilities = skill_manifest["capabilities"]
    assert isinstance(capabilities, dict)
    assert capabilities["core_validation"]["level"] == "L1"
    assert capabilities["core_validation"]["status"] == "available"
    assert capabilities["release_export"]["status"] == "available"
    assert capabilities["authoring_workflow"]["status"] == "available"
    assert capabilities["authoring_workflow"]["workflow_kind"] == "opinionated_personal_workflow"
    assert capabilities["authoring_workflow"]["profile"] == "leyu-workflow"
    assert capabilities["authoring_workflow"]["bundled"] is True
    assert capabilities["authoring_workflow"]["evidence_level"] == "STATIC_VERIFIED"
    assert capabilities["native_stage_routing"]["status"] == "optional_dependency"
    assert capabilities["runtime_stack"]["status"] == "not_configured"
    export_manifest = json.loads((ROOT / "public-export-manifest.json").read_text(encoding="utf-8"))
    assert export_manifest["public_repository"] == "st-character-card-authoring-public"
    assert export_manifest["release_line"] == "v0.1.0"
    assert export_manifest["product_kind"] == "opinionated_personal_workflow"
    assert export_manifest["artifact_profile"] == "workflow-distribution"
    assert export_manifest["artifact_release_line"] == export_manifest["release_line"]
    assert export_manifest["strict_core_release_line"] == "v0.1.0-public-readiness-core-rc2"
    assert export_manifest["release_gate_runner"] == "scripts/release_gate.py"
    assert export_manifest["external_release_gates"] == ["exact_head_github_actions"]
    assert "references/**" in export_manifest["source_scope"]["include"]
    assert "templates/**" in export_manifest["source_scope"]["include"]
    assert "tests/**" in export_manifest["source_scope"]["include"]
    assert "release/public-core/**" in export_manifest["source_scope"]["exclude"]
    assert "references/**" not in export_manifest["source_scope"]["exclude"]
    assert "templates/**" not in export_manifest["source_scope"]["exclude"]
    assert "workflow-provenance-manifest.json" in export_manifest["source_scope"]["include"]
    assert export_manifest["artifact_release_line"] == export_manifest["release_line"]
    assert export_manifest["strict_core_release_line"] != export_manifest["artifact_release_line"]


def test_skill_frontmatter_declares_the_host_dependency_without_optional_sibling_claims():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]
    assert "version: '0.1.0'" in frontmatter
    assert "dependencies:" in frontmatter
    assert "- hermes-agent" in frontmatter
    assert "dependencies: []" not in frontmatter


def test_doc_audit_reports_missing_relative_reference(tmp_path):
    (tmp_path / "README.md").write_text("See `references/missing-contract.md`.\n", encoding="utf-8")
    result = audit_docs(tmp_path)
    assert any(issue["code"] == "DOC_LINK_MISSING" for issue in result["issues"])


def test_doc_audit_accepts_existing_relative_reference(tmp_path):
    (tmp_path / "README.md").write_text("See `references/contract.md`.\n", encoding="utf-8")
    (tmp_path / "references").mkdir()
    (tmp_path / "references/contract.md").write_text("ok\n", encoding="utf-8")
    result = audit_docs(tmp_path)
    assert result["errors"] == 0


def test_doc_audit_ignores_glob_and_regex_examples(tmp_path):
    (tmp_path / "README.md").write_text("Use `scripts/*.py`, `templates/semantic-*-v1.md`, and `.{4,100}`.\n", encoding="utf-8")
    result = audit_docs(tmp_path)
    assert result["errors"] == 0


def test_doc_audit_classifies_known_sibling_reference_as_warning(tmp_path):
    (tmp_path / "README.md").write_text("See `scripts/audit_native_stage_architecture.py`.\n", encoding="utf-8")
    result = audit_docs(tmp_path)
    assert result["errors"] == 0
    assert result["warnings"][0]["code"] == "DOC_LINK_SIBLING_REFERENCE"


def test_public_audit_rejects_private_path_and_missing_license(tmp_path):
    private_path = "C:" + chr(92) + "Users" + chr(92) + "alice" + chr(92) + "card.json"
    (tmp_path / "README.md").write_text(f"private path {private_path}\n", encoding="utf-8")
    (tmp_path / "SKILL.md").write_text("public skill\n", encoding="utf-8")
    result = audit_tree(tmp_path)
    codes = {issue["code"] for issue in result["issues"]}
    assert "PRIVATE_PATH" in codes
    assert "LICENSE_MISSING" in codes


def test_public_audit_distinguishes_source_and_artifact_modes(tmp_path):
    (tmp_path / "README.md").write_text("internal path C:" + chr(92) + "Users" + chr(92) + "owner\n", encoding="utf-8")
    (tmp_path / "SKILL.md").write_text("internal\n", encoding="utf-8")

    source_result = audit_tree(tmp_path, audit_kind="source")
    artifact_result = audit_tree(tmp_path, audit_kind="artifact")

    assert source_result["release_blocking"] is False
    assert artifact_result["release_blocking"] is True
    assert source_result["errors"] == artifact_result["errors"]


def test_public_audit_requires_resolved_provenance_when_requested(tmp_path):
    required = ("README.md", "SKILL.md", "LICENSE", "skill-manifest.json", "public-export-manifest.json")
    for name in required:
        (tmp_path / name).write_text("{}\n" if name.endswith(".json") else "public\n", encoding="utf-8")
    provenance = tmp_path / "provenance.json"

    missing = audit_tree(tmp_path, provenance_manifest=provenance, require_provenance=True)
    assert any(item["code"] == "PROVENANCE_MANIFEST_MISSING" for item in missing["issues"])

    provenance.write_text(json.dumps({
        "schema_version": 1,
        "manifest_kind": "provenance",
        "files": {
            name: {"origin": "original", "redistribution": "allowed", "review_status": "resolved"}
            for name in required
        },
    }), encoding="utf-8")
    resolved = audit_tree(tmp_path, provenance_manifest=provenance, require_provenance=True)
    assert not any(item["code"].startswith("PROVENANCE_") for item in resolved["issues"])


def test_public_audit_accepts_minimal_clean_tree(tmp_path):
    for name in ("README.md", "SKILL.md", "LICENSE", "skill-manifest.json", "public-export-manifest.json"):
        (tmp_path / name).write_text("{}\n" if name.endswith(".json") else "public\n", encoding="utf-8")
    result = audit_tree(tmp_path)
    assert result["errors"] == 0


def test_public_audit_does_not_flag_its_own_policy_patterns(tmp_path):
    for name in ("README.md", "SKILL.md", "LICENSE"):
        (tmp_path / name).write_text("public\n", encoding="utf-8")
    (tmp_path / "skill-manifest.json").write_text("{}\n", encoding="utf-8")
    policy_path = "C:" + chr(92) + "Users" + chr(92) + "<name>"
    (tmp_path / "public-export-manifest.json").write_text(json.dumps({"private_path_pattern": policy_path}) + "\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/audit_public_release.py").write_text("D:" + chr(92) + "hermes and BEGIN " + "PRIVATE KEY\n", encoding="utf-8")
    result = audit_tree(tmp_path)
    assert result["errors"] == 0


def test_doctor_reports_core_level_without_optional_siblings(tmp_path):
    for directory in ("scripts", "templates", "tests"):
        (tmp_path / directory).mkdir()
    for name in ("SKILL.md", "README.md", "skill-manifest.json", "public-export-manifest.json"):
        (tmp_path / name).write_text("{}\n" if name.endswith(".json") else "public\n", encoding="utf-8")
    result = inspect_environment(tmp_path, run_tests=False, hermes_home=tmp_path / "missing-hermes")
    assert result["capability_level"] == "L1"
    assert result["checks"]["native_stage_routing"]["status"] == "MISSING"
