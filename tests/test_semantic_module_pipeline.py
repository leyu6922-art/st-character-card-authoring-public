from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def semantic_manifest() -> dict:
    return {
        "semantic_profile": "modular_semantic_v1",
        "contract_level": "standard",
        "project_id": "semantic-fixture",
        "source_scope": {"canonical_sources": [], "excluded_sources": [], "source_hashes": {}},
        "player_anchor": {"mode": "{{user}}", "entity_id": "player"},
        "narrative_mode": "open_sandbox",
        "architecture_mode": "flat",
        "authoritative_route": "natural_keys",
        "authoritative_state": "narrative_only",
        "runtime_capabilities": ["natural_trigger", "open_sandbox"],
        "content_surface": "runtime_clean",
        "visibility_policy": {"model": "runtime_visible", "character_knowledge": "declared_per_module", "build_only": ["source_refs"]},
        "policy_bundle": "RULE_OPEN_CARD_V1",
        "characters": {"示例角色": {"entity_id": "char-example", "modules": ["核心心理与性格"]}},
        "world_modules": ["世界观/地点/示例地点"],
        "projections": [{"semantic_ref": "世界观/地点/示例地点", "runtime_role": "scene", "flat": {"load": "selective", "natural_keys": ["示例入口"]}}],
    }


def modern_semantic_manifest(comment: str, schema: str, module_type: str) -> dict:
    manifest = semantic_manifest()
    manifest.update({
        "text_profile": "semantic_markdown_v1",
        "text_metadata_policy": "generated",
        "contract_profile": "open_semantic_module_v1",
        "module_records": {
            comment: {
                "module_type": module_type,
                "text_profile": "semantic_markdown_v1",
                "content_schema": schema,
                "contract_profile": "open_semantic_module_v1",
            }
        },
    })
    manifest["characters"] = {}
    manifest["world_modules"] = []
    for key in (
        "event_modules",
        "scene_modules",
        "relation_modules",
        "knowledge_modules",
        "organization_modules",
        "rule_modules",
        "mechanism_modules",
    ):
        manifest[key] = []

    if comment.startswith("角色/"):
        _namespace, entity, module = comment.split("/", 2)
        manifest["characters"] = {entity: {"entity_id": "char-example", "modules": [module]}}
        runtime_role = "character_module"
    elif comment.startswith("世界观/"):
        manifest["world_modules"] = [comment]
        runtime_role = "world_module"
    elif comment.startswith("关系/"):
        manifest["relation_modules"] = [comment]
        runtime_role = "world_module"
    else:
        manifest["mechanism_modules"] = [comment]
        runtime_role = "event_candidate"
    manifest["projections"] = [{
        "semantic_ref": comment,
        "runtime_role": runtime_role,
        "flat": {"load": "constant"},
    }]
    return manifest


def role_content() -> str:
    return """条目作用：核心角色档案。\n核心锚点：示例角色的身份与关系。\n触发条件：听见异常时。\n具体表现：先观察再询问。\n特质交叠：谨慎与好奇同时出现时先试探。\n语言与称谓：对{{user}}使用正式称谓。\n信息边界：不知道未被告知的后台事实。\n不应误写：不能替{{user}}决定。\n可开放变化：地点、顺序和关系推进可由互动改变。"""


def place_content() -> str:
    return """地点定位：调查与交谈空间。\n启用时间：当前场景即可自然到达。\n空间布局：入口、公开区、内侧桌位和后门。\n现实规则：营业时间、门禁和旁观者视线有效。\n场景边界：不会无前提发生不可逆结果。\n剧情功能：承载观察、谈判和候选事件入口。\n自然入口：门、灯、桌位、钥匙和营业。\n可开放变化：玩家可改变停留、离开和调查顺序。"""


def markdown_role_content() -> str:
    return """# 角色模块：示例角色｜核心心理与性格

## 条目作用

描述稳定心理。

## 核心锚点

- 核心需求：保持判断权。

## 触发与响应

根据现场压力选择试探或有限回应。

## 具体表现

先观察，再回应。

## 特质交叠

谨慎与好奇同时存在。

## 语言与称谓

保持正式称谓。

## 信息边界

只使用已确认信息。

## 不应误写

不替玩家决定。

## 可开放变化

反应强度可以变化。"""


