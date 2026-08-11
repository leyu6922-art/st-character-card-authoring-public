from __future__ import annotations

import json
from pathlib import Path


def title(stage: str) -> str:
    return f"【开场：{stage}·回归场景｜测试】"


def units(stage: str, pack: str) -> str:
    body = "当前阶段的候选素材，包含明确前提、自然进入、人物反应和后果，不视为既定历史。"
    return "\n".join(
        f"【{pack}_{stage}_{index:02d}_素材】{body}" for index in range(1, 7)
    )


def pack(stage: str, name: str, *, keys: list[str] | None = None) -> dict:
    return {
        "id": f"{name}-{stage}",
        "comment": f"{name}_{stage}",
        "content": units(stage, name),
        "keys": [title(stage)] if keys is None else keys,
        "secondary_keys": [],
        "enabled": True,
        "constant": False,
        "selective": True,
        "extensions": {
            "selective": True,
            "scan_depth": 999,
            "prevent_recursion": True,
            "exclude_recursion": True,
        },
    }


def archive() -> dict:
    return {
        "id": "archive",
        "comment": "角色A·全程因果档案",
        "content": "角色A的完整因果方向覆盖P0至P1，未来变化只在当前阶段前置条件成立后才可能发生。",
        "keys": [], "secondary_keys": [], "enabled": True, "constant": True, "selective": False,
        "extensions": {},
    }


def memory_gate() -> dict:
    return {
        "id": "memory-gate",
        "comment": "绝对优先级·阶段记忆与叙事可见性协议",
        "content": "当前阶段只把起步至当前路由阶段的事件当作已发生记忆，未来阶段内容只能作为候选方向。",
        "keys": [], "secondary_keys": [], "enabled": True, "constant": True, "selective": False,
        "extensions": {},
    }


def native_card(*, pack_keys: list[str] | None = None, include_all_packs: bool = True) -> dict:
    names = ["阶段核心", "成人体验", "场景体验", "事件库"]
    if not include_all_packs:
        names = ["阶段核心"]
    entries = [archive(), memory_gate(), *(pack("P0", name, keys=pack_keys) for name in names)]
    return {
        "spec": "chara_card_v3",
        "spec_version": "3.0",
        "data": {
            "first_mes": f"{title('P0')}\n围裙出现在当前开场正文。",
            "alternate_greetings": [],
            "group_only_greetings": [],
            "system_prompt": "阶段表演规则：模型可理解全阶段人物弧线，但当前角色仅记得当前路由阶段已发生的事实。",
            "character_book": {"entries": entries},
        },
    }


def contract() -> dict:
    entries = {
        "角色A·全程因果档案": {"role": "constant"},
        "绝对优先级·阶段记忆与叙事可见性协议": {"role": "constant"},
    }
    for name in ("阶段核心", "成人体验", "场景体验", "事件库"):
        entries[f"{name}_P0"] = {"role": "stage_pack", "stage": "P0", "pack": name}
    return {
        "schema_version": 2,
        "mode": "leyu_large_native_greeting_stage_v1",
        "architecture_mode": "stage_routing",
        "route_source": "greeting_title",
        "stages": ["P0"],
        "required_packs": ["阶段核心", "成人体验", "场景体验", "事件库"],
        "min_units_per_pack": 6,
        "min_unit_chars": 120,
        "phase_memory": {
            "causal_archives": ["角色A·全程因果档案"],
            "memory_gate": "绝对优先级·阶段记忆与叙事可见性协议",
            "system_prompt_anchor_required": True,
        },
        "entries": entries,
    }


def test_greeting_title_alone_activates_native_stage_detection(load_script_module):
    gate = load_script_module("final_delivery_gate.py")
    card = native_card(pack_keys=["围裙"])

    assert gate.detect_stage_routing(card) is True


def test_greeting_declared_stage_requires_title_bound_four_packs_in_validator(load_script_module, tmp_path):
    validator = load_script_module("validate_card.py")
    path = tmp_path / "greeting-only.json"
    path.write_text(json.dumps(native_card(pack_keys=["围裙"], include_all_packs=False), ensure_ascii=False), encoding="utf-8")

    _ok, errors, _warnings = validator.validate_card(str(path))

    assert any("STAGE_PACK_INCOMPLETE" in error and "P0" in error for error in errors)


def test_greeting_declared_stage_requires_title_bound_four_packs_in_enrichment(load_script_module, tmp_path):
    enrichment = load_script_module("enrichment_self_check.py")
    path = tmp_path / "greeting-only.json"
    path.write_text(json.dumps(native_card(pack_keys=["围裙"], include_all_packs=False), ensure_ascii=False), encoding="utf-8")

    issues = enrichment.check_card(str(path))

    assert any("STAGE_ROUTING" in message and "P0" in message for _level, message in issues)


