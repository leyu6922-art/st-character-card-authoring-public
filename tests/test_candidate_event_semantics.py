from __future__ import annotations


def valid_soft_contract():
    return {
        "schema_version": 1,
        "narrative_mode": "soft_stage",
        "event_policy": "candidate_pool",
        "transition_policy": "outcome_based",
        "facts": {"F1": {"statement": "当前已确认事实"}, "F2": {"statement": "后续事实"}},
        "stages": {
            "P2": {
                "facts_in_force": ["F1"],
                "knowledge_boundaries": {"角色A": ["F1"]},
                "unresolved_threads": ["T1"],
                "candidate_events": ["P2-E01"],
                "transition_conditions": ["TC1"],
                "forbidden_future_facts": ["F2"],
            },
            "P3": {
                "terminal": True,
                "facts_in_force": ["F2"],
                "knowledge_boundaries": {"角色A": ["F1", "F2"]},
                "unresolved_threads": [],
                "candidate_events": [],
                "transition_conditions": [],
                "forbidden_future_facts": [],
            },
        },
        "events": {
            "P2-E01": {
                "stage": "P2",
                "prerequisites": ["F1"],
                "entry_points": ["地点入口"],
                "npc_initiative": ["NPC主动观察"],
                "player_interruptible": True,
                "auto_fact": False,
                "possible_outcomes": ["O1", "O2"],
                "invalidated_by": ["F2"],
                "state_writes": ["facts_in_force", "event_status"],
                "source_evidence": ["source-note-1"],
            }
        },
        "transitions": {
            "TC1": {"from": "P2", "to": "P3", "requires": ["F2"], "requires_any": [], "blocked_by": [], "irreversible": True}
        },
    }


def valid_open_sandbox_candidate_contract():
    return {
        "schema_version": 1,
        "narrative_mode": "open_sandbox",
        "event_policy": "candidate_pool",
        "transition_policy": "none",
        "facts": {},
        "events": {
            "HOME-A": {
                "prerequisites": [],
                "entry_points": ["home"],
                "npc_initiative": ["NPC自主观察"],
                "player_interruptible": True,
                "auto_fact": False,
                "possible_outcomes": ["continue", "pause"],
                "invalidated_by": [],
                "state_writes": ["facts_in_force"],
                "source_evidence": ["source-note-home"],
                "scopes": ["location:home", "character:A"],
            }
        },
    }


def test_candidate_event_requires_all_semantic_fields(load_script_module):
    module = load_script_module("audit_candidate_event_semantics.py")
    contract = valid_soft_contract()
    event = contract["events"]["P2-E01"]
    event.pop("invalidated_by")
    event.pop("possible_outcomes")

    result = module.audit_contract(contract)

    assert any("invalidated_by" in error for error in result.errors)
    assert any("possible_outcomes" in error for error in result.errors)


def test_candidate_event_requires_multiple_outcomes_and_interruptibility(load_script_module):
    module = load_script_module("audit_candidate_event_semantics.py")
    contract = valid_soft_contract()
    event = contract["events"]["P2-E01"]
    event["possible_outcomes"] = ["O1"]
    event["player_interruptible"] = False

    result = module.audit_contract(contract)

    assert any("至少两个" in error for error in result.errors)
    assert any("player_interruptible" in error for error in result.errors)


def test_valid_candidate_event_contract_passes(load_script_module):
    module = load_script_module("audit_candidate_event_semantics.py")

    result = module.audit_contract(valid_soft_contract())

    assert result.errors == []


def test_candidate_event_must_not_auto_fact(load_script_module):
    module = load_script_module("audit_candidate_event_semantics.py")
    contract = valid_soft_contract()
    contract["events"]["P2-E01"]["auto_fact"] = True

    result = module.audit_contract(contract)

    assert any("auto_fact" in error for error in result.errors)


def test_terminal_soft_stage_without_candidate_events_is_allowed(load_script_module):
    module = load_script_module("audit_candidate_event_semantics.py")
    contract = valid_soft_contract()
    contract["stages"]["P3"] = {
        "terminal": True,
        "facts_in_force": ["F2"],
        "knowledge_boundaries": {"角色A": ["F1", "F2"]},
        "unresolved_threads": [],
        "candidate_events": [],
        "transition_conditions": [],
        "forbidden_future_facts": [],
    }

    result = module.audit_contract(contract)

    assert result.errors == []


def test_open_sandbox_candidate_pool_allows_events_without_stages_or_event_stage(load_script_module):
    module = load_script_module("audit_candidate_event_semantics.py")

    result = module.audit_contract(valid_open_sandbox_candidate_contract())

    assert result.errors == []


def test_open_sandbox_candidate_pool_rejects_hidden_transitions(load_script_module):
    module = load_script_module("audit_candidate_event_semantics.py")
    contract = valid_open_sandbox_candidate_contract()
    contract["transitions"] = {"T1": {"from": "home", "to": "away"}}

    result = module.audit_contract(contract)

    assert any("open_sandbox" in error and "transitions" in error for error in result.errors)


def valid_open_situation_seed_contract():
    return {
        "schema_version": 1,
        "narrative_mode": "open_sandbox",
        "event_mode": "open_situation_seed",
        "event_policy": "candidate_pool",
        "transition_policy": "none",
        "facts": {},
        "events": {
            "HOME-SEED": {
                "entry_points": ["门口的脚步声", "未读消息"],
                "npc_initiative": ["NPC可能观察环境或改变说话方式"],
                "player_interruptible": True,
                "auto_fact": False,
                "source_evidence": ["source-note-home"],
                "open_directions": ["调查", "保护", "忽略", "谈判或改写关系"],
                "not_fixed": ["触发时间", "具体动机", "发展顺序", "台词", "结果", "阶段转移"],
            }
        },
    }


def test_open_situation_seed_does_not_require_fixed_outcomes_or_state_writes(load_script_module):
    module = load_script_module("audit_candidate_event_semantics.py")

    result = module.audit_contract(valid_open_situation_seed_contract())

    assert result.errors == []


def test_open_situation_seed_rejects_hidden_fixed_chain_fields(load_script_module):
    module = load_script_module("audit_candidate_event_semantics.py")
    forbidden_fields = (
        "next",
        "ordered_steps",
        "requires_all_events",
        "fixed_outcome",
        "route_lock",
        "stage_transition",
        "mandatory",
        "completion_required",
    )

    for field_name in forbidden_fields:
        contract = valid_open_situation_seed_contract()
        contract["events"]["HOME-SEED"][field_name] = False

        result = module.audit_contract(contract)

        assert any(field_name in error for error in result.errors), field_name


def test_open_situation_seed_requires_explicit_not_fixed_boundary(load_script_module):
    module = load_script_module("audit_candidate_event_semantics.py")
    contract = valid_open_situation_seed_contract()
    contract["events"]["HOME-SEED"].pop("not_fixed")

    result = module.audit_contract(contract)

    assert any("not_fixed" in error for error in result.errors)


def test_open_situation_seed_cannot_write_facts_before_event_occurs(load_script_module):
    module = load_script_module("audit_candidate_event_semantics.py")
    contract = valid_open_situation_seed_contract()
    contract["events"]["HOME-SEED"]["state_writes"] = ["facts_in_force"]

    result = module.audit_contract(contract)

    assert any("state_writes" in error for error in result.errors)
