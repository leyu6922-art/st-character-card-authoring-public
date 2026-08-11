#!/usr/bin/env python3
"""Audit direct canonical-source material coverage in a finished character card.

This is an evidence gate: it measures whether an eligible runtime entry contains at
least one exact normalized excerpt from the supplied canonical source. It does not
judge prose quality, and it never treats a source match as permission to bypass
scope or safety review.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


NON_MATERIAL_ROLES = {"identity_toggle", "feature_toggle", "system_constant"}
SYSTEM_MARKERS = ("OOC", "系统", "状态栏", "规则", "协议", "文风", "防护", "锚点")


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", str(text))


def eligible_entry(entry: dict[str, Any]) -> bool:
    ext = entry.get("extensions") or {}
    role = ext.get("entry_role")
    comment = str(entry.get("comment", ""))
    if not entry.get("enabled", True) or entry.get("constant"):
        return False
    if role in NON_MATERIAL_ROLES or any(marker in comment for marker in SYSTEM_MARKERS):
        return False
    return bool(normalized(entry.get("content", "")))


def has_canonical_excerpt(content: str, source: str, min_quote_chars: int = 24, source_windows: set[str] | None = None) -> bool:
    body = normalized(content)
    source = normalized(source)
    if len(body) < min_quote_chars or len(source) < min_quote_chars:
        return False
    windows = source_windows if source_windows is not None else {
        source[start : start + min_quote_chars] for start in range(0, len(source) - min_quote_chars + 1)
    }
    return any(
        body[start : start + min_quote_chars] in windows
        for start in range(0, len(body) - min_quote_chars + 1)
    )


def audit_card_data(card: dict[str, Any], source: str, min_quote_chars: int = 24) -> dict[str, Any]:
    data = card.get("data", card)
    entries = data.get("character_book", {}).get("entries", [])
    eligible = [entry for entry in entries if eligible_entry(entry)]
    normalized_source = normalized(source)
    source_windows = {
        normalized_source[start : start + min_quote_chars]
        for start in range(0, max(0, len(normalized_source) - min_quote_chars + 1))
    }
    matched_ids: list[int] = []
    unmatched_ids: list[int] = []
    for entry in eligible:
        target = matched_ids if has_canonical_excerpt(
            entry.get("content", ""), source, min_quote_chars, source_windows
        ) else unmatched_ids
        target.append(entry.get("id"))
    count = len(eligible)
    coverage = (len(matched_ids) / count) if count else None
    return {
        "eligible": count,
        "matched": len(matched_ids),
        "coverage": coverage,
        "status": "ok" if count else "no_eligible",
        "matched_ids": matched_ids,
        "unmatched_ids": unmatched_ids,
    }


def read_source(paths: list[Path]) -> str:
    return "\n".join(path.read_text(encoding="utf-8-sig") for path in paths)


def load_corpus_mode(manifest_path: Path | None) -> str:
    if manifest_path is None:
        return "legacy_unspecified"
    raw = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    value = raw.get("corpus_mode") if isinstance(raw, dict) else None
    return value if isinstance(value, str) and value else "legacy_unspecified"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit canonical excerpt coverage for runtime material entries.")
    parser.add_argument("card", type=Path)
    parser.add_argument("--source", action="append", type=Path, required=True, help="Canonical text file; repeatable.")
    parser.add_argument("--minimum", type=float, default=None, help="explicit coverage minimum; defaults to 0.60 except curated_anchor_set")
    parser.add_argument("--manifest", type=Path, help="optional Manifest v2 supplying corpus_mode")
    parser.add_argument("--min-quote-chars", type=int, default=24)
    args = parser.parse_args()
    if args.minimum is not None and not 0 <= args.minimum <= 1:
        parser.error("--minimum must be between 0 and 1")
    corpus_mode = load_corpus_mode(args.manifest)
    minimum = args.minimum if args.minimum is not None else (0.0 if corpus_mode == "curated_anchor_set" else 0.60)
    card = json.loads(args.card.read_text(encoding="utf-8-sig"))
    source = read_source(args.source)
    result = audit_card_data(card, source, args.min_quote_chars)
    coverage_text = "N/A" if result["coverage"] is None else f"{result['coverage']:.1%}"
    print(f"eligible={result['eligible']} matched={result['matched']} coverage={coverage_text}")
    if result["unmatched_ids"]:
        print("unmatched_ids=" + ",".join(map(str, result["unmatched_ids"])))
    if result["status"] == "no_eligible":
        if corpus_mode == "curated_anchor_set" and args.minimum is None:
            print("SOURCE_COVERAGE_NOT_APPLICABLE_CURATED_ANCHORS")
            return 0
        print("SOURCE_COVERAGE_NO_ELIGIBLE_ENTRIES", file=sys.stderr)
        return 1
    if corpus_mode == "curated_anchor_set" and args.minimum is None:
        print("SOURCE_COVERAGE_CURATED_ANCHORS_NO_UNIVERSAL_MINIMUM")
        return 0
    return 0 if result["coverage"] >= minimum else 2


if __name__ == "__main__":
    raise SystemExit(main())
