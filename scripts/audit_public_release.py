"""Static public-release audit for paths, secrets, provenance markers, and scope."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SKIP_PARTS = {".git", ".pytest_cache", "__pycache__", "_archived", "_maintenance_backups"}
PRIVATE_PATH_RE = re.compile(
    r"(?i)(?:[A-Z]:/Users/(?!<[^>]+>/)[^/\s]+|D:/hermes|/home/(?!<[^>]+>/)[^/\s]+/|/mnt/c/Users/(?!<[^>]+>/)[^/\s]+/)"
)
SECRET_RES = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*[\"'][A-Za-z0-9_./+=-]{16,}[\"']"),
)


def _issue(code: str, **fields: str) -> dict:
    return {"code": code, **fields}


def audit_tree(
    root: Path,
    *,
    audit_kind: str = "artifact",
    provenance_manifest: Path | None = None,
    require_provenance: bool = False,
) -> dict:
    if audit_kind not in {"source", "artifact"}:
        raise ValueError("audit_kind must be source or artifact")
    root = Path(root).resolve()
    provenance_path = Path(provenance_manifest).resolve() if provenance_manifest else None
    issues: list[dict] = []
    for required in ("README.md", "SKILL.md", "LICENSE", "skill-manifest.json", "public-export-manifest.json"):
        if not (root / required).exists():
            issues.append(_issue("LICENSE_MISSING" if required == "LICENSE" else "REQUIRED_FILE_MISSING", file=required))
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        if relative in {"skill-manifest.json", "public-export-manifest.json", "scripts/audit_public_release.py"}:
            continue
        if path.name.startswith(".env") or path.suffix in {".pyc", ".pyo"}:
            issues.append(_issue("PRIVATE_ARTIFACT", file=relative))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if PRIVATE_PATH_RE.search(text.replace("\\", "/")):
            issues.append(_issue("PRIVATE_PATH", file=path.relative_to(root).as_posix()))
        if any(pattern.search(text) for pattern in SECRET_RES):
            issues.append(_issue("SECRET_PATTERN", file=path.relative_to(root).as_posix()))
    for name in ("skill-manifest.json", "public-export-manifest.json"):
        path = root / name
        if path.exists():
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                issues.append(_issue("MANIFEST_INVALID_JSON", file=name))
    if require_provenance:
        if provenance_path is None or not provenance_path.exists():
            issues.append(_issue("PROVENANCE_MANIFEST_MISSING", file=str(provenance_path or "<unspecified>")))
        else:
            try:
                provenance = json.loads(provenance_path.read_text(encoding="utf-8-sig"))
                files = provenance.get("files") if isinstance(provenance, dict) else None
                if provenance.get("manifest_kind") != "provenance" or not isinstance(files, dict):
                    issues.append(_issue("PROVENANCE_MANIFEST_INVALID", file=str(provenance_path)))
                else:
                    for path in root.rglob("*"):
                        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
                            continue
                        if provenance_path == path.resolve():
                            continue
                        rel = path.relative_to(root).as_posix()
                        record = files.get(rel)
                        if not isinstance(record, dict) or record.get("review_status") != "resolved" or record.get("redistribution") != "allowed":
                            issues.append(_issue("PROVENANCE_UNRESOLVED", file=rel))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                issues.append(_issue("PROVENANCE_MANIFEST_INVALID", file=str(provenance_path)))
    return {
        "schema_version": 1,
        "audit_kind": audit_kind,
        "release_blocking": audit_kind == "artifact",
        "errors": len(issues),
        "issues": sorted(issues, key=lambda x: (x["code"], x["file"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a tree before public export")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--kind", choices=("source", "artifact"), default="artifact")
    parser.add_argument("--provenance-manifest", type=Path)
    parser.add_argument("--require-provenance", action="store_true")
    args = parser.parse_args()
    result = audit_tree(
        args.root,
        audit_kind=args.kind,
        provenance_manifest=args.provenance_manifest,
        require_provenance=args.require_provenance,
    )
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Public release audit: {'PASS' if not result['errors'] else 'FAIL'}")
        for issue in result["issues"]:
            print(f"{issue['code']}: {issue['file']}")
    return 1 if result["errors"] and result["release_blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
