from __future__ import annotations

import json

import pytest


def _stage_title(stage: str = "P0") -> str:
    return f"【开场：{stage}·测试场景｜测试作品】"


def _stage_card(prompt: str, *, greeting: bool = True, entry_title: bool = True) -> dict:
    entries = []
    if entry_title:
        entries.append({
            "id": 1,
            "comment": "阶段核心_P0",
            "content": "当前阶段素材。",
            "keys": [_stage_title()],
            "secondary_keys": [],
            "enabled": True,
            "constant": False,
            "selective": True,
            "extensions": {},
        })
    return {
        "data": {
            "first_mes": _stage_title() + "\n开场正文" if greeting else "普通开场正文",
            "alternate_greetings": [],
            "system_prompt": prompt,
            "character_book": {"entries": entries},
        }
    }


def test_phase_memory_anchor_uses_one_shared_rule_with_stable_ids(load_script_module):
    memory = load_script_module("lib/stage_memory.py")

    missing = memory.phase_memory_anchor_issues(
        "阶段表演规则：模型可以理解完整人物弧线，并持续遵守当前阶段事实边界与信息可见性规则，但没有第二个规定锚点。"
    )
    short = memory.phase_memory_anchor_issues("阶段表演规则：当前角色仅记得当前阶段。")
    valid = memory.phase_memory_anchor_issues(
        "阶段表演规则：模型可以理解完整人物弧线；当前角色仅记得起步至当前路由阶段已经发生的事实，未来内容只能作为候选方向。"
    )

    assert {issue.rule_id for issue in missing} == {"STAGE_MEMORY_ONLY_REMEMBERS_ANCHOR_MISSING"}
    assert {issue.rule_id for issue in short} == {"STAGE_MEMORY_ANCHOR_TOO_SHORT"}
    assert valid == []


def test_stage_title_declaration_is_not_inferred_from_entry_binding(load_script_module):
    routing = load_script_module("lib/stage_routing.py")
    entry_only = _stage_card("", greeting=False, entry_title=True)
    greeting_only = _stage_card("", greeting=True, entry_title=False)

    assert routing.declared_titles_by_stage(entry_only) == {}
    assert routing.bound_titles_by_stage(entry_only) == {"P0": {_stage_title()}}
    assert routing.all_titles_by_stage(entry_only) == {"P0": {_stage_title()}}
    assert routing.has_native_stage_routing(entry_only) is False
    assert routing.has_native_stage_routing(greeting_only) is True


def test_source_coverage_marks_zero_eligible_entries_as_not_a_hundred_percent_pass(load_script_module):
    coverage = load_script_module("audit_source_material_coverage.py")
    card = {
        "data": {
            "character_book": {
                "entries": [{
                    "id": 1,
                    "comment": "OOC系统常驻",
                    "content": "系统说明不属于原文素材。",
                    "enabled": True,
                    "constant": True,
                    "extensions": {"entry_role": "system_constant"},
                }]
            }
        }
    }

    result = coverage.audit_card_data(card, "足够长的 canonical source text for testing")

    assert result["eligible"] == 0
    assert result["coverage"] is None
    assert result["status"] == "no_eligible"


def test_delivery_manifest_builds_complete_plan_without_running_inapplicable_appendix_audit(load_script_module, tmp_path):
    runner = load_script_module("run_delivery.py")
    manifest_path = tmp_path / "build_manifest.json"
    manifest_path.write_text(json.dumps({
        "schema_version": 1,
        "prototype": "A",
        "routing_mode": "native_greeting_title",
        "greeting_mode": "player_prose",
        "require_build": True,
        "canonical_sources": ["sources/chapter-01.txt", "sources/chapter-02.txt"],
        "source_coverage_required": True,
        "source_coverage_minimum": 0.60,
        "stage_entry_contract": "stage-entry-contract.json",
        "player_agency_modes_required": False,
    }, ensure_ascii=False), encoding="utf-8")
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    (source_dir / "chapter-01.txt").write_text("原文甲", encoding="utf-8")
    (source_dir / "chapter-02.txt").write_text("原文乙", encoding="utf-8")
    (tmp_path / "stage-entry-contract.json").write_text("{}", encoding="utf-8")
    (tmp_path / "card.json").write_text("{}", encoding="utf-8")

    plan = runner.build_delivery_plan(tmp_path / "card.json", manifest_path)

    assert "--require-build" in plan.argv
    assert plan.argv.count("--source") == 2
    assert "--native-stage-routing" in plan.argv
    assert "--stage-entry-contract" in plan.argv
    assert "--greeting-layer-audit" not in plan.argv
    assert "--greeting-mode" not in plan.argv
    statuses = {item.name: (item.status, item.reason) for item in plan.checks}
    assert statuses["source coverage"][0] == "RUN"
    assert statuses["Greeting appendix audit"] == ("SKIP", "greeting_mode=player_prose")


