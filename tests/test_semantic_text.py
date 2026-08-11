from __future__ import annotations

import json
import subprocess
import sys

import pytest
from pathlib import Path


def card_with_entries(entries: list[dict]) -> dict:
    return {
        "data": {
            "character_book": {
                "entries": entries,
            }
        }
    }


def entry(comment: str, content: str) -> dict:
    return {
        "comment": comment,
        "content": content,
        "keys": [],
        "secondary_keys": [],
        "enabled": True,
        "constant": True,
        "selective": False,
    }


def manifest_for(
    comment: str,
    schema: str = "character_psychology_v1",
    module_type: str = "character_psychology",
) -> dict:
    return {
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
    }


def delivery_semantic_manifest_for(comment: str) -> dict:
    manifest = manifest_for(comment)
    manifest.update({
        "semantic_profile": "modular_semantic_v1",
        "contract_level": "standard",
        "project_id": "semantic-text-fixture",
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
        "world_modules": [],
        "projections": [{"semantic_ref": comment, "runtime_role": "character_module", "flat": {"load": "constant"}}],
    })
    return manifest


def valid_psychology() -> str:
    return """# 角色模块：示例角色｜核心心理与性格

## 条目作用

描述稳定心理锚点以及不同压力下的反应倾向。

## 核心锚点

- **核心需求：** 保持对局面的判断权。
- **核心恐惧：** 失去解释和退出的机会。

## 触发与响应

### 当公开追问发生时

优先判断现场压力，再从回避、试探或有限解释中选择反应。

## 不应误写

- 不把一次反应写成永久改变。
- 不替玩家完成决定。

## 可开放变化

- 反应强度和表达方式可以随关系与现场变化。
"""


def test_valid_semantic_markdown_module_passes(load_script_module):
    module = load_script_module("audit_semantic_text.py")
    comment = "角色/示例角色/核心心理与性格"
    issues = module.audit(
        card_with_entries([entry(comment, valid_psychology())]),
        manifest_for(comment),
        require_profile=True,
    )
    assert issues == []


def test_missing_heading_and_wrong_order_are_reported(load_script_module):
    module = load_script_module("audit_semantic_text.py")
    comment = "角色/示例角色/核心心理与性格"
    content = """描述稳定心理。

## 核心锚点

- 核心需求：保持判断权。

## 条目作用

本条描述心理。

## 可开放变化

可以随互动变化。
"""
    issues = module.audit(
        card_with_entries([entry(comment, content)]),
        manifest_for(comment),
        require_profile=True,
    )
    codes = {issue["code"] for issue in issues}
    assert "H1_MISSING" in codes
    assert "MISSING_REQUIRED_SECTION" in codes
    assert "SECTION_ORDER_INVALID" in codes


def test_duplicate_section_is_rejected(load_script_module):
    module = load_script_module("audit_semantic_text.py")
    comment = "角色/示例角色/核心心理与性格"
    content = valid_psychology().replace(
        "## 不应误写\n\n- 不把一次反应写成永久改变。",
        "## 不应误写\n\n- 不把一次反应写成永久改变。\n\n## 核心锚点\n\n- 重复标题不应出现。",
    )
    issues = module.audit(
        card_with_entries([entry(comment, content)]),
        manifest_for(comment),
        require_profile=True,
    )
    assert "DUPLICATE_SECTION" in {issue["code"] for issue in issues}


def test_indentation_dependent_yaml_tree_is_rejected(load_script_module):
    module = load_script_module("audit_semantic_text.py")
    comment = "角色/示例角色/核心心理与性格"
    content = valid_psychology() + "\n人格:\n  表层:\n    - 谨慎\n"
    issues = module.audit(
        card_with_entries([entry(comment, content)]),
        manifest_for(comment),
        require_profile=True,
    )
    assert "YAML_INDENTATION_DEPENDENCY" in {issue["code"] for issue in issues}


def test_content_schema_separates_place_from_psychology(load_script_module):
    module = load_script_module("audit_semantic_text.py")
    comment = "世界观/地点/示例地点"
    content = """# 地点模块：示例地点

## 条目作用

描述地点。

## 地点定位

用于交谈和观察。

## 空间布局

入口、公开区和后侧空间。

## 自然入口

通过营业、门和熟人介绍进入。

## 现实规则

旁观者、营业时间和退出路径有效。

## 不应误写

- 不在无入口时强行切换地点。

## 可开放变化

- 人员分布和停留顺序可以变化。
"""
    manifest = manifest_for(comment, "place_v1")
    manifest["module_records"][comment]["module_type"] = "place"
    issues = module.audit(
        card_with_entries([entry(comment, content)]),
        manifest,
        require_profile=True,
    )
    assert issues == []


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
def test_official_text_template_matches_its_schema(
    load_script_module,
    skill_root,
    template,
    comment,
    schema,
    module_type,
):
    module = load_script_module("audit_semantic_text.py")
    content = (skill_root / "templates" / template).read_text(encoding="utf-8")
    issues = module.audit(
        card_with_entries([entry(comment, content)]),
        manifest_for(comment, schema, module_type),
        require_profile=True,
    )
    assert issues == []


