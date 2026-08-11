"""Diagnose installation health and available capability level."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _check(status: str, detail: str) -> dict:
    return {"status": status, "detail": detail}


def inspect_environment(root: Path, run_tests: bool = False, hermes_home: Path | None = None) -> dict:
    root = Path(root).resolve()
    checks: dict[str, dict] = {}
    checks["python"] = _check("PASS" if sys.version_info >= (3, 11) else "FAIL", f"{sys.version_info.major}.{sys.version_info.minor}")
    for name in ("SKILL.md", "README.md", "skill-manifest.json", "public-export-manifest.json"):
        checks[name] = _check("PASS" if (root / name).exists() else "FAIL", str(root / name))
    for name, directory in (("scripts", "scripts"), ("templates", "templates"), ("tests_dir", "tests")):
        checks[name] = _check("PASS" if (root / directory).is_dir() else "FAIL", str(root / directory))
    try:
        json.loads((root / "skill-manifest.json").read_text(encoding="utf-8"))
        json.loads((root / "public-export-manifest.json").read_text(encoding="utf-8"))
        checks["manifests"] = _check("PASS", "both JSON manifests parse")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        checks["manifests"] = _check("FAIL", str(exc))
    try:
        import pytest  # noqa: F401
        checks["pytest"] = _check("PASS", "importable")
    except ImportError:
        checks["pytest"] = _check("MISSING", "install pytest for test execution")
    hermes = hermes_home or (Path(os.environ["HERMES_HOME"]) if os.environ.get("HERMES_HOME") else None)
    checks["hermes"] = _check("PASS", str(hermes)) if hermes and hermes.exists() else _check("NOT_CONFIGURED", "pass --hermes-home or set HERMES_HOME")
    stage = root.parent / "standalone-card-stage-routing"
    preset = root.parent / "sillytavern-preset-debugging"
    checks["native_stage_routing"] = _check("PASS", str(stage)) if stage.exists() else _check("MISSING", "optional sibling not found")
    checks["preset_debugging"] = _check("PASS", str(preset)) if preset.exists() else _check("MISSING", "optional sibling not found")
    checks["sillytavern_runtime"] = _check("NOT_CONFIGURED", "runtime probe is not part of static doctor")
    if run_tests:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=root, text=True, capture_output=True)
        checks["tests"] = _check("PASS" if proc.returncode == 0 else "FAIL", proc.stdout.strip().splitlines()[-1] if proc.stdout else proc.stderr[-500:])
    else:
        checks["tests"] = _check("NOT_RUN", "use --run-tests")
    core_ids = ["python", "SKILL.md", "README.md", "skill-manifest.json", "public-export-manifest.json", "scripts", "templates", "tests_dir", "manifests", "pytest"]
    core_ok = all(checks[item]["status"] == "PASS" for item in core_ids)
    capability = "L1" if core_ok else "UNAVAILABLE"
    if core_ok and checks["hermes"]["status"] == "PASS":
        capability = "L2"
    if capability == "L2" and checks["native_stage_routing"]["status"] == "PASS":
        capability = "L3"
    return {"schema_version": 1, "status": "PASS" if core_ok else "FAIL", "capability_level": capability, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose Skill installation and capability level")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--hermes-home", type=Path)
    parser.add_argument("--run-tests", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    result = inspect_environment(args.root, args.run_tests, args.hermes_home)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Installation health: {result['status']}; capability level: {result['capability_level']}")
        for name, check in result["checks"].items():
            print(f"{name:24} {check['status']:16} {check['detail']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
