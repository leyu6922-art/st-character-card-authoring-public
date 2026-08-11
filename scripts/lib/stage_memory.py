"""Shared phase-memory anchor validation for native Greeting-stage cards."""
from __future__ import annotations

import re

from lib.card_issues import Issue


RULE_LABEL = "阶段表演规则"
ONLY_REMEMBERS = "仅记得"


def _visible_text(text: str) -> str:
    """Normalize whitespace and harmless markup before checking a compact anchor."""
    without_tags = re.sub(r"<[^>]+>", "", str(text or ""))
    return re.sub(r"\s+", "", without_tags).strip()


def phase_memory_anchor_issues(
    system_prompt: str,
    minimum_length: int = 40,
    *,
    profile: str = "leyu-production",
    path: str = "data.system_prompt",
) -> list[Issue]:
    """Return stable diagnostics for the one shared phase-memory prompt contract.

    The contract deliberately validates a compact anchor only. The detailed
    semantics belong in the required causal archive and memory-gate entries.
    """
    if minimum_length < 1:
        raise ValueError("minimum_length must be positive")

    text = _visible_text(system_prompt)
    issues: list[Issue] = []
    if len(text) < minimum_length:
        issues.append(Issue(
            "STAGE_MEMORY_ANCHOR_TOO_SHORT",
            "error",
            path,
            f"阶段记忆system_prompt锚点至少{minimum_length}字，当前{len(text)}字",
            profile,
            True,
        ))
    if RULE_LABEL not in text:
        issues.append(Issue(
            "STAGE_MEMORY_RULE_LABEL_MISSING",
            "error",
            path,
            "system_prompt缺少“阶段表演规则”锚点",
            profile,
            True,
        ))
    if ONLY_REMEMBERS not in text:
        issues.append(Issue(
            "STAGE_MEMORY_ONLY_REMEMBERS_ANCHOR_MISSING",
            "error",
            path,
            "system_prompt缺少“仅记得”阶段记忆锚点",
            profile,
            True,
        ))
    return issues
