"""Run the machine-checkable gates for the Leyu workflow distribution."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
LOCAL_GATE_NAMES = {
    "audit_public_release",
    "audit_docs_links",
    "full_pytest",
    "pipeline_static_audit",
    "compileall",
    "workflow_provenance_resolved",
    "private_path_and_secret_scan",
    "export_tree_rebuild_check",
    "nested_public_core_reference_integrity",
}
EXTERNAL_GATE_NAMES = {"exact_head_github_actions"}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _gate(status: str, detail: str, **extra: Any) -> dict[str, Any]:
    result = {"status": status, "detail": detail}
    result.update(extra)
    return result


def evaluate_manifest_contract(root: Path = ROOT) -> dict[str, Any]:
    """Validate the relationship between the root manifest and this runner."""
    root = Path(root).resolve()
    errors: list[str] = []
    try:
        manifest = _load_json(root / "public-export-manifest.json")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {"errors": [f"manifest load failed: {exc}"], "manifest": None}

    if manifest.get("manifest_kind") != "public-export":
        errors.append("public-export-manifest.json must declare manifest_kind=public-export")
    required = manifest.get("required_release_gates")
    external = manifest.get("external_release_gates")
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        errors.append("required_release_gates must be a list of strings")
        required = []
    if not isinstance(external, list) or not all(isinstance(item, str) for item in external):
        errors.append("external_release_gates must be a list of strings")
        external = []
    required_set = set(required)
    external_set = set(external)
    allowed_gate_names = LOCAL_GATE_NAMES | EXTERNAL_GATE_NAMES
    unknown_required = sorted(required_set - allowed_gate_names)
    unknown_external = sorted(external_set - EXTERNAL_GATE_NAMES)
    overlap = sorted((required_set & external_set) - EXTERNAL_GATE_NAMES)
    missing_external_declaration = sorted((required_set & EXTERNAL_GATE_NAMES) - external_set)
    if unknown_required:
        errors.append(f"unknown release gates: {', '.join(unknown_required)}")
    if unknown_external:
        errors.append(f"unknown external release gates: {', '.join(unknown_external)}")
    if overlap:
        errors.append(f"release gates cannot be both local and external: {', '.join(overlap)}")
    if missing_external_declaration:
        errors.append(f"external release gates must be declared: {', '.join(missing_external_declaration)}")
    runner = manifest.get("release_gate_runner")
    if runner != "scripts/release_gate.py":
        errors.append("release_gate_runner must be scripts/release_gate.py")
    if not (root / "scripts/release_gate.py").is_file():
        errors.append("scripts/release_gate.py is missing")
    if manifest.get("artifact_profile") != "workflow-distribution":
        errors.append("artifact_profile must be workflow-distribution")
    if manifest.get("artifact_release_line") != manifest.get("release_line"):
        errors.append("artifact_release_line must equal the workflow release_line")
    if manifest.get("strict_core_release_line") != "v0.1.0-public-readiness-core-rc2":
        errors.append("strict_core_release_line must identify the nested strict Core RC2")
    provenance = manifest.get("provenance_manifest")
    if provenance != "workflow-provenance-manifest.json":
        errors.append("root workflow provenance_manifest must be workflow-provenance-manifest.json")
    if not (root / "workflow-provenance-manifest.json").is_file():
        errors.append("workflow-provenance-manifest.json is missing")
    if manifest.get("current_blockers") != []:
        errors.append("current_blockers must be empty for this candidate gate")
    return {
        "errors": errors,
        "manifest": manifest,
        "required_release_gates": required,
        "external_release_gates": external,
    }


def verify_external_head(root: Path = ROOT, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Verify the exact commit identity when running inside GitHub Actions."""
    root = Path(root).resolve()
    environment = dict(os.environ if env is None else env)
    if environment.get("GITHUB_ACTIONS", "").lower() != "true":
        return _gate(
            "EXTERNAL_REQUIRED",
            "run in GitHub Actions to verify exact-head workflow evidence",
            expected_sha=None,
            actual_sha=None,
        )
    expected = environment.get("GITHUB_SHA", "").strip().lower()
    if not expected:
        return _gate("FAIL", "GITHUB_SHA is missing", expected_sha=None, actual_sha=None)
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    actual = proc.stdout.strip().lower()
    if proc.returncode != 0 or not actual:
        return _gate("FAIL", "cannot read checked-out git HEAD", expected_sha=expected, actual_sha=actual)
    if actual != expected:
        return _gate("FAIL", "GITHUB_SHA does not match checked-out HEAD", expected_sha=expected, actual_sha=actual)
    return _gate("PASS", "GITHUB_SHA matches checked-out HEAD", expected_sha=expected, actual_sha=actual)


