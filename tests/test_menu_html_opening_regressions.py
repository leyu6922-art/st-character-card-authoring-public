from __future__ import annotations

import copy
import json
from pathlib import Path


def stage_title(stage: str = "P0") -> str:
    return f"【开场：{stage}·测试场景｜测试作品】"


def menu_title() -> str:
    return "【图鉴：角色总览｜MENU】"


def stage_units(pack: str) -> str:
    body = (
        "当前阶段的候选素材包含明确前提、自然进入、人物反应和后果，"
        "只在当前阶段条件成立后调用，不把未来内容写成已经发生的事实。"
        "角色只能根据当前可观察信息回应，未发生的路线保持为候选，不替玩家决定。"
        "每个单元都保留地点、人物、动作、阻断和玩家接管位置，避免把素材压缩成抽象标签。"
    )
    return "\n\n".join(
        f"【{pack}_P0_{index:02d}_素材】{body}" for index in range(1, 7)
    )


def stage_card(*, greeting: str) -> dict:
    packs = ["阶段核心", "成人体验", "场景体验", "事件库"]
    entries = [
        {
            "id": "archive",
            "comment": "角色A·全程因果档案",
            "content": "角色A的完整因果方向覆盖P0至P1，未来变化只在当前阶段前置条件成立后才可能发生。",
            "keys": [],
            "secondary_keys": [],
            "enabled": True,
            "constant": True,
            "selective": False,
            "extensions": {},
        },
        {
            "id": "memory-gate",
            "comment": "绝对优先级·阶段记忆与叙事可见性协议",
            "content": "当前阶段只把起步至当前路由阶段的事件当作已发生记忆，未来阶段内容只能作为候选方向。",
            "keys": [],
            "secondary_keys": [],
            "enabled": True,
            "constant": True,
            "selective": False,
            "extensions": {},
        },
    ]
    entries.extend(
        {
            "id": f"{pack}-P0",
            "comment": f"{pack}_P0",
            "content": stage_units(pack),
            "keys": [stage_title()],
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
        for pack in packs
    )
    return {
        "spec": "chara_card_v3",
        "spec_version": "3.0",
        "data": {
            "first_mes": greeting,
            "alternate_greetings": [],
            "group_only_greetings": [],
            "system_prompt": "阶段表演规则：模型可理解全阶段人物弧线，但当前角色仅记得当前路由阶段已发生的事实。",
            "character_book": {"entries": entries},
        },
    }


def stage_contract() -> dict:
    entries = {
        "角色A·全程因果档案": {"role": "constant"},
        "绝对优先级·阶段记忆与叙事可见性协议": {"role": "constant"},
    }
    for pack in ("阶段核心", "成人体验", "场景体验", "事件库"):
        entries[f"{pack}_P0"] = {"role": "stage_pack", "stage": "P0", "pack": pack}
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


def test_menu_is_a_first_class_non_stage_entry_and_does_not_require_four_packs(load_script_module):
    routing = load_script_module("lib/stage_routing.py")
    auditor = load_script_module("audit_stage_entry_contracts.py")
    trigger_audit = load_script_module("audit_worldbook_triggers.py")

    card = stage_card(greeting=f"{menu_title()}\n<html><body>角色总览</body></html>")
    card["data"]["alternate_greetings"] = [f"{stage_title()}\n当前阶段开场。"]

    assert routing.parse_stage_title(menu_title()) == ("MENU", menu_title())
    assert routing.declared_titles_by_stage(card) == {
        "MENU": {menu_title()},
        "P0": {stage_title()},
    }

    result = auditor.audit_card(card, stage_contract())
    assert result.errors == []

    data = card["data"]
    sources = trigger_audit.build_sources(data)
    audits = trigger_audit.analyze_entries(data["character_book"]["entries"], sources)
    findings, _warnings = trigger_audit.stage_route_findings(audits, sources)
    assert not any("MENU" in finding for finding in findings)


def test_html_stage_title_inside_markup_is_not_required_to_be_visible_first(load_script_module):
    auditor = load_script_module("audit_stage_entry_contracts.py")
    html = f"<html><body><!-- {stage_title()} --><section>图鉴内容</section></body></html>"

    result = auditor.audit_card(stage_card(greeting=html), stage_contract())

    assert result.errors == []


def test_html_greeting_skips_repeated_ui_lines_and_residue_scan_keeps_case_boundary(load_script_module, tmp_path):
    validator = load_script_module("validate_card.py")
    gate = load_script_module("final_delivery_gate.py")
    source = json.loads(
        (Path(__file__).resolve().parent / "fixtures" / "valid_leyu_manual_toggle.json").read_text(
            encoding="utf-8"
        )
    )
    source["data"]["first_mes"] = (
        "<html><body>\n"
        "<section>角色页</section>\n"
        "<section>角色页</section>\n"
        "<section>角色页</section>\n"
        "</body></html>"
    )
    path = tmp_path / "html-opening.json"
    path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

    report = validator.validate_card_report(str(path), greeting_mode="ai_trigger")

    assert not any("同一行重复" in issue.message for issue in report.issues)

    lowercase = copy.deepcopy(source)
    lowercase["data"]["first_mes"] = "<html><input placeholder='todo'></html>"
    lowercase_path = tmp_path / "html-lowercase.json"
    lowercase_path.write_text(json.dumps(lowercase, ensure_ascii=False), encoding="utf-8")
    lowercase_result = gate.scan_forbidden(lowercase_path, r18=False)
    assert not any("PLACEHOLDER/TODO" in message for message in lowercase_result.errors)

    uppercase = copy.deepcopy(source)
    uppercase["data"]["first_mes"] = "<html><input placeholder='TODO'></html>"
    uppercase_path = tmp_path / "html-uppercase.json"
    uppercase_path.write_text(json.dumps(uppercase, ensure_ascii=False), encoding="utf-8")
    uppercase_result = gate.scan_forbidden(uppercase_path, r18=False)
    assert any("PLACEHOLDER/TODO" in message for message in uppercase_result.errors)
