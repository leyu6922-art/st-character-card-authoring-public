#!/usr/bin/env python3
"""Enforce runtime-entry contracts for native Greeting-stage character cards.

The sidecar contract is build provenance, not model-visible card content. It
makes every worldbook entry declare why and how it can load, then verifies that
claim with the same matcher used by trigger audits.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from lib.stage_memory import phase_memory_anchor_issues
from lib.worldbook_matcher import entry_trigger_match
from lib.stage_routing import (
    STAGE_RE,
    card_entries,
    greeting_texts,
    parse_title,
    primary_keys,
    title_matches,
)

ALLOWED_ROLES = {"constant", "stage_pack", "character", "scene", "chat_only", "manual"}
REQUIRED_PACKS = ("阶段核心", "成人体验", "场景体验", "事件库")
POLICY_MODE = "leyu_large_native_greeting_stage_v1"
MIN_UNITS_PER_PACK = 6
MIN_UNIT_CHARS = 120
# Native standalone stage contracts currently accept Greeting-title routing only.
AN_STAGE_RE = re.compile(r"ROUTE_STAGE=(P\d+)")
INITVAR_PREFIX_RE = re.compile(r"\A\s*<initvar>[\s\S]*?</initvar>\s*", re.IGNORECASE)
UNIT_LABEL_RE = re.compile(r"【(?P<pack>[^_】]+)_(?P<stage>P\d+)_(?P<identifier>\d{2,})[^】]*】")
ANALYSIS_RESIDUE = (
    re.compile(r"【(?:源文档|映射模块|证据标注)[：:]"),
    re.compile(r"\bE-\d{3}\b"),
)
MODEL_VISIBLE_STRING_FIELDS = (
    "description",
    "personality",
    "scenario",
    "system_prompt",
    "post_history_instructions",
    "first_mes",
    "mes_example",
)
MODEL_VISIBLE_GREETING_LIST_FIELDS = ("alternate_greetings", "group_only_greetings")


@dataclass(frozen=True)
class Contract:
    schema_version: int
    architecture_mode: str
    route_source: str
    stages: tuple[str, ...]
    required_packs: tuple[str, ...]
    min_units_per_pack: int
    min_unit_chars: int
    entries: dict[str, dict[str, Any]]
    phase_memory: dict[str, Any]


@dataclass
class AuditResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _card_entries(card: dict[str, Any]) -> list[dict[str, Any]]:
    return card_entries(card)


def _greetings(card: dict[str, Any]) -> list[str]:
    return greeting_texts(card)


def _entry_keys(entry: dict[str, Any]) -> set[str]:
    return set(primary_keys(entry))


def _phase_memory_body_errors(entry: dict[str, Any], label: str, anchors: tuple[str, ...]) -> list[str]:
    """Reject present-but-empty memory components before reporting a green contract."""
    content = str(entry.get("content", "")).strip()
    errors: list[str] = []
    if len(content) < 40:
        errors.append(f"phase_memory{label}正文过短（至少40字）")
    missing = [anchor for anchor in anchors if anchor not in content]
    if missing:
        errors.append(f"phase_memory{label}正文缺少语义锚点{missing}")
    return errors


def _parse_contract(raw: Any) -> tuple[Contract | None, list[str]]:
    errors: list[str] = []
    if not isinstance(raw, dict):
        return None, ["stage entry contract根节点必须是对象"]
    schema_version = raw.get("schema_version")
    if schema_version != 2:
        errors.append("stage entry contract.schema_version必须为2；native Greeting-title 路线不接受v1合同")
    if raw.get("mode") != POLICY_MODE:
        errors.append(f"stage entry contract.mode必须为{POLICY_MODE!r}")

    architecture_mode = raw.get("architecture_mode", "stage_routing")
    if architecture_mode not in {"stage_routing"}:
        errors.append("stage entry contract.architecture_mode必须为'stage_routing'")

    route_source = raw.get("route_source", "greeting_title")
    if route_source != "greeting_title":
        errors.append("stage entry contract.route_source当前生产模式必须为'greeting_title'；author_note暂未接入native运行时")

    phase_memory = raw.get("phase_memory", {})
    if not isinstance(phase_memory, dict):
        errors.append("stage entry contract.phase_memory必须是对象")
        phase_memory = {}
    archives = _as_string_list(phase_memory.get("causal_archives"))
    if not archives:
        errors.append("stage entry contract.phase_memory.causal_archives必须是非空字符串数组")
    if not isinstance(phase_memory.get("memory_gate"), str) or not phase_memory.get("memory_gate"):
        errors.append("stage entry contract.phase_memory.memory_gate必须是非空字符串")
    if phase_memory.get("system_prompt_anchor_required") is not True:
        errors.append("stage entry contract.phase_memory.system_prompt_anchor_required必须为true")

    stages = tuple(_as_string_list(raw.get("stages")))
    if not stages:
        errors.append("stage entry contract.stages必须是非空字符串数组")
    elif len(set(stages)) != len(stages) or any(STAGE_RE.fullmatch(stage) is None for stage in stages):
        errors.append("stage entry contract.stages必须是唯一的P数字阶段名")

    packs = tuple(_as_string_list(raw.get("required_packs")))
    if len(packs) != len(REQUIRED_PACKS) or set(packs) != set(REQUIRED_PACKS):
        errors.append(f"stage entry contract.required_packs必须精确为{list(REQUIRED_PACKS)}")

    min_units = raw.get("min_units_per_pack")
    if not isinstance(min_units, int) or isinstance(min_units, bool) or min_units < MIN_UNITS_PER_PACK:
        errors.append(f"stage entry contract.min_units_per_pack必须≥{MIN_UNITS_PER_PACK}的整数")
        min_units = MIN_UNITS_PER_PACK
    min_unit_chars = raw.get("min_unit_chars")
    if not isinstance(min_unit_chars, int) or isinstance(min_unit_chars, bool) or min_unit_chars < MIN_UNIT_CHARS:
        errors.append(f"stage entry contract.min_unit_chars必须≥{MIN_UNIT_CHARS}的整数")
        min_unit_chars = MIN_UNIT_CHARS

    contracts = raw.get("entries")
    if not isinstance(contracts, dict) or not contracts:
        errors.append("stage entry contract.entries必须是非空对象")
        contracts = {}
    else:
        contracts = {str(comment): value for comment, value in contracts.items()}
        for comment, item in contracts.items():
            if not comment or not isinstance(item, dict):
                errors.append(f"entries.{comment or '<empty>'}必须是非空comment对应的对象")
                continue
            if item.get("role") not in ALLOWED_ROLES:
                errors.append(f"entries.{comment}.role必须为{sorted(ALLOWED_ROLES)}之一")

    if errors:
        return None, errors
    return Contract(schema_version, architecture_mode, route_source, stages, packs, min_units, min_unit_chars, contracts, phase_memory), []


def load_contract(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, [f"无法读取stage entry contract: {exc}"]
    if raw.startswith(b"\xef\xbb\xbf"):
        return None, ["stage entry contract带UTF-8 BOM；请使用无BOM UTF-8"]
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, [f"stage entry contract不是有效UTF-8 JSON: {exc}"]
    return value if isinstance(value, dict) else None, [] if isinstance(value, dict) else ["stage entry contract根节点必须是对象"]


def architecture_manifest_from_contract(raw_contract: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """Translate this policy contract into the sibling native-architecture manifest."""
    contract, errors = _parse_contract(raw_contract)
    if contract is None:
        return None, errors
    manifest = {
        "route_mode": "native_greeting_title",
        "route_source": contract.route_source,
        "architecture_mode": contract.architecture_mode,
        "stages": list(contract.stages),
        "required_packs": list(contract.required_packs),
        "min_units_per_pack": contract.min_units_per_pack,
        "phase_memory": contract.phase_memory,
    }
    return manifest, []


def _stage_titles(card: dict[str, Any], contract: Contract, result: AuditResult) -> dict[str, set[str]]:
    titles = {stage: set() for stage in contract.stages}
    for index, greeting in enumerate(_greetings(card)):
        matches = title_matches(greeting)
        if len(matches) != 1:
            result.errors.append(f"Greeting[{index}]必须含且仅含一个完整阶段标题，实际{len(matches)}个")
            continue
        stage, title = parse_title(matches[0])
        is_html = greeting.lstrip().startswith("<html")
        if stage == "MENU":
            # 图鉴 MENU（独立菜单入口）不属于阶段包体系，不要求四包。
            continue
        if not is_html:
            visible = INITVAR_PREFIX_RE.sub("", greeting, count=1).lstrip()
            if contract.route_source == "greeting_title" and not visible.startswith(title):
                result.errors.append(f"Greeting[{index}]完整阶段标题必须是忽略前置initvar后的首个可见内容")
        # HTML 开场页（如 P0 图鉴入口）标题在 HTML 注释内，跳过可见内容检查，
        # 但仍是合法阶段标题声明（世界书可扫注释内子串触发阶段包）。
        if stage not in titles:
            result.errors.append(f"Greeting[{index}]使用未声明阶段标题: {title}")
            continue
        titles[stage].add(title)
    for stage, values in titles.items():
        if not values:
            result.errors.append(f"缺少{stage}完整Greeting标题")
    return titles


def _unit_sections(content: str, pack: str, stage: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Return valid unit bodies while making every unit-like label a hard boundary."""
    matches = list(UNIT_LABEL_RE.finditer(content))
    sections: list[tuple[str, str]] = []
    errors: list[str] = []
    identifiers: set[str] = set()
    for index, match in enumerate(matches):
        actual_pack = match.group("pack")
        actual_stage = match.group("stage")
        identifier = match.group("identifier")
        if actual_pack != pack or actual_stage != stage:
            errors.append(f"混入其他包/阶段素材标签: {actual_pack}_{actual_stage}_{identifier}")
            continue
        if identifier in identifiers:
            errors.append(f"素材单元编号重复: {identifier}")
        identifiers.add(identifier)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        sections.append((identifier, content[match.end():end].strip()))
    return sections, errors


