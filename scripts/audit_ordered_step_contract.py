#!/usr/bin/env python3
"""Audit ordered steps for linear-stage narrative contracts."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lib.narrative_contracts import load_json, validate_contract_bundle


@dataclass
class AuditResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def audit_contract(contract: Any) -> AuditResult:
    result = AuditResult()
    if not isinstance(contract, dict):
        result.errors.append("linear narrative contract根节点必须是对象")
        return result
    if contract.get("narrative_mode") != "linear_stage":
        result.errors.append(f"CONTRACT_MODE_MISMATCH: ordered-step审计不适用{contract.get('narrative_mode')!r}")
        return result
    if contract.get("event_policy") != "ordered_steps" or contract.get("transition_policy") != "step_completion":
        result.errors.append("linear_stage必须使用ordered_steps + step_completion")
    steps = contract.get("steps")
    if not isinstance(steps, list) or not steps:
        result.errors.append("linear_stage必须声明非空steps数组")
        return result
    ids = [step.get("step_id") for step in steps if isinstance(step, dict)]
    if len(ids) != len(set(ids)):
        result.errors.append("linear_stage steps存在重复step_id")
    if any(not isinstance(step, dict) or not step.get("step_id") for step in steps):
        result.errors.append("linear_stage每个step必须声明step_id")
        return result
    known = set(ids)
    for step in steps:
        next_id = step.get("next")
        if next_id is not None and next_id not in known:
            result.errors.append(f"linear_stage step {step['step_id']} next未定义: {next_id}")

    if len(ids) == len(set(ids)):
        reachable: set[str] = set()
        current = ids[0]
        lookup = {step["step_id"]: step for step in steps}
        while current is not None and current in known and current not in reachable:
            reachable.add(current)
            current = lookup[current].get("next")
        if current is not None and current in reachable:
            result.errors.append(f"linear_stage steps存在循环: {current}")
        unreachable = known - reachable
        for step_id in sorted(unreachable):
            result.errors.append(f"linear_stage step不可达: {step_id}")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--manifest", type=Path, help="optional Manifest v2 for cross-file bundle validation")
    args = parser.parse_args(argv)
    try:
        raw = json.loads(args.contract.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    result = audit_contract(raw)
    if args.manifest:
        try:
            manifest = load_json(args.manifest)
            state_contract = None
            state_meta = manifest.get("runtime_state", {})
            if isinstance(state_meta, dict) and state_meta.get("contract"):
                state_path = Path(state_meta["contract"])
                if not state_path.is_absolute():
                    state_path = args.manifest.parent / state_path
                if state_path.is_file():
                    state_contract = load_json(state_path)
            bundle = validate_contract_bundle(manifest, raw, state_contract, args.manifest.parent)
            result.errors[0:0] = [f"{issue.code}: {issue.message}" for issue in bundle.errors]
        except (OSError, UnicodeError, ValueError) as exc:
            result.errors.insert(0, f"CONTRACT_BUNDLE_LOAD_ERROR: {exc}")
    for error in result.errors:
        print(f"ERROR: {error}")
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
