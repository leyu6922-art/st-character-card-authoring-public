"""Shared validation for narrative/runtime dimensions in Manifest v2."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


NARRATIVE_MODES = {"linear_stage", "soft_stage", "open_sandbox"}
EVENT_MODES = {"open_situation_seed", "guided_candidate", "scripted_sequence", "legacy_unspecified"}
ROUTE_POLICIES = {"player_led", "guided", "locked", "legacy_unspecified"}
CORPUS_MODES = {"curated_anchor_set", "expanded_reference_corpus", "legacy_unspecified"}
RUNTIME_DRIVERS = {"native_st", "external_extension"}
STATE_AUTHORITIES = {"none", "prompt_record", "mvu", "external_extension"}
UPDATE_MODES = {"manual", "model", "script"}
RECOVERY_POLICIES = {
    "greeting_baseline",
    "latest_valid_record",
    "variable_snapshot",
    "external_checkpoint",
}
RELIABILITIES = {"best_effort", "authoritative"}
EVENT_POLICIES = {"ordered_steps", "candidate_pool", "none"}
TRANSITION_POLICIES = {"step_completion", "outcome_based", "none"}
SANDBOX_SCOPES = {"focused", "ensemble", "legacy_unspecified"}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    level: str = "error"


@dataclass
class ManifestValidation:
    normalized: dict[str, Any]
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    capability_missing: list[ValidationIssue] = field(default_factory=list)
    capability_issues: list[ValidationIssue] = field(default_factory=list)
    capability_state: str = "VERIFIED"


@dataclass
class BundleValidation:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    capability_issues: list[ValidationIssue] = field(default_factory=list)
    capability_state: str = "VERIFIED"


CAPABILITY_MISSING = "CAPABILITY_MISSING"
DECLARED_UNVERIFIED = "DECLARED_UNVERIFIED"
VERIFIED = "VERIFIED"


def _issue(code: str, message: str, level: str = "error") -> ValidationIssue:
    return ValidationIssue(code, message, level)


def _resolve(raw: Any, base_dir: Path) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (base_dir / path).resolve()


def _require_enum(raw: dict[str, Any], key: str, allowed: set[str], errors: list[ValidationIssue]) -> str | None:
    value = raw.get(key)
    if value not in allowed:
        errors.append(_issue(
            f"INVALID_{key.upper()}",
            f"{key}必须为{sorted(allowed)}之一，实际为{value!r}",
        ))
        return None
    return str(value)


def validate_manifest(raw: Any, base_dir: Path | str = ".") -> ManifestValidation:
    """Validate the new dimensions while leaving v1 semantics untouched."""
    base = Path(base_dir).expanduser().resolve()
    if not isinstance(raw, dict):
        return ManifestValidation({}, [_issue("MANIFEST_NOT_OBJECT", "Manifest必须是JSON对象")])

    version = raw.get("schema_version")
    if version == 1:
        normalized = dict(raw)
        normalized.setdefault("narrative_mode", "legacy_unspecified")
        normalized.setdefault("event_mode", "legacy_unspecified")
        normalized.setdefault("route_policy", "legacy_unspecified")
        normalized.setdefault("corpus_mode", "legacy_unspecified")
        normalized.setdefault("sandbox_scope", "legacy_unspecified")
        normalized.setdefault("runtime_driver", "native_st")
        return ManifestValidation(normalized)
    if version != 2:
        return ManifestValidation({}, [_issue("UNSUPPORTED_MANIFEST_SCHEMA", "Manifest schema_version必须为1或2")])

    normalized = dict(raw)
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    capability_missing: list[ValidationIssue] = []
    capability_issues: list[ValidationIssue] = []
    capability_state = VERIFIED

    if "prototype" not in raw or not isinstance(raw.get("prototype"), str) or not raw.get("prototype", "").strip():
        errors.append(_issue("PROTOTYPE_REQUIRED", "Manifest v2必须显式声明prototype，不能默认回退到A型"))

    mode = raw.get("narrative_mode")
    if mode not in NARRATIVE_MODES:
        errors.append(_issue(
            "NARRATIVE_MODE_REQUIRED",
            "Manifest v2必须显式声明narrative_mode，不能从routing_mode推断",
        ))
        mode = None
    content_modes = {
        "event_mode": (EVENT_MODES, "legacy_unspecified"),
        "route_policy": (ROUTE_POLICIES, "legacy_unspecified"),
        "corpus_mode": (CORPUS_MODES, "legacy_unspecified"),
    }
    for key, (allowed, default) in content_modes.items():
        value = raw.get(key, default)
        if value not in allowed:
            errors.append(_issue(
                f"INVALID_{key.upper()}",
                f"{key}必须为{sorted(allowed)}之一，实际为{value!r}",
            ))
        normalized[key] = value if value in allowed else default
    sandbox_scope = raw.get("sandbox_scope", "legacy_unspecified")
    if sandbox_scope not in SANDBOX_SCOPES:
        errors.append(_issue(
            "INVALID_SANDBOX_SCOPE",
            f"sandbox_scope必须为{sorted(SANDBOX_SCOPES)}之一，实际为{sandbox_scope!r}",
        ))
        sandbox_scope = "legacy_unspecified"
    elif sandbox_scope != "legacy_unspecified" and mode != "open_sandbox":
        errors.append(_issue(
            "SANDBOX_SCOPE_NARRATIVE_MISMATCH",
            "sandbox_scope只有narrative_mode=open_sandbox时才允许声明",
        ))
    normalized["sandbox_scope"] = sandbox_scope
    driver = _require_enum(raw, "runtime_driver", RUNTIME_DRIVERS, errors)
    event_policy = _require_enum(raw, "event_policy", EVENT_POLICIES, errors)
    transition_policy = _require_enum(raw, "transition_policy", TRANSITION_POLICIES, errors)

    state = raw.get("runtime_state")
    if not isinstance(state, dict):
        errors.append(_issue("RUNTIME_STATE_REQUIRED", "Manifest v2必须声明runtime_state对象"))
        state = {}
    authority = _require_enum(state, "authority", STATE_AUTHORITIES, errors)
    update_mode = _require_enum(state, "update_mode", UPDATE_MODES, errors)
    recovery = _require_enum(state, "recovery_policy", RECOVERY_POLICIES, errors)
    reliability = _require_enum(state, "reliability", RELIABILITIES, errors)

    if mode in {"linear_stage", "soft_stage"}:
        narrative_path = _resolve(raw.get("narrative_contract"), base)
        if narrative_path is None:
            errors.append(_issue("NARRATIVE_CONTRACT_REQUIRED", f"{mode}必须声明narrative_contract"))
        elif not narrative_path.is_file():
            errors.append(_issue("NARRATIVE_CONTRACT_MISSING", f"narrative_contract不存在: {narrative_path}"))
    elif mode == "open_sandbox" and event_policy == "candidate_pool":
        narrative_path = _resolve(raw.get("narrative_contract"), base)
        if narrative_path is None or not narrative_path.is_file():
            errors.append(_issue("NARRATIVE_CONTRACT_REQUIRED", "open_sandbox候选事件池必须有narrative_contract"))

    state_contract = _resolve(state.get("contract"), base)
    if mode in {"linear_stage", "soft_stage"}:
        if state_contract is None:
            errors.append(_issue("RUNTIME_STATE_CONTRACT_REQUIRED", f"{mode}必须声明runtime_state.contract"))
        elif not state_contract.is_file():
            errors.append(_issue("RUNTIME_STATE_CONTRACT_MISSING", f"runtime state contract不存在: {state_contract}"))
    elif mode == "open_sandbox" and authority != "none":
        if state_contract is None:
            errors.append(_issue("RUNTIME_STATE_CONTRACT_REQUIRED", "open_sandbox使用持久状态权威时必须声明runtime_state.contract"))
        elif not state_contract.is_file():
            errors.append(_issue("RUNTIME_STATE_CONTRACT_MISSING", f"runtime state contract不存在: {state_contract}"))
    elif authority == "none":
        if state.get("contract") not in (None, ""):
            errors.append(_issue("STATE_CONTRACT_WITHOUT_AUTHORITY", "authority=none不能声明runtime_state.contract"))
        if recovery != "greeting_baseline":
            errors.append(_issue("NONE_STATE_RECOVERY_INVALID", "authority=none必须使用greeting_baseline恢复"))

    if mode in {"linear_stage", "soft_stage"} and authority == "none":
        errors.append(_issue("RUNTIME_STATE_AUTHORITY_REQUIRED", f"{mode}不能使用authority=none"))

    if mode == "linear_stage" and (event_policy != "ordered_steps" or transition_policy != "step_completion"):
        errors.append(_issue("LINEAR_POLICY_MISMATCH", "linear_stage必须使用ordered_steps + step_completion"))
    if mode == "soft_stage" and (event_policy != "candidate_pool" or transition_policy != "outcome_based"):
        errors.append(_issue("SOFT_POLICY_MISMATCH", "soft_stage必须使用candidate_pool + outcome_based"))
    if mode == "open_sandbox" and (event_policy not in {"none", "candidate_pool"} or transition_policy != "none"):
        errors.append(_issue("OPEN_POLICY_MISMATCH", "open_sandbox必须使用event_policy=none或candidate_pool，并使用transition_policy=none"))

    event_mode = normalized["event_mode"]
    route_policy = normalized["route_policy"]
    if event_mode == "open_situation_seed":
        if mode != "open_sandbox":
            errors.append(_issue("EVENT_MODE_NARRATIVE_MISMATCH", "open_situation_seed必须使用narrative_mode=open_sandbox"))
        if event_policy != "candidate_pool":
            errors.append(_issue("OPEN_SITUATION_EVENT_POLICY_REQUIRED", "open_situation_seed必须使用event_policy=candidate_pool，以便审计开放种子合同"))
        if transition_policy != "none":
            errors.append(_issue("OPEN_SITUATION_TRANSITION_INVALID", "open_situation_seed必须使用transition_policy=none"))
    elif event_mode == "scripted_sequence" and mode != "linear_stage":
        errors.append(_issue("EVENT_MODE_NARRATIVE_MISMATCH", "scripted_sequence必须使用narrative_mode=linear_stage"))
    elif event_mode == "guided_candidate" and mode == "linear_stage":
        errors.append(_issue("EVENT_MODE_NARRATIVE_MISMATCH", "guided_candidate不能配合linear_stage固定步骤运行"))
    if route_policy == "locked" and mode == "open_sandbox":
        errors.append(_issue("ROUTE_POLICY_NARRATIVE_MISMATCH", "open_sandbox不能声明route_policy=locked"))

    if authority == "prompt_record" and reliability == "authoritative":
        errors.append(_issue("PROMPT_RECORD_NOT_AUTHORITATIVE", "prompt_record只能声明best_effort，不能声明authoritative"))
    if authority == "external_extension":
        if driver != "external_extension":
            errors.append(_issue("EXTERNAL_AUTHORITY_DRIVER_MISMATCH", "external_extension authority必须配合runtime_driver=external_extension"))
        if update_mode != "script":
            errors.append(_issue("EXTERNAL_AUTHORITY_WRITER_MISMATCH", "external_extension authority必须由script写入"))
        if recovery != "external_checkpoint":
            errors.append(_issue("EXTERNAL_AUTHORITY_RECOVERY_MISMATCH", "external_extension authority必须从external_checkpoint恢复"))
    if reliability == "authoritative":
        if not authoritative_evidence_is_verified(raw, base):
            errors.append(_issue(
                "AUTHORITATIVE_EVIDENCE_REQUIRED",
                "reliability=authoritative必须提供可复现的runtime_state_verification证据",
            ))
    if driver == "external_extension":
        capability_state, capability_issue = inspect_external_extension(raw, base)
        if capability_issue is not None:
            capability_issues.append(capability_issue)
            if capability_state == CAPABILITY_MISSING:
                capability_missing.append(capability_issue)

    normalized.update({
        "narrative_mode": mode,
        "runtime_driver": driver,
        "event_policy": event_policy,
        "transition_policy": transition_policy,
    })
    return ManifestValidation(
        normalized,
        errors,
        warnings,
        capability_missing,
        capability_issues,
        capability_state,
    )


def authoritative_evidence_is_verified(raw: dict[str, Any], base_dir: Path) -> bool:
    """Return whether a supported execution protocol proved authoritative state.

    A JSON report that merely claims ``write/read/recovery=true`` is not execution
    evidence.  The isolated fixture protocol is intentionally not implemented in
    this version, so authoritative state remains unavailable until that protocol
    can produce evidence itself.
    """
    del raw, base_dir
    return False


def inspect_external_extension(raw: dict[str, Any], base_dir: Path) -> tuple[str, ValidationIssue | None]:
    missing: list[str] = []
    extension_path = _resolve(raw.get("runtime_driver_contract"), base_dir)
    if extension_path is None or not extension_path.is_file():
        missing.append("runtime_driver_contract")
    assets = raw.get("runtime_driver_assets")
    if not isinstance(assets, list) or not assets:
        missing.append("runtime_driver_assets")
    else:
        missing_assets = [
            str(_resolve(item, base_dir) or item)
            for item in assets
            if _resolve(item, base_dir) is None or not _resolve(item, base_dir).is_file()
        ]
        if missing_assets:
            missing.append("runtime_driver_assets:" + ",".join(missing_assets))
    fixture = _resolve(raw.get("runtime_driver_test_fixture"), base_dir)
    if fixture is None or not fixture.is_file():
        missing.append("runtime_driver_test_fixture")
    if missing:
        return CAPABILITY_MISSING, _issue(
            CAPABILITY_MISSING,
            "runtime_driver=external_extension缺少: " + ", ".join(missing),
            "warning",
        )

    try:
        extension = load_json(extension_path)
        fixture_spec = load_json(fixture)
    except (OSError, UnicodeError, ValueError) as exc:
        return CAPABILITY_MISSING, _issue(
            CAPABILITY_MISSING,
            f"external_extension合同或fixture不可解析: {exc}",
            "warning",
        )
    capabilities = extension.get("capabilities")
    if (
        extension.get("schema_version") != 1
        or extension.get("driver") != "external_extension"
        or not isinstance(capabilities, list)
        or not capabilities
        or not all(isinstance(item, str) and item.strip() for item in capabilities)
    ):
        return CAPABILITY_MISSING, _issue(
            CAPABILITY_MISSING,
            "external_extension合同必须声明schema_version=1且driver=external_extension",
            "warning",
        )
    if not isinstance(fixture_spec, dict):
        return CAPABILITY_MISSING, _issue(
            CAPABILITY_MISSING,
            "external_extension fixture必须是JSON对象",
            "warning",
        )
    return DECLARED_UNVERIFIED, _issue(
        DECLARED_UNVERIFIED,
        "external_extension合同和资产存在，但尚未执行并验证read/write/recovery fixture",
        "warning",
    )


def validate_contract_bundle(
    manifest: Any,
    narrative_contract: dict[str, Any] | None = None,
    runtime_state_contract: dict[str, Any] | None = None,
    base_dir: Path | str = ".",
) -> BundleValidation:
    """Validate all cross-file dimensions from one shared implementation."""
    result = BundleValidation()
    manifest_result = validate_manifest(manifest, base_dir)
    result.errors.extend(manifest_result.errors)
    result.warnings.extend(manifest_result.warnings)
    result.capability_issues.extend(manifest_result.capability_issues)
    result.capability_state = manifest_result.capability_state
    if manifest_result.normalized.get("schema_version") != 2:
        return result

    mode = manifest_result.normalized.get("narrative_mode")
    event_policy = manifest_result.normalized.get("event_policy")
    transition_policy = manifest_result.normalized.get("transition_policy")
    state_meta = manifest.get("runtime_state", {}) if isinstance(manifest, dict) else {}
    if not isinstance(state_meta, dict):
        state_meta = {}

    needs_narrative = mode in {"linear_stage", "soft_stage"} or (
        mode == "open_sandbox" and event_policy == "candidate_pool"
    )
    if needs_narrative and narrative_contract is None:
        result.errors.append(_issue("NARRATIVE_CONTRACT_REQUIRED", "当前Manifest模式需要已加载的narrative contract"))
    if narrative_contract is not None and not isinstance(narrative_contract, dict):
        result.errors.append(_issue("NARRATIVE_CONTRACT_NOT_OBJECT", "narrative contract必须是对象"))
        narrative_contract = None
    if narrative_contract is not None:
        checks = (
            ("narrative_mode", mode, "MANIFEST_NARRATIVE_MODE_MISMATCH"),
            ("event_policy", event_policy, "MANIFEST_EVENT_POLICY_MISMATCH"),
            ("transition_policy", transition_policy, "MANIFEST_TRANSITION_POLICY_MISMATCH"),
        )
        for key, expected, code in checks:
            if narrative_contract.get(key) != expected:
                result.errors.append(_issue(code, f"Manifest {key}={expected!r} 与 narrative contract={narrative_contract.get(key)!r} 不一致"))
        if manifest.get("event_mode") is not None:
            declared_event_mode = narrative_contract.get("event_mode", "guided_candidate")
            if declared_event_mode != manifest_result.normalized.get("event_mode"):
                result.errors.append(_issue(
                    "MANIFEST_EVENT_MODE_MISMATCH",
                    f"Manifest event_mode={manifest_result.normalized.get('event_mode')!r} 与 narrative contract={declared_event_mode!r} 不一致",
                ))

    needs_state = mode in {"linear_stage", "soft_stage"} or (
        mode == "open_sandbox" and state_meta.get("authority") != "none"
    )
    if needs_state and runtime_state_contract is None:
        result.errors.append(_issue("RUNTIME_STATE_CONTRACT_REQUIRED", "当前Manifest模式需要已加载的runtime-state contract"))
    if runtime_state_contract is not None and not isinstance(runtime_state_contract, dict):
        result.errors.append(_issue("RUNTIME_STATE_CONTRACT_NOT_OBJECT", "runtime-state contract必须是对象"))
        runtime_state_contract = None
    if runtime_state_contract is not None:
        expected_recovery = state_meta.get("recovery_policy")
        declared_recovery = runtime_state_contract.get("manifest_recovery_policy")
        if declared_recovery != expected_recovery:
            result.errors.append(_issue(
                "RUNTIME_STATE_RECOVERY_MISMATCH",
                f"Manifest recovery_policy={expected_recovery!r} 与 runtime-state manifest_recovery_policy={declared_recovery!r} 不一致",
            ))
    return result


def load_validated_content_policy(
    manifest_path: Path | str,
    *,
    reject_unverified: bool = True,
) -> dict[str, str]:
    """Load a complete Manifest/contract bundle before enabling content policy.

    A small JSON object containing only event/corpus/route fields is not a
    policy Manifest and cannot activate relaxed gates. Manifest v1 remains
    legacy-compatible and returns legacy-unspecified policy dimensions.
    """
    path = Path(manifest_path).expanduser().resolve()
    try:
        manifest = load_json(path)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"policy Manifest读取失败: {exc}") from exc

    validation = validate_manifest(manifest, path.parent)
    narrative_contract = None
    narrative_raw = manifest.get("narrative_contract")
    if narrative_raw:
        narrative_path = _resolve(narrative_raw, path.parent)
        if narrative_path is not None and narrative_path.is_file():
            try:
                narrative_contract = load_json(narrative_path)
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"narrative contract读取失败: {exc}") from exc

    runtime_state_contract = None
    state_meta = manifest.get("runtime_state", {})
    if isinstance(state_meta, dict) and state_meta.get("contract"):
        state_path = _resolve(state_meta.get("contract"), path.parent)
        if state_path is not None and state_path.is_file():
            try:
                runtime_state_contract = load_json(state_path)
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"runtime-state contract读取失败: {exc}") from exc

    bundle = validate_contract_bundle(
        manifest,
        narrative_contract,
        runtime_state_contract,
        path.parent,
    )
    errors = [*validation.errors, *bundle.errors]
    if reject_unverified and validation.capability_state != VERIFIED:
        errors.extend(validation.capability_issues)
    if errors:
        details = "; ".join(f"{issue.code}: {issue.message}" for issue in errors)
        raise ValueError(details)

    normalized = validation.normalized
    return {
        "event_mode": str(normalized.get("event_mode", "legacy_unspecified")),
        "corpus_mode": str(normalized.get("corpus_mode", "legacy_unspecified")),
        "route_policy": str(normalized.get("route_policy", "legacy_unspecified")),
        "sandbox_scope": str(normalized.get("sandbox_scope", "legacy_unspecified")),
    }


def load_json(path: Path | str) -> dict[str, Any]:
    """Read a contract as UTF-8 JSON and reject BOM/invalid roots."""
    file_path = Path(path)
    raw = file_path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"合同带UTF-8 BOM: {file_path}")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"合同根节点必须是对象: {file_path}")
    return value
