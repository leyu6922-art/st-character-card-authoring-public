#!/usr/bin/env python3
"""Audit the opt-in semantic Markdown text layer.

This gate owns only presentation structure and module content schemas. Project
contracts, knowledge state, projections, and runtime behavior stay in the
existing semantic-module audit.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TEXT_PROFILE = "semantic_markdown_v1"

SCHEMAS: dict[str, tuple[str, ...]] = {
    "character_identity_v1": (
        "条目作用", "核心锚点", "关系与公开状态", "不应误写", "可开放变化",
    ),
    "character_psychology_v1": (
        "条目作用", "核心锚点", "触发与响应", "不应误写", "可开放变化",
    ),
    "character_language_v1": (
        "条目作用", "基础语气", "对象差异", "语言样例", "不应误写", "可开放变化",
    ),
    "place_v1": (
        "条目作用", "地点定位", "空间布局", "自然入口", "现实规则", "不应误写", "可开放变化",
    ),
    "interaction_mechanism_v1": (
        "条目作用", "机制定位", "前置条件", "自然入口", "执行流程", "失败与偏离", "不应误写", "可开放变化",
    ),
    "relationship_v1": (
        "条目作用", "关系锚点", "当前状态", "变化条件", "不应误写", "可开放变化",
    ),
}

SCHEMA_MODULE_TYPES: dict[str, frozenset[str]] = {
    "character_identity_v1": frozenset({"character_identity"}),
    "character_psychology_v1": frozenset({"character_psychology"}),
    "character_language_v1": frozenset({"character_language"}),
    "place_v1": frozenset({"place"}),
    "interaction_mechanism_v1": frozenset({"interaction_mechanism"}),
    "relationship_v1": frozenset({"relationship", "character_relationship"}),
}

COMMENT_MODULE_TYPES: dict[str, frozenset[str]] = {
    "基础信息与关系锚点": frozenset({"character_identity"}),
    "核心心理与性格": frozenset({"character_psychology"}),
    "语言与称谓": frozenset({"character_language"}),
}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
YAML_KEY_RE = re.compile(r"^[^:\s][^:\n]*:\s*$")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def entries_from_card(card: dict[str, Any]) -> list[dict[str, Any]]:
    data = card.get("data", card)
    book = data.get("character_book", {}) if isinstance(data, dict) else {}
    entries = book.get("entries", []) if isinstance(book, dict) else []
    return [item for item in entries if isinstance(item, dict)]


def add_issue(issues: list[dict[str, str]], level: str, code: str, message: str, comment: str = "") -> None:
    issues.append({"level": level, "code": code, "comment": comment, "message": message})


def allowed_types_for_comment(comment: str) -> frozenset[str] | None:
    parts = comment.split("/", 2)
    if len(parts) < 3:
        return None
    namespace, category, module_name = parts
    if namespace == "角色":
        return COMMENT_MODULE_TYPES.get(module_name)
    if namespace == "世界观" and category == "地点":
        return frozenset({"place"})
    if namespace == "机制" and category == "互动机制":
        return frozenset({"interaction_mechanism"})
    if namespace == "关系":
        return frozenset({"relationship", "character_relationship"})
    return None


def headings(content: str) -> list[tuple[int, str, int]]:
    found: list[tuple[int, str, int]] = []
    for line_number, line in enumerate(content.splitlines(), 1):
        match = HEADING_RE.match(line)
        if match:
            found.append((len(match.group(1)), match.group(2).strip().strip("# "), line_number))
    return found


def has_yaml_indentation_dependency(content: str) -> bool:
    lines = content.splitlines()
    for index, line in enumerate(lines[:-1]):
        if not YAML_KEY_RE.match(line.strip()) or line.startswith((" ", "\t")):
            continue
        next_line = lines[index + 1]
        if re.match(r"^(?: {2,}|\t+)(?:[-*]\s+|[^:\n]+:\s*)", next_line):
            return True
    return False


def audit_content(content: str, schema: str, issues: list[dict[str, str]], comment: str) -> None:
    required = SCHEMAS.get(schema)
    if required is None:
        add_issue(issues, "ERROR", "UNKNOWN_CONTENT_SCHEMA", f"未知 content_schema：{schema}。", comment)
        return
    if not content.strip():
        add_issue(issues, "ERROR", "EMPTY_TEXT", "模块正文为空。", comment)
        return

    parsed = headings(content)
    if not parsed or parsed[0][0] != 1:
        add_issue(issues, "ERROR", "H1_MISSING", "正文第一段必须是唯一的 Markdown 一级标题。", comment)
    if sum(level == 1 for level, _title, _line in parsed) > 1:
        add_issue(issues, "ERROR", "H1_MULTIPLE", "正文只能有一个 Markdown 一级标题。", comment)
    first_nonempty = next((line.strip() for line in content.splitlines() if line.strip()), "")
    if not re.match(r"^#\s+", first_nonempty):
        add_issue(issues, "ERROR", "H1_NOT_FIRST", "Markdown 一级标题必须位于正文第一个非空行。", comment)
    if any(level > 3 for level, _title, _line in parsed):
        add_issue(issues, "ERROR", "HEADING_DEPTH_INVALID", "正文标题层级不得深于三级。", comment)

    titles = [title for _level, title, _line in parsed]
    for title in sorted({item for item in titles if titles.count(item) > 1}):
        add_issue(issues, "ERROR", "DUPLICATE_SECTION", f"章节标题重复：{title}。", comment)

    required_level_issues: set[str] = set()
    level_two_titles = [title for level, title, _line in parsed if level == 2]
    for title in required:
        levels = [level for level, parsed_title, _line in parsed if parsed_title == title]
        if not levels:
            add_issue(issues, "ERROR", "MISSING_REQUIRED_SECTION", f"缺少必需章节：{title}。", comment)
        elif 2 not in levels:
            required_level_issues.add(title)
            add_issue(
                issues,
                "ERROR",
                "REQUIRED_SECTION_LEVEL_INVALID",
                f"必需章节必须使用 Markdown 二级标题：{title}。",
                comment,
            )
    present = [title for title in level_two_titles if title in required]
    expected_order = [title for title in required if title in present]
    if not required_level_issues and present != expected_order:
        add_issue(issues, "ERROR", "SECTION_ORDER_INVALID", f"章节顺序应遵循：{' → '.join(required)}。", comment)

    if has_yaml_indentation_dependency(content):
        add_issue(
            issues,
            "ERROR",
            "YAML_INDENTATION_DEPENDENCY",
            "正文包含依赖精确缩进才能解释的 YAML 式嵌套结构；请改用 Markdown 标题、列表或段落。",
            comment,
        )


def audit(card: dict[str, Any], manifest: dict[str, Any], *, require_profile: bool = False) -> list[dict[str, str]]:
    profile = manifest.get("text_profile")
    if profile is None:
        if require_profile:
            return [{"level": "ERROR", "code": "TEXT_PROFILE_MISMATCH", "comment": "", "message": "manifest 未声明 text_profile。"}]
        return [{
            "level": "INFO",
            "code": "TEXT_PROFILE_NOT_ENABLED",
            "comment": "",
            "message": "text_profile 未启用，跳过 semantic Markdown 文本审计。",
        }]
    if profile != TEXT_PROFILE:
        return [{"level": "ERROR", "code": "TEXT_PROFILE_MISMATCH", "comment": "", "message": f"不支持的 text_profile：{profile}。"}]

    records = manifest.get("module_records")
    if not isinstance(records, dict) or not records:
        return [{"level": "ERROR", "code": "TEXT_MODULE_RECORDS_MISSING", "comment": "", "message": "semantic Markdown profile 至少需要一个 module_records。"}]

    entries = entries_from_card(card)
    by_comment = {str(item.get("comment", "")): item for item in entries}
    issues: list[dict[str, str]] = []
    for comment, record in records.items():
        if not isinstance(record, dict):
            add_issue(issues, "ERROR", "BAD_MODULE_RECORD", "module_records 的记录必须是对象。", str(comment))
            continue
        comment = str(comment)
        if comment not in by_comment:
            add_issue(issues, "ERROR", "MODULE_RECORD_NOT_FOUND", "module_records 引用的条目不存在。", comment)
            continue
        record_profile = record.get("text_profile", profile)
        if record_profile != TEXT_PROFILE:
            add_issue(issues, "ERROR", "TEXT_PROFILE_MISMATCH", f"模块 text_profile 无效：{record_profile}。", comment)
            continue
        schema = record.get("content_schema")
        if not isinstance(schema, str) or not schema:
            add_issue(issues, "ERROR", "CONTENT_SCHEMA_MISSING", "模块记录缺少 content_schema。", comment)
            continue
        module_type = record.get("module_type")
        allowed_module_types = SCHEMA_MODULE_TYPES.get(schema)
        if not isinstance(module_type, str) or not module_type:
            add_issue(issues, "ERROR", "MODULE_TYPE_MISSING", "模块记录缺少 module_type。", comment)
        elif allowed_module_types is not None and module_type not in allowed_module_types:
            add_issue(
                issues,
                "ERROR",
                "MODULE_TYPE_SCHEMA_MISMATCH",
                f"module_type={module_type} 与 content_schema={schema} 不匹配；允许类型：{', '.join(sorted(allowed_module_types))}。",
                comment,
            )
        allowed_path_types = allowed_types_for_comment(comment)
        if isinstance(module_type, str) and allowed_path_types is not None and module_type not in allowed_path_types:
            add_issue(
                issues,
                "ERROR",
                "MODULE_PATH_TYPE_MISMATCH",
                f"comment 路径 {comment} 不允许 module_type={module_type}；允许类型：{', '.join(sorted(allowed_path_types))}。",
                comment,
            )
        audit_content(str(by_comment[comment].get("content", "")), schema, issues, comment)
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit opt-in semantic Markdown module text")
    parser.add_argument("card", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        card = load_json(args.card)
        manifest = load_json(args.manifest) if args.manifest else {}
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
    if any(item["level"] == "ERROR" for item in issues):
        return 1
    if any(item["level"] in {"WARNING", "WARN"} for item in issues):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