def markdown_place_content() -> str:
    return """# 地点模块：示例地点

## 条目作用

描述地点的可用范围。

## 地点定位

用于交谈和观察。

## 启用时间

当前场景即可自然到达。

## 空间布局

入口、公开区和内侧空间。

## 自然入口

通过营业、门或熟人进入。

## 现实规则

门禁、旁观者和退出路径有效。

## 场景边界

不可逆结果需要互动前提。

## 剧情功能

承载调查与候选入口。

## 不应误写

不无前提切换地点。

## 可开放变化

人员分布和停留顺序可以变化。"""


def card_with_entries(entries: list[dict]) -> dict:
    return {"data": {"name": "semantic-fixture", "description": "fixture", "first_mes": "场景开始，等待{{user}}输入。", "character_book": {"name": "semantic-fixture-world", "entries": entries}}}


def entry(comment: str, content: str) -> dict:
    return {"comment": comment, "content": content, "keys": [], "secondary_keys": [], "enabled": True, "constant": True, "selective": False}


def build_v2_manifest(**overrides) -> dict:
    manifest = {
        "schema_version": 2,
        "prototype": "A",
        "prototype_confidence": "high",
        "prototype_reason": ["test fixture"],
        "content_mode": "safe",
        "narrative_mode": "open_sandbox",
        "event_mode": "open_situation_seed",
        "event_policy": "candidate_pool",
        "transition_policy": "none",
        "corpus_mode": "curated_anchor_set",
        "sandbox_scope": "focused",
        "routing_mode": "flat",
        "runtime_driver": "native_st",
        "runtime_state": {"authority": "none", "update_mode": "manual", "recovery_policy": "greeting_baseline", "reliability": "best_effort"},
        "route_policy": "player_led",
        "semantic_manifest": "build/semantic-module-manifest.json",
        "canonical_sources": [],
    }
    manifest.update(overrides)
    return manifest


def write_project(tmp_path: Path, *, manifest: dict | None = None, card: dict | None = None):
    (tmp_path / "build").mkdir(exist_ok=True)
    card_path = tmp_path / "card.json"
    card_path.write_text(json.dumps(card or card_with_entries([
        entry("角色/示例角色/核心心理与性格", role_content()),
        entry("世界观/地点/示例地点", place_content()),
    ]), ensure_ascii=False), encoding="utf-8")
    semantic_path = tmp_path / "build" / "semantic-module-manifest.json"
    semantic_path.write_text(json.dumps(manifest or semantic_manifest(), ensure_ascii=False), encoding="utf-8")
    build_manifest = {
        "schema_version": 1,
        "prototype": "A",
        "prototype_confidence": "high",
        "prototype_reason": ["test fixture"],
        "content_mode": "safe",
        "routing_mode": "flat",
        "runtime_driver": "native_st",
        "runtime_state": {"authority": "none"},
        "greeting_mode": "player_prose",
        "greeting_appendix_standard": "none",
        "require_build": False,
        "canonical_sources": [],
        "source_coverage_required": False,
        "semantic_manifest": "build/semantic-module-manifest.json",
    }
    build_path = tmp_path / "build_manifest.json"
    build_path.write_text(json.dumps(build_manifest, ensure_ascii=False), encoding="utf-8")
    return card_path, semantic_path, build_path


def test_manifest_alignment_accepts_matching_open_flat_contract(load_script_module):
    module = load_script_module("audit_manifest_alignment.py")
    issues = module.audit_manifest_alignment(build_v2_manifest(), semantic_manifest())
    assert issues == []


def test_manifest_alignment_rejects_route_and_narrative_conflicts(load_script_module):
    module = load_script_module("audit_manifest_alignment.py")
    delivery = build_v2_manifest(routing_mode="native_greeting_title", narrative_mode="soft_stage")
    issues = module.audit_manifest_alignment(delivery, semantic_manifest())
    codes = {issue["code"] for issue in issues}
    assert "ARCHITECTURE_ROUTE_MISMATCH" in codes
    assert "NARRATIVE_MODE_MISMATCH" in codes


