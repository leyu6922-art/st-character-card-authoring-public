#!/usr/bin/env python3
"""Read-only token-load analysis using the shared World Info matcher.

This diagnostic estimates card text load for a greeting or supplied chat text. It
never edits the card. Trigger reachability and key changes belong to
`audit_worldbook_triggers.py` plus explicit source edits, not an optimizer.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from lib.worldbook_matcher import entry_trigger_match


def _entries_from_card(card: dict[str, Any]) -> list[dict[str, Any]]:
    data = card.get("data", card)
    book = data.get("character_book") or card.get("character_book") or {}
    entries = book.get("entries", [])
    if isinstance(entries, dict):
        entries = list(entries.values())
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        raise ValueError("character_book.entries must be an array/object of entry objects")
    return entries


def _runtime_category(entry: dict[str, Any]) -> str:
    """Classify visible runtime responsibility without prescribing a budget."""
    if entry.get("constant"):
        return "constant"
    comment = str(entry.get("comment", ""))
    ext = entry.get("extensions") if isinstance(entry.get("extensions"), dict) else {}
    declared = str(ext.get("runtime_category", ""))
    if declared:
        return declared
    for label, category in (
        ("阶段核心", "stage_core"),
        ("成人体验", "adult_pack"),
        ("场景体验", "scene_pack"),
        ("事件库", "event_pack"),
    ):
        if label in comment:
            return category
    if "事件" in comment or "种子" in comment:
        return "event"
    if "场景" in comment:
        return "scene"
    return "common_content"


def _category_summary(items: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for entry in items:
        category = _runtime_category(entry)
        bucket = summary.setdefault(category, {"entries": 0, "chars": 0, "ids": []})
        bucket["entries"] += 1
        bucket["chars"] += len(str(entry.get("content", "")))
        bucket["ids"].append(entry.get("id", "?"))
    return summary


def analyze_token_load(path: str | Path, custom_text: str | None = None, optimize: bool = False) -> dict[str, Any]:
    """Return a non-mutating load report using actual enabled/selective matching."""
    if optimize:
        raise ValueError(
            "optimize=True is retired: this analyzer is read-only. Run audit_worldbook_triggers.py, "
            "then make explicit source changes reviewed by build-sync."
        )
    card_path = Path(path).expanduser().resolve()
    card = json.loads(card_path.read_text(encoding="utf-8-sig"))
    if not isinstance(card, dict):
        raise ValueError("card root must be an object")
    data = card.get("data", card)
    entries = _entries_from_card(card)
    source_text = custom_text if custom_text is not None else str(data.get("first_mes", ""))

    constant_entries = [entry for entry in entries if entry.get("constant") and entry.get("enabled", True)]
    triggered = [
        (entry, entry_trigger_match(entry, source_text))
        for entry in entries
        if not entry.get("constant")
    ]
    triggered = [(entry, match) for entry, match in triggered if match.ok]

    const_chars = sum(len(str(entry.get("content", ""))) for entry in constant_entries)
    triggered_chars = sum(len(str(entry.get("content", ""))) for entry, _match in triggered)
    total_chars = const_chars + triggered_chars
    est_tokens = total_chars // 2

    key_to_entries: dict[str, list[Any]] = {}
    for entry in entries:
        if entry.get("constant") or not entry.get("enabled", True):
            continue
        for key in entry.get("keys", []):
            key = str(key)
            if key:
                key_to_entries.setdefault(key, []).append(entry.get("id", "?"))
    key_counts = Counter({key: len(ids) for key, ids in key_to_entries.items()})
    generic_keys = [(key, count, key_to_entries[key]) for key, count in key_counts.items() if count >= 2]

    active_entries = constant_entries + [entry for entry, _match in triggered]
    categories = _category_summary(active_entries)
    report = {
        "source": str(card_path),
        "source_text_chars": len(source_text),
        "total_entries": len(entries),
        "const_entries": len(constant_entries),
        "triggered_entries": len(triggered),
        "triggered_ids": [entry.get("id", "?") for entry, _match in triggered],
        "trigger_reasons": {
            str(entry.get("id", "?")): {
                "primary_hits": match.primary_hits,
                "secondary_hits": match.secondary_hits,
            }
            for entry, match in triggered
        },
        "const_chars": const_chars,
        "triggered_chars": triggered_chars,
        "total_chars": total_chars,
        "est_tokens": est_tokens,
        "estimate_note": "rough character-count estimate only; compare with SillyTavern Prompt Itemization before setting any policy threshold",
        "categories": categories,
        "shared_keys": generic_keys,
        "status": "diagnostic",
    }
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only token load analysis for a character card")
    parser.add_argument("card", help="card JSON path")
    parser.add_argument("--text", help="simulate this text instead of data.first_mes")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    report = analyze_token_load(args.card, custom_text=args.text)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"entries: {report['total_entries']} (constant={report['const_entries']}, triggered={report['triggered_entries']})")
        print(f"chars: constant={report['const_chars']} triggered={report['triggered_chars']} total={report['total_chars']}")
        print(f"estimated tokens (rough only): {report['est_tokens']}")
        for category, summary in report["categories"].items():
            print(f"category {category}: entries={summary['entries']} chars={summary['chars']} ids={summary['ids']}")
        if report["triggered_ids"]:
            print(f"triggered IDs: {report['triggered_ids']}")
        if report["shared_keys"]:
            print(f"shared keys: {report['shared_keys'][:10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
