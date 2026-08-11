#!/usr/bin/env python3
"""Verify that a controlled enrichment pass only changed approved card content.

Usage:
  python verify_enrichment_pass.py BASE.json CANDIDATE.json manifest.json [-o report.md]

The manifest is intentionally small and project-local. Example:
{
  "pass_name": "protagonist-consolidation",
  "allowed_entry_ids": [5, 10, 11],
  "allowed_card_field_paths": ["data.character_version"],
  "allowed_entry_fields": ["content"],
  "required_headings": {"5": ["【主体形象总锚点】"]},
  "min_total_content_delta": 1000,
  "max_total_content_delta": 25000
}
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def get_data(card: Dict[str, Any]) -> Dict[str, Any]:
    data = card.get("data", card)
    if not isinstance(data, dict):
        raise ValueError("card.data must be an object")
    return data


def get_entries(card: Dict[str, Any]) -> List[Dict[str, Any]]:
    book = get_data(card).get("character_book") or card.get("character_book") or {}
    entries = book.get("entries", []) if isinstance(book, dict) else []
    if isinstance(entries, dict):
        entries = list(entries.values())
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        raise ValueError("character_book.entries must be a list of objects")
    return entries


def delete_path(obj: Dict[str, Any], dotted_path: str) -> None:
    parts = [p for p in dotted_path.split(".") if p]
    current: Any = obj
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict) and parts:
        current.pop(parts[-1], None)


def card_metadata_diff(base: Dict[str, Any], candidate: Dict[str, Any], allowed_paths: Iterable[str]) -> List[str]:
    left, right = copy.deepcopy(base), copy.deepcopy(candidate)
    for card in (left, right):
        for entries_path in ("data.character_book.entries", "character_book.entries"):
            delete_path(card, entries_path)
        for path in allowed_paths:
            delete_path(card, path)
    if left == right:
        return []
    return ["卡片元数据有未获准改动（只允许 manifest.allowed_card_field_paths 中的字段）"]


def mapping(entries: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    result: Dict[int, Dict[str, Any]] = {}
    for entry in entries:
        eid = entry.get("id")
        if not isinstance(eid, int):
            raise ValueError(f"entry id must be an int: {eid!r}")
        if eid in result:
            raise ValueError(f"duplicate entry id: {eid}")
        result[eid] = entry
    return result


def verify(base: Dict[str, Any], candidate: Dict[str, Any], manifest: Dict[str, Any]) -> Tuple[List[str], List[str], Dict[str, Any]]:
    allowed_ids = {int(x) for x in manifest.get("allowed_entry_ids", [])}
    allowed_fields = set(manifest.get("allowed_entry_fields", ["content"]))
    allowed_card_paths = manifest.get("allowed_card_field_paths", [])
    required_headings = {int(k): list(v) for k, v in manifest.get("required_headings", {}).items()}
    min_by_entry = {int(k): int(v) for k, v in manifest.get("min_content_delta_by_entry", {}).items()}
    max_by_entry = {int(k): int(v) for k, v in manifest.get("max_content_delta_by_entry", {}).items()}
    errors: List[str] = []
    notes: List[str] = []

    errors.extend(card_metadata_diff(base, candidate, allowed_card_paths))
    base_map, candidate_map = mapping(get_entries(base)), mapping(get_entries(candidate))
    if set(base_map) != set(candidate_map):
        missing = sorted(set(base_map) - set(candidate_map))
        added = sorted(set(candidate_map) - set(base_map))
        errors.append(f"条目集合变化：删除={missing or '-'} 新增={added or '-'}；受控加料默认禁止增删条目")

    changed_ids: List[int] = []
    total_delta = 0
    for eid in sorted(set(base_map) & set(candidate_map)):
        old, new = base_map[eid], candidate_map[eid]
        changed_fields = sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))
        if not changed_fields:
            continue
        changed_ids.append(eid)
        forbidden_fields = [field for field in changed_fields if field not in allowed_fields]
        if forbidden_fields:
            errors.append(f"[{eid}] 未获准字段改动：{', '.join(forbidden_fields)}")
        if "content" in changed_fields:
            delta = len(str(new.get("content", ""))) - len(str(old.get("content", "")))
            total_delta += delta
            if eid not in allowed_ids:
                errors.append(f"[{eid}] content 被改动，但不在 allowed_entry_ids")
            if eid in min_by_entry and delta < min_by_entry[eid]:
                errors.append(f"[{eid}] content 增量 {delta} < manifest 最小值 {min_by_entry[eid]}")
            if eid in max_by_entry and delta > max_by_entry[eid]:
                errors.append(f"[{eid}] content 增量 {delta} > manifest 最大值 {max_by_entry[eid]}")
            notes.append(f"[{eid}] content delta={delta}")
        elif eid not in allowed_ids:
            errors.append(f"[{eid}] 被改动，但不在 allowed_entry_ids")

    min_total = manifest.get("min_total_content_delta")
    max_total = manifest.get("max_total_content_delta")
    if min_total is not None and total_delta < int(min_total):
        errors.append(f"总 content 增量 {total_delta} < manifest 最小值 {min_total}")
    if max_total is not None and total_delta > int(max_total):
        errors.append(f"总 content 增量 {total_delta} > manifest 最大值 {max_total}")

    for eid, headings in required_headings.items():
        entry = candidate_map.get(eid)
        if entry is None:
            errors.append(f"required_headings 指向不存在的条目 [{eid}]")
            continue
        content = str(entry.get("content", ""))
        for heading in headings:
            if heading not in content:
                errors.append(f"[{eid}] 缺少要求的结构标题：{heading}")

    untouched_allowed = sorted(allowed_ids - set(changed_ids))
    if untouched_allowed:
        notes.append("获准但本轮未改动的条目：" + ", ".join(map(str, untouched_allowed)))
    summary = {"changed_ids": changed_ids, "total_content_delta": total_delta, "allowed_ids": sorted(allowed_ids)}
    return errors, notes, summary


def make_report(base_path: Path, candidate_path: Path, manifest_path: Path, errors: List[str], notes: List[str], summary: Dict[str, Any]) -> str:
    status = "FAIL" if errors else "PASS"
    lines = [
        f"# Controlled Enrichment Pass — {status}",
        "",
        f"- baseline: `{base_path}`",
        f"- candidate: `{candidate_path}`",
        f"- manifest: `{manifest_path}`",
        f"- allowed IDs: `{summary['allowed_ids']}`",
        f"- changed IDs: `{summary['changed_ids']}`",
        f"- total content delta: `{summary['total_content_delta']}` chars",
        "",
    ]
    if errors:
        lines += ["## Errors", *[f"- {item}" for item in errors], ""]
    if notes:
        lines += ["## Notes", *[f"- {item}" for item in notes], ""]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a controlled card-enrichment pass against a baseline and manifest")
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    parser.add_argument("manifest")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)
    base_path, candidate_path, manifest_path = map(lambda value: Path(value).expanduser().resolve(), [args.baseline, args.candidate, args.manifest])
    base, candidate, manifest = load_json(base_path), load_json(candidate_path), load_json(manifest_path)
    errors, notes, summary = verify(base, candidate, manifest)
    report = make_report(base_path, candidate_path, manifest_path, errors, notes, summary)
    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
    print(report)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
