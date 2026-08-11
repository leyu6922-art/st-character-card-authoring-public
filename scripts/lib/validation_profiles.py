"""CCv3 core validation independent from Leyu production policy."""
from __future__ import annotations

from numbers import Number
from typing import Any

from lib.card_issues import Issue, ValidationReport


CCV3_CORE = "ccv3-core"
LEYU_PRODUCTION = "leyu-production"
PROFILES = (CCV3_CORE, LEYU_PRODUCTION)

REQUIRED_DATA_TYPES: dict[str, type | tuple[type, ...]] = {
    "name": str,
    "description": str,
    "tags": list,
    "creator": str,
    "character_version": str,
    "mes_example": str,
    "extensions": dict,
    "system_prompt": str,
    "post_history_instructions": str,
    "first_mes": str,
    "alternate_greetings": list,
    "personality": str,
    "scenario": str,
    "creator_notes": str,
    "group_only_greetings": list,
}
OPTIONAL_DATA_TYPES: dict[str, type | tuple[type, ...]] = {
    "nickname": str,
    "creator_notes_multilingual": dict,
    "source": list,
    "creation_date": Number,
    "modification_date": Number,
    "assets": list,
}


def _issue(rule_id: str, severity: str, path: str, message: str) -> Issue:
    return Issue(rule_id, severity, path, message, CCV3_CORE)


def _is_number(value: Any) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool)


def _matches_expected_type(value: Any, expected_type: type | tuple[type, ...]) -> bool:
    """Python bool is a Number subclass, but is never a valid CCv3 numeric value."""
    if expected_type is Number:
        return _is_number(value)
    return isinstance(value, expected_type)


def validate_ccv3_core(card: Any) -> ValidationReport:
    report = ValidationReport(CCV3_CORE)
    if not isinstance(card, dict):
        report.issues.append(_issue("CCV3_ROOT_NOT_OBJECT", "error", "$", "card root must be a JSON object"))
        return report

    if card.get("spec") != "chara_card_v3":
        report.issues.append(_issue("CCV3_SPEC_INVALID", "error", "spec", "must equal 'chara_card_v3'"))
    if card.get("spec_version") != "3.0":
        report.issues.append(_issue("CCV3_SPEC_VERSION_INVALID", "error", "spec_version", "must equal '3.0'"))

    data = card.get("data")
    if not isinstance(data, dict):
        report.issues.append(_issue("CCV3_DATA_NOT_OBJECT", "error", "data", "must be a JSON object"))
        return report

    for field_name, expected_type in REQUIRED_DATA_TYPES.items():
        path = f"data.{field_name}"
        if field_name not in data:
            report.issues.append(_issue("CCV3_REQUIRED_DATA_FIELD_MISSING", "error", path, "required CCv3 data field is missing"))
        elif not _matches_expected_type(data[field_name], expected_type):
            report.issues.append(_issue("CCV3_DATA_FIELD_TYPE", "error", path, f"must be {expected_type}"))

    for list_field in ("tags", "alternate_greetings", "group_only_greetings"):
        value = data.get(list_field)
        if isinstance(value, list) and not all(isinstance(item, str) for item in value):
            report.issues.append(_issue("CCV3_DATA_LIST_ITEM_TYPE", "error", f"data.{list_field}", "must contain only strings"))

    for field_name, expected_type in OPTIONAL_DATA_TYPES.items():
        if field_name in data and not _matches_expected_type(data[field_name], expected_type):
            report.issues.append(_issue("CCV3_OPTIONAL_DATA_FIELD_TYPE", "error", f"data.{field_name}", f"must be {expected_type} when present"))

    multilingual = data.get("creator_notes_multilingual")
    if isinstance(multilingual, dict) and not all(isinstance(value, str) for value in multilingual.values()):
        report.issues.append(_issue("CCV3_CREATOR_NOTES_MULTILINGUAL_VALUE_TYPE", "error", "data.creator_notes_multilingual", "values must be strings"))
    source = data.get("source")
    if isinstance(source, list) and not all(isinstance(value, str) for value in source):
        report.issues.append(_issue("CCV3_SOURCE_ITEM_TYPE", "error", "data.source", "must contain only strings"))
    assets = data.get("assets")
    if isinstance(assets, list):
        for index, asset in enumerate(assets):
            if not isinstance(asset, dict) or any(not isinstance(asset.get(field), str) for field in ("type", "uri", "name", "ext")):
                report.issues.append(_issue("CCV3_ASSET_FIELD_TYPE", "error", f"data.assets[{index}]", "must be an object with string type, uri, name, and ext"))

    if "character_book" in data and data["character_book"] is not None:
        _validate_lorebook(data["character_book"], "data.character_book", report)

    return report