def _check_analysis_residue(card: dict[str, Any], entries: list[dict[str, Any]], result: AuditResult) -> None:
    data = card.get("data", card)
    texts: list[tuple[str, str]] = []
    for field in MODEL_VISIBLE_STRING_FIELDS:
        value = data.get(field, card.get(field, ""))
        if isinstance(value, str):
            texts.append((f"data.{field}", value))
    for field in MODEL_VISIBLE_GREETING_LIST_FIELDS:
        values = data.get(field, card.get(field, [])) or []
        if not isinstance(values, list):
            continue
        for index, value in enumerate(values):
            if isinstance(value, str):
                texts.append((f"data.{field}[{index}]", value))
    for entry in entries:
        if isinstance(entry.get("content"), str):
            texts.append((f"entry[{entry.get('id', '?')}].content", entry["content"]))
    hits = [f"{path}: {pattern.pattern}" for path, text in texts for pattern in ANALYSIS_RESIDUE if pattern.search(text)]
    if hits:
        result.errors.append("模型可见层含分析层/构建残留: " + "; ".join(hits[:8]))


def _check_stage_pack(
    entry: dict[str, Any],
    item: dict[str, Any],
    name: str,
    titles: dict[str, set[str]],
    contract: Contract,
    result: AuditResult,
) -> None:
    stage = item.get("stage")
    pack = item.get("pack")
    if stage not in contract.stages:
        result.errors.append(f"{name}声明了无效stage={stage!r}")
        return
    if pack not in contract.required_packs:
        result.errors.append(f"{name}声明了无效pack={pack!r}")
        return
    expected_name = f"{pack}_{stage}"
    if name != expected_name:
        result.errors.append(f"{name}的stage_pack comment必须为{expected_name}")
    if entry.get("enabled") is not True:
        result.errors.append(f"{name}必须enabled=true")
    if entry.get("constant") is not False:
        result.errors.append(f"{name}必须constant=false")
    if entry.get("selective") is not True:
        result.errors.append(f"{name}必须selective=true")
    if entry.get("secondary_keys") != []:
        result.errors.append(f"{name}必须显式secondary_keys=[]，不得用secondary_keys承担阶段路由")
    extensions = entry.get("extensions") or {}
    if extensions.get("selective") is not True:
        result.errors.append(f"{name}必须extensions.selective=true并与顶层selective=true同步")
    if extensions.get("scan_depth") != 999:
        result.errors.append(f"{name}必须extensions.scan_depth=999")
    if extensions.get("prevent_recursion") is not True:
        result.errors.append(f"{name}必须extensions.prevent_recursion=true")
    if extensions.get("exclude_recursion") is not True:
        result.errors.append(f"{name}必须extensions.exclude_recursion=true")
    actual_keys = _entry_keys(entry)
    expected_titles = titles.get(stage, set())
    if actual_keys != expected_titles:
        result.errors.append(f"{name}阶段标题key不精确：期望{sorted(expected_titles)}，实际{sorted(actual_keys)}")
    unit_sections, unit_errors = _unit_sections(str(entry.get("content", "")), pack, stage)
    unit_ids = {identifier for identifier, _ in unit_sections}
    result.errors.extend(f"{name}{error}" for error in unit_errors)
    if len(unit_ids) < contract.min_units_per_pack:
        result.errors.append(f"{name}素材单元不足：期望≥{contract.min_units_per_pack}，实际{len(unit_ids)}")
    short_units = [
        identifier
        for identifier, body in unit_sections
        if len(re.sub(r"\s+", "", body)) < contract.min_unit_chars
    ]
    if short_units:
        result.errors.append(
            f"{name}素材单元过短：{', '.join(short_units[:8])}低于{contract.min_unit_chars}字符"
        )
    for greeting in _greetings_for_stage(titles, stage, entry, False):
        if not entry_trigger_match(entry, greeting).ok:
            result.errors.append(f"{name}未在本阶段Greeting触发")
            break
    for greeting in _greetings_for_stage(titles, stage, entry, True):
        if entry_trigger_match(entry, greeting).ok:
            result.errors.append(f"{name}跨阶段Greeting误触发")
            break


