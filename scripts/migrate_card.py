#!/usr/bin/env python3
"""Non-destructive character-card schema migration with explicit semantic flags."""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Sequence

from atomic_write_json import AtomicWriteResult, atomic_write_json
from lib.validation_profiles import validate_ccv3_core


@dataclass
class MigrationResult:
    output_path: Path
    changes: list[str] = field(default_factory=list)
    write_result: AtomicWriteResult | None = None


DATA_DEFAULTS = {
    "name": "",
    "description": "",
    "tags": [],
    "creator": "",
    "character_version": "",
    "mes_example": "",
    "extensions": {},
    "system_prompt": "",
    "post_history_instructions": "",
    "first_mes": "",
    "alternate_greetings": [],
    "personality": "",
    "scenario": "",
    "creator_notes": "",
    "group_only_greetings": [],
}
POS_NUM_TO_STR = {0: "before_char", 1: "after_char"}
SUPPLEMENTARY_REPLACEMENTS = {"📍": "[地点]", "🎭": "[角色]", "📖": "[叙事]", "💡": "[提示]"}


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def normalize_position(value: Any) -> str:
    """Normalize only positions admitted by the CCv3 core profile.

    ``before_def`` / ``after_def`` and native numeric 2 / 3 / 4 are
    SillyTavern-specific placement concepts. A core migrator must not silently emit them as if they
    were portable CCv3; callers need an explicit future ST-export adapter.
    """
    if value is None:
        return "after_char"
    if isinstance(value, bool):
        raise ValueError("entry position must not be boolean")
    if isinstance(value, int):
        if value in POS_NUM_TO_STR:
            return POS_NUM_TO_STR[value]
        raise ValueError(f"entry position {value!r} is not supported by CCv3 migration")
    if value in {"before_char", "after_char"}:
        return str(value)
    raise ValueError(f"entry position {value!r} is not supported by CCv3 migration")


def normalize_unicode(text: str) -> str:
    return "".join(SUPPLEMENTARY_REPLACEMENTS.get(char, "[特殊符号]") if ord(char) > 0xFFFF else char for char in text)


def validate_migrated_ccv3(payload: Any) -> None:
    """Block writes when migration would produce a card outside the core profile."""
    report = validate_ccv3_core(payload)
    if report.ok:
        return
    details = "\n".join(
        f"[{issue.rule_id}] {issue.path}: {issue.message}"
        for issue in report.errors
    )
    raise ValueError(f"CCV3 core validation failed after migration\n{details}")