def test_manifest_alignment_rejects_explicit_source_scope_drift(load_script_module):
    module = load_script_module("audit_manifest_alignment.py")
    delivery = build_v2_manifest(canonical_sources=["source/current.txt"])
    semantic = semantic_manifest()
    semantic["source_scope"]["canonical_sources"] = ["source/other.txt"]
    issues = module.audit_manifest_alignment(delivery, semantic)
    assert any(issue["code"] == "SOURCE_SCOPE_MISMATCH" for issue in issues)


def test_manifest_alignment_rejects_one_sided_empty_source_scope(load_script_module):
    module = load_script_module("audit_manifest_alignment.py")
    delivery = build_v2_manifest(canonical_sources=["source/current.txt"])
    semantic = semantic_manifest()
    semantic["source_scope"]["canonical_sources"] = []
    issues = module.audit_manifest_alignment(delivery, semantic)
    assert any(issue["code"] == "SOURCE_SCOPE_MISMATCH" for issue in issues)


def test_manifest_alignment_uses_project_root_for_both_source_scopes(load_script_module, tmp_path):
    module = load_script_module("audit_manifest_alignment.py")
    delivery = build_v2_manifest(canonical_sources=["source/current.txt"])
    semantic = semantic_manifest()
    semantic["source_scope"]["canonical_sources"] = ["source/current.txt"]
    issues = module.audit_manifest_alignment(
        delivery,
        semantic,
        delivery_base=tmp_path,
        semantic_base=tmp_path / "build",
    )
    assert issues == []


def test_manifest_alignment_rejects_runtime_driver_and_capability_conflict(load_script_module):
    module = load_script_module("audit_manifest_alignment.py")
    delivery = build_v2_manifest(routing_mode="native_greeting_title", runtime_driver="native_st")
    semantic = semantic_manifest()
    semantic["architecture_mode"] = "mvu"
    semantic["runtime_capabilities"] = ["mvu"]
    issues = module.audit_manifest_alignment(delivery, semantic)
    codes = {issue["code"] for issue in issues}
    assert "RUNTIME_DRIVER_MISMATCH" in codes
    assert "RUNTIME_CAPABILITY_MISMATCH" in codes


def test_manifest_alignment_rejects_unreliable_stat_state_authority(load_script_module):
    module = load_script_module("audit_manifest_alignment.py")
    delivery = build_v2_manifest(runtime_state={"authority": "prompt_record"})
    semantic = semantic_manifest()
    semantic["authoritative_state"] = "stat_data"
    issues = module.audit_manifest_alignment(delivery, semantic)
    assert "AUTHORITATIVE_STATE_MISMATCH" in {issue["code"] for issue in issues}


def test_open_route_negated_lock_terms_do_not_trigger(load_script_module):
    module = load_script_module("audit_semantic_modules.py")
    content = """条目作用：开放路线边界。\n核心锚点：事件只提供候选入口。\n具体表现：等待玩家输入。\n不应误写：不得采用固定顺序，也不能声称必须发生。\n可开放变化：由互动决定后续。"""
    issues = module.audit(card_with_entries([
        entry("角色/示例角色/开放路线", content),
        entry("世界观/地点/示例地点", place_content()),
    ]), semantic_manifest())
    assert "OPEN_ROUTE_LOCKED" not in {issue["code"] for issue in issues}


def test_formal_event_namespace_is_not_skipped(load_script_module):
    module = load_script_module("audit_semantic_modules.py")
    content = """条目作用：候选事件入口。\n核心锚点：事件不是固定事实。\n具体表现：等待自然触发。\n可开放变化：必须发生。"""
    issues = module.audit(card_with_entries([
        entry("事件/候选/雨夜拜访", content),
        entry("世界观/地点/示例地点", place_content()),
    ]), semantic_manifest())
    assert "OPEN_ROUTE_LOCKED" in {issue["code"] for issue in issues}


def test_standard_contract_requires_declared_modules(load_script_module):
    module = load_script_module("audit_semantic_modules.py")
    manifest = semantic_manifest()
    manifest.pop("characters")
    manifest.pop("world_modules")
    issues = module.audit(card_with_entries([
        entry("角色/示例角色/核心心理与性格", role_content()),
        entry("世界观/地点/示例地点", place_content()),
    ]), manifest)
    assert "MISSING_SEMANTIC_MODULES" in {issue["code"] for issue in issues}


