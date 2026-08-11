from __future__ import annotations

import json
from pathlib import Path

import pytest


def base_v2(tmp_path: Path, *, mode: str = "soft_stage") -> dict:
    narrative = tmp_path / "narrative-contract.json"
    state = tmp_path / "runtime-state-contract.json"
    narrative.write_text("{}", encoding="utf-8")
    state.write_text("{}", encoding="utf-8")
    return {
        "schema_version": 2,
        "prototype": "A",
        "content_mode": "r18",
        "routing_mode": "native_greeting_title",
        "runtime_driver": "native_st",
        "narrative_mode": mode,
        "event_policy": "candidate_pool" if mode != "linear_stage" else "ordered_steps",
        "transition_policy": "outcome_based" if mode == "soft_stage" else ("step_completion" if mode == "linear_stage" else "none"),
        "narrative_contract": narrative.name,
        "runtime_state": {
            "authority": "prompt_record",
            "update_mode": "model",
            "contract": state.name,
            "recovery_policy": "latest_valid_record",
            "reliability": "best_effort",
        },
        "source_coverage_required": False,
    }


def test_manifest_v1_is_legacy_unspecified_and_does_not_require_new_contracts(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    raw = {
        "schema_version": 1,
        "prototype": "A",
        "routing_mode": "native_greeting_title",
        "greeting_mode": "player_prose",
    }

    result = module.validate_manifest(raw, tmp_path)

    assert result.errors == []
    assert result.normalized["narrative_mode"] == "legacy_unspecified"
    assert result.normalized["schema_version"] == 1


def test_soft_stage_requires_narrative_contract(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    raw = base_v2(tmp_path)
    raw.pop("narrative_contract")

    result = module.validate_manifest(raw, tmp_path)

    assert any(issue.code == "NARRATIVE_CONTRACT_REQUIRED" for issue in result.errors)


def test_soft_stage_requires_runtime_state_contract(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    raw = base_v2(tmp_path)
    raw["runtime_state"].pop("contract")

    result = module.validate_manifest(raw, tmp_path)

    assert any(issue.code == "RUNTIME_STATE_CONTRACT_REQUIRED" for issue in result.errors)


def test_open_sandbox_with_state_authority_requires_runtime_state_contract(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    raw = base_v2(tmp_path, mode="open_sandbox")
    raw["runtime_state"].pop("contract")

    result = module.validate_manifest(raw, tmp_path)

    assert any(issue.code == "RUNTIME_STATE_CONTRACT_REQUIRED" for issue in result.errors)


def test_manifest_v2_does_not_guess_mode_from_routing(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    raw = {
        "schema_version": 2,
        "prototype": "A",
        "routing_mode": "native_greeting_title",
        "runtime_driver": "native_st",
        "event_policy": "candidate_pool",
        "transition_policy": "none",
        "runtime_state": {
            "authority": "none",
            "update_mode": "manual",
            "recovery_policy": "greeting_baseline",
            "reliability": "best_effort",
        },
    }

    result = module.validate_manifest(raw, tmp_path)

    assert any(issue.code == "NARRATIVE_MODE_REQUIRED" for issue in result.errors)


def test_v2_without_content_modes_preserves_legacy_semantics(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    raw = base_v2(tmp_path)

    result = module.validate_manifest(raw, tmp_path)

    assert result.errors == []
    assert result.normalized["event_mode"] == "legacy_unspecified"
    assert result.normalized["route_policy"] == "legacy_unspecified"
    assert result.normalized["corpus_mode"] == "legacy_unspecified"


def test_open_framework_policy_is_validated_explicitly(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    raw = base_v2(tmp_path, mode="open_sandbox")
    raw.update({
        "event_mode": "open_situation_seed",
        "route_policy": "player_led",
        "corpus_mode": "curated_anchor_set",
        "event_policy": "candidate_pool",
        "transition_policy": "none",
    })
    raw["runtime_state"] = {
        "authority": "none",
        "update_mode": "manual",
        "contract": "",
        "recovery_policy": "greeting_baseline",
        "reliability": "best_effort",
    }

    result = module.validate_manifest(raw, tmp_path)

    assert result.errors == []
    assert result.normalized["event_mode"] == "open_situation_seed"
    assert result.normalized["route_policy"] == "player_led"


def _write_valid_open_policy(tmp_path: Path, *, sandbox_scope: str = "focused") -> Path:
    manifest = base_v2(tmp_path, mode="open_sandbox")
    manifest.update({
        "event_mode": "open_situation_seed",
        "route_policy": "player_led",
        "corpus_mode": "curated_anchor_set",
        "sandbox_scope": sandbox_scope,
        "event_policy": "candidate_pool",
        "transition_policy": "none",
    })
    manifest["runtime_state"] = {
        "authority": "none",
        "update_mode": "manual",
        "contract": "",
        "recovery_policy": "greeting_baseline",
        "reliability": "best_effort",
    }
    narrative = {
        "schema_version": 1,
        "narrative_mode": "open_sandbox",
        "event_mode": "open_situation_seed",
        "event_policy": "candidate_pool",
        "transition_policy": "none",
        "facts": {},
        "events": {},
    }
    (tmp_path / manifest["narrative_contract"]).write_text(json.dumps(narrative), encoding="utf-8")
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_load_validated_content_policy_returns_normalized_open_policy(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    manifest_path = _write_valid_open_policy(tmp_path)

    policy = module.load_validated_content_policy(manifest_path)

    assert policy == {
        "event_mode": "open_situation_seed",
        "corpus_mode": "curated_anchor_set",
        "route_policy": "player_led",
        "sandbox_scope": "focused",
    }


def test_load_validated_content_policy_rejects_incomplete_manifest(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    path = tmp_path / "fake-policy.json"
    path.write_text(json.dumps({
        "schema_version": 2,
        "event_mode": "open_situation_seed",
        "corpus_mode": "curated_anchor_set",
        "route_policy": "player_led",
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="PROTOTYPE_REQUIRED"):
        module.load_validated_content_policy(path)


def test_load_validated_content_policy_rejects_missing_narrative_contract(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    manifest_path = _write_valid_open_policy(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["narrative_contract"] = "missing-narrative.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="NARRATIVE_CONTRACT_REQUIRED"):
        module.load_validated_content_policy(manifest_path)


def test_load_validated_content_policy_validates_runtime_state_contract(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    manifest = base_v2(tmp_path)
    (tmp_path / manifest["narrative_contract"]).write_text(json.dumps({
        "schema_version": 1,
        "narrative_mode": "soft_stage",
        "event_policy": "candidate_pool",
        "transition_policy": "outcome_based",
    }), encoding="utf-8")
    (tmp_path / manifest["runtime_state"]["contract"]).write_text(json.dumps({
        "schema_version": 1,
        "manifest_recovery_policy": "latest_valid_record",
    }), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    policy = module.load_validated_content_policy(manifest_path)

    assert policy["event_mode"] == "legacy_unspecified"
    state = json.loads((tmp_path / manifest["runtime_state"]["contract"]).read_text(encoding="utf-8"))
    state["manifest_recovery_policy"] = "greeting_baseline"
    (tmp_path / manifest["runtime_state"]["contract"]).write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(ValueError, match="RUNTIME_STATE_RECOVERY_MISMATCH"):
        module.load_validated_content_policy(manifest_path)


def test_open_situation_seed_cannot_be_paired_with_linear_stage(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    raw = base_v2(tmp_path, mode="linear_stage")
    raw.update({
        "event_mode": "open_situation_seed",
        "route_policy": "player_led",
        "corpus_mode": "curated_anchor_set",
    })

    result = module.validate_manifest(raw, tmp_path)

    assert any(issue.code == "EVENT_MODE_NARRATIVE_MISMATCH" for issue in result.errors)


def test_manifest_rejects_unknown_content_mode(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    raw = base_v2(tmp_path)
    raw["event_mode"] = "random_plot_generator"

    result = module.validate_manifest(raw, tmp_path)

    assert any(issue.code == "INVALID_EVENT_MODE" for issue in result.errors)


def test_external_extension_without_capability_assets_is_not_green(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    raw = base_v2(tmp_path)
    raw["runtime_driver"] = "external_extension"
    raw["runtime_state"].update({
        "authority": "external_extension",
        "update_mode": "script",
        "recovery_policy": "external_checkpoint",
        "reliability": "authoritative",
    })
    raw["runtime_driver_contract"] = "missing-extension-contract.json"

    result = module.validate_manifest(raw, tmp_path)

    assert any(issue.code == "AUTHORITATIVE_EVIDENCE_REQUIRED" for issue in result.errors)
    assert any(issue.code == "CAPABILITY_MISSING" for issue in result.capability_missing)


def test_manifest_v2_rejects_authoritative_prompt_record(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    raw = base_v2(tmp_path)
    raw["runtime_state"]["reliability"] = "authoritative"

    result = module.validate_manifest(raw, tmp_path)

    assert any(issue.code == "PROMPT_RECORD_NOT_AUTHORITATIVE" for issue in result.errors)


def test_external_extension_contract_alone_is_still_capability_missing(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    raw = base_v2(tmp_path)
    extension = tmp_path / "extension-contract.json"
    extension.write_text("{}", encoding="utf-8")
    raw["runtime_driver"] = "external_extension"
    raw["runtime_driver_contract"] = extension.name
    raw["runtime_state"].update({
        "authority": "external_extension",
        "update_mode": "script",
        "recovery_policy": "external_checkpoint",
        "reliability": "authoritative",
    })

    result = module.validate_manifest(raw, tmp_path)

    assert any(issue.code == "CAPABILITY_MISSING" for issue in result.capability_missing)
    assert any("runtime_driver_assets" in issue.message for issue in result.capability_missing)