def migrated_card(
    source: dict[str, Any],
    *,
    renumber_ids: bool = False,
    prevent_recursion: bool | None = None,
    normalize_supplementary_unicode: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    card = deepcopy(source)
    changes: list[str] = []
    if not isinstance(card.get("data"), dict):
        card["data"] = {key: card.get(key, default) for key, default in DATA_DEFAULTS.items()}
        if "character_book" in card:
            card["data"]["character_book"] = card["character_book"]
        changes.append("created data object from legacy top-level fields")
    data = card["data"]
    if card.get("spec") != "chara_card_v3":
        card["spec"] = "chara_card_v3"
        changes.append("set top-level spec=chara_card_v3")
    if card.get("spec_version") != "3.0":
        card["spec_version"] = "3.0"
        changes.append("set top-level spec_version=3.0")
    for key, default in DATA_DEFAULTS.items():
        if key not in data:
            data[key] = deepcopy(default)
            changes.append(f"added data.{key}")
    if not isinstance(data.get("extensions"), dict):
        data["extensions"] = {}
        changes.append("normalized data.extensions to object")

    book = data.get("character_book")
    if book is None:
        book = {"name": f"{data.get('name') or 'card'} lorebook", "extensions": {}, "entries": []}
        data["character_book"] = book
        changes.append("created empty character_book")
    if not isinstance(book, dict):
        raise ValueError("data.character_book must be an object for migration")
    book.setdefault("name", f"{data.get('name') or 'card'} lorebook")
    if not isinstance(book.get("extensions"), dict):
        book["extensions"] = {}
        changes.append("normalized character_book.extensions to object")
    entries = book.get("entries", [])
    if isinstance(entries, dict):
        entries = list(entries.values())
        book["entries"] = entries
        changes.append("converted character_book.entries object to list")
    if not isinstance(entries, list):
        raise ValueError("data.character_book.entries must be a list or object")

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"entry {index} must be an object")
        aliases = (("key", "keys"), ("keysecondary", "secondary_keys"), ("order", "insertion_order"), ("uid", "id"))
        for legacy_key, canonical_key in aliases:
            if canonical_key not in entry and legacy_key in entry:
                entry[canonical_key] = deepcopy(entry[legacy_key])
                changes.append(f"entry[{index}] copied {legacy_key} -> {canonical_key}")
        if "enabled" not in entry and "disable" in entry:
            entry["enabled"] = not bool(entry["disable"])
            changes.append(f"entry[{index}] copied disable -> enabled")
        entry.setdefault("id", index)
        entry["keys"] = ensure_list(entry.get("keys"))
        entry["secondary_keys"] = ensure_list(entry.get("secondary_keys"))
        entry.setdefault("content", "")
        entry.setdefault("comment", "")
        entry.setdefault("constant", False)
        entry.setdefault("selective", False)
        entry.setdefault("enabled", True)
        entry.setdefault("insertion_order", 100)
        entry.setdefault("use_regex", False)
        entry["position"] = normalize_position(entry.get("position", "after_char"))
        if not isinstance(entry.get("extensions"), dict):
            entry["extensions"] = {}
            changes.append(f"entry[{index}] normalized extensions to object")
        if renumber_ids and entry.get("id") != index:
            entry["id"] = index
            changes.append(f"entry[{index}] renumbered id")
        if prevent_recursion is not None and entry["extensions"].get("prevent_recursion") is not prevent_recursion:
            entry["extensions"]["prevent_recursion"] = prevent_recursion
            changes.append(f"entry[{index}] set prevent_recursion={prevent_recursion}")
        if normalize_supplementary_unicode:
            for field_name in ("content", "comment"):
                original = str(entry.get(field_name, ""))
                normalized = normalize_unicode(original)
                if normalized != original:
                    entry[field_name] = normalized
                    changes.append(f"entry[{index}] normalized supplementary unicode in {field_name}")

    if normalize_supplementary_unicode:
        for field_name in ("first_mes", "description", "personality", "scenario"):
            original = str(data.get(field_name, ""))
            normalized = normalize_unicode(original)
            if normalized != original:
                data[field_name] = normalized
                changes.append(f"normalized supplementary unicode in data.{field_name}")
        data["alternate_greetings"] = [normalize_unicode(str(value)) for value in data.get("alternate_greetings", [])]
    return card, changes


def migrate_card(
    input_path: str | Path,
    output_path: str | Path,
    *,
    renumber_ids: bool = False,
    set_prevent_recursion: bool | None = None,
    normalize_supplementary_unicode: bool = False,
    backup: bool = True,
) -> MigrationResult:
    source_path = Path(input_path).expanduser().resolve()
    destination = Path(output_path).expanduser().resolve()
    if source_path == destination:
        raise ValueError("migration output must be a new file; refusing in-place overwrite")
    source = json.loads(source_path.read_text(encoding="utf-8-sig"))
    if not isinstance(source, dict):
        raise ValueError("card JSON root must be an object")
    card, changes = migrated_card(
        source,
        renumber_ids=renumber_ids,
        prevent_recursion=set_prevent_recursion,
        normalize_supplementary_unicode=normalize_supplementary_unicode,
    )
    write_result = atomic_write_json(card, destination, backup=backup, validate=validate_migrated_ccv3)
    return MigrationResult(destination, changes, write_result)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview or write a non-destructive CCv3 card migration")
    parser.add_argument("input", help="source JSON card")
    parser.add_argument("--output", help="new output path; default: <input>.migrated.json")
    parser.add_argument("--write", action="store_true", help="perform the migration; default is dry-run")
    parser.add_argument("--renumber-ids", action="store_true", help="explicitly reassign lorebook IDs by list position")
    parser.add_argument("--set-prevent-recursion", choices=("true", "false"), help="explicitly rewrite every entry recursion value")
    parser.add_argument("--normalize-unicode", action="store_true", help="explicitly replace supplementary-plane symbols")
    args = parser.parse_args(argv)
    source_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve() if args.output else source_path.with_name(f"{source_path.stem}.migrated{source_path.suffix}")
    source = json.loads(source_path.read_text(encoding="utf-8-sig"))
    card, changes = migrated_card(
        source,
        renumber_ids=args.renumber_ids,
        prevent_recursion=None if args.set_prevent_recursion is None else args.set_prevent_recursion == "true",
        normalize_supplementary_unicode=args.normalize_unicode,
    )
    print(json.dumps({"dry_run": not args.write, "output": str(output_path), "changes": changes}, ensure_ascii=False, indent=2))
    if args.write:
        result = atomic_write_json(card, output_path, backup=True, validate=validate_migrated_ccv3)
        print(f"wrote={result.output_path} sha256={result.sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
