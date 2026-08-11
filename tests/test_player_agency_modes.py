from __future__ import annotations


def mode_entry(
    mode: str,
    *,
    enabled: bool | None = None,
    content: str = "",
    entry_role: str | None = None,
    enforcement: str | None = None,
) -> dict:
    if enabled is None:
        enabled = mode == "player_agency_boundary"
    if entry_role is None:
        entry_role = "system_constant" if mode == "player_agency_boundary" else "feature_toggle"
    return {
        "id": 0 if mode == "narrative_director" else 1,
        "comment": "自动推进剧情" if mode == "narrative_director" else "玩家行动边界与场景悬停",
        "content": content,
        "constant": True,
        "enabled": enabled,
        "keys": [],
        "secondary_keys": [],
        "selective": False,
        "position": "before_char",
        "extensions": {
            "entry_role": entry_role,
            "feature_mode": mode,
            **({"enforcement": enforcement} if enforcement is not None else ({"enforcement": "always_on"} if mode == "player_agency_boundary" else {})),
            "position": 0,
            "depth": 4,
            "ignore_budget": True,
            "exclude_recursion": True,
        },
    }


def legacy_disabled_boundary() -> dict:
    entry = mode_entry(
        "player_agency_boundary",
        enabled=False,
        content=BOUNDARY,
        entry_role="feature_toggle",
        enforcement="legacy",
    )
    entry["extensions"].pop("enforcement")
    return entry


DIRECTOR = """
【自动推进剧情】NPC、环境和候选事件可以主动引入变化；每次只展开一个主要事件。
不得替{{user}}说话、思考、选择、移动或完成关键行动。若玩家行动边界与场景悬停已启用，后者优先。
"""

BOUNDARY = """
【玩家行动边界与场景悬停】本条优先于自动推进剧情。AI不得替{{user}}说话或生成台词，不得替{{user}}思考或写内心，
不得替{{user}}决定、选择、同意或拒绝，不得替{{user}}移动、进入或离开场景，不得替{{user}}使用物品、接受邀约或完成调查，
不得替{{user}}结束当前互动、跨越时间或切换阶段，不得把{{user}}尚未观察或获知的事实写进{{user}}记忆、判断或台词。
每次回复停在NPC动作、环境变化或问题刚出现的接管点，等待{{user}}回应。
"""


def test_required_policy_rejects_card_without_both_modes(load_script_module):
    audit = load_script_module("audit_player_agency_modes.py")
    result = audit.audit_entries([], require_modes=True)
    assert "PLAYER_AGENCY_MODES_MISSING" in result.rule_ids


def test_recognized_modes_must_be_disabled_and_have_high_priority(load_script_module):
    audit = load_script_module("audit_player_agency_modes.py")
    director = mode_entry("narrative_director", enabled=True, content=DIRECTOR)
    director["extensions"]["depth"] = 2
    result = audit.audit_entries([director, mode_entry("player_agency_boundary", content=BOUNDARY)])
    assert "PLAYER_AGENCY_MODE_DEFAULT_ENABLED" in result.rule_ids
    assert "PLAYER_AGENCY_MODE_PRIORITY_INVALID" in result.rule_ids


def test_boundary_mode_requires_strong_player_agency_coverage(load_script_module):
    audit = load_script_module("audit_player_agency_modes.py")
    weak = "不得替{{user}}做决定，也不要离开场景。"
    result = audit.audit_entries([
        mode_entry("narrative_director", content=DIRECTOR),
        mode_entry("player_agency_boundary", content=weak),
    ])
    assert "PLAYER_AGENCY_BOUNDARY_COVERAGE_THIN" in result.rule_ids


def test_complete_manual_dual_modes_pass(load_script_module):
    audit = load_script_module("audit_player_agency_modes.py")
    result = audit.audit_entries([
        mode_entry("narrative_director", content=DIRECTOR),
        mode_entry("player_agency_boundary", content=BOUNDARY),
    ], require_modes=True)
    assert result.ok, result.errors


def test_unrelated_feature_toggle_does_not_trigger_dual_mode_contract(load_script_module):
    audit = load_script_module("audit_player_agency_modes.py")
    unrelated = mode_entry("other_feature", enabled=True, content="这是遗留功能开关。")
    result = audit.audit_entries([unrelated])
    assert result.ok, result.errors


def test_player_led_boundary_can_be_required_without_director_mode(load_script_module):
    audit = load_script_module("audit_player_agency_modes.py")

    missing = audit.audit_entries([], require_boundary=True)
    assert "PLAYER_AGENCY_MODES_MISSING" in missing.rule_ids

    result = audit.audit_entries(
        [mode_entry("player_agency_boundary", content=BOUNDARY)],
        require_boundary=True,
    )
    assert result.ok, result.errors


def test_player_led_boundary_cannot_be_disabled(load_script_module):
    audit = load_script_module("audit_player_agency_modes.py")
    disabled = mode_entry("player_agency_boundary", enabled=False, content=BOUNDARY)

    result = audit.audit_entries(
        [disabled],
        require_boundary=True,
        require_boundary_always_on=True,
    )

    assert "PLAYER_AGENCY_BOUNDARY_NOT_ALWAYS_ON" in result.rule_ids


def test_player_led_boundary_requires_system_constant_always_on_contract(load_script_module):
    audit = load_script_module("audit_player_agency_modes.py")
    wrong_role = mode_entry(
        "player_agency_boundary",
        enabled=False,
        content=BOUNDARY,
        entry_role="feature_toggle",
        enforcement="manual",
    )

    result = audit.audit_entries(
        [wrong_role],
        require_boundary=True,
        require_boundary_always_on=True,
    )

    assert "PLAYER_AGENCY_BOUNDARY_NOT_ALWAYS_ON" in result.rule_ids


def test_guided_route_accepts_legacy_disabled_boundary(load_script_module):
    audit = load_script_module("audit_player_agency_modes.py")

    result = audit.audit_entries([legacy_disabled_boundary()])

    assert result.ok, result.errors


def test_legacy_unspecified_route_accepts_legacy_disabled_boundary(load_script_module):
    audit = load_script_module("audit_player_agency_modes.py")

    result = audit.audit_entries(
        [
            mode_entry("narrative_director", content=DIRECTOR),
            legacy_disabled_boundary(),
        ],
        require_modes=True,
    )

    assert result.ok, result.errors


def test_player_led_requires_always_on_boundary_explicitly(load_script_module):
    audit = load_script_module("audit_player_agency_modes.py")

    disabled = audit.audit_entries(
        [legacy_disabled_boundary()],
        require_boundary=True,
        require_boundary_always_on=True,
    )
    enabled = audit.audit_entries(
        [mode_entry("player_agency_boundary", content=BOUNDARY)],
        require_boundary=True,
        require_boundary_always_on=True,
    )

    assert "PLAYER_AGENCY_BOUNDARY_NOT_ALWAYS_ON" in disabled.rule_ids
    assert enabled.ok, enabled.errors
