"""Shared issue model for validation and delivery gates."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha1
import re
from typing import Any, Iterable


@dataclass(frozen=True)
class Issue:
    rule_id: str
    severity: str  # error | warning | info
    path: str
    message: str
    profile: str
    blocking: bool = False

    def render(self) -> str:
        return f"[{self.rule_id}] {self.path}: {self.message}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
            "profile": self.profile,
            "blocking": self.blocking,
        }


@dataclass
class ValidationReport:
    profile: str
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "ok": self.ok,
            "issues": [issue.as_dict() for issue in self.issues],
        }


def stable_legacy_rule_id(prefix: str, message: str) -> str:
    """Give legacy text diagnostics a stable, aggregate-friendly fallback id."""
    normalized = re.sub(r"\[\d+\]", "[entry]", message)
    normalized = re.sub(r"\d+", "#", normalized)
    normalized = re.sub(r"'[^']*'", "'<text>'", normalized)
    digest = sha1(normalized.encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}_{digest}"


def has_distinct_blocking_warning_threshold(issues: Iterable[Issue], threshold: int = 3) -> bool:
    rule_ids = {
        issue.rule_id
        for issue in issues
        if issue.severity == "warning" and issue.blocking
    }
    return len(rule_ids) >= threshold
