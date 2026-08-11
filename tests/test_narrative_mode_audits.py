from __future__ import annotations

import pytest

from copy import deepcopy

from test_candidate_event_semantics import valid_soft_contract
from test_narrative_contract_hardening import structured_sandbox_card


def linear_contract():
    return {
        "schema_version": 1,
        "narrative_mode": "linear_stage",
        "event_policy": "ordered_steps",
        "transition_policy": "step_completion",
        "steps": [
            {"step_id": "S1", "next": "S2"},
            {"step_id": "S2", "next": "S3"},
            {"step_id": "S3", "next": None},
        ],
    }


def test_linear_stage_allows_ordered_steps(load_script_module):
    module = load_script_module("audit_ordered_step_contract.py")

    result = module.audit_contract(linear_contract())

    assert result.errors == []


def test_linear_stage_rejects_unreachable_or_duplicate_step(load_script_module):
    module = load_script_module("audit_ordered_step_contract.py")
    contract = linear_contract()
    contract["steps"].append({"step_id": "S2", "next": None})

    result = module.audit_contract(contract)

    assert any("重复" in error for error in result.errors)


def test_linear_stage_reports_dangling_next_without_crashing(load_script_module):
    module = load_script_module("audit_ordered_step_contract.py")
    contract = linear_contract()
    contract["steps"][0]["next"] = "UNKNOWN"

    result = module.audit_contract(contract)

    assert any("next未定义" in error for error in result.errors)


def test_soft_stage_rejects_fixed_chain_without_bypass_semantics(load_script_module):
    module = load_script_module("audit_stage_transition_policy.py")
    contract = valid_soft_contract()
    contract["events"]["P2-E01"]["player_interruptible"] = False
    contract["events"]["P2-E01"]["possible_outcomes"] = ["唯一结果"]
    contract["stages"]["P2"]["candidate_events"] = ["P2-E01"]

    result = module.audit_contract(contract)

    assert any("可绕行" in error or "候选" in error for error in result.errors)


def test_soft_stage_rejects_transition_without_irreversible_outcome(load_script_module):
    module = load_script_module("audit_stage_transition_policy.py")
    contract = valid_soft_contract()
    contract["transitions"]["TC1"].pop("irreversible")

    result = module.audit_contract(contract)

    assert any("irreversible" in error for error in result.errors)


def test_open_sandbox_does_not_require_transition_conditions(load_script_module):
    module = load_script_module("audit_open_sandbox_entries.py")

    result = module.audit_card(structured_sandbox_card(), {"narrative_mode": "open_sandbox", "event_policy": "none"})

    assert result.errors == []


def test_open_sandbox_requires_world_continuation_and_npc_initiative(load_script_module):
    module = load_script_module("audit_open_sandbox_entries.py")
    card = {
        "data": {
            "character_book": {"entries": [
                {"comment": "角色A", "content": "角色档案", "keys": ["角色A"]},
                {"comment": "场景·客厅", "content": "场景入口", "keys": ["客厅"]},
                {"comment": "事件候选", "content": "可绕开的候选事件", "keys": ["敲门"]},
            ]}
        }
    }

    result = module.audit_card(card, {"narrative_mode": "open_sandbox"})

    assert any("character_entry" in error for error in result.errors)
    assert any("npc_initiative" in error for error in result.errors)


def test_simulator_distinguishes_skip_reject_invalidate_and_transition(load_script_module):
    module = load_script_module("simulate_freeplay_paths.py")
    contract = valid_soft_contract()

    result = module.simulate_paths(contract)

    assert result["normal"]["event_status"]["P2-E01"] == "executed"
    assert result["skip"]["event_status"]["P2-E01"] == "skipped"
    assert result["reject"]["event_status"]["P2-E01"] == "rejected"
    assert result["invalidate"]["event_status"]["P2-E01"] == "invalidated"
    assert result["transition"]["current_stage"] == "P3"


def test_invalidated_event_cannot_be_executed_again(load_script_module):
    module = load_script_module("simulate_freeplay_paths.py")
    contract = valid_soft_contract()
    state = module.initial_state(contract)

    module.apply_event_status(state, "P2-E01", "invalidated")

    with pytest.raises(ValueError, match="terminal event"):
        module.apply_event_status(state, "P2-E01", "executed")


def test_transition_policy_rejects_unknown_stage_reference(load_script_module):
    module = load_script_module("audit_stage_transition_policy.py")
    contract = valid_soft_contract()
    contract["transitions"]["TC1"]["to"] = "UNKNOWN"

    result = module.audit_contract(contract)

    assert any("未声明阶段" in error for error in result.errors)


def test_blocked_transition_does_not_fire(load_script_module):
    module = load_script_module("simulate_freeplay_paths.py")
    contract = valid_soft_contract()
    contract["transitions"]["TC1"]["blocked_by"] = ["F_BLOCK"]
    contract["stages"]["P2"]["facts_in_force"].append("F_BLOCK")

    result = module.simulate_paths(contract)

    assert result["transition"]["current_stage"] == "P2"