def test_module_type_must_match_content_schema(load_script_module):
    module = load_script_module("audit_semantic_text.py")
    comment = "角色/示例角色/核心心理与性格"
    manifest = manifest_for(comment, "character_psychology_v1", "place")
    issues = module.audit(
        card_with_entries([entry(comment, valid_psychology())]),
        manifest,
        require_profile=True,
    )
    assert "MODULE_TYPE_SCHEMA_MISMATCH" in {issue["code"] for issue in issues}


@pytest.mark.parametrize(
    ("comment", "schema", "module_type"),
    [
        ("角色/示例角色/语言与称谓", "character_psychology_v1", "character_psychology"),
        ("世界观/地点/示例地点", "character_psychology_v1", "character_psychology"),
        ("机制/互动机制/示例互动", "place_v1", "place"),
    ],
)
def test_comment_path_must_match_module_type(load_script_module, comment, schema, module_type):
    module = load_script_module("audit_semantic_text.py")
    if schema == "place_v1":
        content = """# 世界观模块：示例地点

## 条目作用

本条描述地点。

## 地点定位

用于测试。

## 空间布局

存在可观察入口。

## 自然入口

互动可以自然发生。

## 现实规则

现场条件会限制行动。

## 不应误写

不替玩家决定。

## 可开放变化

入口和后果可以变化。
"""
    else:
        content = valid_psychology()
    issues = module.audit(
        card_with_entries([entry(comment, content)]),
        manifest_for(comment, schema, module_type),
        require_profile=True,
    )
    assert "MODULE_PATH_TYPE_MISMATCH" in {issue["code"] for issue in issues}


def test_required_sections_must_be_level_two_headings(load_script_module):
    module = load_script_module("audit_semantic_text.py")
    comment = "角色/示例角色/核心心理与性格"
    content = """# 角色模块：示例角色

### 条目作用

描述稳定心理。

### 核心锚点

保持判断权。

### 触发与响应

根据现场压力选择回应。

### 不应误写

不替玩家决定。

### 可开放变化

反应强度可以变化。
"""
    issues = module.audit(
        card_with_entries([entry(comment, content)]),
        manifest_for(comment),
        require_profile=True,
    )
    assert "REQUIRED_SECTION_LEVEL_INVALID" in {issue["code"] for issue in issues}


def test_contract_profile_is_not_used_as_text_schema(load_script_module):
    module = load_script_module("audit_semantic_text.py")
    comment = "角色/示例角色/核心心理与性格"
    manifest = manifest_for(comment)
    manifest["contract_profile"] = "different_contract_owned_by_another_gate"
    manifest["module_records"][comment]["contract_profile"] = "different_contract_owned_by_another_gate"
    issues = module.audit(
        card_with_entries([entry(comment, valid_psychology())]),
        manifest,
        require_profile=True,
    )
    assert issues == []


def test_opt_in_profile_is_skipped_for_legacy_manifest(load_script_module):
    module = load_script_module("audit_semantic_text.py")
    comment = "角色/示例角色/核心心理与性格"
    issues = module.audit(
        card_with_entries([entry(comment, "legacy content")]),
        {},
    )
    assert issues == [{
        "level": "INFO",
        "code": "TEXT_PROFILE_NOT_ENABLED",
        "comment": "",
        "message": "text_profile 未启用，跳过 semantic Markdown 文本审计。",
    }]


def test_cli_returns_error_for_missing_required_text_section(skill_root, tmp_path):
    comment = "角色/示例角色/核心心理与性格"
    card_path = tmp_path / "card.json"
    manifest_path = tmp_path / "manifest.json"
    card_path.write_text(
        json.dumps(card_with_entries([entry(comment, "# 标题\n\n## 条目作用\n\n只有一节。")]), ensure_ascii=False),
        encoding="utf-8",
    )
    manifest_path.write_text(json.dumps(manifest_for(comment), ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(skill_root / "scripts" / "audit_semantic_text.py"), str(card_path), "--manifest", str(manifest_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 1
    assert "MISSING_REQUIRED_SECTION" in proc.stdout



def test_delivery_plan_runs_text_audit_when_profile_is_enabled(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card_path = tmp_path / "card.json"
    semantic_path = tmp_path / "semantic.json"
    build_path = tmp_path / "build_manifest.json"
    comment = "角色/示例角色/核心心理与性格"
    card_path.write_text(json.dumps(card_with_entries([entry(comment, valid_psychology())]), ensure_ascii=False), encoding="utf-8")
    semantic_path.write_text(json.dumps(delivery_semantic_manifest_for(comment), ensure_ascii=False), encoding="utf-8")
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
    plan = module.build_delivery_plan(card_path, build_path)
    checks = {check.name: check.status for check in plan.checks}
    assert checks["semantic text audit"] == "RUN"


def test_delivery_semantic_audit_returns_text_issues(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card_path = tmp_path / "card.json"
    semantic_path = tmp_path / "semantic.json"
    build_path = tmp_path / "build_manifest.json"
    comment = "角色/示例角色/核心心理与性格"
    card_path.write_text(json.dumps(card_with_entries([entry(comment, "# 标题\n\n## 条目作用\n\n只有一节。")]), ensure_ascii=False), encoding="utf-8")
    semantic_path.write_text(json.dumps(delivery_semantic_manifest_for(comment), ensure_ascii=False), encoding="utf-8")
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
    assert "MISSING_REQUIRED_SECTION" in {issue["code"] for issue in issues}
