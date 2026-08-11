#!/usr/bin/env python3
"""Audit outcome-based transitions for soft-stage narrative contracts."""
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
        result.errors.append("narrative contract根节点必须是对象")
        return result
    if contract.get("narrative_mode") != "soft_stage":
        result.errors.append(f"CONTRACT_MODE_MISMATCH: transition-policy审计不适用{contract.get('narrative_mode')!r}")
        return result
    if contract.get("transition_policy") != "outcome_based":
        result.errors.append("soft_stage必须使用outcome_based transition_policy")
    stages = contract.get("stages", {})
    events = contract.get("events", {})
    transitions = contract.get("transitions", {})
    if not isinstance(stages, dict) or not isinstance(events, dict):
        result.errors.append("soft_stage必须声明对象类型的stages和events")
        return result
    if not isinstance(transitions, dict) or not transitions:
        result.errors.append("soft_stage必须声明非空transitions")
        transitions = {}

    stage_ids = set(stages)
    transition_ids = set(transitions)
    for stage_id, stage in stages.items():
        if not isinstance(stage, dict):
            continue
        conditions = stage.get("transition_conditions", [])
        if isinstance(conditions, list):
            for condition_id in conditions:
                if condition_id not in transition_ids:
                    result.errors.append(f"阶段{stage_id}引用未定义转移条件: {condition_id}")

    for stage_id, stage in stages.items():
        if not isinstance(stage, dict):
            continue
        event_ids = stage.get("candidate_events", [])
        if not event_ids:
            if stage.get("terminal") is True and not stage.get("transition_conditions"):
                continue
            result.errors.append(f"阶段{stage_id}没有candidate_events，无法形成可绕行候选池")
            continue
        for event_id in event_ids:
            event = events.get(event_id)
            if not isinstance(event, dict):
                continue
            outcomes = event.get("possible_outcomes", [])
            if event.get("player_interruptible") is not True or len(outcomes) < 2:
                result.errors.append(
                    f"阶段{stage_id}候选事件{event_id}缺少可绕行语义：必须可中断且至少有两个结果"
                )
        conditions = stage.get("transition_conditions")
        if not isinstance(conditions, list) or not conditions:
            result.errors.append(f"阶段{stage_id}必须使用结果条件，而不是固定事件完成条件")

    for condition_id, condition in transitions.items():
        if not isinstance(condition, dict):
            result.errors.append(f"transitions.{condition_id}必须是对象")
            continue
        if not condition.get("from") or not condition.get("to"):
            result.errors.append(f"transitions.{condition_id}必须声明from/to")
        else:
            if condition["from"] not in stage_ids:
                result.errors.append(f"transitions.{condition_id}.from未声明阶段: {condition['from']}")
            if condition["to"] not in stage_ids:
                result.errors.append(f"transitions.{condition_id}.to未声明阶段: {condition['to']}")
        if not condition.get("requires") and not condition.get("requires_any"):
            result.errors.append(f"transitions.{condition_id}必须声明事实结果条件")
        if condition.get("irreversible") is not True:
            result.errors.append(f"transitions.{condition_id}必须声明irreversible=true")
        if condition.get("requires_all_events") is True:
            result.errors.append(f"transitions.{condition_id}不能要求所有候选事件完成")
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
