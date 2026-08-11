from __future__ import annotations

import json

import pytest


def _pass(gate, name: str):
    return gate.GateResult(name, "PASS")


def _minimal_card(path):
    path.write_text('{"data":{"character_book":{"entries":[]}}}', encoding="utf-8")


def test_final_delivery_gate_exposes_repeatable_canonical_sources(load_script_module):
    gate = load_script_module("final_delivery_gate.py")
    option_strings = {
        option
        for action in gate.build_parser()._actions
        for option in action.option_strings
    }

    assert "--source" in option_strings
    assert "--source-coverage-minimum" in option_strings


def test_final_delivery_gate_blocks_when_explicit_source_coverage_fails(load_script_module, tmp_path, monkeypatch):
    gate = load_script_module("final_delivery_gate.py")
    card = tmp_path / "candidate.json"
    source = tmp_path / "chapter-01.txt"
    _minimal_card(card)
    source.write_text("canonical source", encoding="utf-8")

    monkeypatch.setattr(gate, "run_validate", lambda _path: _pass(gate, "validate"))
    monkeypatch.setattr(gate, "run_player_agency_modes", lambda *_args, **_kwargs: _pass(gate, "agency"))
    monkeypatch.setattr(gate, "run_audit", lambda *_args: _pass(gate, "trigger"))
    monkeypatch.setattr(gate, "run_enrichment", lambda *_args: _pass(gate, "enrichment"))
    monkeypatch.setattr(gate, "run_build_sync", lambda *_args: _pass(gate, "build"))
    monkeypatch.setattr(gate, "scan_forbidden", lambda *_args, **_kwargs: _pass(gate, "scan"))
    monkeypatch.setattr(
        gate,
        "run_source_material_coverage",
        lambda _card, _sources, _minimum: gate.GateResult(
            "audit_source_material_coverage.py", "FAIL", ["coverage=50.0% < minimum=60.0%"]
        ),
    )

    report = tmp_path / "delivery.md"
    assert gate.main([
        str(card), "--source", str(source), "--source-coverage-minimum", "0.60", "-o", str(report),
    ]) == 1
    assert "audit_source_material_coverage.py | FAIL" in report.read_text(encoding="utf-8")


def test_final_delivery_gate_rejects_coverage_threshold_without_sources(load_script_module, tmp_path):
    gate = load_script_module("final_delivery_gate.py")
    card = tmp_path / "candidate.json"
    _minimal_card(card)

    with pytest.raises(SystemExit) as exc:
        gate.main([str(card), "--source-coverage-minimum", "0.80"])
    assert exc.value.code == 4


def test_final_delivery_source_coverage_uses_real_source_auditor(load_script_module, tmp_path):
    gate = load_script_module("final_delivery_gate.py")
    card = tmp_path / "candidate.json"
    source = tmp_path / "chapter-01.txt"
    excerpt = "她把银杯放回桌面窗外的雨声压住了脚步声随后抬眼看向来人"
    card.write_text(
        json.dumps({
            "data": {
                "character_book": {
                    "entries": [{
                        "id": 7,
                        "comment": "角色档案",
                        "content": excerpt,
                        "enabled": True,
                        "constant": False,
                        "extensions": {"entry_role": "common_content"},
                    }]
                }
            }
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    source.write_text("前文。" + excerpt + "。后文。", encoding="utf-8")

    passed = gate.run_source_material_coverage(card, [source], 0.60)
    failed = gate.run_source_material_coverage(card, [tmp_path / "missing.txt"], 0.60)

    assert passed.status == "PASS"
    assert any("eligible=1 matched=1 coverage=100.0%" in note for note in passed.notes)
    assert failed.status == "FAIL"
    assert "canonical source file not found" in failed.errors[0]
