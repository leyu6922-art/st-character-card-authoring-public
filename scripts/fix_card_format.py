#!/usr/bin/env python3
"""Deprecated compatibility wrapper for the non-destructive v5.2 migrator.

Use `migrate_card.py` for new code. Unlike the old formatter, this wrapper never
rewrites the source card: it writes `<source>.migrated.json` unless an explicit
new output path is supplied.
"""
from __future__ import annotations

from pathlib import Path

from migrate_card import migrate_card


def fix_card(path: str, card_name: str = "", output_path: str | None = None):
    source = Path(path).expanduser().resolve()
    destination = Path(output_path).expanduser().resolve() if output_path else source.with_name(f"{source.stem}.migrated{source.suffix}")
    result = migrate_card(source, destination)
    return [f"output: {result.output_path}", *result.changes]


def fix_recursive_triggers(*_args, **_kwargs):
    raise RuntimeError(
        "fix_recursive_triggers() was destructive and is retired. "
        "Use migrate_card.py --set-prevent-recursion true --write with a new --output path."
    )


def optimize_token_load(*_args, **_kwargs):
    raise RuntimeError(
        "optimize_token_load() is retired. Run audit_worldbook_triggers.py and make explicit source edits."
    )


if __name__ == "__main__":
    print("Deprecated wrapper. Use: python migrate_card.py INPUT --output OUTPUT --write")
