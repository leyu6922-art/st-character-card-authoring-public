from __future__ import annotations

import json
from pathlib import Path

from test_candidate_event_semantics import (
    valid_open_sandbox_candidate_contract,
    valid_open_situation_seed_contract,
    valid_soft_contract,
)
from test_narrative_contract_hardening import structured_sandbox_card
from test_player_agency_modes import BOUNDARY, mode_entry
from test_narrative_contracts import base_v2
from test_runtime_state_contract import valid_contract as valid_runtime_state


def write_soft_project(tmp_path: Path):
    card = tmp_path / "card.json"
    card.write_text(json.dumps({"data": {"character_book": {"entries": []}}}, ensure_ascii=False), encoding="utf-8")
    narrative = tmp_path / "narrative.json"
    narrative.write_text(json.dumps(valid_soft_contract(), ensure_ascii=False), encoding="utf-8")
    state = tmp_path / "state.json"
    state.write_text(json.dumps(valid_runtime_state(), ensure_ascii=False), encoding="utf-8")
    manifest = base_v2(tmp_path)
    manifest.update({
        "routing_mode": "flat",
        "narrative_contract": narrative.name,
        "runtime_state": {
            "authority": "prompt_record",
            "update_mode": "model",
            "contract": state.name,
            "recovery_policy": "latest_valid_record",
            "reliability": "best_effort",
        },
    })
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return card, manifest_path, manifest


def write_open_candidate_project(tmp_path: Path):
    card = tmp_path / "card.json"
    card.write_text(json.dumps(structured_sandbox_card(), ensure_ascii=False), encoding="utf-8")
    narrative = tmp_path / "narrative.json"
    narrative.write_text(json.dumps(valid_open_sandbox_candidate_contract(), ensure_ascii=False), encoding="utf-8")
    manifest = base_v2(tmp_path, mode="open_sandbox")
    manifest.update({
        "routing_mode": "flat",
        "sandbox_scope": "ensemble",
        "narrative_contract": narrative.name,
        "runtime_state": {
            "authority": "none",
            "update_mode": "manual",
            "contract": "",
            "recovery_policy": "greeting_baseline",
            "reliability": "best_effort",
        },
    })
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return card, manifest_path, manifest


def write_open_situation_project(tmp_path: Path):
    card = tmp_path / "card.json"
    card_data = structured_sandbox_card()
    card_data["data"]["character_book"]["entries"].append(
        mode_entry("player_agency_boundary", content=BOUNDARY)
    )
    card.write_text(json.dumps(card_data, ensure_ascii=False), encoding="utf-8")
    narrative = tmp_path / "narrative.json"
    narrative.write_text(json.dumps(valid_open_situation_seed_contract(), ensure_ascii=False), encoding="utf-8")
    manifest = base_v2(tmp_path, mode="open_sandbox")
    manifest.update({
        "routing_mode": "flat",
        "event_mode": "open_situation_seed",
        "route_policy": "player_led",
        "corpus_mode": "curated_anchor_set",
        "sandbox_scope": "ensemble",
        "narrative_contract": narrative.name,
        "runtime_state": {
            "authority": "none",
            "update_mode": "manual",
            "contract": "",
            "recovery_policy": "greeting_baseline",
            "reliability": "best_effort",
        },
    })
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return card, manifest_path, manifest


def test_v1_plan_has_no_v2_narrative_checks(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card = tmp_path / "card.json"
    card.write_text("{}", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "prototype": "A",
        "routing_mode": "flat",
        "greeting_mode": "player_prose",
    }), encoding="utf-8")

    plan = module.build_delivery_plan(card, manifest)

    assert plan.narrative_mode == "legacy_unspecified"
    assert all("narrative" not in check.name for check in plan.checks)