def test_manifest_rejects_missing_required_canonical_source(load_script_module, tmp_path):
    runner = load_script_module("run_delivery.py")
    manifest_path = tmp_path / "build_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "prototype": "A",
                "routing_mode": "flat",
                "greeting_mode": "player_prose",
                "canonical_sources": ["missing-chapter.txt"],
                "source_coverage_required": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="canonical source does not exist"):
        runner.load_delivery_manifest(manifest_path)



def test_manifest_rejects_missing_native_stage_contract_file(load_script_module, tmp_path):
    runner = load_script_module("run_delivery.py")
    manifest_path = tmp_path / "build_manifest.json"
    manifest_path.write_text(json.dumps({
        "schema_version": 1,
        "prototype": "A",
        "routing_mode": "native_greeting_title",
        "greeting_mode": "ai_trigger",
        "stage_entry_contract": "missing-contract.json",
        "source_coverage_required": False,
    }, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="stage_entry_contract does not exist"):
        runner.load_delivery_manifest(manifest_path)


def test_simple_stage_manifest_reaches_final_gate_with_preset_pair(load_script_module, tmp_path):
    runner = load_script_module("run_delivery.py")
    card_path = tmp_path / "card.json"
    manifest_path = tmp_path / "build_manifest.json"
    preset_path = tmp_path / "preset.json"
    policy_path = tmp_path / "preset-policy.json"
    card_path.write_text("{}", encoding="utf-8")
    preset_path.write_text("{}", encoding="utf-8")
    policy_path.write_text("{}", encoding="utf-8")
    manifest_path.write_text(json.dumps({
        "schema_version": 1,
        "prototype": "A",
        "routing_mode": "simple_stage_route",
        "greeting_mode": "ai_trigger",
        "preset": "preset.json",
        "preset_policy": "preset-policy.json",
        "source_coverage_required": False,
    }, ensure_ascii=False), encoding="utf-8")

    plan = runner.build_delivery_plan(card_path, manifest_path)

    assert "--simple-stage-route" in plan.argv
    assert "--native-stage-routing" not in plan.argv
    assert plan.argv[plan.argv.index("--preset") + 1] == str(preset_path.resolve())
    assert plan.argv[plan.argv.index("--preset-policy") + 1] == str(policy_path.resolve())
    assert plan.argv[plan.argv.index("--greeting-mode") + 1] == "ai_trigger"

def test_delivery_plan_rejects_missing_card_before_final_gate(load_script_module, tmp_path):
    runner = load_script_module("run_delivery.py")
    manifest_path = tmp_path / "build_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "prototype": "A",
                "routing_mode": "flat",
                "greeting_mode": "player_prose",
                "source_coverage_required": False,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="card does not exist"):
        runner.build_delivery_plan(tmp_path / "missing-card.json", manifest_path)


def test_delivery_manifest_rejects_required_source_coverage_without_sources(load_script_module, tmp_path):
    runner = load_script_module("run_delivery.py")
    manifest_path = tmp_path / "build_manifest.json"
    manifest_path.write_text(json.dumps({
        "schema_version": 1,
        "prototype": "A",
        "routing_mode": "flat",
        "greeting_mode": "player_prose",
        "source_coverage_required": True,
    }), encoding="utf-8")
    (tmp_path / "card.json").write_text("{}", encoding="utf-8")

    try:
        runner.build_delivery_plan(tmp_path / "card.json", manifest_path)
    except ValueError as exc:
        assert "source_coverage_required" in str(exc)
    else:
        raise AssertionError("required source coverage without canonical_sources must fail")


def test_token_analyzer_reports_runtime_categories_without_blocking_threshold(load_script_module, tmp_path):
    analyzer = load_script_module("analyze_token_load.py")
    card_path = tmp_path / "card.json"
    card_path.write_text(json.dumps({
        "data": {
            "first_mes": "触发标题",
            "character_book": {"entries": [{
                "id": 1,
                "comment": "阶段核心_P0",
                "content": "阶段内容",
                "keys": ["触发标题"],
                "secondary_keys": [],
                "enabled": True,
                "constant": False,
                "selective": True,
                "extensions": {"entry_role": "common_content"},
            }]},
        }
    }, ensure_ascii=False), encoding="utf-8")

    report = analyzer.analyze_token_load(card_path)

    assert report["categories"]["stage_core"]["entries"] == 1
    assert report["status"] == "diagnostic"
    assert "threshold" not in report


