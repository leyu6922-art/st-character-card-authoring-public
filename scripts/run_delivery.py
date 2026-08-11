#!/usr/bin/env python3
"""Manifest-driven, single-entry delivery runner for production character cards.

This wrapper chooses final_delivery_gate.py flags from explicit project policy.
It never replaces the final gate and always prints RUN/SKIP decisions first.
Manifest v1 keeps the legacy path; Manifest v2 adds independent narrative,
runtime-driver, and runtime-state audits.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from audit_candidate_event_semantics import audit_contract as audit_candidate_events
from audit_manifest_alignment import audit_manifest_alignment
from audit_open_sandbox_entries import audit_card as audit_open_sandbox
from audit_ordered_step_contract import audit_contract as audit_ordered_steps
from audit_semantic_modules import audit as audit_semantic_modules
from audit_semantic_modules import load_manifest as load_semantic_manifest
from audit_semantic_modules import summarize_coverage as summarize_semantic_coverage
from audit_semantic_text import audit as audit_semantic_text
from audit_runtime_state_contract import audit_contract as audit_runtime_state
from audit_stage_transition_policy import audit_contract as audit_stage_transitions
from lib.narrative_contracts import (
    CAPABILITY_MISSING,
    DECLARED_UNVERIFIED,
    VERIFIED,
    load_json,
    load_validated_content_policy,
    validate_contract_bundle,
    validate_manifest,
)
from simulate_freeplay_paths import simulate_paths


GREETING_MODES = {"player_prose", "prose_plus_director_appendix", "ai_trigger"}
GREETING_APPENDIX_STANDARDS = {"none", "stage_brief_v1"}
ROUTING_MODES = {"flat", "native_greeting_title", "simple_stage_route"}


DELIVERY_MANIFEST_NOT_FOUND = "DELIVERY_MANIFEST_NOT_FOUND"
DELIVERY_MANIFEST_JSON_INVALID = "DELIVERY_MANIFEST_JSON_INVALID"
DELIVERY_MANIFEST_SCHEMA_INVALID = "DELIVERY_MANIFEST_SCHEMA_INVALID"
SEMANTIC_MANIFEST_NOT_FOUND = "SEMANTIC_MANIFEST_NOT_FOUND"
SEMANTIC_MANIFEST_JSON_INVALID = "SEMANTIC_MANIFEST_JSON_INVALID"


class DeliveryConfigError(ValueError):
    """A stable, machine-readable configuration/input failure."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class DeliveryCheck:
    name: str
    status: str
    reason: str


@dataclass(frozen=True)
class DeliveryPlan:
    card_path: Path
    manifest_path: Path
    project_dir: Path
    argv: list[str]
    checks: list[DeliveryCheck]
    narrative_mode: str = "legacy_unspecified"


@dataclass
class NarrativeAuditReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    capability_missing: list[str] = field(default_factory=list)
    capability_unverified: list[str] = field(default_factory=list)
    capability_state: str = VERIFIED


