#!/usr/bin/env python3
"""Audit the schema and runtime semantics of runtime-state-contract.json."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REQUIRED_STATE_FIELDS = {
    "revision",
    "current_stage",
    "facts_in_force",
    "knowledge_boundaries",
    "unresolved_threads",
    "event_status",
    "transition_flags",
    "last_major_event",
    "last_update_source",
}
REQUIRED_EVENT_STATUS = {
    "available",
    "active",
    "executed",
    "rejected",
    "skipped",
    "invalidated",
}


@dataclass
class AuditResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def audit_contract(contract: Any, runtime_meta: dict[str, Any] | None = None) -> AuditResult:
    result = AuditResult()
    if not isinstance(contract, dict):
        result.errors.append("runtime state contract根节点必须是对象")
        return result
    if contract.get("schema_version") != 1:
        result.errors.append("runtime state contract.schema_version必须为1")

    shape = contract.get("state_shape")
    shape_fields: set[str] = set()
    if not isinstance(shape, dict):
        result.errors.append("runtime state contract.state_shape必须是对象")
    else:
        shape_fields = set(shape)
        for field_name in sorted(REQUIRED_STATE_FIELDS - set(shape)):
            result.errors.append(f"state_shape缺少{field_name}")

    statuses = contract.get("allowed_event_status")
    if not isinstance(statuses, list):
        result.errors.append("allowed_event_status必须是数组")
    else:
        if any(not isinstance(status, str) or not status.strip() for status in statuses):
            result.errors.append("allowed_event_status的每个元素必须是非空字符串")
        if all(isinstance(status, str) for status in statuses) and len(statuses) != len(set(statuses)):
            result.errors.append("allowed_event_status不能包含重复值")
        status_names = {status for status in statuses if isinstance(status, str)}
        missing = REQUIRED_EVENT_STATUS - status_names
        for status in sorted(missing):
            result.errors.append(f"allowed_event_status缺少{status}")

    writers = contract.get("writers")
    declared_writers: set[str] = set()
    if not isinstance(writers, list) or not writers:
        result.errors.append("runtime state contract必须声明非空writers")
    else:
        for index, writer in enumerate(writers):
            if not isinstance(writer, dict):
                result.errors.append(f"writers[{index}]必须是对象")
                continue
            writer_name = writer.get("writer")
            if writer_name not in {"manual", "model", "script"}:
                result.errors.append(f"writers[{index}].writer必须是manual/model/script")
            else:
                declared_writers.add(writer_name)
            trigger = writer.get("trigger")
            if not isinstance(trigger, str) or not trigger.strip():
                result.errors.append(f"writers[{index}].trigger必须是非空字符串")
            fields = writer.get("fields")
            if not isinstance(fields, list) or not fields:
                result.errors.append(f"writers[{index}].fields必须是非空数组")
            else:
                if any(not isinstance(field, str) or not field.strip() for field in fields):
                    result.errors.append(f"writers[{index}].fields必须全部是非空字符串")
                for field in fields:
                    if field not in shape_fields:
                        result.errors.append(f"writers[{index}].fields引用不存在的state_shape字段: {field}")
                if all(isinstance(field, str) for field in fields) and len(fields) != len(set(fields)):
                    result.errors.append(f"writers[{index}].fields不能包含重复字段")

    for field_name in ("conflict_policy", "recovery_policy"):
        if not isinstance(contract.get(field_name), str) or not contract[field_name].strip():
            result.errors.append(f"runtime state contract缺少{field_name}")

    if runtime_meta:
        authority = runtime_meta.get("authority")
        update_mode = runtime_meta.get("update_mode")
        reliability = runtime_meta.get("reliability")
        if update_mode not in {"manual", "model", "script"}:
            result.errors.append("runtime_state.update_mode必须是manual/model/script")
        elif declared_writers and update_mode not in declared_writers:
            result.errors.append("runtime state writer与update_mode不一致")
        if authority == "prompt_record" and reliability == "authoritative":
            result.errors.append("prompt_record不能声明authoritative运行可靠性")
        if authority == "external_extension":
            if runtime_meta.get("update_mode") != "script":
                result.errors.append("external_extension状态必须由script写入")
            if runtime_meta.get("recovery_policy") != "external_checkpoint":
                result.errors.append("external_extension状态必须从external_checkpoint恢复")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--runtime-state", type=Path, help="Manifest runtime_state metadata JSON")
    args = parser.parse_args(argv)
    try:
        raw = json.loads(args.contract.read_text(encoding="utf-8"))
        meta = json.loads(args.runtime_state.read_text(encoding="utf-8")) if args.runtime_state else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    result = audit_contract(raw, meta)
    for error in result.errors:
        print(f"ERROR: {error}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