def test_formal_mechanism_namespace_and_type_are_registered(load_script_module):
    module = load_script_module("audit_semantic_modules.py")
    manifest = semantic_manifest()
    manifest["mechanism_modules"] = ["机制/互动机制/示例互动"]
    manifest["modules"] = {
        "机制/互动机制/示例互动": {"module_type": "interaction_mechanism"},
    }
    content = """核心锚点：互动机制是候选入口。
具体表现：等待条件满足。
可开放变化：可以被打断或偏离。
"""
    issues = module.audit(card_with_entries([
        entry("角色/示例角色/核心心理与性格", role_content()),
        entry("世界观/地点/示例地点", place_content()),
        entry("机制/互动机制/示例互动", content),
    ]), manifest)
    assert "BAD_MODULE_TYPE" not in {issue["code"] for issue in issues}
    assert any(
        issue["code"] == "MISSING_SEMANTIC_FIELD"
        and issue["comment"] == "机制/互动机制/示例互动"
        for issue in issues
    )


def test_interaction_mechanism_without_event_candidate_role_is_not_locked(load_script_module):
    module = load_script_module("audit_semantic_modules.py")
    comment = "机制/互动机制/示例互动"
    manifest = modern_semantic_manifest(comment, "interaction_mechanism_v1", "interaction_mechanism")
    manifest["projections"][0]["runtime_role"] = "world_module"
    card = card_with_entries([entry(comment, "机制必须发生，之后必然进入下一步。")])
    issues = module.audit(card, manifest)
    assert "OPEN_ROUTE_LOCKED" not in {issue["code"] for issue in issues}


def test_path_type_mismatch_is_rejected_by_unified_delivery(
    load_script_module,
    skill_root,
    tmp_path,
):
    module = load_script_module("run_delivery.py")
    comment = "角色/示例角色/语言与称谓"
    card_path = tmp_path / "card.json"
    semantic_path = tmp_path / "semantic.json"
    build_path = tmp_path / "build_manifest.json"
    content = (skill_root / "templates" / "semantic-character-psychology-v1.md").read_text(encoding="utf-8")
    card_path.write_text(json.dumps(card_with_entries([entry(comment, content)]), ensure_ascii=False), encoding="utf-8")
    semantic_path.write_text(
        json.dumps(modern_semantic_manifest(comment, "character_psychology_v1", "character_psychology"), ensure_ascii=False),
        encoding="utf-8",
    )
    build_path.write_text(json.dumps({
        "schema_version": 1,
        "prototype": "A",
        "routing_mode": "flat",
        "runtime_driver": "native_st",
        "runtime_state": {"authority": "none"},
        "narrative_mode": "open_sandbox",
        "greeting_mode": "player_prose",
        "semantic_manifest": "semantic.json",
    }, ensure_ascii=False), encoding="utf-8")
    issues = module.run_semantic_audit(card_path, build_path)
    assert "MODULE_PATH_TYPE_MISMATCH" in {issue["code"] for issue in issues}


def test_interaction_mechanism_event_candidate_enforces_open_route_lock(
    load_script_module,
    skill_root,
    tmp_path,
):
    module = load_script_module("run_delivery.py")
    comment = "机制/互动机制/示例互动"
    card_path = tmp_path / "card.json"
    semantic_path = tmp_path / "semantic.json"
    build_path = tmp_path / "build_manifest.json"
    content = (skill_root / "templates" / "semantic-interaction-mechanism-v1.md").read_text(encoding="utf-8")
    content = content.replace("[谁可能提出，什么现实需求会引出，玩家如何发现]", "机制必须发生，之后必然进入下一步。")
    card_path.write_text(json.dumps(card_with_entries([entry(comment, content)]), ensure_ascii=False), encoding="utf-8")
    semantic_path.write_text(
        json.dumps(modern_semantic_manifest(comment, "interaction_mechanism_v1", "interaction_mechanism"), ensure_ascii=False),
        encoding="utf-8",
    )
    build_path.write_text(json.dumps({
        "schema_version": 1,
        "prototype": "A",
        "routing_mode": "flat",
        "runtime_driver": "native_st",
        "runtime_state": {"authority": "none"},
        "narrative_mode": "open_sandbox",
        "greeting_mode": "player_prose",
        "semantic_manifest": "semantic.json",
    }, ensure_ascii=False), encoding="utf-8")
    issues = module.run_semantic_audit(card_path, build_path)
    assert "OPEN_ROUTE_LOCKED" in {issue["code"] for issue in issues}


