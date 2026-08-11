from __future__ import annotations

import json
import importlib.util
from pathlib import Path

import pytest

SIBLING_SCRIPTS = Path(__file__).resolve().parents[2] / "standalone-card-stage-routing" / "scripts"
requires_sibling_skill = pytest.mark.skipif(
    not SIBLING_SCRIPTS.is_dir(),
    reason="sibling skill standalone-card-stage-routing not checked out (single-skill CI layout)",
)


def stages() -> list[str]:
    return ["P0", "P1", "P2", "P3", "P4", "P5"]


def packs() -> list[str]:
    return ["阶段核心", "成人体验", "场景体验", "事件库"]


def title(stage: str) -> str:
    return f"【开场：{stage}·阶段素材｜作品标识】"


def pack_entry(stage: str, pack: str) -> dict:
    material = (
        "该素材单元明确给出进入条件、人物主动动作、可用对白、当下心理、场景变化、选择分歧与关系余波，"
        "模型必须将其作为当前阶段的候选创作素材自然融入叙事，而不是复述为资料说明。"
        "内容同时保留人物之间的信息边界与情绪张力，说明谁先观察、谁会试探、谁可能退让，"
        "并给出本轮结束后会遗留的关系变化，确保它能够真实推动剧情而非充当剧情索引。"
    )
    units = "\n".join(
        f"【{pack}_{stage}_{index:02d}_素材】{material}"
        for index in range(1, 7)
    )
    return {
        "id": f"{pack}-{stage}",
        "comment": f"{pack}_{stage}",
        "content": units,
        "keys": [title(stage)],
        "secondary_keys": [],
        "enabled": True,
        "constant": False,
        "selective": True,
        "extensions": {
            "scan_depth": 999,
            "selective": True,
            "prevent_recursion": True,
            "exclude_recursion": True,
        },
    }


def valid_card() -> dict:
    greetings = [f"{title(stage)}\n这是{stage}阶段的独立开场正文。" for stage in stages()]
    entries = [pack_entry(stage, pack) for stage in stages() for pack in packs()]
    entries.extend([
        {
            "id": "causal-archive", "comment": "角色A·全程因果档案",
            "content": "角色A的完整因果方向覆盖P0至P5，未来变化只在当前阶段前置条件成立后才可能发生。",
            "keys": [], "secondary_keys": [], "enabled": True, "constant": True, "selective": False, "extensions": {},
        },
        {
            "id": "memory-gate", "comment": "绝对优先级·阶段记忆与叙事可见性协议",
            "content": "当前阶段只把起步至当前路由阶段的事实当作已发生记忆，未来阶段内容只能作为候选方向。",
            "keys": [], "secondary_keys": [], "enabled": True, "constant": True, "selective": False, "extensions": {},
        },
    ])
    return {
        "spec": "chara_card_v3", "spec_version": "3.0",
        "data": {
            "first_mes": greetings[0], "alternate_greetings": greetings[1:],
            "character_book": {"entries": entries},
            "system_prompt": "阶段表演规则：模型可理解全阶段人物弧线，但当前角色仅记得起步至当前路由阶段已发生的事实。",
        },
    }


def valid_contract() -> dict:
    entries = {
        f"{pack}_{stage}": {"role": "stage_pack", "stage": stage, "pack": pack}
        for stage in stages() for pack in packs()
    }
    entries.update({
        "角色A·全程因果档案": {"role": "constant"},
        "绝对优先级·阶段记忆与叙事可见性协议": {"role": "constant"},
    })
    return {
        "schema_version": 2,
        "mode": "leyu_large_native_greeting_stage_v1",
        "architecture_mode": "stage_routing",
        "route_source": "greeting_title",
        "stages": stages(), "required_packs": packs(),
        "min_units_per_pack": 6, "min_unit_chars": 120,
        "phase_memory": {
            "causal_archives": ["角色A·全程因果档案"],
            "memory_gate": "绝对优先级·阶段记忆与叙事可见性协议",
            "system_prompt_anchor_required": True,
        },
        "entries": entries,
    }


def valid_contract_v2() -> dict:
    return valid_contract()


def valid_card_v2() -> dict:
    return valid_card()


