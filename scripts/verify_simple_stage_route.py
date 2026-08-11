#!/usr/bin/env python3
"""Verify the paired-preset `阶段P#` route-state contract for a stage card.

This validator is intentionally limited to the simple-marker architecture. It
checks card-side facts; the paired preset still needs a real ST run.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


def load_card(path: Path) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        card = json.load(handle)
    data = card.get("data", card)
    if not isinstance(data, dict):
        raise ValueError("card.data must be an object")
    book = data.get("character_book") or card.get("character_book") or {}
    entries = book.get("entries", []) if isinstance(book, dict) else []
    if isinstance(entries, dict):
        entries = list(entries.values())
    if not isinstance(entries, list):
        raise ValueError("character_book.entries must be a list/dict")
    return card, data, entries


def all_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from all_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from all_strings(item)


def audit_card(card_path: Path, stages: Sequence[int], marker_prefix: str = "阶段P", scan_depth: int | None = 2, forbidden: Sequence[str] = ()) -> Tuple[List[str], List[str], Dict[str, Any]]:
    card, data, entries = load_card(card_path)
    expected = {f"{marker_prefix}{stage}" for stage in stages}
    marker_re = re.compile(r"^" + re.escape(marker_prefix) + r"(\d+)$")
    errors: List[str] = []
    notes: List[str] = []

    greetings = [("first_mes", str(data.get("first_mes", "")))]
    greetings += [(f"alternate[{index}]", str(text)) for index, text in enumerate(data.get("alternate_greetings", []) or [])]
    greeting_stages: List[str] = []
    for label, greeting in greetings:
        blocks = re.findall(r"<route_state>\s*([^<]*?)\s*</route_state>", greeting, flags=re.S)
        if len(blocks) != 1:
            errors.append(f"{label}: route_state 块数量={len(blocks)}，必须恰好为1")
            continue
        payload = blocks[0].strip()
        if payload not in expected:
            errors.append(f"{label}: route_state payload={payload!r}，必须是 {sorted(expected)} 之一")
            continue
        greeting_stages.append(payload)
    missing_greeting_stages = sorted(expected - set(greeting_stages))
    if missing_greeting_stages:
        errors.append("没有任何 greeting 冷启动以下阶段：" + ", ".join(missing_greeting_stages))

    stage_entries: List[Dict[str, Any]] = []
    disabled_stage_entries: List[Any] = []
    per_stage = {marker: 0 for marker in expected}
    for entry in entries:
        keys = [str(key) for key in entry.get("keys", []) if key]
        stage_keys = [key for key in keys if marker_re.fullmatch(key)]
        # Disabled archive/history entries do not participate in ST matching.  They
        # are intentionally retained by versioned cards and must not fail the live
        # route contract merely because they preserve an old stage key.
        if not entry.get("enabled", True):
            if stage_keys:
                disabled_stage_entries.append(entry.get("id"))
            continue
        bare_keys = [key for key in keys if re.fullmatch(r"P\d+", key)]
        if bare_keys:
            errors.append(f"[{entry.get('id')}] 使用裸阶段 key：{bare_keys}")
        if not stage_keys:
            continue
        stage_entries.append(entry)
        invalid = [key for key in stage_keys if key not in expected]
        if invalid:
            errors.append(f"[{entry.get('id')}] 非法阶段 key：{invalid}")
        other_keys = [key for key in keys if key not in stage_keys]
        if other_keys:
            errors.append(f"[{entry.get('id')}] 简化阶段条目混入非阶段 keys：{other_keys}")
        if not entry.get("enabled", True) or entry.get("constant", False):
            errors.append(f"[{entry.get('id')}] 阶段条目必须 enabled=true 且 constant=false")
        if entry.get("selective") is True or entry.get("secondary_keys"):
            errors.append(f"[{entry.get('id')}] 简化阶段条目不得使用 selective/secondary_keys")
        ext = entry.get("extensions", {}) or {}
        if ext.get("selective") is True:
            errors.append(f"[{entry.get('id')}] extensions.selective=true 与简化阶段路由冲突")
        if scan_depth is not None and ext.get("scan_depth") != scan_depth:
            errors.append(f"[{entry.get('id')}] scan_depth={ext.get('scan_depth')!r}，预期 {scan_depth}")
        for marker in stage_keys:
            per_stage[marker] += 1
    if not stage_entries:
        errors.append("未检测到任何以阶段 marker 为 key 的阶段条目")
    missing_entries = [marker for marker, count in sorted(per_stage.items()) if count == 0]
    if missing_entries:
        errors.append("缺少阶段条目：" + ", ".join(missing_entries))

    all_text = "\n".join(all_strings(card))
    for token in forbidden:
        if token and token in all_text:
            errors.append(f"禁止残留命中：{token!r}")
    notes.append(f"greetings={len(greetings)} live_stage_entries={len(stage_entries)} per_stage={per_stage}")
    if disabled_stage_entries:
        notes.append(f"ignored disabled archived stage entries={disabled_stage_entries}")
    return errors, notes, {"greetings": len(greetings), "stage_entries": len(stage_entries), "per_stage": per_stage}


def make_report(card_path: Path, errors: List[str], notes: List[str]) -> str:
    status = "FAIL" if errors else "PASS"
    lines = [f"# Simple Stage Route Contract — {status}", "", f"- card: `{card_path}`", ""]
    if errors:
        lines += ["## Errors", *[f"- {item}" for item in errors], ""]
    if notes:
        lines += ["## Notes", *[f"- {item}" for item in notes], ""]
    return "\n".join(lines)


def parse_stages(value: str) -> List[int]:
    if "-" in value:
        first, last = value.split("-", 1)
        return list(range(int(first), int(last) + 1))
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify simple `阶段P#` route_state stage-card invariants")
    parser.add_argument("card")
    parser.add_argument("--stages", default="0-6", help="e.g. 0-6 or 0,1,2")
    parser.add_argument("--marker-prefix", default="阶段P")
    parser.add_argument("--scan-depth", type=int, default=2)
    parser.add_argument("--forbid", action="append", default=[], help="forbidden string; repeatable")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)
    path = Path(args.card).expanduser().resolve()
    errors, notes, _summary = audit_card(path, parse_stages(args.stages), args.marker_prefix, args.scan_depth, args.forbid)
    report = make_report(path, errors, notes)
    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
    print(report)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
