from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from test_candidate_event_semantics import valid_soft_contract
from test_runtime_state_contract import valid_contract as valid_runtime_state


def make_manifest(tmp_path: Path, *, mode: str = "soft_stage", event_policy: str | None = None) -> dict:
    narrative = tmp_path / "narrative.json"
    state = tmp_path / "state.json"
    narrative.write_text(json.dumps(valid_soft_contract(), ensure_ascii=False), encoding="utf-8")
    state_contract = valid_runtime_state()
    state_contract["manifest_recovery_policy"] = "latest_valid_record"
    state.write_text(json.dumps(state_contract, ensure_ascii=False), encoding="utf-8")
    policy = event_policy or ("ordered_steps" if mode == "linear_stage" else "candidate_pool")
    transition = "step_completion" if mode == "linear_stage" else "none" if mode == "open_sandbox" else "outcome_based"
    return {
        "schema_version": 2,
        "prototype": "A",
        "routing_mode": "flat",
        "runtime_driver": "native_st",
        "narrative_mode": mode,
        "event_policy": policy,
        "transition_policy": transition,
        "narrative_contract": narrative.name if policy == "candidate_pool" else "",
        "runtime_state": {
            "authority": "prompt_record",
            "update_mode": "model",
            "contract": state.name,
            "recovery_policy": "latest_valid_record",
            "reliability": "best_effort",
        },
    }