def _run_command(name: str, command: list[str], root: Path) -> dict[str, Any]:
    started = time.monotonic()
    proc = subprocess.run(
        command,
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    combined = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    lines = [line for line in combined.splitlines() if line.strip()]
    detail = lines[-1] if lines else "no output"
    return _gate(
        "PASS" if proc.returncode == 0 else "FAIL",
        detail,
        returncode=proc.returncode,
        duration_seconds=round(time.monotonic() - started, 3),
        command=command,
        output_tail=lines[-20:],
    )


def _run_docs_gate(root: Path) -> dict[str, Any]:
    from scripts.audit_docs import audit_docs

    result = audit_docs(root)
    return _gate(
        "PASS" if result["errors"] == 0 else "FAIL",
        f"documentation errors={result['errors']} warnings={len(result['warnings'])}",
        errors=result["errors"],
        warnings=len(result["warnings"]),
        issues=result["issues"],
    )


def _run_export_gates(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    from scripts.audit_public_release import audit_tree
    from scripts.export_public import export_tree

    manifest = root / "public-export-manifest.json"
    review_manifest = root / "release" / "public-review-manifest.json"
    with tempfile.TemporaryDirectory(prefix="leyu-workflow-release-gate-") as temp_dir:
        destination = Path(temp_dir) / "artifact"
        result = export_tree(
            root,
            destination,
            manifest,
            review_manifest=review_manifest,
            run_audit=True,
        )
        export_ok = result.get("published") is True and not result.get("errors")
        export_gate = _gate(
            "PASS" if export_ok else "FAIL",
            f"exported_files={len(result.get('copied', []))} errors={len(result.get('errors', []))}",
            exported_files=len(result.get("copied", [])),
            errors=result.get("errors", []),
            manual_review=result.get("manual_review", []),
        )
        if not destination.is_dir():
            audit_result = {"errors": 1, "issues": [{"code": "EXPORT_NOT_CREATED", "file": str(destination)}]}
        else:
            provenance = destination / "workflow-provenance-manifest.json"
            audit_result = audit_tree(
                destination,
                audit_kind="artifact",
                provenance_manifest=provenance,
                require_provenance=True,
            )
        audit_ok = audit_result["errors"] == 0
        artifact_gate = _gate(
            "PASS" if audit_ok else "FAIL",
            f"artifact errors={audit_result['errors']}",
            errors=audit_result["errors"],
            issues=audit_result["issues"],
        )
        provenance_issues = [
            item for item in audit_result.get("issues", []) if item["code"].startswith("PROVENANCE_")
        ]
        provenance_gate = _gate(
            "PASS" if not provenance_issues and export_ok else "FAIL",
            f"provenance issues={len(provenance_issues)}",
            issues=provenance_issues,
        )
        privacy_issues = [
            item for item in audit_result.get("issues", [])
            if item["code"] in {"PRIVATE_PATH", "SECRET_PATTERN", "PRIVATE_ARTIFACT"}
        ]
        privacy_gate = _gate(
            "PASS" if not privacy_issues and export_ok else "FAIL",
            f"private-path/secret issues={len(privacy_issues)}",
            issues=privacy_issues,
        )
    return export_gate, artifact_gate, {"provenance": provenance_gate, "privacy": privacy_gate}


def run_release_gate(
    root: Path = ROOT,
    *,
    require_external: bool = False,
) -> dict[str, Any]:
    root = Path(root).resolve()
    contract = evaluate_manifest_contract(root)
    gates: dict[str, dict[str, Any]] = {}
    if contract["errors"]:
        gates["manifest_contract"] = _gate("FAIL", "; ".join(contract["errors"]), errors=contract["errors"])
        return {
            "schema_version": 1,
            "status": "FAIL",
            "release_candidate": True,
            "gates": gates,
            "external_gates": {},
            "errors": contract["errors"],
        }
    gates["manifest_contract"] = _gate("PASS", "workflow manifest contract is internally consistent")
    gates["full_pytest"] = _run_command("full_pytest", [sys.executable, "-m", "pytest", "-q"], root)
    gates["audit_docs_links"] = _run_docs_gate(root)
    gates["compileall"] = _run_command(
        "compileall", [sys.executable, "-m", "compileall", "-q", "scripts", "tests"], root
    )
    gates["pipeline_static_audit"] = _run_command(
        "pipeline_static_audit",
        [sys.executable, "scripts/audit_skill_pipeline.py", "--skill-root", str(root)],
        root,
    )
    export_gate, artifact_gate, export_details = _run_export_gates(root)
    gates["export_tree_rebuild_check"] = export_gate
    gates["audit_public_release"] = artifact_gate
    gates["workflow_provenance_resolved"] = export_details["provenance"]
    gates["private_path_and_secret_scan"] = export_details["privacy"]
    gates["nested_public_core_reference_integrity"] = _run_command(
        "nested_public_core_reference_integrity",
        [
            sys.executable,
            "scripts/audit_public_core_integrity.py",
            "--skill-root",
            str(root),
            "--format",
            "json",
        ],
        root,
    )
    external = {"exact_head_github_actions": verify_external_head(root)}
    required_failures = [
        name for name in contract["required_release_gates"]
        if name not in contract["external_release_gates"]
        and gates.get(name, {}).get("status") != "PASS"
    ]
    external_failures = [
        name for name in contract["external_release_gates"]
        if external.get(name, {}).get("status") != "PASS"
    ]
    errors = [f"required gate failed: {name}" for name in required_failures]
    if require_external:
        errors.extend(f"external gate not verified: {name}" for name in external_failures)
    if errors:
        status = "FAIL"
    elif external_failures:
        status = "PASS_WITH_EXTERNAL_PENDING"
    else:
        status = "PASS"
    return {
        "schema_version": 1,
        "status": status,
        "release_candidate": True,
        "require_external": require_external,
        "gates": gates,
        "external_gates": external,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Leyu workflow release-candidate gates")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--release-candidate", action="store_true", help="run all release-candidate gates")
    parser.add_argument("--require-external", action="store_true", help="require exact-head GitHub Actions identity")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    result = run_release_gate(args.root, require_external=args.require_external)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Workflow release gate: {result['status']}")
        for name, gate in result["gates"].items():
            print(f"{name:42} {gate['status']:24} {gate['detail']}")
        for name, gate in result["external_gates"].items():
            print(f"{name:42} {gate['status']:24} {gate['detail']}")
        for error in result["errors"]:
            print(f"ERROR: {error}")
    return 0 if result["status"] in {"PASS", "PASS_WITH_EXTERNAL_PENDING"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
