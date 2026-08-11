from __future__ import annotations


def event_entry(entry_id: int, keys: list[str], comment: str = "事件种子·走廊偶遇") -> dict:
    return {
        "id": entry_id,
        "comment": comment,
        "content": "候选事件。",
        "constant": False,
        "enabled": True,
        "keys": keys,
        "secondary_keys": [],
        "selective": True,
        "extensions": {"entry_role": "common_content"},
    }


def identity_entry(content: str) -> dict:
    return {
        "id": 1,
        "comment": "选开·指挥官身份",
        "content": content,
        "constant": True,
        "enabled": False,
        "keys": [],
        "secondary_keys": [],
        "selective": False,
        "extensions": {"entry_role": "identity_toggle"},
    }


def test_non_stage_event_seed_requires_three_distinct_natural_primary_keys(load_script_module):
    validator = load_script_module("validate_card.py")

    errors = validator._event_seed_key_errors([event_entry(1, ["走廊", "门锁"])])

    assert any(error.startswith("EVENT_SEED_KEY_COUNT") for error in errors)


def test_stage_routed_event_seed_is_exempt_from_three_key_rule(load_script_module):
    validator = load_script_module("validate_card.py")
    stage = event_entry(1, ["【开场：P2·雨夜走廊｜港区】"], "事件库_P2")

    assert validator._event_seed_key_errors([stage]) == []


def test_identity_toggle_rejects_raw_you_outside_dialogue(load_script_module):
    validator = load_script_module("validate_card.py")
    errors: list[str] = []
    warnings: list[str] = []

    validator._validate_g_entry_contract(
        [identity_entry("{{user}}扮演指挥官。你掌握港区权限。")], errors, warnings
    )

    assert any(error.startswith("G_IDENTITY_TOGGLE_RAW_YOU") for error in errors)


def test_dialogue_corpus_requires_speaker_to_recipient_label(load_script_module):
    checker = load_script_module("enrichment_self_check.py")

    assert checker.corpus_quote_mapping_violations("【林娜→指挥官·甲板】「我知道了。」") == []
    assert checker.corpus_quote_mapping_violations("【甲板】「我知道了。」") == ["我知道了。"]


def test_profile_fields_need_substantive_card_description(load_script_module):
    checker = load_script_module("enrichment_self_check.py")
    issues = checker.profile_field_issues({"description": "标签", "personality": "冷静", "scenario": "港区"})

    assert len(issues) == 3
    assert all("需≥" in issue for issue in issues)


def test_profile_context_contract_requires_world_and_player_ai_boundaries(load_script_module):
    checker = load_script_module("enrichment_self_check.py")
    bare = {
        "description": "这是足够长的角色说明。" * 30,
        "personality": "这是足够长的人格说明。" * 30,
        "scenario": "这是足够长的场景说明。" * 30,
        "system_prompt": "继续叙事。",
    }
    complete = {
        "description": "港区世界观中，各阵营围绕港口与舰队展开冲突。" * 12,
        "personality": "核心人物各自有明确的欲望、关系与语言差异。" * 12,
        "scenario": "{{user}}由玩家扮演；玩家可以决定当前行动与关系走向。" * 12,
        "system_prompt": "AI只扮演NPC、旁白与环境，不代写{{user}}的说话、思考、行动或跨场景决定。",
    }

    bare_issues = checker.profile_context_issues(bare)
    assert any("世界/舞台" in issue for issue in bare_issues)
    assert any("{{user}}" in issue for issue in bare_issues)
    assert any("AI/NPC" in issue for issue in bare_issues)
    assert checker.profile_context_issues(complete) == []