def test_v2_soft_stage_missing_narrative_contract_fails_runner(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card = tmp_path / "card.json"
    card.write_text("{}", encoding="utf-8")
    manifest = base_v2(tmp_path)
    manifest.pop("narrative_contract")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    try:
        module.load_delivery_manifest(manifest_path)
    except ValueError as exc:
        assert "NARRATIVE_CONTRACT_REQUIRED" in str(exc)
    else:
        raise AssertionError("missing narrative contract unexpectedly passed")


def test_v2_soft_stage_missing_runtime_state_contract_fails_runner(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    manifest = base_v2(tmp_path)
    manifest["runtime_state"].pop("contract")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    try:
        module.load_delivery_manifest(manifest_path)
    except ValueError as exc:
        assert "RUNTIME_STATE_CONTRACT_REQUIRED" in str(exc)
    else:
        raise AssertionError("missing runtime state contract unexpectedly passed")


def test_external_extension_is_capability_missing_not_green(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card, manifest_path, manifest = write_soft_project(tmp_path)
    manifest["runtime_driver"] = "external_extension"
    manifest["runtime_driver_contract"] = "missing-extension.json"
    manifest["runtime_state"].update({
        "authority": "external_extension",
        "update_mode": "script",
        "recovery_policy": "external_checkpoint",
        "reliability": "best_effort",
    })
    state_path = manifest_path.parent / "state.json"
    state_contract = json.loads(state_path.read_text(encoding="utf-8"))
    state_contract["manifest_recovery_policy"] = "external_checkpoint"
    state_path.write_text(json.dumps(state_contract, ensure_ascii=False), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    plan = module.build_delivery_plan(card, manifest_path)

    assert any(check.status == "CAPABILITY_MISSING" for check in plan.checks)
    report = module.run_narrative_audits(card, manifest_path)
    assert report.capability_missing


def test_external_extension_dry_run_returns_capability_missing_status(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card, manifest_path, manifest = write_soft_project(tmp_path)
    manifest["runtime_driver"] = "external_extension"
    manifest["runtime_driver_contract"] = "missing-extension.json"
    manifest["runtime_state"].update({
        "authority": "external_extension",
        "update_mode": "script",
        "recovery_policy": "external_checkpoint",
        "reliability": "best_effort",
    })
    state_path = manifest_path.parent / "state.json"
    state_contract = json.loads(state_path.read_text(encoding="utf-8"))
    state_contract["manifest_recovery_policy"] = "external_checkpoint"
    state_path.write_text(json.dumps(state_contract, ensure_ascii=False), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert module.main([str(card), "--manifest", str(manifest_path), "--dry-run"]) == 2


def test_soft_stage_runner_executes_only_soft_audits(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card, manifest_path, _manifest = write_soft_project(tmp_path)

    plan = module.build_delivery_plan(card, manifest_path)
    report = module.run_narrative_audits(card, manifest_path)

    assert plan.narrative_mode == "soft_stage"
    assert report.errors == []
    names = {check.name: check.status for check in plan.checks}
    assert names["candidate-event audit"] == "RUN"
    assert names["transition-policy audit"] == "RUN"
    assert names["freeplay path simulation"] == "RUN"
    assert names["ordered-step audit"] == "SKIP"
    assert names["open-sandbox audit"] == "SKIP"


def test_open_sandbox_candidate_pool_without_stages_passes_runner(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card, manifest_path, _manifest = write_open_candidate_project(tmp_path)

    report = module.run_narrative_audits(card, manifest_path)

    assert report.errors == []


def test_soft_stage_runner_skips_freeplay_after_candidate_audit_failure(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card, manifest_path, manifest = write_soft_project(tmp_path)
    narrative_path = manifest_path.parent / manifest["narrative_contract"]
    contract = json.loads(narrative_path.read_text(encoding="utf-8"))
    contract["events"]["P9-E01"] = {"stage": "P9"}
    narrative_path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")

    report = module.run_narrative_audits(card, manifest_path)

    assert any("events.P9-E01" in error for error in report.errors)
    assert not any("freeplay path simulation" in error for error in report.errors)


def test_soft_stage_malformed_stages_returns_controlled_narrative_error(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card, manifest_path, manifest = write_soft_project(tmp_path)
    narrative_path = manifest_path.parent / manifest["narrative_contract"]
    contract = json.loads(narrative_path.read_text(encoding="utf-8"))
    contract["stages"] = ["malformed"]
    narrative_path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")

    report = module.run_narrative_audits(card, manifest_path)

    assert report.errors
    assert any("stages" in error for error in report.errors)


def test_open_situation_runner_skips_transition_and_path_simulation(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card, manifest_path, _manifest = write_open_situation_project(tmp_path)

    plan = module.build_delivery_plan(card, manifest_path)
    report = module.run_narrative_audits(card, manifest_path)

    assert report.errors == []
    names = {check.name: (check.status, check.reason) for check in plan.checks}
    assert names["candidate-event audit"][0] == "RUN"
    assert names["transition-policy audit"][0] == "SKIP"
    assert names["freeplay path simulation"][0] == "SKIP"
    assert names["player agency boundary"] == ("RUN", "route_policy=player_led")
    assert "--require-player-boundary" in plan.argv


def test_soft_stage_simulation_exception_is_controlled(load_script_module, tmp_path):
    module = load_script_module("run_delivery.py")
    card, manifest_path, _manifest = write_soft_project(tmp_path)

    def raise_simulation(_contract):
        raise AttributeError("malformed simulation fixture")

    module.simulate_paths = raise_simulation
    report = module.run_narrative_audits(card, manifest_path)

    assert any("freeplay path simulation could not run" in error for error in report.errors)
