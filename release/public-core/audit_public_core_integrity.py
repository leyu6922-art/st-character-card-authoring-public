#!/usr/bin/env python3
"""Minimal static integrity audit for the sanitized Public Core artifact."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED = (
    "README.md",
    "SKILL.md",
    "LICENSE",
    "skill-manifest.json",
    "public-export-manifest.json",
    "scripts/audit_docs.py",
    "scripts/audit_public_release.py",
    "scripts/doctor.py",
    "scripts/export_public.py",
    "scripts/audit_public_core_integrity.py",
)


def _core_file_exists(root: Path, relative: str) -> bool:
    direct = root / relative
    if direct.is_file():
        return True
    # Private source trees keep sanitized override documents under release/public-core.
    return (root / "release" / "public-core" / relative).is_file()


def audit(root: Path) -> dict:
    root = Path(root).resolve()
    missing = [path for path in REQUIRED if not _core_file_exists(root, path)]
    return {
        "schema_version": 1,
        "audit_kind": "public-core-integrity",
        "status": "PASS" if not missing else "FAIL",
        "errors": [{"code": "REQUIRED_CORE_FILE_MISSING", "file": path} for path in missing],
        "checks": {"required_files": len(REQUIRED) - len(missing), "required_files_total": len(REQUIRED)},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit the sanitized Public Core integrity contract")
    parser.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    result = audit(args.skill_root)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if args.format == "json":
        print(rendered)
    else:
        print(f"Public Core integrity audit - {result['status']}")
        for error in result["errors"]:
            print(f"{error['code']}: {error['file']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