def audit(load_script_module, card: dict, contract: dict):
    module = load_script_module("audit_stage_entry_contracts.py")
    return module.audit_card(card, contract)


def test_complete_p0_to_p5_contract_passes(load_script_module):
    result = audit(load_script_module, valid_card(), valid_contract())

    assert result.errors == []


def test_contract_cannot_weaken_mandatory_density_floors(load_script_module):
    contract = valid_contract()
    contract["min_units_per_pack"] = 1
    contract["min_unit_chars"] = 1

    result = audit(load_script_module, valid_card(), contract)

    assert any("min_units_per_pack必须≥6" in error for error in result.errors)
    assert any("min_unit_chars必须≥120" in error for error in result.errors)


def test_valid_contract_translates_to_the_sibling_architecture_manifest(load_script_module):
    module = load_script_module("audit_stage_entry_contracts.py")

    manifest, errors = module.architecture_manifest_from_contract(valid_contract())

    assert errors == []
    assert manifest is not None
    assert manifest["route_mode"] == "native_greeting_title"
    assert manifest["route_source"] == "greeting_title"
    assert manifest["architecture_mode"] == "stage_routing"
    assert manifest["stages"] == stages()
    assert manifest["required_packs"] == packs()
    assert manifest["phase_memory"]["memory_gate"] == "绝对优先级·阶段记忆与叙事可见性协议"


def test_schema_v2_requires_phase_memory_and_exports_it(load_script_module):
    module = load_script_module("audit_stage_entry_contracts.py")
    contract = valid_contract_v2()
    manifest, errors = module.architecture_manifest_from_contract(contract)
    assert errors == []
    assert manifest["architecture_mode"] == "stage_routing"
    assert manifest["route_source"] == "greeting_title"
    assert manifest["phase_memory"]["memory_gate"] == "绝对优先级·阶段记忆与叙事可见性协议"


def test_schema_v1_rejects_silently_ignored_phase_memory(load_script_module):
    """v1 合同携带 phase_memory 必须显式报错，不得静默忽略造成“记忆架构已审计”的错觉"""
    module = load_script_module("audit_stage_entry_contracts.py")
    contract = valid_contract()
    contract["schema_version"] = 1
    contract.pop("phase_memory")
    _contract, errors = module._parse_contract(contract)
    assert any("schema_version必须为2" in error for error in errors)


def test_schema_v2_rejects_missing_phase_memory_fields(load_script_module):
    module = load_script_module("audit_stage_entry_contracts.py")
    contract = valid_contract_v2()
    contract["phase_memory"] = {}
    manifest, errors = module.architecture_manifest_from_contract(contract)
    assert manifest is None
    assert any("causal_archives" in error for error in errors)
    assert any("memory_gate" in error for error in errors)


def test_formal_v2_template_is_accepted_by_real_contract_parser(load_script_module):
    module = load_script_module("audit_stage_entry_contracts.py")
    template = Path(__file__).parents[1] / "templates" / "stage-entry-contract.example.json"
    raw, load_errors = module.load_contract(template)
    assert load_errors == []
    assert raw is not None
    _contract, errors = module._parse_contract(raw)
    assert errors == []


@requires_sibling_skill
def test_v2_title_card_passes_real_contract_and_sibling_audits(load_script_module, tmp_path):
    gate = load_script_module("final_delivery_gate.py")
    card_path = tmp_path / "stage.json"
    contract_path = tmp_path / "stage-entry-contract.json"
    card_path.write_text(json.dumps(valid_card_v2(), ensure_ascii=False), encoding="utf-8")
    contract_path.write_text(json.dumps(valid_contract_v2(), ensure_ascii=False), encoding="utf-8")
    contract_result = gate.run_stage_entry_contract(card_path, contract_path)
    assert contract_result.status == "PASS", contract_result.errors
    contract_mod = load_script_module("audit_stage_entry_contracts.py")
    raw, errors = contract_mod.load_contract(contract_path)
    assert errors == [] and raw is not None
    manifest, errors = contract_mod.architecture_manifest_from_contract(raw)
    assert errors == [] and manifest is not None
    native_results = gate.run_native_stage_routing(card_path, stage_manifest=manifest)
    assert [result.status for result in native_results] == ["PASS", "PASS"], [result.errors for result in native_results]


