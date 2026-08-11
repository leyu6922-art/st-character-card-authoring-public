from __future__ import annotations

import json


def test_missing_sibling_capability_is_a_named_gate_failure(load_script_module, monkeypatch, tmp_path):
    gate = load_script_module("final_delivery_gate.py")
    card_path = tmp_path / "card.json"
    card_path.write_text(json.dumps({"spec": "chara_card_v3", "spec_version": "3.0", "data": {}}), encoding="utf-8")

    monkeypatch.setattr(gate, "sibling_skill_script", lambda *_args: tmp_path / "missing.py")
    results = gate.run_native_stage_routing(card_path)

    assert len(results) == 2
    assert all(result.status == "FAIL" for result in results)
    assert all(any("[CAPABILITY_MISSING]" in message for message in result.errors) for result in results)


def test_three_repeated_yellow_warnings_do_not_escalate(load_script_module, monkeypatch, tmp_path):
    gate = load_script_module("final_delivery_gate.py")

    class RepeatedWarningCheck:
        @staticmethod
        def check_card(*_args, **_kwargs):
            return [("🟡", f"场景[{index}] '场景{index}' 缺少安全等级定义") for index in range(3)]

    monkeypatch.setattr(gate, "import_script", lambda _name: RepeatedWarningCheck)
    result = gate.run_enrichment(tmp_path / "card.json", r18=True, prototype="A", three_path="")

    assert result.status == "WARN"
    assert not result.errors


def test_three_distinct_blocking_yellow_rules_escalate(load_script_module, monkeypatch, tmp_path):
    gate = load_script_module("final_delivery_gate.py")

    class DistinctWarningCheck:
        @staticmethod
        def check_card(*_args, **_kwargs):
            return [
                ("🟡", "场景[1] '场景' 缺少安全等级定义"),
                ("🟡", "行为模板[2] '角色' 行为链偏少 (1个)"),
                ("🟡", "缺少独立描写库条目 (身体/感官/氛围不应和对话语料混在同一条)"),
            ]

    monkeypatch.setattr(gate, "import_script", lambda _name: DistinctWarningCheck)
    result = gate.run_enrichment(tmp_path / "card.json", r18=True, prototype="A", three_path="")

    assert result.status == "FAIL"
    assert any("BLOCKING_WARNING_THRESHOLD" in error for error in result.errors)
