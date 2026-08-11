from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


Issue = dict[str, str]


ARCHITECTURE_ROUTING = {
    "flat": {"flat"},
    "native_stage": {"native_greeting_title", "simple_stage_route"},
    "mvu": {"native_greeting_title", "simple_stage_route"},
}

NARRATIVE_COMPATIBILITY = {
    "open_sandbox": {"open_sandbox"},
    "stage_progression": {"linear_stage", "soft_stage"},
    "source_default": {"source_default", "legacy_unspecified"},
}

STAGE_ROUTES = {"native_greeting_title", "simple_stage_route"}
ARCHITECTURE_DRIVERS = {
    "flat": {"native_st", "external_extension"},
    "native_stage": {"native_st", "external_extension"},
    "mvu": {"external_extension"},
}
CAPABILITY_DRIVERS = {
    "natural_trigger": {"native_st", "external_extension"},
    "open_sandbox": {"native_st", "external_extension"},
    "native_stage": {"native_st", "external_extension"},
    "mvu": {"external_extension"},
    "persistent_state": {"external_extension"},
}
STATE_AUTHORITY_COMPATIBILITY = {
    "narrative_only": {"none", "prompt_record", "external_extension"},
    "greeting_snapshot": {"prompt_record", "external_extension"},
    "stat_data": {"external_extension"},
}


def _issue(level: str, code: str, message: str) -> Issue:
    return {"level": level, "code": code, "comment": "", "message": message}


def _normalise_sources(value: Any, base: Path | None) -> set[str] | None:
    if not isinstance(value, list):
        return None
    result: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return None
        raw = item.strip().replace("\\", "/")
        path = Path(raw)
        if base is not None and not path.is_absolute():
            raw = str((base / path).resolve(strict=False)).replace("\\", "/")
        result.add(raw.lower())
    return result


def audit_manifest_alignment(
    delivery_manifest: dict[str, Any],
    semantic_manifest: dict[str, Any],
    *,
    delivery_base: Path | None = None,
    semantic_base: Path | None = None,
) -> list[Issue]:
    """Check cross-file contracts that neither manifest can validate alone."""
    if semantic_manifest.get("semantic_profile") != "modular_semantic_v1":
        return []

    issues: list[Issue] = []
    routing = delivery_manifest.get("routing_mode")
    architecture = semantic_manifest.get("architecture_mode")
    if routing is not None and architecture in ARCHITECTURE_ROUTING:
        if routing not in ARCHITECTURE_ROUTING[architecture]:
            issues.append(_issue(
                "ERROR",
                "ARCHITECTURE_ROUTE_MISMATCH",
                f"semantic architecture_mode={architecture} 与 build routing_mode={routing} 不兼容。",
            ))

    runtime_driver = delivery_manifest.get("runtime_driver")
    if not isinstance(runtime_driver, str) or not runtime_driver.strip():
        issues.append(_issue(
            "ERROR",
            "RUNTIME_DRIVER_MISSING",
            "声明 semantic_manifest 时，build manifest 必须声明 runtime_driver。",
        ))
    elif architecture in ARCHITECTURE_DRIVERS and runtime_driver not in ARCHITECTURE_DRIVERS[architecture]:
        issues.append(_issue(
            "ERROR",
            "RUNTIME_DRIVER_MISMATCH",
            f"semantic architecture_mode={architecture} 不支持 build runtime_driver={runtime_driver}。",
        ))

    capabilities = semantic_manifest.get("runtime_capabilities")
    if isinstance(capabilities, list):
        for capability in capabilities:
            if capability not in CAPABILITY_DRIVERS:
                issues.append(_issue(
                    "ERROR",
                    "UNKNOWN_RUNTIME_CAPABILITY",
                    f"semantic runtime_capabilities 包含未注册能力：{capability}。",
                ))
            elif isinstance(runtime_driver, str) and runtime_driver not in CAPABILITY_DRIVERS[capability]:
                issues.append(_issue(
                    "ERROR",
                    "RUNTIME_CAPABILITY_MISMATCH",
                    f"semantic runtime capability={capability} 与 build runtime_driver={runtime_driver} 不兼容。",
                ))

    semantic_narrative = semantic_manifest.get("narrative_mode")
    delivery_narrative = delivery_manifest.get("narrative_mode")
    if (
        semantic_narrative in NARRATIVE_COMPATIBILITY
        and delivery_narrative is not None
        and delivery_narrative not in NARRATIVE_COMPATIBILITY[semantic_narrative]
    ):
        issues.append(_issue(
            "ERROR",
            "NARRATIVE_MODE_MISMATCH",
            f"semantic narrative_mode={semantic_narrative} 与 build narrative_mode={delivery_narrative} 不兼容。",
        ))

    authoritative_route = semantic_manifest.get("authoritative_route")
    if authoritative_route in {"greeting_title", "runtime.stage"} and routing is not None:
        if routing not in STAGE_ROUTES:
            issues.append(_issue(
                "ERROR",
                "AUTHORITATIVE_ROUTE_MISMATCH",
                f"semantic authoritative_route={authoritative_route} 要求阶段路由，但 build routing_mode={routing}。",
            ))

    runtime_state = delivery_manifest.get("runtime_state")
    runtime_authority = runtime_state.get("authority") if isinstance(runtime_state, dict) else None
    authoritative_state = semantic_manifest.get("authoritative_state")
    allowed_authorities = STATE_AUTHORITY_COMPATIBILITY.get(authoritative_state)
    if allowed_authorities is not None and runtime_authority not in allowed_authorities:
        issues.append(_issue(
            "ERROR",
            "AUTHORITATIVE_STATE_MISMATCH",
            f"semantic authoritative_state={authoritative_state} 不接受 build runtime_state.authority={runtime_authority}。",
        ))

    source_base = delivery_base or semantic_base
    semantic_sources = _normalise_sources(
        (semantic_manifest.get("source_scope") or {}).get("canonical_sources")
        if isinstance(semantic_manifest.get("source_scope"), dict)
        else None,
        source_base,
    )
    delivery_sources = _normalise_sources(delivery_manifest.get("canonical_sources"), source_base)
    if semantic_sources is not None and delivery_sources is not None and semantic_sources != delivery_sources:
        issues.append(_issue(
            "ERROR",
            "SOURCE_SCOPE_MISMATCH",
            "semantic source_scope.canonical_sources 与 build canonical_sources 不一致。",
        ))

    return issues


def _load_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ValueError(f"manifest root must be an object: {path}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit build/semantic manifest alignment")
    parser.add_argument("--build-manifest", required=True, type=Path)
    parser.add_argument("--semantic-manifest", required=True, type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    try:
        delivery = _load_object(args.build_manifest)
        semantic = _load_object(args.semantic_manifest)
        issues = audit_manifest_alignment(
            delivery,
            semantic,
            delivery_base=args.build_manifest.parent,
            semantic_base=args.semantic_manifest.parent,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR INPUT: {exc}", file=sys.stderr)
        return 3

    if args.as_json:
        print(json.dumps(issues, ensure_ascii=False, indent=2))
    else:
        for item in issues:
            print(f"{item['level']} {item['code']}: {item['message']}")
    if any(item["level"] == "ERROR" for item in issues):
        return 1
    if any(item["level"] in {"WARNING", "WARN"} for item in issues):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
