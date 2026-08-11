#!/usr/bin/env python3
"""Audit modular semantic worldbook entries and the opt-in project contract.

The audit is opt-in: a manifest must declare semantic_profile=modular_semantic_v1.
When contract_level is present, M0 project/runtime fields and Standard/Full
projection requirements are checked as well. This keeps legacy cards unchanged
while making the new content contract executable.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROLE_REQUIRED = {
    "基础信息与关系锚点": ["条目作用", "核心锚点", "不应误写", "可开放变化"],
    "外显与生活状态": ["条目作用", "核心锚点", "具体表现", "可开放变化"],
    "核心心理与性格": ["条目作用", "核心锚点", "触发条件", "具体表现", "特质交叠", "不应误写", "可开放变化"],
    "行为响应与特质交叠": ["条目作用", "触发条件", "具体表现", "特质交叠", "可开放变化"],
    "语言与称谓": ["条目作用", "核心锚点", "语言与称谓", "具体表现", "不应误写", "可开放变化"],
    "关系网与情感动态": ["条目作用", "核心锚点", "信息边界", "具体表现", "不应误写", "可开放变化"],
    "场景物件与职业机制": ["条目作用", "核心锚点", "具体表现", "信息边界", "可开放变化"],
    "信息边界与误写红线": ["条目作用", "信息边界", "不应误写", "可开放变化"],
}
WORLD_REQUIRED = {
    "地点": [
        "地点定位", "启用时间", "空间布局", "现实规则", "场景边界",
        "剧情功能", "自然入口", "可开放变化",
    ],
    "时间": ["条目作用", "时间", "动线", "信息边界", "可开放变化"],
}
GENERIC_MODULE_REQUIRED = ["条目作用", "核心锚点", "具体表现", "可开放变化"]
NAMESPACE_REQUIRED = {
    "角色": ROLE_REQUIRED,
    "世界观": WORLD_REQUIRED,
    "地点": {"默认": GENERIC_MODULE_REQUIRED},
    "组织": {"默认": GENERIC_MODULE_REQUIRED},
    "规则": {"默认": GENERIC_MODULE_REQUIRED},
    "事件": {"默认": GENERIC_MODULE_REQUIRED},
    "情境": {"默认": GENERIC_MODULE_REQUIRED},
    "关系": {"默认": GENERIC_MODULE_REQUIRED},
    "机制": {"默认": GENERIC_MODULE_REQUIRED},
    "知识": {"默认": GENERIC_MODULE_REQUIRED},
    "场景": {"默认": GENERIC_MODULE_REQUIRED},
}
OPEN_ROUTE_NAMESPACES = {"事件", "情境", "场景"}
RUNTIME_ROLES = {"character_module", "world_module", "event_candidate", "scene", "stage_pack", "state_effect", "knowledge"}
MODULE_TYPES = {
    "character_identity", "character_psychology", "character_language", "character_relationship",
    "place", "organization", "rule", "event_candidate", "scene", "relationship", "knowledge",
    "interaction_mechanism", "state", "world_fact",
}
LOCK_EXEMPT_SECTIONS = {"不应误写", "误写红线", "行为红线", "禁止事项", "禁止行为"}
SEMANTIC_SECTIONS = {
    "条目作用", "核心锚点", "触发条件", "具体表现", "特质交叠", "语言与称谓",
    "信息边界", "可开放变化", "不应误写", "误写红线", "行为红线", "禁止事项", "禁止行为",
}
NEGATED_LOCK_PREFIX = re.compile(r"(?:不得|不要|不能|不可|禁止|避免|不应|不写|不将|不把|不是|并非|无需)[^。！？；\n]{0,24}$")

CONTRACT_LEVELS = {"lite", "standard", "full"}
ARCHITECTURES = {"flat", "native_stage", "mvu"}
ROUTES = {"natural_keys", "greeting_title", "runtime.stage"}
STATES = {"narrative_only", "greeting_snapshot", "stat_data"}
CONTRACT_REQUIRED = {
    "lite": [
        "project_id", "narrative_mode", "architecture_mode",
        "authoritative_route", "authoritative_state", "runtime_capabilities",
    ],
    "standard": [
        "project_id", "source_scope", "player_anchor", "narrative_mode",
        "architecture_mode", "authoritative_route", "authoritative_state",
        "runtime_capabilities", "visibility_policy", "policy_bundle", "projections",
    ],
    "full": [
        "project_id", "source_scope", "player_anchor", "narrative_mode",
        "architecture_mode", "authoritative_route", "authoritative_state",
        "runtime_capabilities", "visibility_policy", "policy_bundle", "projections",
        "entities", "facts", "relations", "knowledge",
    ],
}
LOCK_TERMS = (
    "自动触发", "自动进入", "固定顺序", "唯一结局", "强制进入",
    "必须发生", "无论玩家怎么做", "不可拒绝", "必然发生",
)
RUNTIME_MARKERS = (
    "ROUTE_STAGE", "stage_pack", "file_id", "build manifest", "build_manifest",
    "[F]", "[I]", "[D]", "[E]", "证据等级", "映射模块", "构建说明",
)
HEADING_RE = re.compile(r"(?:^|\n)\s*(?:[#【\[]\s*)?([^：:\n】\]]{2,24})\s*[：:\]】]", re.M)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ValueError("card root must be an object")
    return value


def load_manifest(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    with path.open("r", encoding="utf-8-sig") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ValueError("manifest root must be an object")
    return value


def entries_from_card(card: dict[str, Any]) -> list[dict[str, Any]]:
    data = card.get("data", card)
    book = data.get("character_book", {}) if isinstance(data, dict) else {}
    entries = book.get("entries", []) if isinstance(book, dict) else []
    return [e for e in entries if isinstance(e, dict)]


def headings(content: str) -> set[str]:
    found = set(HEADING_RE.findall(content))
    for line in content.splitlines():
        line = line.strip().strip("#【】[] ")
        if line and len(line) <= 24 and not any(ch in line for ch in "。！？；"):
            found.add(line.rstrip(":："))
    return found


def has_heading(found: set[str], required: str) -> bool:
    aliases = {
        "触发条件": {"触发条件", "触发条件与响应", "触发与响应"},
        "具体表现": {"具体表现", "可观察表现", "行为表现"},
        "信息边界": {"信息边界", "知情边界"},
        "语言与称谓": {"语言与称谓", "语言规范"},
        "可开放变化": {"可开放变化", "开放变化", "开放空间"},
        "不应误写": {"不应误写", "误写红线", "行为红线"},
        "特质交叠": {"特质交叠", "交叠与冲突", "性格交叠与碰撞"},
    }
    return bool(found & aliases.get(required, {required}))


def add_issue(issues: list[dict[str, str]], level: str, code: str, message: str, comment: str = "") -> None:
    issues.append({"level": level, "code": code, "comment": comment, "message": message})


def namespace_spec(comment: str) -> tuple[str, str, list[str]] | None:
    parts = comment.split("/")
    namespace = parts[0] if parts else ""
    if namespace not in NAMESPACE_REQUIRED:
        return None
    if namespace == "角色":
        if len(parts) < 3 or not parts[1] or not parts[2]:
            return namespace, "", []
        module = parts[2]
        return namespace, module, ROLE_REQUIRED.get(module, GENERIC_MODULE_REQUIRED)
    if namespace == "世界观":
        if len(parts) < 3 or not parts[1] or not parts[2]:
            return namespace, "", []
        module = parts[1]
        return namespace, module, WORLD_REQUIRED.get(module, GENERIC_MODULE_REQUIRED)
    if len(parts) < 3 or not parts[1] or not parts[2]:
        return namespace, "", []
    return namespace, parts[1], NAMESPACE_REQUIRED[namespace].get("默认", GENERIC_MODULE_REQUIRED)


def actionable_lock_hits(content: str) -> list[str]:
    hits: list[str] = []
    exempt = False
    for line in content.splitlines():
        stripped = line.strip().strip("#【】[] ")
        label = stripped.split("：", 1)[0].split(":", 1)[0].strip()
        if label in SEMANTIC_SECTIONS:
            exempt = label in LOCK_EXEMPT_SECTIONS
            if exempt:
                continue
        if exempt:
            continue
        for term in LOCK_TERMS:
            start = 0
            while True:
                index = line.find(term, start)
                if index < 0:
                    break
                prefix = line[max(0, index - 32):index]
                if not NEGATED_LOCK_PREFIX.search(prefix):
                    hits.append(term)
                start = index + len(term)
    return list(dict.fromkeys(hits))


def audit_manifest_contract(manifest: dict[str, Any], issues: list[dict[str, str]]) -> None:
    """Validate the opt-in project/runtime contract without touching legacy cards."""
    if manifest.get("semantic_profile") != "modular_semantic_v1":
        return
    level = manifest.get("contract_level")
    if level is None:
        add_issue(
            issues, "WARNING", "CONTRACT_LEVEL_MISSING",
            "未声明 contract_level；保留早期模块化兼容模式，生产卡应使用 lite/standard/full。",
        )
        return
    if level not in CONTRACT_LEVELS:
        add_issue(issues, "ERROR", "BAD_CONTRACT_LEVEL", f"contract_level 无效：{level}。")
        return
    for field in CONTRACT_REQUIRED[level]:
        if field not in manifest:
            add_issue(issues, "ERROR", "MISSING_PROJECT_CONTRACT", f"项目合同缺少字段：{field}。")

    architecture = manifest.get("architecture_mode")
    if architecture not in ARCHITECTURES:
        add_issue(issues, "ERROR", "BAD_ARCHITECTURE_MODE", f"architecture_mode 无效：{architecture}。")
    route = manifest.get("authoritative_route")
    if route not in ROUTES:
        add_issue(issues, "ERROR", "BAD_AUTHORITATIVE_ROUTE", f"authoritative_route 无效：{route}。")
    state = manifest.get("authoritative_state")
    if state not in STATES:
        add_issue(issues, "ERROR", "BAD_AUTHORITATIVE_STATE", f"authoritative_state 无效：{state}。")
    if not isinstance(manifest.get("runtime_capabilities", []), list):
        add_issue(issues, "ERROR", "BAD_RUNTIME_CAPABILITIES", "runtime_capabilities 必须是数组。")
    modules = manifest.get("modules")
    if modules is not None:
        if isinstance(modules, dict):
            module_items = list(modules.items())
        elif isinstance(modules, list):
            module_items = [(str(index), item) for index, item in enumerate(modules)]
        else:
            module_items = []
            add_issue(issues, "ERROR", "BAD_MODULE_REGISTRY", "modules 必须是对象或记录数组。")
        for module_id, metadata in module_items:
            if not isinstance(metadata, dict):
                add_issue(issues, "ERROR", "BAD_MODULE_RECORD", f"modules[{module_id}] 必须是对象。")
                continue
            module_type = metadata.get("module_type")
            if module_type not in MODULE_TYPES:
                add_issue(issues, "ERROR", "BAD_MODULE_TYPE", f"modules[{module_id}] 缺少或使用了无效 module_type：{module_type}。")
    if level in {"lite", "standard", "full"} and not expected_comments(manifest):
        add_issue(issues, "ERROR", "MISSING_SEMANTIC_MODULES", "合同未声明任何角色、世界观或其他语义模块。")
    if level in {"lite", "standard", "full"}:
        projections = manifest.get("projections")
        if not isinstance(projections, list) or not projections:
            add_issue(issues, "ERROR", "MISSING_PROJECTION_ENTRYPOINT", "合同至少需要一个 projection 作为运行时入口。")
    if level in {"standard", "full"}:
        source_scope = manifest.get("source_scope")
        if not isinstance(source_scope, dict):
            add_issue(issues, "ERROR", "BAD_SOURCE_SCOPE", "source_scope 必须是对象。")
        player_anchor = manifest.get("player_anchor")
        if not isinstance(player_anchor, dict) or not player_anchor.get("mode"):
            add_issue(issues, "ERROR", "BAD_PLAYER_ANCHOR", "player_anchor 必须声明 mode。")
        visibility = manifest.get("visibility_policy")
        if not isinstance(visibility, dict) or not visibility.get("model"):
            add_issue(issues, "ERROR", "BAD_VISIBILITY_POLICY", "visibility_policy 必须声明 model 可见性。")
        projections = manifest.get("projections")
        if not isinstance(projections, list):
            add_issue(issues, "ERROR", "BAD_PROJECTIONS", "projections 必须是数组。")
        else:
            seen_refs: set[str] = set()
            for index, projection in enumerate(projections):
                if not isinstance(projection, dict) or not projection.get("semantic_ref") or not projection.get("runtime_role"):
                    add_issue(issues, "ERROR", "BAD_PROJECTION", f"projections[{index}] 缺少 semantic_ref/runtime_role。")
                    continue
                ref = str(projection["semantic_ref"])
                if ref in seen_refs:
                    add_issue(issues, "ERROR", "DUPLICATE_PROJECTION", f"projection 重复引用 semantic_ref：{ref}。")
                seen_refs.add(ref)
                if projection["runtime_role"] not in RUNTIME_ROLES:
                    add_issue(issues, "ERROR", "BAD_RUNTIME_ROLE", f"projection runtime_role 无效：{projection['runtime_role']}。")
    if level == "full":
        registry_codes = {"entities": "ENTITY", "facts": "FACT", "relations": "RELATION", "knowledge": "KNOWLEDGE"}
        for registry, code_name in registry_codes.items():
            value = manifest.get(registry)
            if not isinstance(value, list):
                add_issue(issues, "ERROR", f"BAD_{code_name}_REGISTRY", f"Full 合同必须提供 {registry} 数组。")
                continue
            if not value:
                add_issue(issues, "ERROR", f"EMPTY_{code_name}_REGISTRY", f"Full 合同的 {registry} 不能为空。")
                continue
            for index, item in enumerate(value):
                if not isinstance(item, dict) or not any(item.get(key) for key in ("id", "semantic_id", "entity_id")):
                    add_issue(issues, "ERROR", f"BAD_{code_name}_ITEM", f"Full 合同的 {registry}[{index}] 必须有稳定 id。")


def expected_comments(manifest: dict[str, Any]) -> set[str]:
    expected: set[str] = set()
    for name, spec in (manifest.get("characters") or {}).items():
        if isinstance(spec, dict):
            modules = spec.get("modules", spec.get("required", []))
        else:
            modules = spec
        if isinstance(modules, list):
            for module in modules:
                expected.add(str(module) if str(module).startswith("角色/") else f"角色/{name}/{module}")
    world = manifest.get("world")
    world_items = manifest.get("world_modules", [])
    if not world_items and isinstance(world, dict):
        world_items = world.get("required", [])
    for item in world_items:
        if isinstance(item, str):
            expected.add(item)
    for key in (
        "event_modules",
        "scene_modules",
        "relation_modules",
        "knowledge_modules",
        "organization_modules",
        "rule_modules",
        "mechanism_modules",
    ):
        for item in manifest.get(key, []) or []:
            if isinstance(item, str):
                expected.add(item)
    return expected


def summarize_coverage(card: dict[str, Any], manifest: dict[str, Any]) -> dict[str, int]:
    """Return read-only migration coverage counts without changing audit policy."""
    if not isinstance(card, dict):
        raise TypeError("card root must be an object for coverage summary")
    comments = {str(entry.get("comment", "")) for entry in entries_from_card(card) if entry.get("comment")}
    formal = {comment for comment in comments if namespace_spec(comment) is not None}
    module_records = manifest.get("module_records")
    modern = set()
    if manifest.get("text_profile") == "semantic_markdown_v1" and isinstance(module_records, dict):
        modern = {str(comment) for comment in module_records if str(comment) in comments}
    declared = expected_comments(manifest)
    return {
        "modern_text_modules_audited": len(modern),
        "legacy_semantic_modules_audited": len(formal - modern),
        "non_semantic_entries_ignored": len(comments - formal),
        "unregistered_formal_namespace_modules": len(formal - declared),
    }


def audit(card: dict[str, Any], manifest: dict[str, Any], *, require_profile: bool = False) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    entries = entries_from_card(card)
    comments = [str(e.get("comment", "")) for e in entries]
    if manifest.get("semantic_profile") != "modular_semantic_v1":
        if require_profile:
            return [{"level": "ERROR", "code": "SEMANTIC_PROFILE_MISMATCH", "comment": "", "message": "build_manifest 已声明 semantic_manifest，但目标文件没有 semantic_profile=modular_semantic_v1。"}]
        return [{"level": "INFO", "code": "PROFILE_NOT_ENABLED", "comment": "", "message": "semantic_profile 未启用，跳过模块化语义门控。"}]
    audit_manifest_contract(manifest, issues)
    modern_text_comments = {
        str(comment)
        for comment in (manifest.get("module_records") or {})
    } if manifest.get("text_profile") == "semantic_markdown_v1" and isinstance(manifest.get("module_records"), dict) else set()

    seen: dict[str, int] = {}
    for e in entries:
        comment = str(e.get("comment", ""))
        spec = namespace_spec(comment)
        if spec is None:
            continue
        namespace, module, required = spec
        seen[comment] = seen.get(comment, 0) + 1
        if not module:
            code = "BAD_ROLE_NAMESPACE" if namespace == "角色" else "BAD_MODULE_NAMESPACE"
            add_issue(issues, "ERROR", code, "模块必须使用 <命名空间>/<分类>/<模块名>。", comment)
            continue
        content = str(e.get("content", ""))
        if not content.strip():
            add_issue(issues, "ERROR", "EMPTY_MODULE", "模块 content 为空。", comment)
            continue
        if comment not in modern_text_comments:
            found = headings(content)
            for field in required:
                if not has_heading(found, field):
                    add_issue(issues, "ERROR", "MISSING_SEMANTIC_FIELD", f"缺少模块字段：{field}。", comment)

        if manifest.get("content_surface", "runtime_clean") == "runtime_clean":
            for marker in RUNTIME_MARKERS:
                if marker in content:
                    add_issue(issues, "ERROR", "RUNTIME_META_LEAK", f"模型可见层包含工程/证据标记：{marker}。", comment)

        open_mode = manifest.get("narrative_mode", manifest.get("mode", "")) == "open_sandbox"
        module_records = manifest.get("module_records")
        module_record = module_records.get(comment, {}) if isinstance(module_records, dict) else {}
        projection_roles = {
            str(item.get("runtime_role"))
            for item in manifest.get("projections", []) or []
            if isinstance(item, dict) and item.get("semantic_ref") == comment and item.get("runtime_role")
        }
        if isinstance(module_record, dict) and module_record.get("runtime_role"):
            projection_roles.add(str(module_record["runtime_role"]))
        event_like = (
            namespace in OPEN_ROUTE_NAMESPACES
            or "event_candidate" in projection_roles
            or any(token in comment for token in ("候选", "路线", "开放"))
        )
        if open_mode and event_like:
            for term in actionable_lock_hits(content):
                add_issue(issues, "ERROR", "OPEN_ROUTE_LOCKED", f"开放模式候选内容包含锁死表达：{term}。", comment)

        for ref in re.findall(r"(?:角色|世界观|地点|组织|规则|事件|情境|关系|机制|知识|场景)/[^\s，。；：:（）()]+", content):
            ref = ref.rstrip("。；，,）)")
            if ref not in comments:
                add_issue(issues, "ERROR", "BROKEN_MODULE_REFERENCE", f"跨条目引用不存在：{ref}。", comment)

    known_refs = set(comments)
    declared_modules = manifest.get("modules")
    if isinstance(declared_modules, dict):
        known_refs.update(str(key) for key in declared_modules)
    elif isinstance(declared_modules, list):
        for item in declared_modules:
            if isinstance(item, str):
                known_refs.add(item)
            elif isinstance(item, dict) and item.get("semantic_id"):
                known_refs.add(str(item["semantic_id"]))
    projections = manifest.get("projections")
    if isinstance(projections, list):
        for projection in projections:
            if not isinstance(projection, dict) or not projection.get("semantic_ref"):
                continue
            ref = str(projection["semantic_ref"])
            if ref not in known_refs:
                add_issue(issues, "ERROR", "PROJECTION_REF_NOT_FOUND", f"projection 引用不存在的语义模块：{ref}。")
            architecture = manifest.get("architecture_mode")
            target = {"flat": "flat", "native_stage": "native_stage", "mvu": "mvu"}.get(architecture)
            if target and not isinstance(projection.get(target), dict):
                add_issue(issues, "ERROR", "PROJECTION_TARGET_MISSING", f"architecture_mode={architecture} 的 projection 缺少 {target} target：{ref}。")

    for comment, count in seen.items():
        if count > 1:
            add_issue(issues, "ERROR", "DUPLICATE_MODULE_COMMENT", f"模块 comment 重复 {count} 次。", comment)

    expected = expected_comments(manifest)
    for comment in sorted(expected - set(comments)):
        add_issue(issues, "ERROR", "DECLARED_MODULE_MISSING", "manifest 声明的模块不存在。", comment)
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit modular semantic card entries")
    parser.add_argument("card", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        card = load_json(args.card)
        manifest = load_manifest(args.manifest)
        issues = audit(card, manifest, require_profile=args.manifest is not None)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR INPUT: {exc}", file=sys.stderr)
        return 3
    if args.as_json:
        print(json.dumps(issues, ensure_ascii=False, indent=2))
    else:
        for issue in issues:
            suffix = f" [{issue['comment']}]" if issue.get("comment") else ""
            print(f"{issue['level']} {issue['code']}{suffix}: {issue['message']}")
    if any(i["level"] == "ERROR" for i in issues):
        return 1
    if any(i["level"] in {"WARNING", "WARN"} for i in issues):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
