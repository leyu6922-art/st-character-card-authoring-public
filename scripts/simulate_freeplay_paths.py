#!/usr/bin/env python3
"""Deterministically exercise candidate-event status and outcome transitions."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any


EVENT_STATUSES = {"available", "active", "executed", "rejected", "skipped", "invalidated"}
TERMINAL_EVENT_STATUSES = {"executed", "rejected", "skipped", "invalidated"}
ALLOWED_STATUS_TRANSITIONS = {
    "available": EVENT_STATUSES - {"available"},
    "active": TERMINAL_EVENT_STATUSES,
    "executed": set(),
    "rejected": set(),
    "skipped": set(),
    "invalidated": set(),
}


def _initial_state(contract: dict[str, Any], current_stage: str | None = None) -> dict[str, Any]:
    stages = contract.get("stages", {})
    current_stage = current_stage or next(iter(stages), None)
    stage = stages.get(current_stage, {}) if current_stage else {}
    event_ids = list(contract.get("events", {}))
    current_event_ids = stage.get("candidate_events", []) if isinstance(stage, dict) else []
    event_status = {event_id: "available" for event_id in current_event_ids if event_id in contract.get("events", {})}
    event_eligibility = {
        event_id: "available" if contract.get("events", {}).get(event_id, {}).get("stage") == current_stage else "locked"
        for event_id in event_ids
    }
    return {
        "revision": 0,
        "current_stage": current_stage,
        "facts_in_force": list(stage.get("facts_in_force", [])) if isinstance(stage, dict) else [],
        "knowledge_boundaries": dict(stage.get("knowledge_boundaries", {})) if isinstance(stage, dict) else {},
        "unresolved_threads": list(stage.get("unresolved_threads", [])) if isinstance(stage, dict) else [],
        "event_status": event_status,
        "event_eligibility": event_eligibility,
        "transition_flags": [],
        "last_major_event": "",
        "last_update_source": "simulator",
    }


def _copy(contract: dict[str, Any], current_stage: str | None = None) -> dict[str, Any]:
    return deepcopy(_initial_state(contract, current_stage))


def initial_state(contract: dict[str, Any]) -> dict[str, Any]:
    """Return a fresh deterministic state for contract-level tests and tooling."""
    return _copy(contract)


def apply_event_status(state: dict[str, Any], event_id: str, status: str) -> None:
    """Apply one contract-allowed event transition."""
    _set_status(state, event_id, status)


def _set_status(state: dict[str, Any], event_id: str, status: str) -> None:
    if status not in EVENT_STATUSES:
        raise ValueError(f"unsupported event status: {status}")
    if event_id not in state["event_status"]:
        raise ValueError(f"unknown event: {event_id}")
    current = state["event_status"][event_id]
    if status not in ALLOWED_STATUS_TRANSITIONS.get(current, set()):
        if current in TERMINAL_EVENT_STATUSES:
            raise ValueError(f"terminal event {event_id} cannot transition from {current} to {status}")
        raise ValueError(f"event {event_id} cannot transition from {current} to {status}")
    state["event_status"][event_id] = status
    state["revision"] += 1
    state["last_major_event"] = event_id


def _apply_transition(contract: dict[str, Any], state: dict[str, Any], fact: str) -> bool:
    if fact and fact not in state["facts_in_force"]:
        state["facts_in_force"].append(fact)
    for transition_id, condition in contract.get("transitions", {}).items():
        if not isinstance(condition, dict):
            continue
        if condition.get("from") != state.get("current_stage"):
            continue
        required = condition.get("requires", [])
        any_required = condition.get("requires_any", [])
        blocked_by = condition.get("blocked_by", [])
        if any(item in state["facts_in_force"] for item in blocked_by):
            continue
        if (required and all(item in state["facts_in_force"] for item in required)) or (
            any_required and any(item in state["facts_in_force"] for item in any_required)
        ):
            target = condition.get("to")
            if target not in contract.get("stages", {}) or target == state.get("current_stage"):
                continue
            state["current_stage"] = target
            target_stage = contract["stages"][target]
            state["facts_in_force"] = list(target_stage.get("facts_in_force", []))
            state["knowledge_boundaries"] = dict(target_stage.get("knowledge_boundaries", {}))
            state["unresolved_threads"] = list(target_stage.get("unresolved_threads", []))
            for event_id in target_stage.get("candidate_events", []):
                state["event_status"][event_id] = "available"
                state["event_eligibility"][event_id] = "available"
            state["transition_flags"].append(transition_id)
            return True
    return False


def simulate_paths(contract: dict[str, Any]) -> dict[str, Any]:
    """Exercise every candidate event and every declared transition deterministically."""
    checks: list[str] = []
    failures: list[dict[str, Any]] = []
    scenarios: list[dict[str, Any]] = []
    events = contract.get("events", {})
    stages = contract.get("stages", {})

    def record_scenario(
        stage: str,
        event: str,
        path: str,
        passed: bool,
        error: str = "",
    ) -> None:
        scenario = {
            "stage": stage,
            "event": event,
            "path": path,
            "passed": passed,
            "error": error,
        }
        scenarios.append(scenario)
        if not passed:
            failures.append(scenario)

    if not isinstance(events, dict) or not events:
        record_scenario("", "", "contract", False, "contract must contain at least one event")
        return {
            "passed": False,
            "ok": False,
            "checks": [],
            "failures": failures,
            "scenarios": scenarios,
            "event_paths": {},
            "transitions": {},
        }

    event_paths: dict[str, dict[str, dict[str, Any]]] = {}
    for event_id, event in events.items():
        if not isinstance(event, dict) or event.get("stage") not in stages:
            stage = event.get("stage", "") if isinstance(event, dict) else ""
            record_scenario(stage, event_id, "contract", False, "event has unknown stage")
            continue
        paths: dict[str, dict[str, Any]] = {}
        for name, status in (("executed", "executed"), ("skipped", "skipped"), ("rejected", "rejected"), ("invalidated", "invalidated")):
            state = _copy(contract, event["stage"])
            try:
                _set_status(state, event_id, status)
                paths[name] = state
                record_scenario(event["stage"], event_id, name, True)
            except ValueError as exc:
                record_scenario(event["stage"], event_id, name, False, str(exc))
        event_paths[event_id] = paths
        checks.append(f"event:{event_id}:executed/skipped/rejected/invalidated")

    first_event_id = next(iter(event_paths), None)
    states: dict[str, Any] = {}
    if first_event_id:
        first_paths = event_paths[first_event_id]
        states["normal"] = first_paths.get("executed", {})
        states["skip"] = first_paths.get("skipped", {})
        states["reject"] = first_paths.get("rejected", {})
        states["invalidate"] = first_paths.get("invalidated", {})

    transition_paths: dict[str, dict[str, Any]] = {}
    transitions = contract.get("transitions", {})
    if not isinstance(transitions, dict):
        record_scenario("", "", "transition_contract", False, "transitions must be an object")
        transitions = {}
    for transition_id, condition in transitions.items():
        if not isinstance(condition, dict):
            record_scenario("", transition_id, "transition_contract", False, "transition must be an object")
            continue
        source = condition.get("from")
        target = condition.get("to")
        if source not in stages or target not in stages or source == target:
            record_scenario(source or "", transition_id, "transition_contract", False, "transition has invalid from/to")
            continue
        transition = _copy(contract, source)
        required = condition.get("requires", [])
        any_required = condition.get("requires_any", [])
        for required_fact in required if isinstance(required, list) else []:
            if required_fact not in transition["facts_in_force"]:
                transition["facts_in_force"].append(required_fact)
        if not required and any_required:
            transition["facts_in_force"].append(any_required[0])
        blocked = condition.get("blocked_by", [])
        if isinstance(blocked, list) and any(item in transition["facts_in_force"] for item in blocked):
            transition_paths[transition_id] = {"blocked": True, "current_stage": transition["current_stage"]}
            checks.append(f"transition:{transition_id}:blocked")
            record_scenario(source, transition_id, "blocked", True)
            continue
        moved = _apply_transition(contract, transition, "")
        if not moved or transition["current_stage"] != target:
            record_scenario(source, transition_id, "transition", False, f"did not move from {source} to {target}")
        else:
            record_scenario(source, transition_id, "transition", True)
        transition_paths[transition_id] = transition
        checks.append(f"transition:{transition_id}:{source}->{target}")

    first_transition = next(iter(transition_paths.values()), {})
    if first_transition and "current_stage" in first_transition:
        states["transition"] = first_transition
    initial = _copy(contract)
    if any(state == "available" for event_id, state in initial["event_eligibility"].items() if events.get(event_id, {}).get("stage") != initial["current_stage"]):
        future_event = next(
            event_id
            for event_id, state in initial["event_eligibility"].items()
            if state == "available" and events.get(event_id, {}).get("stage") != initial["current_stage"]
        )
        record_scenario(initial["current_stage"], future_event, "availability", False, "future-stage events cannot be initially available")
    passed = not failures
    return {
        **states,
        "passed": passed,
        "ok": passed,
        "checks": checks,
        "failures": failures,
        "scenarios": scenarios,
        "event_paths": event_paths,
        "transitions": transition_paths,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)
    try:
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
        result = simulate_paths(contract)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
