#!/usr/bin/env python3
"""Audit candidate-event semantics in a narrative contract."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lib.narrative_contracts import load_json, validate_contract_bundle


REQUIRED_EVENT_FIELDS = (
    "prerequisites",
    "entry_points",
    "npc_initiative",
    "player_interruptible",
    "auto_fact",
    "possible_outcomes",
    "invalidated_by",
    "state_writes",
    "source_evidence",
)
OPEN_SEED_FORBIDDEN_FIELDS = frozenset({
    "next",
    "ordered_steps",
    "requires_all_events",
    "fixed_outcome",
    "route_lock",
    "stage_transition",
    "mandatory",
    "completion_required",
})


@dataclass
class AuditResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def _non_empty_string_list(value: Any) -> bool:
    return _string_list(value) and bool(value)


def _check_fact_refs(result: AuditResult, owner: str, values: Any, facts: dict[str, Any], label: str) -> None:
    if not _string_list(values):
        result.errors.append(f"{owner}.{label}必须是字符串数组")
        return
    for fact_id in values:
        if fact_id not in facts:
            result.errors.append(f"{owner}引用未声明事实: {fact_id}")


def _check_open_forbidden_fields(result: AuditResult, owner: str, value: dict[str, Any]) -> None:
    for field_name in OPEN_SEED_FORBIDDEN_FIELDS:
        if field_name in value:
            result.errors.append(f"{owner}开放种子禁止声明固定链字段: {field_name}")


def _audit_open_situation_event(
    result: AuditResult,
    event_id: str,
    event: dict[str, Any],
    facts: dict[str, Any],
) -> None:
    """Validate an open prompt seed without turning it into a scripted event."""
    owner = f"events.{event_id}"
    _check_open_forbidden_fields(result, owner, event)
    if "prerequisites" in event:
        if not _string_list(event["prerequisites"]):
            result.errors.append(f"{owner}.prerequisites必须是字符串数组")
        else:
            _check_fact_refs(result, owner, event["prerequisites"], facts, "prerequisites")
    for field_name in ("entry_points", "npc_initiative", "source_evidence", "open_directions", "not_fixed"):
        if not _non_empty_string_list(event.get(field_name)):
            result.errors.append(f"{owner}{field_name}必须是非空字符串数组")
    if event.get("player_interruptible") is not True:
        result.errors.append(f"{owner}必须允许玩家中断（player_interruptible=true）")
    if event.get("auto_fact") is not False:
        result.errors.append(f"{owner}必须声明auto_fact=false，开放种子不可自动事实化")
    if "state_writes" in event and event.get("state_writes") not in ([], None):
        result.errors.append(f"{owner}state_writes必须省略或为空数组，开放种子不能预先写入状态")
    if "possible_outcomes" in event and event.get("possible_outcomes") not in ([], None):
        result.errors.append(f"{owner}不能声明固定possible_outcomes，应使用open_directions")
    if "invalidated_by" in event:
        if not _string_list(event["invalidated_by"]):
            result.errors.append(f"{owner}.invalidated_by必须是字符串数组")
        else:
            _check_fact_refs(result, owner, event["invalidated_by"], facts, "invalidated_by")


def audit_contract(contract: Any, runtime_state_contract: dict[str, Any] | None = None) -> AuditResult:
    result = AuditResult()
    if not isinstance(contract, dict):
        result.errors.append("narrative contract根节点必须是对象")
        return result
    if contract.get("schema_version") != 1:
        result.errors.append("narrative contract.schema_version必须为1")
    mode = contract.get("narrative_mode")
    if mode not in {"soft_stage", "open_sandbox"}:
        result.errors.append(f"CONTRACT_MODE_MISMATCH: candidate-event审计不适用{mode!r}")
    event_mode = contract.get("event_mode", "guided_candidate")
    if event_mode not in {"guided_candidate", "open_situation_seed"}:
        result.errors.append(f"INVALID_EVENT_MODE: candidate-event审计不支持{event_mode!r}")
    if event_mode == "open_situation_seed" and mode != "open_sandbox":
        result.errors.append("EVENT_MODE_NARRATIVE_MISMATCH: open_situation_seed必须使用open_sandbox")
    if contract.get("event_policy") != "candidate_pool":
        result.errors.append("候选事件审计要求event_policy=candidate_pool")
    if mode == "open_sandbox" and contract.get("transition_policy") != "none":
        result.errors.append("open_sandbox candidate_pool必须使用transition_policy=none")

    stages_value = contract.get("stages")
    if mode == "soft_stage":
        if not isinstance(stages_value, dict) or not stages_value:
            result.errors.append("soft_stage candidate_pool必须声明非空stages")
            stages = {}
        else:
            stages = stages_value
    elif mode == "open_sandbox":
        if stages_value is None:
            stages = {}
        elif not isinstance(stages_value, dict):
            result.errors.append("open_sandbox stages若声明必须是对象")
            stages = {}
        else:
            stages = stages_value
    else:
        stages = stages_value if isinstance(stages_value, dict) else {}

    events = contract.get("events")
    if not isinstance(events, dict) or not events:
        result.errors.append("candidate_pool必须声明非空events")
        stages = {}
        events = {}
    facts = contract.get("facts", {})
    if not isinstance(facts, dict):
        result.errors.append("facts必须是对象")
        facts = {}
    referenced: set[str] = set()
    if mode == "soft_stage":
        for stage_id, stage in stages.items():
            if not isinstance(stage, dict):
                result.errors.append(f"stages.{stage_id}必须是对象")
                continue
            for field_name in (
                "facts_in_force",
                "knowledge_boundaries",
                "unresolved_threads",
                "candidate_events",
                "transition_conditions",
                "forbidden_future_facts",
            ):
                if field_name not in stage:
                    result.errors.append(f"stages.{stage_id}缺少{field_name}")
            for field_name in ("facts_in_force", "unresolved_threads", "candidate_events", "transition_conditions", "forbidden_future_facts"):
                if field_name in stage and not _string_list(stage[field_name]):
                    result.errors.append(f"stages.{stage_id}.{field_name}必须是字符串数组")
            boundaries = stage.get("knowledge_boundaries")
            if not isinstance(boundaries, dict):
                result.errors.append(f"stages.{stage_id}.knowledge_boundaries必须是对象")
            else:
                for actor, visible_facts in boundaries.items():
                    if not isinstance(actor, str) or not actor.strip():
                        result.errors.append(f"stages.{stage_id}.knowledge_boundaries角色名必须是非空字符串")
                    _check_fact_refs(result, f"stages.{stage_id}.knowledge_boundaries[{actor}]", visible_facts, facts, "facts")
            _check_fact_refs(result, f"stages.{stage_id}", stage.get("facts_in_force"), facts, "facts_in_force")
            _check_fact_refs(result, f"stages.{stage_id}", stage.get("forbidden_future_facts"), facts, "forbidden_future_facts")
            candidate_ids = stage.get("candidate_events")
            if isinstance(candidate_ids, list):
                referenced.update(item for item in candidate_ids if isinstance(item, str))
    elif mode == "open_sandbox":
        _check_open_forbidden_fields(result, "contract", contract)
        for stage_id, stage in stages.items():
            if not isinstance(stage, dict):
                result.errors.append(f"open_sandbox stages.{stage_id}必须是对象")
                continue
            _check_open_forbidden_fields(result, f"stages.{stage_id}", stage)
            if "transition_conditions" in stage and stage["transition_conditions"] != []:
                result.errors.append(f"open_sandbox stages.{stage_id}.transition_conditions必须为空")

    for event_id, event in events.items():
        if not isinstance(event, dict):
            result.errors.append(f"events.{event_id}必须是对象")
            continue
        if event_mode != "open_situation_seed":
            for field_name in REQUIRED_EVENT_FIELDS:
                if field_name not in event:
                    result.errors.append(f"events.{event_id}缺少{field_name}")
        if not isinstance(event_id, str) or not event_id.strip():
            result.errors.append("events的ID必须是非空字符串")
        stage_id = event.get("stage")
        if mode == "soft_stage":
            if "stage" not in event:
                result.errors.append(f"events.{event_id}缺少stage")
            elif stage_id not in stages:
                result.errors.append(f"events.{event_id}.stage未声明: {stage_id}")
            else:
                candidate_ids = stages[stage_id].get("candidate_events")
                if not _string_list(candidate_ids) or event_id not in candidate_ids:
                    result.errors.append(f"events.{event_id}未被其阶段candidate_events引用")
        elif mode == "open_sandbox" and stage_id is not None:
            if not isinstance(stage_id, str) or not stage_id.strip():
                result.errors.append(f"events.{event_id}.stage若声明必须是非空字符串")
            elif stages and stage_id not in stages:
                result.errors.append(f"events.{event_id}.stage未声明: {stage_id}")
        if event_mode == "open_situation_seed":
            _audit_open_situation_event(result, event_id, event, facts)
            continue
        if not _string_list(event.get("prerequisites")):
            result.errors.append(f"events.{event_id}.prerequisites必须是字符串数组")
        if not _non_empty_string_list(event.get("entry_points")):
            result.errors.append(f"events.{event_id}.entry_points必须是非空字符串数组")
        if not _non_empty_string_list(event.get("npc_initiative")):
            result.errors.append(f"events.{event_id}.npc_initiative必须是非空字符串数组")
        if event.get("player_interruptible") is not True:
            result.errors.append(f"events.{event_id}必须允许玩家中断（player_interruptible=true）")
        if event.get("auto_fact") is not False:
            result.errors.append(f"events.{event_id}必须声明auto_fact=false，候选事件不可自动事实化")
        outcomes = event.get("possible_outcomes")
        if not _string_list(outcomes) or len(outcomes) < 2:
            result.errors.append(f"events.{event_id}possible_outcomes至少两个结果")
        elif len(outcomes) != len(set(outcomes)):
            result.errors.append(f"events.{event_id}possible_outcomes不能重复")
        if not _string_list(event.get("invalidated_by")):
            result.errors.append(f"events.{event_id}invalidated_by必须是字符串数组")
        if not _non_empty_string_list(event.get("state_writes")):
            result.errors.append(f"events.{event_id}state_writes必须是非空字符串数组")
        elif runtime_state_contract is not None:
            shape = runtime_state_contract.get("state_shape")
            if isinstance(shape, dict):
                for field_name in event["state_writes"]:
                    if field_name not in shape:
                        result.errors.append(f"events.{event_id}.state_writes引用不存在的state_shape字段: {field_name}")
        if not _non_empty_string_list(event.get("source_evidence")):
            result.errors.append(f"events.{event_id}source_evidence必须是非空数组")
        _check_fact_refs(result, f"events.{event_id}", event.get("prerequisites"), facts, "prerequisites")
        _check_fact_refs(result, f"events.{event_id}", event.get("invalidated_by"), facts, "invalidated_by")

    for event_id in sorted(referenced - set(events)):
        result.errors.append(f"stage candidate_events引用未定义事件: {event_id}")

    transitions = contract.get("transitions", {})
    if mode == "open_sandbox":
        if "transitions" in contract and transitions != {}:
            result.errors.append("open_sandbox transition_policy=none不能声明transitions")
        return result
    if not isinstance(transitions, dict):
        result.errors.append("transitions必须是对象")
        transitions = {}
    for stage_id, stage in stages.items():
        for transition_id in stage.get("transition_conditions", []) if isinstance(stage.get("transition_conditions"), list) else []:
            if transition_id not in transitions:
                result.errors.append(f"stages.{stage_id}.transition_conditions引用未定义转移: {transition_id}")
    for transition_id, transition in transitions.items():
        if not isinstance(transition, dict):
            result.errors.append(f"transitions.{transition_id}必须是对象")
            continue
        for field_name in ("requires", "requires_any", "blocked_by"):
            _check_fact_refs(result, f"transitions.{transition_id}", transition.get(field_name), facts, field_name)
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
    result = AuditResult()
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
            result = audit_contract(raw, state_contract)
            bundle = validate_contract_bundle(manifest, raw, state_contract, args.manifest.parent)
            result.errors[0:0] = [f"{issue.code}: {issue.message}" for issue in bundle.errors]
        except (OSError, UnicodeError, ValueError) as exc:
            result.errors.insert(0, f"CONTRACT_BUNDLE_LOAD_ERROR: {exc}")
    else:
        result = audit_contract(raw)
    for error in result.errors:
        print(f"ERROR: {error}")
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