def _validate_lorebook(book: Any, path: str, report: ValidationReport) -> None:
    if not isinstance(book, dict):
        report.issues.append(_issue("CCV3_LOREBOOK_NOT_OBJECT", "error", path, "must be a JSON object"))
        return

    if not isinstance(book.get("extensions"), dict):
        report.issues.append(_issue("CCV3_LOREBOOK_EXTENSIONS_INVALID", "error", f"{path}.extensions", "must be an object"))
    entries = book.get("entries")
    if not isinstance(entries, list):
        report.issues.append(_issue("CCV3_LOREBOOK_ENTRIES_INVALID", "error", f"{path}.entries", "must be an array"))
        return

    optional_types: dict[str, type | tuple[type, ...]] = {
        "name": str,
        "description": str,
        "scan_depth": Number,
        "token_budget": Number,
        "recursive_scanning": bool,
    }
    for field_name, expected_type in optional_types.items():
        if field_name in book and not _matches_expected_type(book[field_name], expected_type):
            report.issues.append(_issue("CCV3_LOREBOOK_FIELD_TYPE", "error", f"{path}.{field_name}", f"must be {expected_type} when present"))

    for index, entry in enumerate(entries):
        _validate_entry(entry, f"{path}.entries[{index}]", report)


def _validate_entry(entry: Any, path: str, report: ValidationReport) -> None:
    if not isinstance(entry, dict):
        report.issues.append(_issue("CCV3_LOREBOOK_ENTRY_NOT_OBJECT", "error", path, "must be a JSON object"))
        return

    required: dict[str, type | tuple[type, ...]] = {
        "keys": list,
        "content": str,
        "extensions": dict,
        "enabled": bool,
        "insertion_order": Number,
        "use_regex": bool,
    }
    for field_name, expected_type in required.items():
        item_path = f"{path}.{field_name}"
        if field_name not in entry:
            report.issues.append(_issue("CCV3_REQUIRED_ENTRY_FIELD_MISSING", "error", item_path, "required lorebook entry field is missing"))
        elif not _matches_expected_type(entry[field_name], expected_type):
            report.issues.append(_issue("CCV3_ENTRY_FIELD_TYPE", "error", item_path, f"must be {expected_type}"))

    if isinstance(entry.get("keys"), list) and not all(isinstance(key, str) for key in entry["keys"]):
        report.issues.append(_issue("CCV3_ENTRY_KEYS_ITEM_TYPE", "error", f"{path}.keys", "must contain only strings"))
    if "secondary_keys" in entry and (
        not isinstance(entry["secondary_keys"], list) or not all(isinstance(key, str) for key in entry["secondary_keys"])
    ):
        report.issues.append(_issue("CCV3_SECONDARY_KEYS_TYPE", "error", f"{path}.secondary_keys", "must be an array of strings when present"))
    if "id" in entry and not (isinstance(entry["id"], str) or _is_number(entry["id"])):
        report.issues.append(_issue("CCV3_ENTRY_ID_TYPE", "error", f"{path}.id", "must be a string, number, or omitted"))
    for field_name in ("constant", "selective"):
        if field_name in entry and not isinstance(entry[field_name], bool):
            report.issues.append(_issue("CCV3_ENTRY_OPTIONAL_BOOL_TYPE", "error", f"{path}.{field_name}", "must be boolean when present"))
    optional_types: dict[str, type | tuple[type, ...]] = {
        "case_sensitive": bool,
        "name": str,
        "priority": Number,
        "comment": str,
    }
    for field_name, expected_type in optional_types.items():
        if field_name in entry and not _matches_expected_type(entry[field_name], expected_type):
            report.issues.append(_issue("CCV3_ENTRY_OPTIONAL_FIELD_TYPE", "error", f"{path}.{field_name}", f"must be {expected_type} when present"))
    if "position" in entry and entry["position"] not in {"before_char", "after_char"}:
        report.issues.append(_issue("CCV3_ENTRY_POSITION_INVALID", "error", f"{path}.position", "must be 'before_char' or 'after_char' when present"))