@pytest.mark.parametrize(
    ("template", "comment", "schema", "module_type"),
    [
        ("semantic-character-identity-v1.md", "角色/示例角色/基础信息与关系锚点", "character_identity_v1", "character_identity"),
        ("semantic-character-psychology-v1.md", "角色/示例角色/核心心理与性格", "character_psychology_v1", "character_psychology"),
        ("semantic-character-language-v1.md", "角色/示例角色/语言与称谓", "character_language_v1", "character_language"),
        ("semantic-place-v1.md", "世界观/地点/示例地点", "place_v1", "place"),
        ("semantic-interaction-mechanism-v1.md", "机制/互动机制/示例互动", "interaction_mechanism_v1", "interaction_mechanism"),
        ("semantic-relationship-v1.md", "关系/示例关系/当前关系", "relationship_v1", "relationship"),
    ],
)
def test_official_template_passes_unified_semantic_audit(
    load_script_module,
    skill_root,
    tmp_path,
    template,
    comment,
    schema,
    module_type,
):
    module = load_script_module("run_delivery.py")
    card_path = tmp_path / "card.json"
    semantic_path = tmp_path / "semantic.json"
    build_path = tmp_path / "build_manifest.json"
    content = (skill_root / "templates" / template).read_text(encoding="utf-8")
    card_path.write_text(json.dumps(card_with_entries([entry(comment, content)]), ensure_ascii=False), encoding="utf-8")
    semantic_path.write_text(
        json.dumps(modern_semantic_manifest(comment, schema, module_type), ensure_ascii=False),
        encoding="utf-8",
    )
    build_path.write_text(json.dumps({
        "schema_version": 1,
        "prototype": "A",
        "routing_mode": "flat",
        "runtime_driver": "native_st",
        "runtime_state": {"authority": "none"},
        "narrative_mode": "open_sandbox",
        "greeting_mode": "player_prose",
        "semantic_manifest": "semantic.json",
    }, ensure_ascii=False), encoding="utf-8")
    issues = module.run_semantic_audit(card_path, build_path)
    assert issues == []


def test_projection_must_reference_a_card_module(load_script_module):
    module = load_script_module("audit_semantic_modules.py")
    manifest = semantic_manifest()
    manifest["projections"][0]["semantic_ref"] = "MOD-NOT-FOUND"
    issues = module.audit(card_with_entries([
        entry("角色/示例角色/核心心理与性格", role_content()),
        entry("世界观/地点/示例地点", place_content()),
    ]), manifest)
    assert "PROJECTION_REF_NOT_FOUND" in {issue["code"] for issue in issues}


def test_full_contract_requires_nonempty_structured_registries(load_script_module):
    module = load_script_module("audit_semantic_modules.py")
    manifest = semantic_manifest()
    manifest["contract_level"] = "full"
    manifest.update({"entities": [], "facts": [], "relations": [], "knowledge": []})
    issues = module.audit(card_with_entries([
        entry("角色/示例角色/核心心理与性格", role_content()),
        entry("世界观/地点/示例地点", place_content()),
    ]), manifest)
    codes = {issue["code"] for issue in issues}
    assert "EMPTY_ENTITY_REGISTRY" in codes
    assert "EMPTY_FACT_REGISTRY" in codes
    assert "EMPTY_RELATION_REGISTRY" in codes
    assert "EMPTY_KNOWLEDGE_REGISTRY" in codes


