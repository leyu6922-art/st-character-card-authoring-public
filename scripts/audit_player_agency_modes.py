#!/usr/bin/env python3
"""Audit the opt-in director and player-agency mode contract for ST cards."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

DIRECTOR_MODE = "narrative_director"
BOUNDARY_MODE = "player_agency_boundary"
REQUIRED_MODES = (DIRECTOR_MODE, BOUNDARY_MODE)


@dataclass
class AgencyAuditResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def rule_ids(self) -> set[str]:
        result = set()
        for message in [*self.errors, *self.warnings]:
            if message.startswith("[") and "]" in message:
                result.add(message[1:message.index("]")])
        return result


def _issue(result: AgencyAuditResult, rule_id: str, message: str) -> None:
    result.errors.append(f"[{rule_id}] {message}")


def _entry_mode(entry: dict) -> str:
    return str((entry.get("extensions") or {}).get("feature_mode") or "")


def _has_any(text: str, markers: Iterable[str]) -> bool:
    return any(marker in text for marker in markers)


def _priority_is_valid(entry: dict) -> bool:
    ext = entry.get("extensions") or {}
    return (
        entry.get("position") == "before_char"
        and ext.get("position") == 0
        and int(ext.get("depth", 0) or 0) >= 4
        and ext.get("ignore_budget") is True
        and ext.get("exclude_recursion") is True
    )


def _boundary_missing_coverage(content: str) -> list[str]:
    groups = {
        "speech": ("说话", "台词", "发言", "回答"),
        "thought": ("思考", "内心", "判断"),
        "decision": ("决定", "选择", "同意", "拒绝"),
        "location": ("移动", "进入", "离开", "场景"),
        "action": ("行动", "使用物品", "接受邀约", "完成调查"),
        "knowledge": ("未观察", "未获知", "未知", "记忆"),
        "timeline": ("时间", "阶段", "切换", "跳过"),
    }
    return [name for name, markers in groups.items() if not _has_any(content, markers)]


def audit_entries(
    entries: list[dict],
    *,
    require_modes: bool = False,
    require_boundary: bool = False,
    require_boundary_always_on: bool = False,
) -> AgencyAuditResult:
    result = AgencyAuditResult()
    by_mode: dict[str, list[dict]] = {mode: [] for mode in REQUIRED_MODES}
    for entry in entries:
        mode = _entry_mode(entry)
        if mode in by_mode:
            by_mode[mode].append(entry)

    found_modes = [mode for mode, matches in by_mode.items() if matches]
    required_modes = list(REQUIRED_MODES) if require_modes else ([BOUNDARY_MODE] if require_boundary else [])
    if not found_modes and not required_modes:
        result.notes.append("player-agency mode contract not declared; legacy card not audited")
        return result

    missing_modes = [mode for mode in required_modes if not by_mode[mode]]
    if missing_modes:
        _issue(
            result,
            "PLAYER_AGENCY_MODES_MISSING",
            "required feature modes missing: " + ", ".join(missing_modes),
        )

    for mode, matches in by_mode.items():
        if len(matches) > 1:
            _issue(
                result,
                "PLAYER_AGENCY_MODE_DUPLICATE",
                f"feature_mode={mode} appears {len(matches)} times; exactly one is required",
            )
        if not matches:
            continue
        entry = matches[0]
        entry_id = entry.get("id", "?")
        ext = entry.get("extensions") or {}
        if mode == DIRECTOR_MODE:
            if not (
                ext.get("entry_role") == "feature_toggle"
                and entry.get("constant") is True
                and entry.get("enabled") is False
                and entry.get("keys") == []
                and entry.get("secondary_keys") == []
                and entry.get("selective") is False
            ):
                _issue(
                    result,
                    "PLAYER_AGENCY_MODE_SCHEMA",
                    f"entry[{entry_id}] {mode} must be a disabled constant feature_toggle with empty keys",
                )
            if entry.get("enabled") is True:
                _issue(
                    result,
                    "PLAYER_AGENCY_MODE_DEFAULT_ENABLED",
                    f"entry[{entry_id}] {mode} must default to enabled=false",
                )
        else:
            always_on_boundary = (
                ext.get("entry_role") == "system_constant"
                and ext.get("enforcement") == "always_on"
                and entry.get("constant") is True
                and entry.get("enabled") is True
                and entry.get("keys") == []
                and entry.get("secondary_keys") == []
                and entry.get("selective") is False
            )
            legacy_disabled_boundary = (
                ext.get("entry_role") == "feature_toggle"
                and entry.get("constant") is True
                and entry.get("enabled") is False
                and entry.get("keys") == []
                and entry.get("secondary_keys") == []
                and entry.get("selective") is False
            )
            if require_boundary_always_on and not always_on_boundary:
                _issue(
                    result,
                    "PLAYER_AGENCY_BOUNDARY_NOT_ALWAYS_ON",
                    f"entry[{entry_id}] {mode} must be an enabled system_constant with enforcement=always_on and empty keys",
                )
            elif not always_on_boundary and not legacy_disabled_boundary:
                _issue(
                    result,
                    "PLAYER_AGENCY_BOUNDARY_SCHEMA",
                    f"entry[{entry_id}] {mode} must use either the legacy disabled feature_toggle or the always-on system_constant schema",
                )
        if not _priority_is_valid(entry):
            _issue(
                result,
                "PLAYER_AGENCY_MODE_PRIORITY_INVALID",
                f"entry[{entry_id}] {mode} must use before_char/ext.position=0/depth>=4/ignore_budget/exclude_recursion",
            )

    director_entries = by_mode[DIRECTOR_MODE]
    if director_entries:
        content = str(director_entries[0].get("content", ""))
        missing = []
        if not _has_any(content, ("NPC", "非玩家")):
            missing.append("NPC scope")
        if "环境" not in content:
            missing.append("environment scope")
        if "事件" not in content:
            missing.append("event scope")
        if not _has_any(content, ("不得替{{user}}", "不得代替{{user}}")):
            missing.append("no-player-substitution rule")
        if not _has_any(content, ("一个主要事件", "一次只推进一个")):
            missing.append("single-event pacing")
        if missing:
            _issue(
                result,
                "PLAYER_AGENCY_DIRECTOR_SCOPE_THIN",
                "narrative director missing: " + ", ".join(missing),
            )

    boundary_entries = by_mode[BOUNDARY_MODE]
    if boundary_entries:
        content = str(boundary_entries[0].get("content", ""))
        missing = _boundary_missing_coverage(content)
        if missing:
            _issue(
                result,
                "PLAYER_AGENCY_BOUNDARY_COVERAGE_THIN",
                "player boundary missing: " + ", ".join(missing),
            )
        if not ("优先" in content and _has_any(content, ("自动推进剧情", "剧情导演"))):
            _issue(
                result,
                "PLAYER_AGENCY_MODE_PRECEDENCE_MISSING",
                "boundary content must state that it overrides the narrative director on conflict",
            )
        if not _has_any(content, ("接管点", "等待{{user}}", "等待玩家")):
            _issue(
                result,
                "PLAYER_AGENCY_SUSPENSION_RULE_THIN",
                "boundary content must require a player takeover point before consequential progression",
            )

    return result


def load_entries(card_path: Path) -> list[dict]:
    card = json.loads(card_path.read_text(encoding="utf-8-sig"))
    data = card.get("data", card)
    entries = (data.get("character_book") or card.get("character_book") or {}).get("entries", [])
    if isinstance(entries, dict):
        entries = list(entries.values())
    if not isinstance(entries, list):
        raise ValueError("character_book.entries must be a list or object")
    return entries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit opt-in player-agency modes")
    parser.add_argument("card", help="final card JSON path")
    parser.add_argument("--require", action="store_true", help="reject cards that omit the dual-mode contract")
    parser.add_argument("--require-boundary", action="store_true", help="require only the player-agency boundary mode; director mode remains optional")
    args = parser.parse_args(argv)
    try:
        result = audit_entries(
            load_entries(Path(args.card)),
            require_modes=args.require,
            require_boundary=args.require_boundary,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"[PLAYER_AGENCY_AUDIT_INPUT_ERROR] {exc}")
        return 3
    for message in result.errors:
        print(message)
    for message in result.warnings:
        print(message)
    for message in result.notes:
        print(f"[NOTE] {message}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
