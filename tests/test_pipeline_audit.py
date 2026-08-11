from __future__ import annotations


def test_pipeline_audit_requires_v52_regression_assets(load_script_module, skill_root):
    audit_module = load_script_module("audit_skill_pipeline.py")
    result = audit_module.audit(skill_root)

    assert not result.errors
    required_notes = {
        "script exists: scripts/atomic_write_json.py",
        "script exists: scripts/audit_greeting_build_wiring.py",
        "Greeting build-wiring regression tests exist: tests/test_greeting_build_wiring.py",
        "script exists: scripts/migrate_card.py",
        "v5.2 workflow reference exists: references/workflows/v5.2-validation-and-migration.md",
        "v5.2 regression workflow exists: .github/workflows/test.yml",
        "v5.2 fixture exists: tests/fixtures/valid_ccv3_core_minimal.json",
        "manifest template parses as JSON and passes runner schema validation",
        "manifest runner dry-run PASS: template → run_delivery.py → effective plan",
        "canonical build fixture assembly sync PASS: assemble_card.py → build sync",
    }
    assert required_notes.issubset(set(result.notes))