def _greetings_for_stage(titles: dict[str, set[str]], stage: str, entry: dict[str, Any], inverse: bool) -> Iterable[str]:
    # The matcher only needs title text for exact-title route validation. This avoids
    # accidental dependence on arbitrary narrative body wording.
    for candidate_stage, values in titles.items():
        if (candidate_stage != stage) == inverse:
            yield from values


def _check_natural_runtime_entry(entry: dict[str, Any], item: dict[str, Any], name: str, result: AuditResult) -> None:
    role = item["role"]
    if entry.get("enabled") is not True or entry.get("constant") is not False:
        result.errors.append(f"{name} role={role}必须enabled=true且constant=false")
    natural_keys = _as_string_list(item.get("natural_keys"))
    if not natural_keys:
        result.errors.append(f"{name} role={role}必须声明natural_keys")
        return
    if not (_entry_keys(entry) & set(natural_keys)):
        result.errors.append(f"{name}缺少声明的自然primary key：{natural_keys}")
    examples = _as_string_list(item.get("load_examples"))
    if not examples:
        result.errors.append(f"{name} role={role}必须声明load_examples")
    else:
        unmatched = [example for example in examples if not entry_trigger_match(entry, example).ok]
        if unmatched:
            result.errors.append(f"{name}的load_examples未全部触发共享matcher: {unmatched[:3]}")
    if role == "scene" and (entry.get("extensions") or {}).get("scan_depth") == 999:
        result.errors.append(f"{name}普通场景不得使用scan_depth=999")