def test_flat_projection_requires_flat_target(load_script_module):
    module = load_script_module("audit_semantic_modules.py")
    manifest = semantic_manifest()
    manifest["projections"][0].pop("flat")
    issues = module.audit(card_with_entries([
        entry("角色/示例角色/核心心理与性格", role_content()),
        entry("世界观/地点/示例地点", place_content()),
    ]), manifest)
    assert "PROJECTION_TARGET_MISSING" in {issue["code"] for issue in issues}


def test_canonical_assembler_preserves_semantic_modules_through_delivery(load_script_module, tmp_path):
    source_project = Path(__file__).resolve().parents[1] / "references" / "audit" / "fixtures" / "good_build_nested"
    project = tmp_path / "good_build_nested"
    shutil.copytree(source_project, project)

    entries_path = project / "build" / "all_entries.json"
    entries = json.loads(entries_path.read_text(encoding="utf-8"))
    template = entries[0]
    role_entry = json.loads(json.dumps(template, ensure_ascii=False))
    role_entry.update({"id": 90, "comment": "角色/示例角色/核心心理与性格", "content": role_content(), "keys": []})
    place_entry = json.loads(json.dumps(template, ensure_ascii=False))
    place_entry.update({"id": 91, "comment": "世界观/地点/示例地点", "content": place_content(), "keys": []})
    entries.extend([role_entry, place_entry])
    for index, item in enumerate(entries):
        item["id"] = index
    entries_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    semantic_path = project / "build" / "semantic-module-manifest.json"
    semantic_path.write_text(json.dumps(semantic_manifest(), ensure_ascii=False, indent=2), encoding="utf-8")
    build_path = project / "build_manifest.json"
    build_path.write_text(json.dumps({
        "schema_version": 1,
        "prototype": "A",
        "routing_mode": "flat",
        "runtime_driver": "native_st",
        "runtime_state": {"authority": "none"},
        "greeting_mode": "player_prose",
        "semantic_manifest": "build/semantic-module-manifest.json",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    assemble = project / "build" / "assemble_card.py"
    assembled = subprocess.run([sys.executable, str(assemble)], capture_output=True, text=True)
    assert assembled.returncode == 0, assembled.stderr

    final_path = project / "good_build_nested.json"
    sync = load_script_module("check_build_sync.py")
    status, sync_issues, _notes = sync.check_build_sync(final_path, project, require_build=True)
    assert status in {"PASS", "WARN"}, sync_issues
    runner = load_script_module("run_delivery.py")
    assert runner.run_semantic_audit(final_path, build_path) == []
    final = json.loads(final_path.read_text(encoding="utf-8"))
    final_comments = {item.get("comment") for item in final["data"]["character_book"]["entries"]}
    assert {"角色/示例角色/核心心理与性格", "世界观/地点/示例地点"} <= final_comments


def test_module_registry_requires_explicit_module_type(load_script_module):
    module = load_script_module("audit_semantic_modules.py")
    manifest = semantic_manifest()
    manifest["modules"] = {"MOD-CHAR-001": {"owner_entity": "CHAR-001"}}
    issues = module.audit(card_with_entries([
        entry("角色/示例角色/核心心理与性格", role_content()),
        entry("世界观/地点/示例地点", place_content()),
    ]), manifest)
    assert "BAD_MODULE_TYPE" in {issue["code"] for issue in issues}


def test_standard_semantic_fixture_passes(load_script_module):
    module = load_script_module("audit_semantic_modules.py")
    issues = module.audit(card_with_entries([
        entry("角色/示例角色/核心心理与性格", role_content()),
        entry("世界观/地点/示例地点", place_content()),
    ]), semantic_manifest())
    assert issues == []


def test_official_semantic_manifest_template_is_executable(load_script_module, tmp_path):
    template_path = Path(__file__).resolve().parents[1] / "templates" / "semantic-module-manifest.example.json"
    template = json.loads(template_path.read_text(encoding="utf-8-sig"))
    card = card_with_entries([
        *[
            entry(f"角色/{character}/{module_name}", markdown_role_content())
            for character, metadata in template["characters"].items()
            for module_name in metadata["modules"]
        ],
        *[
            entry(comment, markdown_place_content() if "/地点/" in comment else markdown_role_content())
            for comment in template["world_modules"]
        ],
    ])
    semantic = load_script_module("audit_semantic_modules.py")
    assert semantic.audit(card, template, require_profile=True) == []

    card_path = tmp_path / "card.json"
    semantic_path = tmp_path / "build" / "semantic-module-manifest.json"
    build_path = tmp_path / "build_manifest.json"
    semantic_path.parent.mkdir()
    card_path.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    semantic_path.write_text(json.dumps(template, ensure_ascii=False), encoding="utf-8")
    build_path.write_text(json.dumps({
        "schema_version": 1,
        "prototype": "A",
        "routing_mode": "flat",
        "runtime_driver": "native_st",
        "runtime_state": {"authority": "none"},
        "greeting_mode": "player_prose",
        "canonical_sources": [],
        "semantic_manifest": "build/semantic-module-manifest.json",
    }, ensure_ascii=False), encoding="utf-8")
    runner = load_script_module("run_delivery.py")
    assert runner.run_semantic_audit(card_path, build_path) == []


def test_semantic_gate_catches_missing_contract_and_locked_open_route(load_script_module):
    module = load_script_module("audit_semantic_modules.py")
    manifest = semantic_manifest()
    manifest.pop("authoritative_route")
    card = card_with_entries([
        entry("角色/示例角色/开放路线", "条目作用：候选路线。核心锚点：开放窗口。具体表现：等待玩家。\n不应误写：不能替玩家决定。\n可开放变化：固定顺序，必须发生。"),
        entry("世界观/地点/示例地点", place_content()),
    ])
    issues = module.audit(card, manifest)
    codes = {issue["code"] for issue in issues}
    assert "MISSING_PROJECT_CONTRACT" in codes
    assert "OPEN_ROUTE_LOCKED" in codes


def test_semantic_gate_catches_declared_missing_and_broken_reference(load_script_module):
    module = load_script_module("audit_semantic_modules.py")
    manifest = semantic_manifest()
    manifest["characters"]["示例角色"]["modules"].append("不存在的模块")
    card = card_with_entries([
        entry("角色/示例角色/核心心理与性格", role_content() + "\n关联：世界观/地点/不存在地点"),
        entry("世界观/地点/示例地点", place_content()),
    ])
    issues = module.audit(card, manifest)
    codes = {issue["code"] for issue in issues}
    assert "DECLARED_MODULE_MISSING" in codes
    assert "BROKEN_MODULE_REFERENCE" in codes


def test_semantic_cli_warning_returns_exit_two(skill_root, tmp_path):
    card_path = tmp_path / "card.json"
    card_path.write_text(json.dumps(card_with_entries([]), ensure_ascii=False), encoding="utf-8")
    manifest_path = tmp_path / "semantic.json"
    manifest_path.write_text(json.dumps({"semantic_profile": "modular_semantic_v1"}, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run([
        sys.executable,
        str(skill_root / "scripts" / "audit_semantic_modules.py"),
        str(card_path),
        "--manifest",
        str(manifest_path),
    ], capture_output=True, text=True)
    assert proc.returncode == 2
    assert "CONTRACT_LEVEL_MISSING" in proc.stdout


def test_legacy_semantic_path_is_explicitly_skipped(load_script_module):
    module = load_script_module("audit_semantic_modules.py")
    issues = module.audit(card_with_entries([]), {})
    assert issues == [{
        "level": "INFO",
        "code": "PROFILE_NOT_ENABLED",
        "comment": "",
        "message": "semantic_profile 未启用，跳过模块化语义门控。",
    }]


def test_build_manifest_connects_semantic_gate_to_runner(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card_path, semantic_path, build_path = write_project(tmp_path)
    plan = module.build_delivery_plan(card_path, build_path)
    assert any(check.name == "manifest alignment" and check.status == "RUN" for check in plan.checks)
    assert any(check.name == "semantic module audit" and check.status == "RUN" for check in plan.checks)
    assert module.run_semantic_audit(card_path, build_path) == []
    assert semantic_path.is_file()


def test_runner_blocks_manifest_alignment_before_final_gate(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card_path, semantic_path, build_path = write_project(tmp_path)
    semantic = semantic_manifest()
    semantic["architecture_mode"] = "native_stage"
    semantic_path.write_text(json.dumps(semantic, ensure_ascii=False), encoding="utf-8")
    issues = module.run_semantic_audit(card_path, build_path)
    assert any(issue["code"] == "ARCHITECTURE_ROUTE_MISMATCH" for issue in issues)


def test_runner_blocks_bad_opt_in_semantic_manifest_before_final_gate(skill_root, tmp_path):
    card_path, semantic_path, build_path = write_project(tmp_path)
    bad = semantic_manifest()
    bad.pop("authoritative_route")
    semantic_path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(skill_root / "scripts" / "run_delivery.py"), str(card_path), "--manifest", str(build_path)],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=60,
    )
    assert proc.returncode == 1
    assert "SEMANTIC ERROR MISSING_PROJECT_CONTRACT" in proc.stdout
    assert "NARRATIVE ERROR" not in proc.stdout


def test_runner_blocks_declared_manifest_without_profile(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card_path, semantic_path, build_path = write_project(tmp_path)
    bad = semantic_manifest()
    bad.pop("semantic_profile")
    semantic_path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    issues = module.run_semantic_audit(card_path, build_path)
    assert any(issue["code"] == "SEMANTIC_PROFILE_MISMATCH" and issue["level"] == "ERROR" for issue in issues)


def test_direct_semantic_cli_rejects_explicit_manifest_without_profile(skill_root, tmp_path):
    card = tmp_path / "card.json"
    card.write_text(json.dumps(card_with_entries([])), encoding="utf-8")
    manifest = tmp_path / "semantic-module-manifest.json"
    manifest.write_text(json.dumps({"contract_level": "standard"}), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(skill_root / "scripts" / "audit_semantic_modules.py"), str(card), "--manifest", str(manifest)],
        text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=60,
    )
    assert proc.returncode == 1
    assert "SEMANTIC_PROFILE_MISMATCH" in proc.stdout


def test_semantic_warning_raises_delivery_floor_without_overriding_error(load_script_module):
    module = load_script_module("run_delivery.py")
    assert module.semantic_status_floor([]) == 0
    assert module.semantic_status_floor([{"level": "INFO"}]) == 0
    assert module.semantic_status_floor([{"level": "WARNING"}]) == 2
    assert module.semantic_status_floor([{"level": "ERROR"}, {"level": "WARNING"}]) == 1


def test_runner_legacy_manifest_keeps_semantic_gate_skipped(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card_path = tmp_path / "card.json"
    card_path.write_text("{}", encoding="utf-8")
    build_path = tmp_path / "build_manifest.json"
    build_path.write_text(json.dumps({"schema_version": 1, "prototype": "A", "routing_mode": "flat", "greeting_mode": "player_prose"}), encoding="utf-8")
    plan = module.build_delivery_plan(card_path, build_path)
    checks = {check.name: check.status for check in plan.checks}
    assert checks["semantic module audit"] == "SKIP"
    assert module.run_semantic_audit(card_path, build_path) == []


def test_content_modules_assemble_before_semantic_gate(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card_path, semantic_path, build_path = write_project(tmp_path)
    content = tmp_path / "content"
    content.mkdir()
    (content / "role.txt").write_text(role_content(), encoding="utf-8")
    (content / "place.txt").write_text(place_content(), encoding="utf-8")
    assembler = tmp_path / "assemble_fixture.py"
    assembler.write_text(
        """import json\nfrom pathlib import Path\nroot = Path(__file__).parent\nrole = (root / 'content/role.txt').read_text(encoding='utf-8')\nplace = (root / 'content/place.txt').read_text(encoding='utf-8')\nentry = lambda comment, content: {'comment': comment, 'content': content, 'keys': [], 'secondary_keys': [], 'enabled': True, 'constant': True, 'selective': False}\ncard = {'data': {'character_book': {'entries': [entry('角色/示例角色/核心心理与性格', role), entry('世界观/地点/示例地点', place)]}}}\n(root / 'card.json').write_text(json.dumps(card, ensure_ascii=False), encoding='utf-8')\n""",
        encoding="utf-8",
    )
    subprocess.run([sys.executable, str(assembler)], check=True)
    assert card_path.is_file()
    assert semantic_path.is_file()
    assert module.run_semantic_audit(card_path, build_path) == []
