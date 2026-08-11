from __future__ import annotations


def valid_contract():
    return {
        "schema_version": 1,
        "state_shape": {
            "revision": "integer",
            "current_stage": "stage_id",
            "facts_in_force": "string[]",
            "knowledge_boundaries": "object",
            "unresolved_threads": "string[]",
            "event_status": "enum-map",
            "transition_flags": "string[]",
            "last_major_event": "string",
            "last_update_source": "enum",
        },
        "allowed_event_status": [
            "available", "active", "executed", "rejected", "skipped", "invalidated"
        ],
        "writers": [{
            "trigger": "major_fact_changed",
            "writer": "model",
            "fields": ["facts_in_force", "knowledge_boundaries", "event_status"],
        }],
        "conflict_policy": "latest_confirmed_fact_wins",
        "recovery_policy": "greeting_baseline_plus_latest_valid_record",
        "manifest_recovery_policy": "latest_valid_record",
    }


def test_valid_runtime_state_contract_passes(load_script_module):
    module = load_script_module("audit_runtime_state_contract.py")

    result = module.audit_contract(valid_contract(), {
        "authority": "prompt_record",
        "update_mode": "model",
        "recovery_policy": "latest_valid_record",
        "reliability": "best_effort",
    })

    assert result.errors == []


def test_runtime_state_contract_requires_all_state_fields(load_script_module):
    module = load_script_module("audit_runtime_state_contract.py")
    contract = valid_contract()
    contract["state_shape"].pop("event_status")
    contract["state_shape"].pop("revision")

    result = module.audit_contract(contract, {
        "authority": "prompt_record",
        "update_mode": "model",
        "recovery_policy": "latest_valid_record",
        "reliability": "best_effort",
    })

    assert any("event_status" in error for error in result.errors)
    assert any("revision" in error for error in result.errors)


def test_runtime_state_contract_requires_complete_event_status_enum(load_script_module):
    module = load_script_module("audit_runtime_state_contract.py")
    contract = valid_contract()
    contract["allowed_event_status"] = ["available", "executed"]

    result = module.audit_contract(contract, {
        "authority": "prompt_record",
        "update_mode": "model",
        "recovery_policy": "latest_valid_record",
        "reliability": "best_effort",
    })

    assert any("rejected" in error for error in result.errors)
    assert any("invalidated" in error for error in result.errors)


def test_runtime_state_contract_requires_writer_conflict_and_recovery_policy(load_script_module):
    module = load_script_module("audit_runtime_state_contract.py")
    contract = valid_contract()
    contract.pop("writers")
    contract.pop("conflict_policy")
    contract.pop("recovery_policy")

    result = module.audit_contract(contract, {
        "authority": "prompt_record",
        "update_mode": "model",
        "recovery_policy": "latest_valid_record",
        "reliability": "best_effort",
    })

    assert any("writers" in error for error in result.errors)
    assert any("conflict_policy" in error for error in result.errors)
    assert any("recovery_policy" in error for error in result.errors)


def test_prompt_record_cannot_claim_authoritative_runtime_state(load_script_module):
    module = load_script_module("audit_runtime_state_contract.py")

    result = module.audit_contract(valid_contract(), {
        "authority": "prompt_record",
        "update_mode": "model",
        "recovery_policy": "latest_valid_record",
        "reliability": "authoritative",
    })

    assert any("prompt_record" in error and "authoritative" in error for error in result.errors)


def test_runtime_state_contract_rejects_writer_mode_mismatch(load_script_module):
    module = load_script_module("audit_runtime_state_contract.py")
    contract = valid_contract()
    contract["writers"][0]["writer"] = "script"

    result = module.audit_contract(contract, {
        "authority": "prompt_record",
        "update_mode": "model",
        "recovery_policy": "latest_valid_record",
        "reliability": "best_effort",
    })

    assert any("writer" in error and "update_mode" in error for error in result.errors)
