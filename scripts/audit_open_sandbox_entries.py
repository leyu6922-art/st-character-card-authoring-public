#!/usr/bin/env python3
"""Audit the entry shape of an open-sandbox card without forcing stage transitions."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lib.narrative_contracts import load_json, validate_contract_bundle


@dataclass
class AuditResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _entries(card: dict[str, Any]) -> list[dict[str, Any]]:
    data = card.get("data", card)
    book = data.get("character_book", {}) if isinstance(data, dict) else {}
    entries = book.get("entries", []) if isinstance(book, dict) else []
    return [entry for entry in entries if isinstance(entry, dict)]


ENTRY_ROLES = {
    "character_entry",
    "scene_entry",
    "behavior_entry",
    "system_constant",
    "event_candidate",
}
INTERACTIVE_ENTRY_ROLES = {
    "character_entry",
    "scene_entry",
    "behavior_entry",
    "event_candidate",
}
SANDBOX_SCOPES = {"focused", "ensemble", "legacy_unspecified"}


def _metadata(entry: dict[str, Any]) -> dict[str, Any]:
    extensions = entry.get("extensions")
    return dict(extensions) if isinstance(extensions, dict) else {}


def _keys(entry: dict[str, Any]) -> list[Any]:
    value = entry.get("keys", entry.get("key", []))
    return value if isinstance(value, list) else [value]


def _has_natural_keys(entry: dict[str, Any]) -> bool:
    keys = _keys(entry)
    normalized = [key.strip().casefold() for key in keys if isinstance(key, str) and key.strip()]
    return bool(keys) and len(normalized) == len(keys) and len(set(normalized)) == len(normalized) and all(
        not key.startswith(("p0", "p1", "p2", "p3", "p4", "p5", "p6", "event:"))
        for key in normalized
    )


def _natural_key_signature(entry: dict[str, Any]) -> tuple[str, ...]:
    return tuple(sorted(key.strip().casefold() for key in _keys(entry)))


def audit_card(card: Any, manifest: dict[str, Any] | None = None) -> AuditResult:
    result = AuditResult()
    if not isinstance(card, dict):
        result.errors.append("open_sandbox card根节点必须是对象")
        return result
    manifest = manifest or {"narrative_mode": "open_sandbox"}
    if manifest.get("narrative_mode") != "open_sandbox":
        result.errors.append(f"CONTRACT_MODE_MISMATCH: open-sandbox审计不适用{manifest.get('narrative_mode')!r}")
        return result
    sandbox_scope = manifest.get("sandbox_scope", "legacy_unspecified")
    if sandbox_scope not in SANDBOX_SCOPES:
        result.errors.append(f"INVALID_SANDBOX_SCOPE: {sandbox_scope!r}")
        sandbox_scope = "legacy_unspecified"
    entries = _entries(card)
    if not entries:
        result.errors.append("open_sandbox必须声明可调用入口条目")
        return result
    counted: dict[str, list[dict[str, Any]]] = {role: [] for role in INTERACTIVE_ENTRY_ROLES}
    seen_entry_ids: set[str] = set()
    seen_key_signatures: dict[str, set[tuple[str, ...]]] = {role: set() for role in counted}
    for index, entry in enumerate(entries):
        metadata = _metadata(entry)
        if metadata.get("sandbox_entry") is not True:
            continue
        valid_entry = True
        if entry.get("enabled") is not True:
            result.errors.append(f"open_sandbox入口[{index}]必须显式enabled=true")
            valid_entry = False
        if entry.get("constant") is not False:
            result.errors.append(f"open_sandbox入口[{index}]必须显式constant=false")
            valid_entry = False
        if entry.get("selective") is not True:
            result.errors.append(f"open_sandbox入口[{index}]必须显式selective=true")
            valid_entry = False
        if not _has_natural_keys(entry):
            result.errors.append(f"open_sandbox入口[{index}]必须声明非空自然keys")
            valid_entry = False
        role = metadata.get("entry_role")
        if role not in ENTRY_ROLES:
            result.errors.append(f"open_sandbox入口[{index}]缺少合法entry_role")
            continue
        if role == "system_constant":
            result.errors.append(f"open_sandbox入口[{index}]的system_constant不能作为可调用入口")
            continue
        entry_id = metadata.get("sandbox_entry_id")
        if not isinstance(entry_id, str) or not entry_id.strip():
            result.errors.append(f"open_sandbox入口[{index}]必须声明唯一sandbox_entry_id")
            valid_entry = False
        else:
            normalized_entry_id = entry_id.strip().casefold()
            if normalized_entry_id in seen_entry_ids:
                result.errors.append(f"open_sandbox入口[{index}]sandbox_entry_id重复: {entry_id}")
                valid_entry = False
            else:
                seen_entry_ids.add(normalized_entry_id)
        role_group = "behavior_entry" if role == "event_candidate" else role
        if valid_entry:
            signature = _natural_key_signature(entry)
            if signature in seen_key_signatures[role_group]:
                result.errors.append(f"open_sandbox入口[{index}]与同类入口重复自然keys: {entry_id}")
                continue
            seen_key_signatures[role_group].add(signature)
            counted[role_group].append(metadata)
    minimum = 1 if sandbox_scope == "focused" else 2
    minimum_label = "一个" if minimum == 1 else "两个"
    if len(counted["character_entry"]) < minimum:
        result.errors.append(
            f"open_sandbox至少需要{minimum_label}独立character_entry"
        )
    if len(counted["scene_entry"]) < minimum:
        result.errors.append(
            f"open_sandbox至少需要{minimum_label}独立scene_entry"
        )
    behavior_count = len(counted["behavior_entry"]) + len(counted["event_candidate"])
    if behavior_count < minimum:
        result.errors.append(
            f"open_sandbox至少需要{minimum_label}独立behavior/event入口"
        )
    if not any(item.get("npc_initiative") is True for item in counted["behavior_entry"] + counted["event_candidate"]):
        result.errors.append("open_sandbox至少需要一个npc_initiative=true入口")
    if not any(_metadata(item).get("world_continuation") is True for item in entries):
        result.warnings.append("open_sandbox的无事件世界延续未由静态结构证明，需人工复核")
    if manifest.get("event_policy") == "ordered_steps":
        result.errors.append("open_sandbox不能声明ordered_steps固定顺序")
    if any(
        _metadata(item).get("requires_all_events") is True
        or _metadata(item).get("ordered_steps") is True
        or _metadata(item).get("next") is not None
        for item in entries
    ):
        result.errors.append("open_sandbox不能把入口声明为固定顺序链")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("card", type=Path)
    parser.add_argument("--manifest", type=Path, help="optional Manifest v2 for cross-file bundle validation")
    args = parser.parse_args(argv)
    try:
        card = json.loads(args.card.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    manifest = None
    result = AuditResult()
    if args.manifest:
        try:
            manifest = load_json(args.manifest)
            narrative_contract = None
            narrative_raw = manifest.get("narrative_contract")
            if narrative_raw:
                narrative_path = Path(narrative_raw)
                if not narrative_path.is_absolute():
                    narrative_path = args.manifest.parent / narrative_path
                if narrative_path.is_file():
                    narrative_contract = load_json(narrative_path)
            state_contract = None
            state_meta = manifest.get("runtime_state", {})
            if isinstance(state_meta, dict) and state_meta.get("contract"):
                state_path = Path(state_meta["contract"])
                if not state_path.is_absolute():
                    state_path = args.manifest.parent / state_path
                if state_path.is_file():
                    state_contract = load_json(state_path)
            bundle = validate_contract_bundle(manifest, narrative_contract, state_contract, args.manifest.parent)
            result.errors.extend(f"{issue.code}: {issue.message}" for issue in bundle.errors)
        except (OSError, UnicodeError, ValueError) as exc:
            result.errors.append(f"CONTRACT_BUNDLE_LOAD_ERROR: {exc}")
    sandbox_result = audit_card(card, manifest)
    result.errors.extend(sandbox_result.errors)
    result.warnings.extend(sandbox_result.warnings)
    for error in result.errors:
        print(f"ERROR: {error}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