@requires_sibling_skill
def test_final_gate_runs_real_contract_and_native_audits_for_v2_card(load_script_module, tmp_path, monkeypatch):
    gate = load_script_module("final_delivery_gate.py")
    card_path = tmp_path / "stage.json"
    contract_path = tmp_path / "stage-entry-contract.json"
    report_path = tmp_path / "delivery.md"
    card_path.write_text(json.dumps(valid_card_v2(), ensure_ascii=False), encoding="utf-8")
    contract_path.write_text(json.dumps(valid_contract_v2(), ensure_ascii=False), encoding="utf-8")

    def passed(name: str):
        return gate.GateResult(name, "PASS")

    # Only unrelated generic quality/build checks are isolated; contract and sibling
    # native-stage audits execute their real implementations.
    monkeypatch.setattr(gate, "run_validate", lambda _path: passed("validate"))
    monkeypatch.setattr(gate, "run_audit", lambda _path, _dir: passed("trigger"))
    monkeypatch.setattr(gate, "run_enrichment", lambda *_args: passed("enrichment"))
    monkeypatch.setattr(gate, "run_build_sync", lambda *_args: passed("build"))
    monkeypatch.setattr(gate, "scan_forbidden", lambda *_args, **_kwargs: passed("scan"))

    exit_code = gate.main([
        str(card_path), "--project-dir", str(tmp_path), "--no-r18",
        "--native-stage-routing", "--stage-entry-contract", str(contract_path),
        "-o", str(report_path),
    ])
    assert exit_code == 0
    report = report_path.read_text(encoding="utf-8")
    assert "audit_stage_entry_contracts.py: PASS" in report
    assert "audit_native_stage_architecture.py: PASS" in report
    assert "audit_stage_card_scripts.py: PASS" in report


@requires_sibling_skill
def test_final_gate_auto_discovers_sidecar_contract_for_title_card(load_script_module, tmp_path, monkeypatch):
    """标题路由卡不带任何阶段 CLI flag 时，main 必须自动发现项目 sidecar 合同并跑全链
    （final_delivery_gate.py 的 sidecar 自动发现分支此前无正例测试）"""
    gate = load_script_module("final_delivery_gate.py")
    card_path = tmp_path / "stage.json"
    report_path = tmp_path / "delivery.md"
    card_path.write_text(json.dumps(valid_card_v2(), ensure_ascii=False), encoding="utf-8")
    (tmp_path / "stage-entry-contract.json").write_text(
        json.dumps(valid_contract_v2(), ensure_ascii=False), encoding="utf-8")

    def passed(name: str):
        return gate.GateResult(name, "PASS")

    monkeypatch.setattr(gate, "run_validate", lambda _path: passed("validate"))
    monkeypatch.setattr(gate, "run_audit", lambda _path, _dir: passed("trigger"))
    monkeypatch.setattr(gate, "run_enrichment", lambda *_args: passed("enrichment"))
    monkeypatch.setattr(gate, "run_build_sync", lambda *_args: passed("build"))
    monkeypatch.setattr(gate, "scan_forbidden", lambda *_args, **_kwargs: passed("scan"))

    exit_code = gate.main([str(card_path), "--project-dir", str(tmp_path), "--no-r18", "-o", str(report_path)])
    assert exit_code == 0
    report = report_path.read_text(encoding="utf-8")
    assert "audit_stage_entry_contracts.py: PASS" in report
    assert "audit_native_stage_architecture.py: PASS" in report
    assert "audit_stage_card_scripts.py: PASS" in report