def _resolve(value: str, base: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (base / path).resolve()


def _resolve_semantic_manifest(manifest: dict[str, Any], manifest_path: Path) -> Path | None:
    """Resolve an explicitly opted-in semantic manifest.

    The delivery manifest and semantic-module manifest are separate contracts.
    Do not infer one from the other: a missing ``semantic_manifest`` means the
    legacy/non-semantic path and is intentionally skipped.
    """
    raw = manifest.get("semantic_manifest")
    if raw in (None, ""):
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise DeliveryConfigError(
            DELIVERY_MANIFEST_SCHEMA_INVALID,
            "semantic_manifest must be a non-empty path string when declared",
        )
    path = _resolve(raw, manifest_path.parent)
    if not path.is_file():
        raise DeliveryConfigError(SEMANTIC_MANIFEST_NOT_FOUND, f"semantic_manifest does not exist: {path}")
    return path


def _common_manifest_v1_checks(manifest: dict[str, Any], path: Path) -> None:
    """Keep the existing v1 validation in one unchanged-looking block."""
    prototype = str(manifest.get("prototype", "")).upper().strip()
    if not prototype:
        raise ValueError("build manifest requires prototype")
    mode = manifest.get("greeting_mode", "player_prose")
    if mode not in GREETING_MODES:
        raise ValueError(f"unsupported greeting_mode: {mode}")
    appendix_standard = manifest.get(
        "greeting_appendix_standard",
        "stage_brief_v1" if mode == "prose_plus_director_appendix" else "none",
    )
    if appendix_standard not in GREETING_APPENDIX_STANDARDS:
        raise ValueError(f"unsupported greeting_appendix_standard: {appendix_standard}")
    if mode == "prose_plus_director_appendix" and appendix_standard != "stage_brief_v1":
        raise ValueError("prose_plus_director_appendix requires greeting_appendix_standard=stage_brief_v1")
    routing = manifest.get("routing_mode", "flat")
    if routing not in ROUTING_MODES:
        raise ValueError(f"unsupported routing_mode: {routing}")
    required = bool(manifest.get("source_coverage_required", False))
    sources = manifest.get("canonical_sources", [])
    if not isinstance(sources, list) or not all(isinstance(item, str) and item.strip() for item in sources):
        raise ValueError("canonical_sources must be a list of non-empty strings")
    if required and not sources:
        raise ValueError("source_coverage_required=true requires canonical_sources")
    if required:
        missing_sources = [
            str(_resolve(raw, path.parent))
            for raw in sources
            if not _resolve(raw, path.parent).is_file()
        ]
        if missing_sources:
            raise ValueError("canonical source does not exist: " + ", ".join(missing_sources))
    minimum = float(manifest.get("source_coverage_minimum", 0.60))
    if not 0 <= minimum <= 1:
        raise ValueError("source_coverage_minimum must be between 0 and 1")
    if routing == "native_greeting_title":
        contract_raw = manifest.get("stage_entry_contract")
        if not contract_raw:
            raise ValueError("routing_mode=native_greeting_title requires stage_entry_contract")
        contract = _resolve(str(contract_raw), path.parent)
        if not contract.is_file():
            raise ValueError(f"stage_entry_contract does not exist: {contract}")
    if routing == "simple_stage_route":
        if not manifest.get("preset") or not manifest.get("preset_policy"):
            raise ValueError("routing_mode=simple_stage_route requires preset and preset_policy")
        for field_name in ("preset", "preset_policy"):
            resource = _resolve(str(manifest[field_name]), path.parent)
            if not resource.is_file():
                raise ValueError(f"{field_name} does not exist: {resource}")


def load_delivery_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise DeliveryConfigError(DELIVERY_MANIFEST_NOT_FOUND, f"build manifest does not exist: {path}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise DeliveryConfigError(DELIVERY_MANIFEST_NOT_FOUND, f"cannot read build manifest: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DeliveryConfigError(DELIVERY_MANIFEST_JSON_INVALID, f"build manifest JSON is invalid: {exc}") from exc
    if not isinstance(manifest, dict):
        raise DeliveryConfigError(DELIVERY_MANIFEST_SCHEMA_INVALID, "build manifest must be a JSON object")
    try:
        version = manifest.get("schema_version")
        if version == 2:
            load_validated_content_policy(path, reject_unverified=False)
            _common_manifest_v1_checks({
                **manifest,
                "prototype": manifest.get("prototype"),
                "greeting_mode": manifest.get("greeting_mode", "player_prose"),
                "routing_mode": manifest.get("routing_mode", "flat"),
            }, path)
            return manifest
        if version != 1:
            raise ValueError("build manifest schema_version must be 1 or 2")
        _common_manifest_v1_checks(manifest, path)
        return manifest
    except DeliveryConfigError:
        raise
    except (OSError, UnicodeDecodeError, TypeError, ValueError, KeyError) as exc:
        raise DeliveryConfigError(DELIVERY_MANIFEST_SCHEMA_INVALID, str(exc)) from exc


def load_semantic_manifest_for_delivery(path: Path) -> dict[str, Any]:
    """Load an opted-in semantic manifest with a stable CLI error category."""
    try:
        return load_semantic_manifest(path)
    except FileNotFoundError as exc:
        raise DeliveryConfigError(SEMANTIC_MANIFEST_NOT_FOUND, f"semantic manifest does not exist: {path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise DeliveryConfigError(SEMANTIC_MANIFEST_JSON_INVALID, f"semantic manifest is invalid: {exc}") from exc


def _append_narrative_checks(checks: list[DeliveryCheck], manifest: dict[str, Any], manifest_path: Path) -> None:
    if manifest.get("schema_version") != 2:
        return
    mode = str(manifest.get("narrative_mode"))
    driver = str(manifest.get("runtime_driver"))
    event_policy = str(manifest.get("event_policy"))
    event_mode = str(manifest.get("event_mode", "legacy_unspecified"))
    validation = validate_manifest(manifest, manifest_path.parent)
    checks.append(DeliveryCheck("narrative mode", "RUN", f"narrative_mode={mode}; no routing inference"))
    if mode == "open_sandbox" and manifest.get("runtime_state", {}).get("authority") == "none":
        checks.append(DeliveryCheck("runtime state contract", "SKIP", "open_sandbox authority=none does not require persistent state"))
    else:
        checks.append(DeliveryCheck("runtime state contract", "RUN", "runtime_state contract is a separate artifact"))
    if driver == "external_extension":
        status = validation.capability_state
        reason = {
            CAPABILITY_MISSING: "external extension contract/assets/fixture missing or invalid",
            DECLARED_UNVERIFIED: "external extension contract/assets declared but fixture is not verified",
            VERIFIED: "external extension read/write/recovery fixture verified",
        }[status]
        checks.append(DeliveryCheck("runtime driver capability", status, reason))
    else:
        checks.append(DeliveryCheck("runtime driver capability", "RUN", "runtime_driver=native_st"))
    if mode == "linear_stage":
        checks.append(DeliveryCheck("ordered-step audit", "RUN", "linear_stage allows ordered steps"))
        checks.append(DeliveryCheck("candidate-event audit", "SKIP", "not required for ordered_steps"))
        checks.append(DeliveryCheck("transition-policy audit", "SKIP", "linear_stage uses step_completion"))
        checks.append(DeliveryCheck("open-sandbox audit", "SKIP", "not an open_sandbox card"))
    elif mode == "soft_stage":
        checks.append(DeliveryCheck("ordered-step audit", "SKIP", "soft_stage is not a fixed step chain"))
        checks.append(DeliveryCheck("candidate-event audit", "RUN", "soft_stage requires candidate_pool"))
        checks.append(DeliveryCheck("transition-policy audit", "RUN", "soft_stage requires outcome_based"))
        checks.append(DeliveryCheck("freeplay path simulation", "RUN", "deterministic contract/state graph only"))
        checks.append(DeliveryCheck("open-sandbox audit", "SKIP", "not an open_sandbox card"))
    elif mode == "open_sandbox":
        checks.append(DeliveryCheck("ordered-step audit", "SKIP", "open_sandbox has no ordered steps"))
        if event_policy == "candidate_pool":
            reason = "open_sandbox open_situation_seed" if event_mode == "open_situation_seed" else "open_sandbox candidate_pool"
            checks.append(DeliveryCheck("candidate-event audit", "RUN", reason))
        else:
            checks.append(DeliveryCheck("candidate-event audit", "SKIP", "open_sandbox event_policy=none"))
        checks.append(DeliveryCheck("transition-policy audit", "SKIP", "open_sandbox does not require stage transitions"))
        checks.append(DeliveryCheck("freeplay path simulation", "SKIP", "open_sandbox has no stage transition simulation"))
        checks.append(DeliveryCheck("open-sandbox audit", "RUN", "multi-entry sandbox checks"))


def build_delivery_plan(card_path: Path, manifest_path: Path) -> DeliveryPlan:
    card_path = card_path.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()
    if not card_path.is_file():
        raise ValueError(f"card does not exist: {card_path}")
    manifest = load_delivery_manifest(manifest_path)
    semantic_manifest_path = _resolve_semantic_manifest(manifest, manifest_path)
    project_dir = _resolve(str(manifest.get("project_dir", card_path.parent)), manifest_path.parent)
    prototype = str(manifest.get("prototype", "")).upper().strip()
    greeting_mode = str(manifest.get("greeting_mode", "player_prose"))
    greeting_appendix_standard = str(
        manifest.get(
            "greeting_appendix_standard",
            "stage_brief_v1" if greeting_mode == "prose_plus_director_appendix" else "none",
        )
    )
    routing_mode = str(manifest.get("routing_mode", "flat"))
    require_build = bool(manifest.get("require_build", False))
    reproducibility_required = bool(manifest.get("build_reproducibility_required", False))
    source_required = bool(manifest.get("source_coverage_required", False))
    sources = [_resolve(raw, manifest_path.parent) for raw in manifest.get("canonical_sources", [])]

    argv = [str(card_path), "--project-dir", str(project_dir), "--prototype", prototype]
    checks = [DeliveryCheck("card validation", "RUN", "final_delivery_gate baseline")]
    if semantic_manifest_path is None:
        checks.append(DeliveryCheck("manifest alignment", "SKIP", "semantic_manifest 未声明；legacy/non-semantic path"))
        checks.append(DeliveryCheck("semantic module audit", "SKIP", "semantic_manifest 未声明；legacy/non-semantic path"))
        checks.append(DeliveryCheck("semantic text audit", "SKIP", "semantic_manifest 未声明；legacy/non-semantic path"))
    else:
        checks.append(DeliveryCheck("manifest alignment", "RUN", f"semantic_manifest={semantic_manifest_path}"))
        checks.append(DeliveryCheck("semantic module audit", "RUN", f"semantic_manifest={semantic_manifest_path}"))
        semantic_manifest = load_semantic_manifest_for_delivery(semantic_manifest_path)
        if semantic_manifest.get("text_profile"):
            checks.append(DeliveryCheck("semantic text audit", "RUN", f"text_profile={semantic_manifest['text_profile']}"))
        else:
            checks.append(DeliveryCheck("semantic text audit", "SKIP", "text_profile 未声明；保留 legacy semantic text path"))
    if manifest.get("schema_version") == 2:
        argv.extend(["--policy-manifest", str(manifest_path)])
        event_mode = manifest.get("event_mode", "legacy_unspecified")
        corpus_mode = manifest.get("corpus_mode", "legacy_unspecified")
        route_policy = manifest.get("route_policy", "legacy_unspecified")
        checks.append(DeliveryCheck(
            "content policy",
            "RUN",
            f"event_mode={event_mode}; corpus_mode={corpus_mode}; route_policy={route_policy}",
        ))
    else:
        checks.append(DeliveryCheck("content policy", "SKIP", "Manifest v1 keeps legacy enrichment semantics"))
    if require_build:
        argv.append("--require-build")
        checks.append(DeliveryCheck("build sync", "RUN", "manifest require_build=true"))
    else:
        checks.append(DeliveryCheck("build sync", "SKIP", "manifest require_build=false"))
    if reproducibility_required:
        argv.append("--require-reproducible-build")
        checks.append(DeliveryCheck("reproducible build", "RUN", "manifest build_reproducibility_required=true; external --execute-builder remains required for verification"))
    else:
        checks.append(DeliveryCheck("reproducible build", "SKIP", "manifest build_reproducibility_required=false"))

    if source_required:
        for source in sources:
            argv.extend(["--source", str(source)])
        if "source_coverage_minimum" in manifest:
            argv.extend(["--source-coverage-minimum", str(manifest["source_coverage_minimum"])])
            coverage_reason = f"{len(sources)} canonical source(s); explicit minimum={manifest['source_coverage_minimum']}"
        else:
            coverage_reason = f"{len(sources)} canonical source(s); minimum resolved by corpus_mode"
        checks.append(DeliveryCheck("source coverage", "RUN", coverage_reason))
    else:
        checks.append(DeliveryCheck("source coverage", "SKIP", "source_coverage_required=false"))

    if greeting_mode == "prose_plus_director_appendix":
        argv.extend([
            "--greeting-mode",
            greeting_mode,
            "--greeting-layer-audit",
            "--greeting-appendix-standard",
            greeting_appendix_standard,
        ])
        checks.append(DeliveryCheck("Greeting appendix audit", "RUN", f"greeting_mode={greeting_mode}, standard={greeting_appendix_standard}"))
        if require_build:
            checks.append(DeliveryCheck("Greeting build wiring", "RUN", "require_build=true; compare build/all_entries.json to assembled Greetings"))
        else:
            checks.append(DeliveryCheck("Greeting build wiring", "SKIP", "require_build=false; no canonical Greeting build source required"))
    else:
        checks.append(DeliveryCheck("Greeting appendix audit", "SKIP", f"greeting_mode={greeting_mode}"))
        if greeting_mode == "ai_trigger":
            argv.extend(["--greeting-mode", greeting_mode])

    if routing_mode == "native_greeting_title":
        contract = _resolve(str(manifest["stage_entry_contract"]), manifest_path.parent)
        argv.extend(["--native-stage-routing", "--stage-entry-contract", str(contract)])
        checks.append(DeliveryCheck("native-stage contract", "RUN", "routing_mode=native_greeting_title"))
    elif routing_mode == "simple_stage_route":
        preset = _resolve(str(manifest["preset"]), manifest_path.parent)
        policy = _resolve(str(manifest["preset_policy"]), manifest_path.parent)
        argv.extend(["--simple-stage-route", "--preset", str(preset), "--preset-policy", str(policy)])
        checks.append(DeliveryCheck("paired-preset stage route", "RUN", "routing_mode=simple_stage_route"))
    else:
        checks.append(DeliveryCheck("stage routing", "SKIP", "routing_mode=flat"))

    route_policy = str(manifest.get("route_policy", "legacy_unspecified"))
    agency_required = bool(manifest.get("player_agency_modes_required", False)) or prototype == "G"
    boundary_required = manifest.get("schema_version") == 2 and route_policy == "player_led"
    if agency_required:
        argv.append("--require-player-agency-modes")
        checks.append(DeliveryCheck("player agency modes", "RUN", "manifest required or prototype=G"))
    else:
        checks.append(DeliveryCheck("player agency modes", "SKIP", "not required for this prototype"))
    if boundary_required:
        argv.append("--require-player-boundary")
        checks.append(DeliveryCheck("player agency boundary", "RUN", "route_policy=player_led"))
    else:
        checks.append(DeliveryCheck("player agency boundary", "SKIP", "route_policy does not require player-led boundary"))

    if str(manifest.get("content_mode", "r18")).lower() in {"safe", "general", "non_r18"}:
        argv.append("--no-r18")
        checks.append(DeliveryCheck("R18 content shell", "SKIP", "content_mode is non-R18"))
    else:
        checks.append(DeliveryCheck("R18 content shell", "RUN", "content_mode defaults to r18"))
    _append_narrative_checks(checks, manifest, manifest_path)
    return DeliveryPlan(card_path, manifest_path, project_dir, argv, checks, str(manifest.get("narrative_mode", "legacy_unspecified")))


def run_narrative_audits(card_path: Path, manifest_path: Path) -> NarrativeAuditReport:
    manifest = load_delivery_manifest(manifest_path)
    report = NarrativeAuditReport()
    if manifest.get("schema_version") != 2:
        return report
    validation = validate_manifest(manifest, manifest_path.parent)
    report.capability_state = validation.capability_state
    for issue in validation.capability_issues:
        if issue.code == CAPABILITY_MISSING:
            report.capability_missing.append(issue.message)
        elif issue.code == DECLARED_UNVERIFIED:
            report.capability_unverified.append(issue.message)
            report.warnings.append(issue.message)
    report.errors.extend(f"{issue.code}: {issue.message}" for issue in validation.errors)
    mode = manifest["narrative_mode"]
    event_policy = manifest.get("event_policy")
    narrative_path_raw = manifest.get("narrative_contract")
    narrative_contract = None
    if narrative_path_raw:
        narrative_path = _resolve(str(narrative_path_raw), manifest_path.parent)
        if narrative_path.is_file():
            try:
                narrative_contract = load_json(narrative_path)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                report.errors.append(f"narrative contract读取失败: {exc}")
        elif mode in {"linear_stage", "soft_stage"} or event_policy == "candidate_pool":
            report.errors.append(f"narrative contract不存在: {narrative_path}")

    state_meta = manifest.get("runtime_state", {})
    state_contract = None
    state_path_raw = state_meta.get("contract") if isinstance(state_meta, dict) else None
    if state_path_raw:
        state_path = _resolve(str(state_path_raw), manifest_path.parent)
        if state_path.is_file():
            try:
                state_contract = load_json(state_path)
                result = audit_runtime_state(state_contract, state_meta)
                report.errors.extend(result.errors)
                report.warnings.extend(result.warnings)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                report.errors.append(f"runtime state contract读取失败: {exc}")

    bundle = validate_contract_bundle(manifest, narrative_contract, state_contract, manifest_path.parent)
    report.errors.extend(f"{issue.code}: {issue.message}" for issue in bundle.errors)
    report.warnings.extend(f"{issue.code}: {issue.message}" for issue in bundle.warnings)

    if narrative_contract is not None:
        if mode == "linear_stage":
            report.errors.extend(audit_ordered_steps(narrative_contract).errors)
        elif mode == "soft_stage":
            candidate_result = audit_candidate_events(narrative_contract, state_contract)
            transition_result = audit_stage_transitions(narrative_contract)
            report.errors.extend(candidate_result.errors)
            report.errors.extend(transition_result.errors)
            if not candidate_result.errors and not transition_result.errors:
                try:
                    simulation = simulate_paths(narrative_contract)
                except (ValueError, TypeError, KeyError, AttributeError) as exc:
                    report.errors.append(f"freeplay path simulation could not run: {type(exc).__name__}: {exc}")
                else:
                    if not simulation.get("passed", simulation.get("ok", False)):
                        failures = simulation.get("failures", [])
                        if not failures:
                            report.errors.append("freeplay path simulation failed: report marked passed=false without a failure record")
                        for failure in failures:
                            if isinstance(failure, dict):
                                report.errors.append(
                                    "freeplay path simulation failed: "
                                    f"stage={failure.get('stage', '')} "
                                    f"event={failure.get('event', '')} "
                                    f"path={failure.get('path', '')} "
                                    f"error={failure.get('error', '')}"
                                )
                            else:
                                report.errors.append(f"freeplay path simulation failed: {failure}")
        elif mode == "open_sandbox":
            if event_policy == "candidate_pool":
                report.errors.extend(audit_candidate_events(narrative_contract, state_contract).errors)

    if mode == "open_sandbox":
        try:
            card = json.loads(card_path.read_text(encoding="utf-8-sig"))
            sandbox_result = audit_open_sandbox(card, manifest)
            report.errors.extend(sandbox_result.errors)
            report.warnings.extend(sandbox_result.warnings)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            report.errors.append(f"open sandbox card读取失败: {exc}")
    return report


def run_semantic_audit(card_path: Path, manifest_path: Path) -> list[dict[str, str]]:
    """Run the opt-in semantic module audit declared by build_manifest.

    The semantic manifest is deliberately separate from Manifest v1/v2. This
    function only crosses that boundary when ``semantic_manifest`` is explicit;
    legacy delivery manifests therefore remain unchanged and skip safely.
    """
    delivery_manifest = load_delivery_manifest(manifest_path)
    semantic_path = _resolve_semantic_manifest(delivery_manifest, manifest_path)
    if semantic_path is None:
        return []
    try:
        card = json.loads(card_path.read_text(encoding="utf-8-sig"))
        semantic_manifest = load_semantic_manifest(semantic_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return [{
            "level": "ERROR",
            "code": "SEMANTIC_AUDIT_INPUT_ERROR",
            "comment": "",
            "message": f"语义 manifest/card 读取失败：{exc}",
        }]
    if not isinstance(card, dict):
        return [{
            "level": "ERROR",
            "code": "SEMANTIC_AUDIT_INPUT_ERROR",
            "comment": "",
            "message": "card root must be an object",
        }]
    issues = audit_manifest_alignment(
        delivery_manifest,
        semantic_manifest,
        delivery_base=manifest_path.parent,
        semantic_base=semantic_path.parent,
    )
    issues.extend(audit_semantic_modules(card, semantic_manifest, require_profile=True))
    if semantic_manifest.get("text_profile"):
        issues.extend(audit_semantic_text(card, semantic_manifest, require_profile=True))
    return issues


def render_plan(plan: DeliveryPlan) -> str:
    lines = ["有效交付计划：", f"- card: {plan.card_path}", f"- manifest: {plan.manifest_path}"]
    for check in plan.checks:
        lines.append(f"- {check.name}: {check.status} — {check.reason}")
    lines.append("- final gate argv: " + " ".join(plan.argv))
    return "\n".join(lines)


def render_semantic_coverage(card_path: Path, manifest_path: Path) -> str | None:
    """Render migration coverage without altering any existing audit decision."""
    try:
        delivery_manifest = load_delivery_manifest(manifest_path)
        semantic_path = _resolve_semantic_manifest(delivery_manifest, manifest_path)
        if semantic_path is None:
            return None
        card = json.loads(card_path.read_text(encoding="utf-8-sig"))
        semantic_manifest = load_semantic_manifest_for_delivery(semantic_path)
        coverage = summarize_semantic_coverage(card, semantic_manifest)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
        return None
    return (
        "- semantic coverage: "
        f"modern text modules audited: {coverage['modern_text_modules_audited']}; "
        f"legacy semantic modules audited: {coverage['legacy_semantic_modules_audited']}; "
        f"non-semantic entries ignored: {coverage['non_semantic_entries_ignored']}; "
        f"unregistered formal namespace modules: {coverage['unregistered_formal_namespace_modules']}"
    )


def semantic_status_floor(issues: list[dict[str, str]]) -> int:
    if any(issue.get("level") == "ERROR" for issue in issues):
        return 1
    if any(issue.get("level") in {"WARNING", "WARN"} for issue in issues):
        return 2
    return 0


def _emit_config_error(error: DeliveryConfigError, output_format: str) -> None:
    payload = {"ok": False, "error": {"code": error.code, "message": error.message}}
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"ERROR {error.code}: {error.message}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run manifest-driven final delivery gate")
    parser.add_argument("card", help="final Character Card V3 JSON")
    parser.add_argument("--manifest", required=True, help="build_manifest.json")
    parser.add_argument("--dry-run", action="store_true", help="print the effective plan without running final_delivery_gate.py")
    parser.add_argument("--format", choices=("text", "json"), default="text", dest="output_format", help="configuration error output format")
    args = parser.parse_args(argv)
    try:
        plan = build_delivery_plan(Path(args.card), Path(args.manifest))
    except DeliveryConfigError as exc:
        _emit_config_error(exc, args.output_format)
        return 2
    except ValueError as exc:
        parser.error(str(exc))
    print(render_plan(plan))
    coverage_line = render_semantic_coverage(plan.card_path, plan.manifest_path)
    if coverage_line:
        print(coverage_line)
    if args.dry_run:
        return 2 if any(check.status in {CAPABILITY_MISSING, DECLARED_UNVERIFIED} for check in plan.checks) else 0

    semantic_issues = run_semantic_audit(plan.card_path, plan.manifest_path)
    for issue in semantic_issues:
        level = issue.get("level", "INFO")
        prefix = "SEMANTIC ERROR" if level == "ERROR" else f"SEMANTIC {level}"
        comment = f" [{issue.get('comment')}]" if issue.get("comment") else ""
        print(f"{prefix} {issue.get('code', 'UNKNOWN')}{comment}: {issue.get('message', '')}")
    semantic_floor = semantic_status_floor(semantic_issues)
    if semantic_floor == 1:
        return 1

    narrative_report = run_narrative_audits(plan.card_path, plan.manifest_path)
    for error in narrative_report.errors:
        print(f"NARRATIVE ERROR: {error}")
    for warning in narrative_report.warnings:
        print(f"NARRATIVE WARNING: {warning}")
    for missing in narrative_report.capability_missing:
        print(f"CAPABILITY_MISSING: {missing}")
    for unverified in narrative_report.capability_unverified:
        print(f"DECLARED_UNVERIFIED: {unverified}")
    if narrative_report.errors:
        return 1

    from final_delivery_gate import main as final_gate_main
    final_status = final_gate_main(plan.argv)
    if narrative_report.capability_state != VERIFIED:
        return max(final_status, semantic_floor, 2)
    return max(final_status, semantic_floor)


if __name__ == "__main__":
    raise SystemExit(main())
