#!/usr/bin/env python3
"""Atomic, no-BOM JSON writing for character-card build artifacts."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Callable, Sequence


@dataclass(frozen=True)
class AtomicWriteResult:
    output_path: Path
    backup_path: Path | None
    sha256: str
    byte_count: int


def _backup_path_for(output_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return output_path.with_name(f"{output_path.stem}.{stamp}.bak{output_path.suffix}")


def _validate_profile_file(candidate_path: Path, profile: str) -> None:
    """Validate the serialized temporary artifact before it can replace output."""
    scripts_dir = str(Path(__file__).resolve().parent)
    inserted = scripts_dir not in sys.path
    if inserted:
        sys.path.insert(0, scripts_dir)
    try:
        from validate_card import validate_card_report
    finally:
        if inserted:
            sys.path.remove(scripts_dir)

    report = validate_card_report(str(candidate_path), profile=profile)
    if report.ok:
        return
    details = "\n".join(
        f"[{issue.rule_id}] {issue.path}: {issue.message}"
        for issue in report.issues
        if issue.severity == "error"
    )
    raise ValueError(f"profile validation failed ({profile})\n{details}")


def atomic_write_json(
    payload: Any,
    output_path: str | Path,
    *,
    backup: bool = True,
    validate: Callable[[Any], None] | None = None,
    validate_file: Callable[[Path], None] | None = None,
    indent: int = 2,
) -> AtomicWriteResult:
    """Validate, write a sibling temporary file, and atomically replace output.

    ``validate`` checks the in-memory payload; ``validate_file`` checks the
    serialized temporary artifact before any existing file is backed up or replaced.
    """
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if validate is not None:
        validate(payload)

    serialized = json.dumps(payload, ensure_ascii=False, indent=indent) + "\n"
    parsed = json.loads(serialized)
    if validate is not None:
        validate(parsed)

    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    backup_path: Path | None = None
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        raw = tmp_path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raise RuntimeError("internal writer created an unexpected UTF-8 BOM")
        json.loads(raw.decode("utf-8"))
        if validate_file is not None:
            validate_file(tmp_path)
        if path.exists() and backup:
            backup_path = _backup_path_for(path)
            shutil.copy2(path, backup_path)
        os.replace(tmp_path, path)
        return AtomicWriteResult(path, backup_path, hashlib.sha256(raw).hexdigest(), len(raw))
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Atomically normalize and write a JSON artifact without a BOM")
    parser.add_argument("input", help="source JSON file")
    parser.add_argument("output", help="destination JSON file")
    parser.add_argument("--no-backup", action="store_true", help="do not create a timestamped backup when replacing output")
    parser.add_argument(
        "--validate-profile",
        choices=("ccv3-core", "leyu-production"),
        help="validate the serialized temporary artifact before replacement",
    )
    args = parser.parse_args(argv)
    payload = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    validate_file = None
    if args.validate_profile:
        validate_file = lambda candidate: _validate_profile_file(candidate, args.validate_profile)
    result = atomic_write_json(
        payload,
        args.output,
        backup=not args.no_backup,
        validate_file=validate_file,
    )
    print(json.dumps({
        "output_path": str(result.output_path),
        "backup_path": str(result.backup_path) if result.backup_path else None,
        "sha256": result.sha256,
        "byte_count": result.byte_count,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