def _check_entry_contract(entry: dict[str, Any], item: dict[str, Any], name: str, titles: dict[str, set[str]], contract: Contract, result: AuditResult) -> None:
    role = item.get("role")
    if role == "stage_pack":
        _check_stage_pack(entry, item, name, titles, contract, result)
    elif role == "constant":
        if entry.get("enabled") is not True or entry.get("constant") is not True or _entry_keys(entry):
            result.errors.append(f"{name} role=constant必须enabled=true、constant=true且keys=[]")
    elif role == "manual":
        if entry.get("enabled") is not False:
            result.errors.append(f"{name} role=manual必须enabled=false")
    elif role in {"character", "scene", "chat_only"}:
        _check_natural_runtime_entry(entry, item, name, result)


def audit_card(card: dict[str, Any], raw_contract: dict[str, Any]) -> AuditResult:
    result = AuditResult()
    contract, errors = _parse_contract(raw_contract)
    result.errors.extend(errors)
    if contract is None:
        return result

    entries = _card_entries(card)
    if not entries:
        result.errors.append("character_book.entries为空或格式无效")
        return result
    comments: dict[str, dict[str, Any]] = {}
    for entry in entries:
        comment = entry.get("comment")
        if not isinstance(comment, str) or not comment:
            result.errors.append(f"entry[{entry.get('id', '?')}]缺少非空comment，无法声明运行时职责")
            continue
        if comment in comments:
            result.errors.append(f"comment重复，无法一对一声明运行时职责: {comment}")
            continue
        comments[comment] = entry

    titles = _stage_titles(card, contract, result)
    _check_analysis_residue(card, entries, result)

    if contract.schema_version >= 2:
        data = card.get("data", card)
        all_comments = {str(entry.get("comment", "")): entry for entry in entries}
        for archive_name in _as_string_list(contract.phase_memory.get("causal_archives")):
            archive = all_comments.get(archive_name)
            if archive is None:
                result.errors.append(f"phase_memory.causal_archives声明的条目不存在: {archive_name}")
            elif not (archive.get("constant") is True and archive.get("enabled") is True and _entry_keys(archive) == set()):
                result.errors.append(f"phase_memory因果档案必须constant=true/enabled=true/keys=[]: {archive_name}")
            else:
                result.errors.extend(_phase_memory_body_errors(archive, "因果档案", ("因果", "阶段")))
        gate_name = contract.phase_memory.get("memory_gate")
        gate = all_comments.get(gate_name)
        if gate is None:
            result.errors.append(f"phase_memory.memory_gate声明的条目不存在: {gate_name}")
        elif not (gate.get("constant") is True and gate.get("enabled") is True and _entry_keys(gate) == set()):
            result.errors.append(f"phase_memory记忆闸门必须constant=true/enabled=true/keys=[]: {gate_name}")
        else:
            result.errors.extend(_phase_memory_body_errors(gate, "记忆闸门", ("当前阶段", "未来")))
        if contract.phase_memory.get("system_prompt_anchor_required"):
            system_prompt = str(data.get("system_prompt", card.get("system_prompt", "")))
            result.errors.extend(
                issue.render()
                for issue in phase_memory_anchor_issues(system_prompt, path="data.system_prompt")
            )

    for comment, entry in comments.items():
        item = contract.entries.get(comment)
        if item is None:
            result.errors.append(f"{comment}未声明运行时职责")
            continue
        _check_entry_contract(entry, item, comment, titles, contract, result)
    for comment in contract.entries:
        if comment not in comments:
            result.errors.append(f"contract声明了不存在的条目: {comment}")

    for stage in contract.stages:
        for pack in contract.required_packs:
            name = f"{pack}_{stage}"
            if name not in comments:
                result.errors.append(f"缺少必需阶段包: {name}")
            elif contract.entries.get(name, {}).get("role") != "stage_pack":
                result.errors.append(f"{name}必须声明role=stage_pack")

    if not result.errors:
        result.notes.append(
            f"阶段合同通过：{'/'.join(contract.stages)}；每阶段四包、条目职责、自然触发和模型层残留均已验证"
        )
    return result


def render(result: AuditResult) -> str:
    lines = ["# Stage Entry Contract Audit"]
    lines.extend(f"- FAIL {message}" for message in result.errors)
    lines.extend(f"- WARN {message}" for message in result.warnings)
    lines.extend(f"- PASS {message}" for message in result.notes)
    lines.append(f"- Summary: {len(result.notes)} PASS / {len(result.warnings)} WARN / {len(result.errors)} FAIL")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit native Greeting-stage entry contracts")
    parser.add_argument("card", help="Character Card V3 JSON")
    parser.add_argument("--contract", required=True, help="stage-entry-contract JSON")
    parser.add_argument("-o", "--output", help="optional report path")
    args = parser.parse_args(argv)
    try:
        card = json.loads(Path(args.card).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"FAIL cannot parse card JSON: {exc}")
        return 1
    raw_contract, load_errors = load_contract(Path(args.contract))
    if load_errors or raw_contract is None:
        for error in load_errors:
            print(f"FAIL {error}")
        return 1
    result = audit_card(card, raw_contract)
    report = render(result)
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
    print(report)
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
