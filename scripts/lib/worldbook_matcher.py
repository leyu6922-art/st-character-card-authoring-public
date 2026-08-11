"""Single source of truth for approximate SillyTavern World Info matching.

The matcher intentionally models the ST v1.18 initial-scan guard for
``extensions.scan_depth``: an explicit value of ``0`` (or a negative value)
produces an empty scan buffer and therefore cannot match any primary key.
``null``/omitted means use ST's global scan depth and is therefore matchable
against the supplied source text in this static approximation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass
class MatchResult:
    ok: bool
    primary_hits: list[str] = field(default_factory=list)
    secondary_hits: list[str] = field(default_factory=list)


def parse_regex_from_string(needle: str) -> tuple[str, int] | None:
    match = re.fullmatch(r"/((?:\\/|[^/])*)/([dgimsuvy]*)", needle)
    if not match:
        return None
    pattern = match.group(1).replace(r"\/", "/")
    flags = 0
    if "i" in match.group(2):
        flags |= re.I
    if "m" in match.group(2):
        flags |= re.M
    if "s" in match.group(2):
        flags |= re.S
    return pattern, flags


def match_key(entry: dict[str, Any], source_text: str, key: str) -> bool:
    key = str(key or "").strip()
    if not key:
        return False
    parsed = parse_regex_from_string(key)
    if parsed:
        pattern, flags = parsed
        try:
            return re.search(pattern, source_text or "", flags) is not None
        except re.error:
            return False

    extensions = entry.get("extensions") or {}
    haystack = source_text or ""
    needle = key
    if extensions.get("case_sensitive") is not True:
        haystack, needle = haystack.lower(), needle.lower()
    if extensions.get("match_whole_words") is True:
        if len(needle.split()) > 1:
            return needle in haystack
        return re.search(r"(?:^|\W)" + re.escape(needle) + r"(?:$|\W)", haystack) is not None
    return needle in haystack


def entry_trigger_match(entry: dict[str, Any], source_text: str) -> MatchResult:
    if entry.get("constant") or not entry.get("enabled", True):
        return MatchResult(False)

    # ST v1.18 calls buffer.get(entry) before primary matching. An explicit
    # scan_depth=0 makes that buffer empty because the initial scan starts at
    # depth 0. Treat it as unreachable; null/omitted delegates to global depth.
    extensions = entry.get("extensions") or {}
    raw_scan_depth = extensions.get("scan_depth", extensions.get("scanDepth"))
    if raw_scan_depth is not None:
        try:
            if int(raw_scan_depth) <= 0:
                return MatchResult(False)
        except (TypeError, ValueError):
            # Preserve the prior permissive approximation for malformed values;
            # structural validators can report the malformed field separately.
            pass

    keys = [str(key) for key in entry.get("keys", []) if key]
    secondary = [str(key) for key in entry.get("secondary_keys", []) if key]
    primary_hits = [key for key in keys if match_key(entry, source_text, key)]
    if not primary_hits:
        return MatchResult(False)

    secondary_hits = [key for key in secondary if match_key(entry, source_text, key)]
    if entry.get("selective") is not True or not secondary:
        return MatchResult(True, primary_hits, secondary_hits)

    logic = entry.get("selectiveLogic", (entry.get("extensions") or {}).get("selectiveLogic", 0))
    try:
        logic = int(logic)
    except (TypeError, ValueError):
        logic = 0
    if logic == 3:  # AND_ALL
        ok = len(secondary_hits) == len(secondary)
    elif logic == 2:  # NOT_ANY
        ok = not secondary_hits
    elif logic == 1:  # NOT_ALL
        ok = len(secondary_hits) < len(secondary)
    else:  # AND_ANY
        ok = bool(secondary_hits)
    return MatchResult(ok, primary_hits, secondary_hits)


def simulate_recursive_activation(
    entries: list[dict[str, Any]], source_text: str, *, max_iterations: int = 10
) -> tuple[set[Any], set[Any]]:
    """Approximate initial plus recursive World Info activation with one matcher.

    Initial activation scans the supplied greeting/chat text. Later rounds scan the
    content of already activated entries, but only candidates explicitly marked
    ``prevent_recursion=False`` may join. Disabled, constant, selective, regex,
    case, and whole-word semantics all remain centralized in ``entry_trigger_match``.
    """
    indexed = [(entry.get("id", index), entry) for index, entry in enumerate(entries)]
    initial_ids = {entry_id for entry_id, entry in indexed if entry_trigger_match(entry, source_text).ok}
    activated_ids = set(initial_ids)

    for _iteration in range(max_iterations):
        activated_content = "\n".join(
            str(entry.get("content", ""))
            for entry_id, entry in indexed
            if entry_id in activated_ids
        )
        additions: set[Any] = set()
        for entry_id, entry in indexed:
            if entry_id in activated_ids:
                continue
            if (entry.get("extensions") or {}).get("prevent_recursion", True) is not False:
                continue
            if entry_trigger_match(entry, activated_content).ok:
                additions.add(entry_id)
        if not additions:
            break
        activated_ids.update(additions)

    return initial_ids, activated_ids