def test_final_gate_does_not_fall_back_to_legacy_p0_p6_when_contract_invalid(load_script_module, tmp_path, monkeypatch):
    """合同 schema 无效（mode 过期）时：真实病因必须可见，且不得回退 legacy P0-P6
    默认审计制造『缺少P#』假红噪声（stage-entry-contract-gate.md §5 的明文承诺）"""
    gate = load_script_module("final_delivery_gate.py")
    card_path = tmp_path / "stage.json"
    contract_path = tmp_path / "stage-entry-contract.json"
    report_path = tmp_path / "delivery.md"
    card_path.write_text(json.dumps(valid_card_v2(), ensure_ascii=False), encoding="utf-8")
    bad_contract = valid_contract_v2()
    bad_contract["mode"] = "native_greeting_stage"
    contract_path.write_text(json.dumps(bad_contract, ensure_ascii=False), encoding="utf-8")

    def passed(name: str):
        return gate.GateResult(name, "PASS")

    monkeypatch.setattr(gate, "run_validate", lambda _path: passed("validate"))
    monkeypatch.setattr(gate, "run_audit", lambda _path, _dir: passed("trigger"))
    monkeypatch.setattr(gate, "run_enrichment", lambda *_args: passed("enrichment"))
    monkeypatch.setattr(gate, "run_build_sync", lambda *_args: passed("build"))
    monkeypatch.setattr(gate, "scan_forbidden", lambda *_args, **_kwargs: passed("scan"))

    exit_code = gate.main([
        str(card_path), "--project-dir", str(tmp_path), "--no-r18",
        "--native-stage-routing", "--stage-entry-contract", str(contract_path),
        "-o", str(report_path),
    ])
    assert exit_code == 1
    report = report_path.read_text(encoding="utf-8")
    assert "leyu_large_native_greeting_stage_v1" in report
    assert "不回退 legacy P0-P6" in report
    assert "缺少P6" not in report
    assert "audit_stage_card_scripts.py" not in report


def test_documented_p_prefix_title_is_accepted(load_script_module):
    card = valid_card()
    card["data"]["first_mes"] = "【开场：P0·关系失衡｜作品标识】\n这是P0阶段的独立开场正文。"
    result = audit(load_script_module, card, valid_contract())
    assert not any("Greeting[0]" in error and "阶段标题" in error for error in result.errors)



def test_contract_uses_the_explicit_large_stage_policy(load_script_module):
    contract = valid_contract()
    contract["mode"] = "native_greeting_stage"

    result = audit(load_script_module, valid_card(), contract)

    assert any("leyu_large_native_greeting_stage_v1" in error for error in result.errors)


def test_required_packs_are_order_independent_but_must_be_exact(load_script_module):
    contract = valid_contract()
    contract["required_packs"] = list(reversed(packs()))

    result = audit(load_script_module, valid_card(), contract)

    assert result.errors == []


def test_enabled_entry_without_contract_is_a_delivery_error(load_script_module):
    card = valid_card()
    card["data"]["character_book"]["entries"].append(
        {
            "id": "orphan",
            "comment": "白佲心理档案",
            "content": "未声明职责的可见运行时内容。",
            "keys": ["白佲心理档案"],
            "secondary_keys": [],
            "enabled": True,
            "constant": False,
            "selective": False,
            "extensions": {},
        }
    )

    result = audit(load_script_module, card, valid_contract())

    assert any("未声明运行时职责" in error for error in result.errors)


def test_character_contract_requires_exact_natural_primary_key_and_working_example(load_script_module):
    card = valid_card()
    card["data"]["character_book"]["entries"].append(
        {
            "id": "character",
            "comment": "白佲人物速览",
            "content": "可运行的人物资料。",
            "keys": ["白佲深度档案"],
            "secondary_keys": [],
            "enabled": True,
            "constant": False,
            "selective": False,
            "extensions": {"match_whole_words": False},
        }
    )
    contract = valid_contract()
    contract["entries"]["白佲人物速览"] = {
        "role": "character",
        "natural_keys": ["白佲"],
        "load_examples": ["白佲走进客厅。"],
    }

    result = audit(load_script_module, card, contract)

    assert any("缺少声明的自然primary key" in error for error in result.errors)


def test_stage_pack_cannot_bind_to_another_stage_title(load_script_module):
    card = valid_card()
    card["data"]["character_book"]["entries"][0]["keys"] = [title("P1")]

    result = audit(load_script_module, card, valid_contract())

    assert any("阶段核心_P0" in error and "标题" in error for error in result.errors)


def test_greeting_allows_only_a_leading_complete_initvar_before_its_title(load_script_module):
    card = valid_card()
    card["data"]["first_mes"] = (
        "<initvar>\nroute_state: P0\n</initvar>\n"
        f"{title('P0')}\n这是P0阶段的独立开场正文。"
    )

    result = audit(load_script_module, card, valid_contract())

    assert result.errors == []