def test_trigger_audit_reports_greeting_stage_packs_not_bound_to_title(load_script_module):
    audit = load_script_module("audit_worldbook_triggers.py")
    card = native_card(pack_keys=["围裙"])
    data = card["data"]
    entries = data["character_book"]["entries"]

    findings, _warnings = audit.stage_route_findings(audit.analyze_entries(entries, audit.build_sources(data)), audit.build_sources(data))

    assert any("STAGE_PACK" in message and "P0" in message for message in findings)


def test_native_contract_rejects_schema_v1_even_without_phase_memory(load_script_module):
    auditor = load_script_module("audit_stage_entry_contracts.py")
    raw = contract()
    raw["schema_version"] = 1
    raw.pop("phase_memory")

    _parsed, errors = auditor._parse_contract(raw)

    assert any("schema_version必须为2" in error for error in errors)


def test_contract_rejects_empty_phase_memory_components(load_script_module):
    auditor = load_script_module("audit_stage_entry_contracts.py")
    card = native_card()
    for entry in card["data"]["character_book"]["entries"][:2]:
        entry["content"] = ""

    result = auditor.audit_card(card, contract())

    assert any("正文" in error and "因果档案" in error for error in result.errors)
    assert any("正文" in error and "记忆闸门" in error for error in result.errors)


def test_explicit_contract_cannot_be_silently_ignored_for_non_stage_card(load_script_module, tmp_path, monkeypatch):
    gate = load_script_module("final_delivery_gate.py")
    card = native_card()
    card["data"]["first_mes"] = "普通开场。"
    for entry in card["data"]["character_book"]["entries"]:
        if not entry["constant"]:
            entry["keys"] = ["围裙"]
    card_path = tmp_path / "plain.json"
    contract_path = tmp_path / "stage-entry-contract.json"
    report_path = tmp_path / "delivery.md"
    card_path.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    contract_path.write_text(json.dumps(contract(), ensure_ascii=False), encoding="utf-8")

    def passed(name: str):
        return gate.GateResult(name, "PASS")

    monkeypatch.setattr(gate, "run_validate", lambda _path: passed("validate"))
    monkeypatch.setattr(gate, "run_audit", lambda _path, _dir: passed("trigger"))
    monkeypatch.setattr(gate, "run_enrichment", lambda *_args: passed("enrichment"))
    monkeypatch.setattr(gate, "run_build_sync", lambda *_args: passed("build"))
    monkeypatch.setattr(gate, "scan_forbidden", lambda *_args, **_kwargs: passed("scan"))

    exit_code = gate.main([
        str(card_path), "--project-dir", str(tmp_path), "--no-r18",
        "--stage-entry-contract", str(contract_path), "-o", str(report_path),
    ])

    assert exit_code == 1
    assert "STAGE_CONTRACT_ROUTE_UNDETECTED" in report_path.read_text(encoding="utf-8")


def test_trigger_audit_cli_returns_nonzero_for_native_stage_binding_error(load_script_module, tmp_path):
    module = load_script_module("audit_worldbook_triggers.py")
    card_path = tmp_path / "misbound-native.json"
    card_path.write_text(json.dumps(native_card(pack_keys=["围裙"]), ensure_ascii=False), encoding="utf-8")
    assert module.main([str(card_path), "--output", str(tmp_path / "report.md")]) == 1


def test_validator_rejects_future_as_fact_in_non_memory_constant(load_script_module, tmp_path):
    validator = load_script_module("validate_card.py")
    card = native_card()
    card["data"]["character_book"]["entries"].append({
        "id": "future-constant", "comment": "人物关系矩阵·常驻",
        "content": "角色A在P4之后已经成为角色B的固定关系，这是一项既定事实。",
        "keys": [], "secondary_keys": [], "enabled": True, "constant": True,
        "selective": False, "extensions": {},
    })
    path = tmp_path / "future-constant.json"
    path.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    _ok, errors, _warnings = validator.validate_card(str(path))
    assert any("STAGE_FUTURE_LEAK_CONSTANT" in error for error in errors)


def test_external_route_marker_detection_covers_single_key_secondary_and_content(load_script_module):
    gate = load_script_module("final_delivery_gate.py")
    card = native_card()
    entry = card["data"]["character_book"]["entries"][2]
    entry["key"] = "route_stage=p3"
    entry["secondary_keys"] = ["ROUTE_STAGE=P4"]
    entry["content"] += "\nROUTE_STAGE=P5"
    evidence = "\n".join(gate.detect_external_route_markers(card)).upper()
    assert "ROUTE_STAGE=P3" in evidence
    assert "ROUTE_STAGE=P4" in evidence
    assert "ROUTE_STAGE=P5" in evidence