def test_bundle_rejects_manifest_contract_mode_and_policy_mismatch(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    manifest = make_manifest(tmp_path)
    contract = valid_soft_contract()
    contract["narrative_mode"] = "open_sandbox"
    contract["event_policy"] = "none"
    contract["transition_policy"] = "none"

    result = module.validate_contract_bundle(manifest, contract, valid_runtime_state(), tmp_path)

    codes = {issue.code for issue in result.errors}
    assert "MANIFEST_NARRATIVE_MODE_MISMATCH" in codes
    assert "MANIFEST_EVENT_POLICY_MISMATCH" in codes
    assert "MANIFEST_TRANSITION_POLICY_MISMATCH" in codes


def test_linear_and_soft_require_state_authority(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    for mode in ("linear_stage", "soft_stage"):
        manifest = make_manifest(tmp_path, mode=mode)
        manifest["runtime_state"]["authority"] = "none"
        result = module.validate_manifest(manifest, tmp_path)
        assert any(issue.code == "RUNTIME_STATE_AUTHORITY_REQUIRED" for issue in result.errors)


def test_manifest_v2_prototype_is_required(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    manifest = make_manifest(tmp_path)
    manifest.pop("prototype")

    result = module.validate_manifest(manifest, tmp_path)

    assert any(issue.code == "PROTOTYPE_REQUIRED" for issue in result.errors)


def test_open_sandbox_event_policy_none_does_not_require_narrative_contract(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    manifest = make_manifest(tmp_path, mode="open_sandbox", event_policy="none")
    manifest["runtime_state"]["authority"] = "none"
    manifest["runtime_state"]["contract"] = ""
    manifest["runtime_state"]["recovery_policy"] = "greeting_baseline"

    result = module.validate_manifest(manifest, tmp_path)

    assert result.errors == []


def test_sandbox_scope_is_only_valid_for_open_sandbox(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    manifest = make_manifest(tmp_path, mode="soft_stage")
    manifest["sandbox_scope"] = "focused"

    result = module.validate_manifest(manifest, tmp_path)

    assert any(issue.code == "SANDBOX_SCOPE_NARRATIVE_MISMATCH" for issue in result.errors)


def test_sandbox_scope_must_use_supported_value(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    manifest = make_manifest(tmp_path, mode="open_sandbox", event_policy="none")
    manifest["sandbox_scope"] = "automatic"

    result = module.validate_manifest(manifest, tmp_path)

    assert any(issue.code == "INVALID_SANDBOX_SCOPE" for issue in result.errors)


def test_runtime_state_recovery_mapping_must_match_manifest(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    manifest = make_manifest(tmp_path)
    state = valid_runtime_state()
    state["manifest_recovery_policy"] = "greeting_baseline"

    result = module.validate_contract_bundle(manifest, valid_soft_contract(), state, tmp_path)

    assert any(issue.code == "RUNTIME_STATE_RECOVERY_MISMATCH" for issue in result.errors)


def test_authoritative_runtime_state_requires_verified_evidence(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    manifest = make_manifest(tmp_path)
    manifest["runtime_state"]["reliability"] = "authoritative"

    result = module.validate_manifest(manifest, tmp_path)

    assert any(issue.code == "AUTHORITATIVE_EVIDENCE_REQUIRED" for issue in result.errors)


def test_external_extension_capability_has_missing_and_declared_unverified_states(load_script_module, tmp_path):
    module = load_script_module("lib/narrative_contracts.py")
    manifest = make_manifest(tmp_path)
    manifest["runtime_driver"] = "external_extension"
    manifest["runtime_state"].update({
        "authority": "external_extension",
        "update_mode": "script",
        "recovery_policy": "external_checkpoint",
        "reliability": "best_effort",
    })
    state = valid_runtime_state()
    state["manifest_recovery_policy"] = "external_checkpoint"
    (tmp_path / "state.json").write_text(json.dumps(state), encoding="utf-8")
    manifest["runtime_driver_contract"] = "extension.json"
    manifest["runtime_driver_assets"] = ["asset.bin"]
    manifest["runtime_driver_test_fixture"] = "fixture.json"

    missing = module.validate_manifest(manifest, tmp_path)
    assert missing.capability_state == "CAPABILITY_MISSING"

    (tmp_path / "extension.json").write_text(json.dumps({"schema_version": 1, "driver": "external_extension", "capabilities": ["read_state", "write_state", "recover_state"]}), encoding="utf-8")
    (tmp_path / "asset.bin").write_bytes(b"asset")
    (tmp_path / "fixture.json").write_text(json.dumps({"status": "DECLARED", "checks": {}}), encoding="utf-8")
    declared = module.validate_manifest(manifest, tmp_path)
    assert declared.errors == []
    assert declared.capability_state == "DECLARED_UNVERIFIED"

    verified_report = {"status": "VERIFIED", "checks": {"write": True, "read": True, "recovery": True}}
    (tmp_path / "fixture.json").write_text(json.dumps(verified_report), encoding="utf-8")
    manifest["runtime_state_verification"] = {"status": "VERIFIED", "artifact": "fixture.json"}
    verified = module.validate_manifest(manifest, tmp_path)
    assert verified.errors == []
    assert verified.capability_state == "DECLARED_UNVERIFIED"
    manifest["runtime_state"]["reliability"] = "authoritative"
    authoritative = module.validate_manifest(manifest, tmp_path)
    assert any(issue.code == "AUTHORITATIVE_EVIDENCE_REQUIRED" for issue in authoritative.errors)


def test_candidate_event_rejects_malformed_types_and_unknown_state_fields(load_script_module):
    module = load_script_module("audit_candidate_event_semantics.py")
    contract = valid_soft_contract()
    event = contract["events"]["P2-E01"]
    event["entry_points"] = "not-a-list"
    event["npc_initiative"] = []
    event["state_writes"] = ["not_a_state_field"]
    event["possible_outcomes"] = ["same", "same"]
    contract["stages"]["P2"]["facts_in_force"] = ["UNKNOWN_FACT"]
    contract["transitions"]["TC1"]["requires"] = ["UNKNOWN_FACT"]

    result = module.audit_contract(contract, valid_runtime_state())

    messages = "\n".join(result.errors)
    assert "entry_points" in messages
    assert "npc_initiative" in messages
    assert "state_writes" in messages
    assert "possible_outcomes" in messages
    assert "UNKNOWN_FACT" in messages


def test_runtime_state_writer_fields_must_be_state_shape_fields(load_script_module):
    module = load_script_module("audit_runtime_state_contract.py")
    contract = valid_runtime_state()
    contract["writers"][0]["fields"] = ["unknown_state_field"]

    result = module.audit_contract(contract, {
        "authority": "prompt_record",
        "update_mode": "model",
        "recovery_policy": "latest_valid_record",
        "reliability": "best_effort",
    })

    assert any("state_shape" in error for error in result.errors)


def test_specialized_audits_reject_wrong_contract_mode(load_script_module):
    ordered = load_script_module("audit_ordered_step_contract.py")
    transition = load_script_module("audit_stage_transition_policy.py")
    candidate = load_script_module("audit_candidate_event_semantics.py")

    assert any("CONTRACT_MODE_MISMATCH" in error for error in ordered.audit_contract(valid_soft_contract()).errors)
    assert any("CONTRACT_MODE_MISMATCH" in error for error in transition.audit_contract({"narrative_mode": "linear_stage"}).errors)
    assert any("CONTRACT_MODE_MISMATCH" in error for error in candidate.audit_contract({"narrative_mode": "linear_stage"}).errors)


def test_candidate_cli_uses_shared_contract_bundle_validation(load_script_module, tmp_path):
    module = load_script_module("audit_candidate_event_semantics.py")
    manifest = make_manifest(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    contract_path = tmp_path / "narrative.json"

    assert module.main([str(contract_path), "--manifest", str(manifest_path)]) == 0

    manifest["narrative_mode"] = "open_sandbox"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert module.main([str(contract_path), "--manifest", str(manifest_path)]) == 1


def test_candidate_cli_rejects_state_writes_outside_manifest_state_shape(load_script_module, tmp_path):
    manifest = make_manifest(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    contract_path = tmp_path / "narrative.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["events"]["P2-E01"]["state_writes"] = ["not_a_state_field"]
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    script = Path(__file__).parents[1] / "scripts" / "audit_candidate_event_semantics.py"
    completed = subprocess.run(
        [sys.executable, str(script), str(contract_path), "--manifest", str(manifest_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "state_writes引用不存在的state_shape字段" in completed.stdout


def test_open_sandbox_keyword_only_card_is_rejected(load_script_module):
    module = load_script_module("audit_open_sandbox_entries.py")
    card = {
        "data": {
            "character_book": {
                "entries": [
                    {"comment": "角色入口", "content": "角色入口、场景入口、NPC主动行为；没有候选事件时世界仍可继续。", "keys": []},
                    {"comment": "系统", "content": "普通内容", "keys": []},
                    {"comment": "规则", "content": "普通内容", "keys": []},
                ]
            }
        }
    }

    result = module.audit_card(card, {"narrative_mode": "open_sandbox", "event_policy": "none"})

    assert result.errors


def structured_sandbox_card(*, character_count: int = 2, scene_count: int = 2, behavior_count: int = 2) -> dict:
    entries = []
    for role, count in ((
        ("character_entry", character_count),
        ("scene_entry", scene_count),
        ("behavior_entry", behavior_count),
    )):
        for index in range(count):
            entries.append({
                "comment": f"{role}-{index}",
                "content": "可调用的结构化入口",
                "keys": [f"自然入口{role}{index}"],
                "enabled": True,
                "constant": False,
                "selective": True,
                "extensions": {
                    "entry_role": role,
                    "sandbox_entry": True,
                    "sandbox_entry_id": f"{role}-{index}",
                    "npc_initiative": role == "behavior_entry",
                },
            })
    return {"data": {"character_book": {"entries": entries}}}


def test_open_sandbox_structural_entries_pass_without_continuation_slogan(load_script_module):
    module = load_script_module("audit_open_sandbox_entries.py")

    result = module.audit_card(structured_sandbox_card(), {"narrative_mode": "open_sandbox", "event_policy": "none"})

    assert result.errors == []
    assert result.warnings


def test_open_sandbox_focused_scope_allows_one_of_each_capability(load_script_module):
    module = load_script_module("audit_open_sandbox_entries.py")

    result = module.audit_card(
        structured_sandbox_card(character_count=1, scene_count=1, behavior_count=1),
        {
            "narrative_mode": "open_sandbox",
            "event_policy": "none",
            "sandbox_scope": "focused",
        },
    )

    assert result.errors == []


def test_open_sandbox_focused_scope_requires_each_capability(load_script_module):
    module = load_script_module("audit_open_sandbox_entries.py")
    for kwargs, expected in (
        ({"character_count": 0}, "character_entry"),
        ({"scene_count": 0}, "scene_entry"),
        ({"behavior_count": 0}, "behavior/event"),
    ):
        result = module.audit_card(
            structured_sandbox_card(**kwargs),
            {
                "narrative_mode": "open_sandbox",
                "event_policy": "none",
                "sandbox_scope": "focused",
            },
        )
        assert any(expected in error for error in result.errors)


def test_open_sandbox_ensemble_scope_keeps_two_of_each_requirement(load_script_module):
    module = load_script_module("audit_open_sandbox_entries.py")

    one_each = module.audit_card(
        structured_sandbox_card(character_count=1, scene_count=1, behavior_count=1),
        {
            "narrative_mode": "open_sandbox",
            "event_policy": "none",
            "sandbox_scope": "ensemble",
        },
    )
    two_each = module.audit_card(
        structured_sandbox_card(),
        {
            "narrative_mode": "open_sandbox",
            "event_policy": "none",
            "sandbox_scope": "ensemble",
        },
    )

    assert any("至少需要两个" in error for error in one_each.errors)
    assert two_each.errors == []


def test_open_sandbox_without_scope_preserves_legacy_two_of_each_requirement(load_script_module):
    module = load_script_module("audit_open_sandbox_entries.py")

    result = module.audit_card(
        structured_sandbox_card(character_count=1, scene_count=1, behavior_count=1),
        {"narrative_mode": "open_sandbox", "event_policy": "none"},
    )

    assert any("至少需要两个" in error for error in result.errors)


def test_open_sandbox_rejects_root_level_build_metadata(load_script_module):
    module = load_script_module("audit_open_sandbox_entries.py")
    card = structured_sandbox_card()
    for entry in card["data"]["character_book"]["entries"]:
        extensions = entry.pop("extensions")
        entry.update(extensions)

    result = module.audit_card(card, {"narrative_mode": "open_sandbox", "event_policy": "none"})

    assert result.errors
    assert all("非法" not in error for error in result.errors)


def test_open_sandbox_constant_entry_does_not_count_as_callable(load_script_module):
    module = load_script_module("audit_open_sandbox_entries.py")
    card = structured_sandbox_card()
    card["data"]["character_book"]["entries"][0]["constant"] = True

    result = module.audit_card(card, {"narrative_mode": "open_sandbox", "event_policy": "none"})

    assert any("character_entry" in error for error in result.errors)


def test_open_sandbox_non_selective_entry_does_not_count_as_callable(load_script_module):
    module = load_script_module("audit_open_sandbox_entries.py")
    card = structured_sandbox_card()
    card["data"]["character_book"]["entries"][0]["selective"] = False

    result = module.audit_card(card, {"narrative_mode": "open_sandbox", "event_policy": "none"})

    assert any("character_entry" in error for error in result.errors)


def test_open_sandbox_duplicate_keys_and_entry_ids_do_not_count_as_independent(load_script_module):
    module = load_script_module("audit_open_sandbox_entries.py")
    card = structured_sandbox_card()
    character_entries = card["data"]["character_book"]["entries"][:2]
    character_entries[1]["keys"] = list(character_entries[0]["keys"])
    character_entries[1]["extensions"]["sandbox_entry_id"] = character_entries[0]["extensions"]["sandbox_entry_id"]

    result = module.audit_card(card, {"narrative_mode": "open_sandbox", "event_policy": "none"})

    messages = "\n".join(result.errors)
    assert "character_entry" in messages
    assert "重复" in messages


def test_freeplay_result_contains_structured_pass_fail_scenarios(load_script_module):
    module = load_script_module("simulate_freeplay_paths.py")
    result = module.simulate_paths(valid_soft_contract())

    assert result["passed"] is True
    assert result["ok"] is True
    assert result["failures"] == []
    assert result["scenarios"]
    assert all(
        set(("stage", "event", "path", "passed", "error")).issubset(scenario)
        for scenario in result["scenarios"]
    )


def test_freeplay_failure_contains_stage_event_path_and_error(load_script_module):
    module = load_script_module("simulate_freeplay_paths.py")
    contract = valid_soft_contract()
    contract["events"]["P9-E01"] = {"stage": "P9"}

    result = module.simulate_paths(contract)

    assert result["passed"] is False
    assert any(
        failure["stage"] == "P9"
        and failure["event"] == "P9-E01"
        and failure["path"] == "contract"
        and failure["error"]
        for failure in result["failures"]
    )


def test_freeplay_simulation_covers_all_events_and_checks_transitions(load_script_module):
    module = load_script_module("simulate_freeplay_paths.py")
    contract = valid_soft_contract()
    contract["events"]["P2-E02"] = dict(contract["events"]["P2-E01"], stage="P2")
    contract["stages"]["P2"]["candidate_events"].append("P2-E02")

    result = module.simulate_paths(contract)

    assert result["ok"] is True
    assert set(result["event_paths"]) == {"P2-E01", "P2-E02"}
    assert result["transition"]["current_stage"] == "P3"
    assert result["checks"]