def test_greeting_rejects_visible_text_or_comment_before_its_title(load_script_module):
    card = valid_card()
    card["data"]["first_mes"] = (
        "<!-- 不能作为标题前缀的模型可见或工程注释 -->\n"
        f"{title('P0')}\n这是P0阶段的独立开场正文。"
    )

    result = audit(load_script_module, card, valid_contract())

    assert any("首个可见内容" in error for error in result.errors)


def test_stage_pack_requires_recursion_guards_and_selective_sync(load_script_module):
    card = valid_card()
    extensions = card["data"]["character_book"]["entries"][0]["extensions"]
    extensions["selective"] = False
    extensions.pop("prevent_recursion")
    extensions.pop("exclude_recursion")

    result = audit(load_script_module, card, valid_contract())

    assert any("extensions.selective" in error for error in result.errors)
    assert any("prevent_recursion=true" in error for error in result.errors)
    assert any("exclude_recursion=true" in error for error in result.errors)


def test_stage_pack_requires_explicit_empty_secondary_keys_and_extension_selective(load_script_module):
    card = valid_card()
    entry = card["data"]["character_book"]["entries"][0]
    entry.pop("secondary_keys")
    entry["extensions"].pop("selective")

    result = audit(load_script_module, card, valid_contract())

    assert any("必须显式secondary_keys=[]" in error for error in result.errors)
    assert any("必须extensions.selective=true" in error for error in result.errors)


def test_constant_role_must_be_an_enabled_runtime_entry(load_script_module):
    card = valid_card()
    card["data"]["character_book"]["entries"].append(
        {
            "id": "constant",
            "comment": "剧情导演与事件推进协议",
            "content": "这是应常驻的剧情导演协议。",
            "keys": [],
            "enabled": False,
            "constant": True,
            "selective": False,
            "extensions": {},
        }
    )
    contract = valid_contract()
    contract["entries"]["剧情导演与事件推进协议"] = {"role": "constant"}

    result = audit(load_script_module, card, contract)

    assert any("role=constant必须enabled=true" in error for error in result.errors)


def test_manual_role_must_remain_disabled(load_script_module):
    card = valid_card()
    card["data"]["character_book"]["entries"].append(
        {
            "id": "manual",
            "comment": "手动身份选开",
            "content": "手动启用时才加载的身份资料。",
            "keys": [],
            "enabled": True,
            "constant": False,
            "selective": False,
            "extensions": {},
        }
    )
    contract = valid_contract()
    contract["entries"]["手动身份选开"] = {"role": "manual"}

    result = audit(load_script_module, card, contract)

    assert any("role=manual必须enabled=false" in error for error in result.errors)


def test_stage_pack_requires_six_labeled_material_units(load_script_module):
    card = valid_card()
    card["data"]["character_book"]["entries"][0]["content"] = "【阶段核心_P0_01_素材】仅一项。"

    result = audit(load_script_module, card, valid_contract())

    assert any("阶段核心_P0" in error and "素材单元不足" in error for error in result.errors)


def test_stage_pack_rejects_six_empty_shell_units(load_script_module):
    card = valid_card()
    card["data"]["character_book"]["entries"][0]["content"] = "\n".join(
        f"【阶段核心_P0_{index:02d}_素材】空壳。" for index in range(1, 7)
    )

    result = audit(load_script_module, card, valid_contract())

    assert any("阶段核心_P0" in error and "素材单元过短" in error for error in result.errors)


def test_stage_pack_rejects_foreign_pack_or_stage_labels(load_script_module):
    card = valid_card()
    card["data"]["character_book"]["entries"][0]["content"] += "\n【事件库_P3_01_错误混入】不应混入其他包或阶段的素材。"

    result = audit(load_script_module, card, valid_contract())

    assert any("混入其他包/阶段素材标签" in error for error in result.errors)


def test_stage_pack_rejects_duplicate_material_identifiers(load_script_module):
    card = valid_card()
    entry = card["data"]["character_book"]["entries"][0]
    entry["content"] = entry["content"].replace("【阶段核心_P0_02_素材】", "【阶段核心_P0_01_素材】")

    result = audit(load_script_module, card, valid_contract())

    assert any("素材单元编号重复" in error for error in result.errors)


