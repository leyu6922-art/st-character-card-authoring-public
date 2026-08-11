"""Audit repository-relative references in Markdown documentation."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SKIP_PARTS = {".git", ".pytest_cache", "__pycache__", "_archived", "_maintenance_backups"}
SIBLING_REFERENCES = {
    "references/staged-novel-native-trigger-architecture.md",
    "scripts/audit_native_stage_architecture.py",
    "scripts/audit_stage_card_scripts.py",
}
PATH_RE = re.compile(r"(?<![\w/])((?:references|scripts|templates|docs|schemas|profiles|examples|project-template|tests)/[^\s`<>\"'\])]+)")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _clean(token: str) -> str:
    token = token.split("#", 1)[0].strip().rstrip(".,;:，。；：）】")
    return token.replace("\\", "/")


def _is_logical_or_external(token: str) -> bool:
    return (token.startswith(("http://", "https://", "mailto:")) or token.startswith("<")
            or token.startswith(("/", "C:/", "D:/", "~", "<card-skill>"))
            or any(char in token for char in "*+?{}[]"))


def audit_docs(root: Path) -> dict:
    root = Path(root).resolve()
    issues: list[dict] = []
    warnings: list[dict] = []
    for path in root.rglob("*.md"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        tokens = set(PATH_RE.findall(text)) | set(LINK_RE.findall(text))
        for raw in tokens:
            token = _clean(raw)
            if not token or _is_logical_or_external(token):
                continue
            candidates = (root / token, path.parent / token)
            if not any(candidate.exists() for candidate in candidates):
                issue = {
                    "code": "DOC_LINK_MISSING",
                    "file": path.relative_to(root).as_posix(),
                    "reference": token,
                }
                if token in SIBLING_REFERENCES:
                    issue["code"] = "DOC_LINK_SIBLING_REFERENCE"
                    warnings.append(issue)
                else:
                    issues.append(issue)
    return {"errors": len(issues), "warnings": sorted(warnings, key=lambda x: (x["file"], x["reference"])), "issues": sorted(issues, key=lambda x: (x["file"], x["reference"]))}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit repository-relative Markdown references")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    result = audit_docs(args.root)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Documentation audit: {'PASS' if not result['errors'] else 'FAIL'}")
        for issue in result["issues"]:
            print(f"{issue['code']}: {issue['file']} -> {issue['reference']}")
        for issue in result["warnings"]:
            print(f"WARNING {issue['code']}: {issue['file']} -> {issue['reference']}")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
