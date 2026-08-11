#!/usr/bin/env python3
"""Deprecated compatibility wrapper for atomic character-card JSON output.

Use `atomic_write_json.py` for all new code. This wrapper retains the historical
function names but no longer contains review-evasion behavior.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from atomic_write_json import atomic_write_json


def safe_write_card(card: dict[str, Any], output_path: str | Path) -> int:
    """Write a card atomically, parse it back, and print a deterministic summary."""
    result = atomic_write_json(card, output_path, backup=True)
    data = card.get("data", {}) if isinstance(card, dict) else {}
    entries = (data.get("character_book") or {}).get("entries", []) if isinstance(data, dict) else []
    print(f"wrote atomically: {result.output_path}")
    print(f"sha256: {result.sha256}")
    print(f"entries: {len(entries) if isinstance(entries, list) else 0}")
    return result.byte_count


def safe_write_text(content: str, output_path: str | Path) -> int:
    """Legacy text helper; JSON card output must use atomic_write_json instead."""
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return path.stat().st_size


def safe_write_entries(entries: list[dict[str, Any]], output_path: str | Path) -> int:
    worldbook = {"entries": {str(index): entry for index, entry in enumerate(entries)}, "originalData": {"entries": {}, "name": "世界书"}}
    return safe_write_card(worldbook, output_path)


if __name__ == "__main__":
    print("Deprecated compatibility wrapper. Use: python atomic_write_json.py INPUT OUTPUT")
