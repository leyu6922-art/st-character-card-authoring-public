from __future__ import annotations


def test_pipeline_audits_source_material_coverage_gate(load_script_module):
    pipeline = load_script_module("audit_skill_pipeline.py")

    assert "audit_source_material_coverage.py" in pipeline.DELIVERY_SCRIPTS
    assert "references/workflows/source-first-material-and-player-agency-contract.md" in pipeline.REQUIRED_REFERENCES
    assert "audit_source_material_coverage.py" in pipeline.REQUIRED_PIPELINE_TEXT
    assert "--source" in pipeline.REQUIRED_PIPELINE_TEXT
    assert "--source" in pipeline.REQUIRED_FINAL_FLAGS
    assert "--source-coverage-minimum" in pipeline.REQUIRED_FINAL_FLAGS