def test_model_visible_analysis_provenance_is_forbidden(load_script_module):
    card = valid_card()
    card["data"]["character_book"]["entries"][0]["content"] += "\n【源文档：12_阶段状态快照.md】"

    result = audit(load_script_module, card, valid_contract())

    assert any("分析层/构建残留" in error for error in result.errors)


@pytest.mark.parametrize("field, value", [
    ("mes_example", "【源文档：分析草稿.md】"),
    ("group_only_greetings", ["【证据标注：E-001】"]),
])
def test_model_visible_auxiliary_fields_cannot_hide_analysis_provenance(load_script_module, field, value):
    card = valid_card()
    card["data"][field] = value

    result = audit(load_script_module, card, valid_contract())

    assert any("分析层/构建残留" in error for error in result.errors)


def test_scene_contract_requires_a_real_shared_matcher_loading_example(load_script_module):
    card = valid_card()
    card["data"]["character_book"]["entries"].append(
        {
            "id": "scene",
            "comment": "场景·客厅",
            "content": "客厅场景素材。",
            "keys": ["客厅"],
            "secondary_keys": [],
            "enabled": True,
            "constant": False,
            "selective": False,
            "extensions": {"match_whole_words": False},
        }
    )
    contract = valid_contract()
    contract["entries"]["场景·客厅"] = {
        "role": "scene",
        "natural_keys": ["客厅"],
        "load_examples": ["厨房的灯还亮着。"],
    }

    result = audit(load_script_module, card, contract)

    assert any("load_examples未全部触发" in error for error in result.errors)


def test_every_declared_loading_example_must_match_shared_matcher(load_script_module):
    card = valid_card()
    card["data"]["character_book"]["entries"].append(
        {
            "id": "scene",
            "comment": "场景·客厅",
            "content": "客厅场景素材。",
            "keys": ["客厅"],
            "secondary_keys": [],
            "enabled": True,
            "constant": False,
            "selective": False,
            "extensions": {"match_whole_words": False},
        }
    )
    contract = valid_contract()
    contract["entries"]["场景·客厅"] = {
        "role": "scene",
        "natural_keys": ["客厅"],
        "load_examples": ["客厅的灯还亮着。", "厨房的灯还亮着。"],
    }

    result = audit(load_script_module, card, contract)

    assert any("load_examples未全部触发" in error for error in result.errors)


def test_final_delivery_gate_turns_contract_violation_into_fail(load_script_module, tmp_path):
    gate = load_script_module("final_delivery_gate.py")
    card = valid_card()
    card["data"]["character_book"]["entries"].append(
        {
            "id": "orphan",
            "comment": "未声明条目",
            "content": "运行时内容。",
            "keys": ["未声明条目"],
            "secondary_keys": [],
            "enabled": True,
            "constant": False,
            "selective": False,
            "extensions": {},
        }
    )
    card_path = tmp_path / "candidate.json"
    contract_path = tmp_path / "stage-entry-contract.json"
    card_path.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    contract_path.write_text(json.dumps(valid_contract(), ensure_ascii=False), encoding="utf-8")

    result = gate.run_stage_entry_contract(card_path, contract_path)

    assert result.status == "FAIL"
    assert any("未声明运行时职责" in error for error in result.errors)


