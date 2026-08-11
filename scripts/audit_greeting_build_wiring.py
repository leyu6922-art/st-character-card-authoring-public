#!/usr/bin/env python3
"""Audit Greeting synchronization between build sources and the final card.

This is intentionally separate from check_build_sync.py: a generic build source
may contain a pure ``greetings`` mapping even when its Lorebook entries are
otherwise synchronized.  For prose_plus_director_appendix, the source Greeting
must retain the delimiter and stage_brief_v1 appendix before assembly.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent


def _load_audit_module():
    path = SCRIPT_DIR / "audit_greeting_layers.py"
    spec = importlib.util.spec_from_file_location("audit_greeting_layers_for_wiring", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _source_greetings(project_dir: Path, audit_module) -> list[tuple[str, str]]:
    path = project_dir / "build" / "all_entries.json"
    if not path.exists():
        raise FileNotFoundError(f"build source does not exist: {path}")
    raw = _load_json(path)
    greetings = raw.get("greetings") if isinstance(raw, dict) else None
    if isinstance(greetings, dict) and all(isinstance(value, str) for value in greetings.values()):
        return [(str(label), value) for label, value in greetings.items()]
    if isinstance(raw, dict):
        extracted = audit_module.get_greetings(raw)
        if extracted:
            return extracted
    raise ValueError("build/all_entries.json does not contain a text greetings mapping")


def _card_greetings(card_path: Path, audit_module) -> list[tuple[str, str]]:
    card = _load_json(card_path)
    greetings = audit_module.get_greetings(card)
    if not greetings:
        raise ValueError("card does not contain first_mes or alternate_greetings")
    return greetings


def audit_build_wiring(
    card_path: Path,
    project_dir: Path,
    min_cn: int = 1400,
    max_cn: int = 1800,
    appendix_standard: str = "none",
) -> dict[str, Any]:
    """Return a deterministic source/artifact Greeting synchronization report."""
    audit_module = _load_audit_module()
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []
    try:
        source = _source_greetings(project_dir, audit_module)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "status": "FAIL",
            "errors": [f"[BUILD_GREETING_SOURCE_MISSING] {exc}"],
            "warnings": [],
            "notes": [],
        }
    try:
        artifact = _card_greetings(card_path, audit_module)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "status": "FAIL",
            "errors": [f"[BUILD_GREETING_ARTIFACT_MISSING] {exc}"],
            "warnings": [],
            "notes": [],
        }

    if len(source) != len(artifact):
        errors.append(
            f"[BUILD_GREETING_COUNT_DRIFT] source={len(source)} artifact={len(artifact)}"
        )

    for index, (source_item, artifact_item) in enumerate(zip(source, artifact)):
        source_label, source_text = source_item
        artifact_label, artifact_text = artifact_item
        label = f"source={source_label}, artifact={artifact_label}, index={index}"
        source_report = audit_module.audit_one(
            source_text, source_label, min_cn, max_cn, appendix_standard
        )
        for issue in source_report["issues"]:
            if issue["severity"] == "error":
                errors.append(
                    f"[BUILD_GREETING_SOURCE_INVALID] {label}: "
                    f"{issue['code']}: {issue['message']}"
                )
            else:
                warnings.append(
                    f"[BUILD_GREETING_SOURCE_WARNING] {label}: "
                    f"{issue['code']}: {issue['message']}"
                )
        if source_text != artifact_text:
            errors.append(
                f"[BUILD_GREETING_CONTENT_DRIFT] {label}: source and assembled Greeting differ"
            )
        notes.append(
            f"{label}: source_body_cjk={source_report['body_cjk']}, "
            f"source_appendix_chars={source_report['appendix_chars']}"
        )

    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    return {"status": status, "errors": errors, "warnings": warnings, "notes": notes}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("card", type=Path)
    parser.add_argument("--project-dir", type=Path, required=True)
    parser.add_argument("--min-cn", type=int, default=1400)
    parser.add_argument("--max-cn", type=int, default=1800)
    parser.add_argument("--appendix-standard", choices=("none", "stage_brief_v1"), default="none")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    result = audit_build_wiring(
        args.card.resolve(), args.project_dir.resolve(), args.min_cn, args.max_cn, args.appendix_standard
    )
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Greeting build wiring: {result['status']}")
        for key in ("errors", "warnings", "notes"):
            for item in result[key]:
                print(f"- {item}")
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
