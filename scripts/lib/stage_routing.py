"""Canonical stage-routing grammar shared by delivery, validation, and audits."""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any, Match

# Supported production title forms. Keep this as the single source of truth.
TITLE_RE = re.compile(
    r"【(?:开场：(?:P(?P<stage_a>\d+)[^】]*?｜[^】]*|[^】]*?｜P(?P<stage_b>\d+)[^】]*)|图鉴：[^】]+｜(?P<stage_menu>MENU))】"
)
STAGE_RE = re.compile(r"^P\d+$")
ROUTE_STAGE_RE = re.compile(r"\bROUTE_STAGE=P\d+\b", re.IGNORECASE)


def title_matches(text: str) -> list[Match[str]]:
    return list(TITLE_RE.finditer(text or ""))


def parse_title(match: Match[str]) -> tuple[str, str]:
    if match.group("stage_menu"):
        return "MENU", match.group(0)
    number = match.group("stage_a") or match.group("stage_b")
    return f"P{number}", match.group(0)


def parse_stage_title(text: str) -> tuple[str, str] | None:
    matches = title_matches(text)
    if len(matches) != 1:
        return None
    return parse_title(matches[0])


def is_stage_title_key(value: object) -> bool:
    return parse_stage_title(str(value)) is not None


def _string_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable) and not isinstance(value, (bytes, dict)):
        return [str(item) for item in value if isinstance(item, str)]
    return []


def primary_keys(entry: dict[str, Any]) -> list[str]:
    """Return the ST primary-key field, supporting legacy singular ``key``."""
    if "keys" in entry:
        return _string_values(entry.get("keys"))
    return _string_values(entry.get("key"))


def secondary_keys(entry: dict[str, Any]) -> list[str]:
    return _string_values(entry.get("secondary_keys"))


def card_data(card: dict[str, Any]) -> dict[str, Any]:
    data = card.get("data", card)
    return data if isinstance(data, dict) else card


def card_entries(card: dict[str, Any]) -> list[dict[str, Any]]:
    data = card_data(card)
    book = data.get("character_book") or card.get("character_book") or {}
    entries = book.get("entries", []) if isinstance(book, dict) else []
    if isinstance(entries, dict):
        entries = list(entries.values())
    return [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []


def greeting_texts(card: dict[str, Any]) -> list[str]:
    data = card_data(card)
    values = [str(data.get("first_mes", "") or "")]
    values.extend(_string_values(data.get("alternate_greetings")))
    values.extend(_string_values(data.get("group_only_greetings")))
    return values


def declared_titles_by_stage(card: dict[str, Any]) -> dict[str, set[str]]:
    """Return native stage-route declarations from Greetings only.

    A stage title in a World Info key is a binding claim, never evidence that the
    card declared native Greeting-title routing in the first place.
    """
    titles: dict[str, set[str]] = {}
    for text in greeting_texts(card):
        for match in title_matches(text):
            stage, title = parse_title(match)
            titles.setdefault(stage, set()).add(title)
    return titles


def bound_titles_by_stage(card: dict[str, Any]) -> dict[str, set[str]]:
    """Return exact stage titles that World Info primary keys bind to."""
    titles: dict[str, set[str]] = {}
    for entry in card_entries(card):
        for key in primary_keys(entry):
            parsed = parse_stage_title(key)
            if parsed:
                stage, title = parsed
                titles.setdefault(stage, set()).add(title)
    return titles


def all_titles_by_stage(card: dict[str, Any]) -> dict[str, set[str]]:
    """Return the union of declared Greeting titles and entry title bindings.

    This diagnostic view must not be used for architecture detection.
    """
    titles = {stage: set(values) for stage, values in declared_titles_by_stage(card).items()}
    for stage, values in bound_titles_by_stage(card).items():
        titles.setdefault(stage, set()).update(values)
    return titles


def titles_by_stage(card: dict[str, Any]) -> dict[str, set[str]]:
    """Backward-compatible diagnostic alias for all declared/bound titles."""
    return all_titles_by_stage(card)


def has_native_stage_routing(card: dict[str, Any]) -> bool:
    return bool(declared_titles_by_stage(card))


def entry_bound_titles(entry: dict[str, Any]) -> set[str]:
    """Return exact native title keys bound to an entry's primary-key field."""
    return {
        parsed[1]
        for key in primary_keys(entry)
        if (parsed := parse_stage_title(key)) is not None
    }


def route_stage_markers(entry: dict[str, Any]) -> list[str]:
    """Return external ROUTE_STAGE evidence from all model-visible entry fields."""
    values = [*primary_keys(entry), *secondary_keys(entry), str(entry.get("content", ""))]
    return [value for value in values if ROUTE_STAGE_RE.search(value)]


def protocol_signature() -> str:
    """Stable representation used by meta-audits to detect matcher drift."""
    return TITLE_RE.pattern