def test_native_contract_mode_runs_sibling_architecture_audit_with_contract_manifest(load_script_module, tmp_path, monkeypatch):
    gate = load_script_module("final_delivery_gate.py")
    architecture_script = tmp_path / "audit_native_stage_architecture.py"
    script_audit_script = tmp_path / "audit_stage_card_scripts.py"
    architecture_script.write_text("# placeholder", encoding="utf-8")
    script_audit_script.write_text("# placeholder", encoding="utf-8")
    card_path = tmp_path / "candidate.json"
    card_path.write_text("{}", encoding="utf-8")

    def sibling(_skill: str, filename: str):
        return architecture_script if filename == architecture_script.name else script_audit_script

    class ArchitectureResult:
        failures: list[str] = []
        warnings: list[str] = []
        passes: list[str] = ["architecture audit passed"]

    class ArchitectureAudit:
        @staticmethod
        def audit_card(_card, *, manifest):
            seen["manifest"] = manifest
            return ArchitectureResult()

    class ScriptResult:
        failures: list[str] = []
        warnings: list[str] = []
        passes: list[str] = ["script audit passed"]

    class ScriptAudit:
        @staticmethod
        def audit_card(_card):
            return ScriptResult()

    seen: dict[str, dict] = {}

    def import_path(_name: str, path):
        if path == architecture_script:
            return ArchitectureAudit()
        assert path == script_audit_script
        return ScriptAudit()

    monkeypatch.setattr(gate, "sibling_skill_script", sibling)
    monkeypatch.setattr(gate, "import_script_path", import_path)

    manifest = {
        "route_mode": "native_greeting_title",
        "stages": stages(),
        "required_packs": packs(),
        "min_units_per_pack": 6,
    }
    results = gate.run_native_stage_routing(card_path, stage_manifest=manifest)

    assert [result.name for result in results] == [
        "audit_native_stage_architecture.py",
        "audit_stage_card_scripts.py",
    ]
    assert all(result.status == "PASS" for result in results)
    assert seen == {"manifest": manifest}


def test_native_stage_cli_requires_entry_contract(load_script_module):
    gate = load_script_module("final_delivery_gate.py")

    with pytest.raises(SystemExit) as exc_info:
        gate.main(["candidate.json", "--native-stage-routing"])

    # CLI 用法错误必须是 exit 4，不得与 exit 2（仅 warning 可人工确认交付）撞码
    assert exc_info.value.code == 4


def test_final_delivery_main_passes_contract_manifest_to_native_gates(load_script_module, tmp_path, monkeypatch):
    gate = load_script_module("final_delivery_gate.py")
    card_path = tmp_path / "candidate.json"
    contract_path = tmp_path / "stage-entry-contract.json"
    card_path.write_text("{}", encoding="utf-8")
    contract_path.write_text(json.dumps(valid_contract(), ensure_ascii=False), encoding="utf-8")
    seen: dict[str, dict] = {}

    def passed(name: str):
        return gate.GateResult(name, "PASS")

    monkeypatch.setattr(gate, "run_card_json_preflight", lambda _path: passed("preflight"))
    monkeypatch.setattr(gate, "run_validate", lambda _path: passed("validate"))
    monkeypatch.setattr(gate, "run_audit", lambda _path, _report_dir: passed("trigger"))
    monkeypatch.setattr(gate, "run_enrichment", lambda *_args: passed("enrichment"))
    monkeypatch.setattr(gate, "run_stage_entry_contract", lambda *_args: passed("contract"))
    monkeypatch.setattr(gate, "run_build_sync", lambda *_args: passed("build"))
    monkeypatch.setattr(gate, "scan_forbidden", lambda *_args, **_kwargs: passed("scan"))

    def native(_path, *, stage_manifest):
        seen["stage_manifest"] = stage_manifest
        return [passed("script audit")]

    monkeypatch.setattr(gate, "run_native_stage_routing", native)

    exit_code = gate.main([
        str(card_path),
        "--native-stage-routing",
        "--stage-entry-contract",
        str(contract_path),
        "--output",
        str(tmp_path / "report.md"),
    ])

    assert exit_code == 0
    manifest = seen["stage_manifest"]
    assert manifest["route_mode"] == "native_greeting_title"
    assert manifest["route_source"] == "greeting_title"
    assert manifest["architecture_mode"] == "stage_routing"
    assert manifest["stages"] == stages()
    assert manifest["required_packs"] == packs()
    assert manifest["phase_memory"]["system_prompt_anchor_required"] is True


def test_stage_entry_schema_v2_remains_orthogonal_to_narrative_contract(load_script_module):
    module = load_script_module("audit_stage_entry_contracts.py")

    manifest, errors = module.architecture_manifest_from_contract(valid_contract())

    assert errors == []
    assert manifest is not None
    assert "narrative_mode" not in manifest
    assert "runtime_state" not in manifest
    assert manifest["architecture_mode"] == "stage_routing"