def test_orphaned_stage_title_key_is_reported_without_triggering_stage_contract(load_script_module, tmp_path):
    validator = load_script_module("validate_card.py")
    card_path = tmp_path / "orphan-title.json"
    card = _stage_card("", greeting=False, entry_title=True)
    card.update({"spec": "chara_card_v3", "spec_version": "3.0"})
    card_path.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")

    report = validator.validate_card_report(str(card_path))

    assert any(issue.rule_id == "STAGE_TITLE_KEY_ORPHANED" for issue in report.warnings)
    assert not any(issue.rule_id == "STAGE_MEMORY_GATE_MISSING" for issue in report.errors)


def test_non_prose_greeting_modes_do_not_inherit_player_prose_minimum(load_script_module, tmp_path):
    validator = load_script_module("validate_card.py")
    card_path = tmp_path / "short-trigger.json"
    card = {
        "spec": "chara_card_v3",
        "spec_version": "3.0",
        "data": {
            "name": "测试",
            "description": "测试",
            "first_mes": "【开场：P0·测试｜测试】\n当前事实。",
            "alternate_greetings": [],
            "mes_example": "",
            "post_history_instructions": "",
            "group_only_greetings": [],
            "character_book": {"entries": []},
        },
    }
    card_path.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")

    prose = validator.validate_card_report(str(card_path), greeting_mode="player_prose")
    trigger = validator.validate_card_report(str(card_path), greeting_mode="ai_trigger")

    assert any("first_mes 仅" in issue.message for issue in prose.errors)
    assert not any("first_mes 仅" in issue.message for issue in trigger.errors)


def test_appendix_greeting_mode_reaches_final_gate_with_its_specific_audit(load_script_module, tmp_path):
    runner = load_script_module("run_delivery.py")
    manifest_path = tmp_path / "build_manifest.json"
    card_path = tmp_path / "card.json"
    card_path.write_text("{}", encoding="utf-8")
    manifest_path.write_text(json.dumps({
        "schema_version": 1,
        "prototype": "A",
        "routing_mode": "flat",
        "greeting_mode": "prose_plus_director_appendix",
        "source_coverage_required": False,
    }, ensure_ascii=False), encoding="utf-8")

    plan = runner.build_delivery_plan(card_path, manifest_path)

    assert "--greeting-mode" in plan.argv
    assert plan.argv[plan.argv.index("--greeting-mode") + 1] == "prose_plus_director_appendix"
    assert "--greeting-layer-audit" in plan.argv
    assert ("Greeting appendix audit", "RUN", "greeting_mode=prose_plus_director_appendix, standard=stage_brief_v1") in [
        (item.name, item.status, item.reason) for item in plan.checks
    ]
    assert ("Greeting build wiring", "SKIP", "require_build=false; no canonical Greeting build source required") in [
        (item.name, item.status, item.reason) for item in plan.checks
    ]


def test_appendix_manifest_with_build_requires_source_wiring_audit(load_script_module, tmp_path):
    runner = load_script_module("run_delivery.py")
    manifest_path = tmp_path / "build_manifest.json"
    card_path = tmp_path / "card.json"
    card_path.write_text("{}", encoding="utf-8")
    manifest_path.write_text(json.dumps({
        "schema_version": 1,
        "prototype": "A",
        "routing_mode": "flat",
        "greeting_mode": "prose_plus_director_appendix",
        "greeting_appendix_standard": "stage_brief_v1",
        "require_build": True,
        "source_coverage_required": False,
    }, ensure_ascii=False), encoding="utf-8")

    plan = runner.build_delivery_plan(card_path, manifest_path)

    assert ("Greeting build wiring", "RUN", "require_build=true; compare build/all_entries.json to assembled Greetings") in [
        (item.name, item.status, item.reason) for item in plan.checks
    ]


def test_v1_manifest_is_explicitly_legacy_unspecified_without_new_checks(load_script_module, tmp_path):
    runner = load_script_module("run_delivery.py")
    card_path = tmp_path / "card.json"
    manifest_path = tmp_path / "build_manifest.json"
    card_path.write_text("{}", encoding="utf-8")
    manifest_path.write_text(json.dumps({
        "schema_version": 1,
        "prototype": "A",
        "routing_mode": "flat",
        "greeting_mode": "player_prose",
        "source_coverage_required": False,
    }), encoding="utf-8")

    plan = runner.build_delivery_plan(card_path, manifest_path)

    assert plan.narrative_mode == "legacy_unspecified"
    assert all(item.name not in {
        "narrative mode", "runtime state contract", "candidate-event audit",
        "transition-policy audit", "ordered-step audit", "open-sandbox audit",
    } for item in plan.checks)
