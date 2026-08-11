"""Fail-closed deterministic exporter for a fresh public repository tree."""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REVIEW_STATUSES = {"approved_public", "rejected_private", "third_party_reviewed"}


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    return data


def _load_export_manifest(path: Path) -> dict[str, Any]:
    data = _load(path)
    if data.get("manifest_kind") != "public-export":
        raise ValueError("manifest must declare manifest_kind=public-export")
    return data


def _load_review_manifest(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    data = _load(path)
    if data.get("manifest_kind") != "public-review":
        raise ValueError("review manifest must declare manifest_kind=public-review")
    reviews = data.get("reviews")
    if not isinstance(reviews, list):
        raise ValueError("review manifest reviews must be a list")
    result: dict[str, str] = {}
    for item in reviews:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("each review must contain a path")
        rel = item["path"].replace("\\", "/")
        status = item.get("status")
        if status not in REVIEW_STATUSES:
            raise ValueError(f"unsupported review status for {rel}: {status}")
        if rel in result:
            raise ValueError(f"duplicate review path: {rel}")
        result[rel] = status
    return result


def _validate_patterns(patterns: list[str]) -> None:
    if len(set(patterns)) != len(patterns):
        raise ValueError("duplicate path pattern")
    for pattern in patterns:
        normalized = pattern.replace("\\", "/")
        if not normalized or "\x00" in normalized:
            raise ValueError("invalid path pattern")
        if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
            raise ValueError("absolute path pattern is not allowed")
        if ".." in Path(normalized).parts:
            raise ValueError("path pattern may not contain ..")


def _match(rel: str, pattern: str) -> bool:
    rel = rel.replace("\\", "/").casefold()
    pattern = pattern.replace("\\", "/").casefold()
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return rel == prefix or rel.startswith(prefix + "/")
    return fnmatch.fnmatchcase(rel, pattern) or (
        pattern.startswith("**/") and fnmatch.fnmatchcase(rel, pattern[3:])
    )


def _any(rel: str, patterns: list[str]) -> bool:
    return any(_match(rel, pattern) for pattern in patterns)


def _binary(path: Path) -> bool:
    raw = path.read_bytes()
    if raw.startswith((bytes((0xFF, 0xFE)), bytes((0xFE, 0xFF)))):
        try:
            raw.decode("utf-16")
            return False
        except UnicodeDecodeError:
            return True
    if 0 in raw:
        return True
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_commit(source: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = proc.stdout.strip()
    return value if proc.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40}", value) else None


def _release_trace(
    source: Path,
    manifest_path: Path,
    copied: list[str],
    manual_review: list[str],
    rejected_private: list[str],
    skill_manifest_path: Path | None = None,
) -> dict[str, Any]:
    skill_manifest = skill_manifest_path or (source / "skill-manifest.json")
    return {
        "source_commit": _source_commit(source),
        "export_manifest_sha256": _sha256(manifest_path),
        "skill_manifest_sha256": _sha256(skill_manifest) if skill_manifest.is_file() else None,
        "export_timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "exported_files": len(copied),
        "manual_review_unresolved": len(manual_review),
        "rejected_private": len(rejected_private),
    }


def export_tree(
    source: Path,
    destination: Path,
    manifest_path: Path,
    *,
    dry_run: bool = False,
    include_manual_review: bool = False,
    review_manifest: Path | None = None,
    run_audit: bool = True,
) -> dict[str, Any]:
    source = Path(source).expanduser().resolve()
    destination = Path(destination).expanduser().resolve()
    manifest_path = Path(manifest_path).expanduser().resolve()
    manifest = _load_export_manifest(manifest_path)
    if include_manual_review:
        raise ValueError("bulk manual review is disabled; provide a review manifest")
    if not source.is_dir():
        raise ValueError(f"source is not a directory: {source}")
    if destination == source or source in destination.parents or destination in source.parents:
        raise ValueError("source and destination must not be inside source or inside destination")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("destination is non-empty; use a fresh destination")

    scope = manifest.get("source_scope", {})
    includes = list(scope.get("include", []))
    excludes = list(scope.get("exclude", []))
    manual_patterns = list(scope.get("manual_review", []))
    _validate_patterns(includes)
    _validate_patterns(excludes)
    _validate_patterns(manual_patterns)
    if set(includes) & set(excludes):
        raise ValueError("allow/deny path pattern conflict")
    raw_overrides = manifest.get("overrides", {})
    if not isinstance(raw_overrides, dict):
        raise ValueError("overrides must be an object")
    overrides: dict[str, Path] = {}
    override_sources: set[str] = set()
    for target_raw, source_raw in raw_overrides.items():
        if not isinstance(target_raw, str) or not isinstance(source_raw, str):
            raise ValueError("override paths must be strings")
        target = target_raw.replace("\\", "/")
        source_rel = source_raw.replace("\\", "/")
        _validate_patterns([target, source_rel])
        source_path = (source / source_rel).resolve()
        if source_path != source and source not in source_path.parents:
            raise ValueError(f"override source escapes source tree: {source_rel}")
        if target in overrides:
            raise ValueError(f"duplicate override target: {target}")
        overrides[target] = source_path
        override_sources.add(source_rel)

    review_path = review_manifest
    if review_path is None and manifest.get("review_manifest"):
        review_path = manifest_path.parent / str(manifest["review_manifest"])
    reviews = _load_review_manifest(review_path) if review_path else {}
    copied: list[str] = []
    skipped: list[str] = []
    manual_review: list[str] = []
    approved_public: list[str] = []
    rejected_private: list[str] = []
    errors: list[str] = []
    staging: Path | None = None
    copy_root = destination
    if not dry_run:
        staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.staging-", dir=str(destination.parent)))
        copy_root = staging

    try:
        for path in sorted(source.rglob("*")):
            rel = path.relative_to(source).as_posix()
            if ".git" in path.parts:
                if not _any(rel, includes) or _any(rel, excludes):
                    skipped.append(rel)
                    continue
                errors.append(f"GIT_METADATA_REJECTED: {rel}")
                continue
            if path.is_symlink():
                errors.append(f"SYMLINK_REJECTED: {rel}")
                continue
            if not path.is_file():
                continue
            if not _any(rel, includes) or _any(rel, excludes):
                skipped.append(rel)
                continue
            if rel in override_sources:
                skipped.append(rel)
                continue
            if _binary(path):
                errors.append(f"BINARY_REJECTED: {rel}")
                continue
            if _any(rel, manual_patterns):
                status = reviews.get(rel)
                if status == "approved_public":
                    approved_public.append(rel)
                elif status == "rejected_private":
                    rejected_private.append(rel)
                    continue
                elif status == "third_party_reviewed":
                    approved_public.append(rel)
                else:
                    manual_review.append(rel)
                    continue
            copied.append(rel)
            if not dry_run:
                target = copy_root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)

        for target_rel, source_path in overrides.items():
            if not source_path.is_file() or source_path.is_symlink():
                errors.append(f"OVERRIDE_SOURCE_REJECTED: {target_rel}")
                continue
            if _binary(source_path):
                errors.append(f"OVERRIDE_BINARY_REJECTED: {target_rel}")
                continue
            if target_rel not in copied:
                copied.append(target_rel)
            if not dry_run:
                target = copy_root / target_rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target)

        if manual_review and run_audit:
            errors.extend(f"MANUAL_REVIEW_UNRESOLVED: {rel}" for rel in manual_review)
        audit: dict[str, Any] | None = None
        if not dry_run and run_audit and not errors:
            try:
                from .audit_public_release import audit_tree
            except ImportError:
                from audit_public_release import audit_tree
            provenance_raw = manifest.get("provenance_manifest")
            provenance_path = (manifest_path.parent / str(provenance_raw)).resolve() if provenance_raw else None
            audit = audit_tree(
                copy_root,
                provenance_manifest=provenance_path,
                require_provenance=bool(manifest.get("require_provenance", False)),
            )
            errors.extend(f"{item['code']}: {item['file']}" for item in audit["issues"])
        if not dry_run and errors:
            return {
                "schema_version": 1, "source": str(source), "destination": str(destination),
                "dry_run": dry_run, "published": False, "copied": copied, "skipped": skipped,
                "manual_review": manual_review, "approved_public": approved_public,
                "rejected_private": rejected_private, "audit": audit if 'audit' in locals() else None,
                "release_trace": _release_trace(
                    source, manifest_path, copied, manual_review, rejected_private,
                    skill_manifest_path=overrides.get("skill-manifest.json"),
                ),
                "errors": errors,
            }
        if not dry_run:
            if destination.exists():
                destination.rmdir()
            copy_root.replace(destination)
            staging = None
        return {
            "schema_version": 1, "source": str(source), "destination": str(destination),
            "dry_run": dry_run, "published": not dry_run, "copied": copied, "skipped": skipped,
            "manual_review": manual_review, "approved_public": approved_public,
            "rejected_private": rejected_private, "audit": audit if 'audit' in locals() else None,
            "release_trace": _release_trace(
                source, manifest_path, copied, manual_review, rejected_private,
                skill_manifest_path=overrides.get("skill-manifest.json"),
            ),
            "errors": errors,
        }
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export a fail-closed public tree from an allowlist manifest")
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--review-manifest")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-audit", action="store_true")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    try:
        result = export_tree(
            Path(args.source), Path(args.destination), Path(args.manifest),
            dry_run=args.dry_run,
            review_manifest=Path(args.review_manifest) if args.review_manifest else None,
            run_audit=not args.no_audit,
        )
    except Exception as exc:
        print(json.dumps({"schema_version": 1, "published": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        report = Path(args.report).expanduser().resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
