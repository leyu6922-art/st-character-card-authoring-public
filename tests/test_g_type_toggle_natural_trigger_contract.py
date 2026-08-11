from __future__ import annotations

import copy
import json
from pathlib import Path


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def issue_ids(report):
    return {issue.rule_id for issue in report.issues}


def load_production_fixture():
    return json.loads(
        (FIXTURES / "valid_leyu_manual_toggle.json").read_text(encoding="utf-8")
    )


def entry_template(entry_id, *, comment, content, constant, enabled, keys=None, role=None):
    source = load_production_fixture()["data"]["character_book"]["entries"][0]
    entry = copy.deepcopy(source)
    entry.update(
        {
            "id": entry_id,
            "comment": comment,
            "content": content,
            "constant": constant,
            "enabled": enabled,
            "keys": list(keys or []),
            "secondary_keys": [],
            "selective": False,
        }
    )
    if role is not None:
        entry["extensions"]["entry_role"] = role
    entry["extensions"]["display_index"] = entry_id
    return entry


def make_card(entries, *, greeting=None):
    if greeting is None:
        greeting = "南向晚站在青云村院门前。莫埃的铁棍碰了一下石阶。" * 100
    card = load_production_fixture()
    card["data"]["first_mes"] = greeting
    card["first_mes"] = greeting
    card["data"]["alternate_greetings"] = []
    card["data"]["character_book"]["entries"] = entries
    return card


def write_card(tmp_path, card, name="card.json"):
    path = tmp_path / name
    path.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    return path


def test_feature_toggle_marked_xuankai_is_not_identity(load_script_module, tmp_path):
    validator = load_script_module("validate_card.py")
    card = make_card(
        [
            entry_template(
                0,
                comment="剧情导演协议·选开功能",
                content="导演协议允许{{user}}之外的NPC主动推进事件。",
                constant=True,
                enabled=True,
                role="feature_toggle",
            )
        ]
    )
    report = validator.validate_card_report(
        str(write_card(tmp_path, card)), profile="leyu-production"
    )
    assert report.ok, [issue.render() for issue in report.issues]
    assert "MANUAL_TOGGLE_ENABLED_TRUE" not in issue_ids(report)


def test_identity_toggle_requires_disabled_and_empty_keys(load_script_module, tmp_path):
    validator = load_script_module("validate_card.py")
    card = make_card(
        [
            entry_template(
                0,
                comment="南问天身份选开",
                content="{{user}}当前扮演南问天。",
                constant=True,
                enabled=True,
                keys=["南问天"],
                role="identity_toggle",
            )
        ]
    )
    report = validator.validate_card_report(
        str(write_card(tmp_path, card)), profile="leyu-production"
    )
    ids = issue_ids(report)
    assert "G_IDENTITY_TOGGLE_SCHEMA" in ids
    assert "MANUAL_TOGGLE_ENABLED_TRUE" not in ids


def test_common_content_user_leak_is_blocked_but_system_is_allowed(load_script_module, tmp_path):
    validator = load_script_module("validate_card.py")
    card = make_card(
        [
            entry_template(
                0,
                comment="人物档案·南向晚",
                content="南向晚是剑道至尊。{{user}}可以观察南向晚。",
                constant=False,
                enabled=True,
                keys=["南向晚"],
                role="common_content",
            ),
            entry_template(
                1,
                comment="人物关系矩阵·系统常驻",
                content="{{user}}=南问天时，南向晚是南问天的母亲。",
                constant=True,
                enabled=True,
                role="system_constant",
            ),
        ]
    )
    report = validator.validate_card_report(
        str(write_card(tmp_path, card)), profile="leyu-production"
    )
    ids = issue_ids(report)
    assert "G_COMMON_CONTENT_USER_LEAK" in ids
    assert not any(
        issue.rule_id == "G_COMMON_CONTENT_USER_LEAK" and "矩阵" in issue.message
        for issue in report.issues
    )


def test_natural_event_requires_two_path_types_and_meta_only_key_is_blocked(load_script_module, tmp_path):
    validator = load_script_module("validate_card.py")
    card = make_card(
        [
            entry_template(
                0,
                comment="事件·院门冲突",
                content="莫埃来到院门，南向晚听见铁棍声并走向石阶，冲突随后升级。",
                constant=False,
                enabled=True,
                keys=["莫埃", "院门", "敲门"],
                role="common_content",
            ),
        ]
    )
    report = validator.validate_card_report(
        str(write_card(tmp_path, card)), profile="leyu-production"
    )
    assert "EVENT_NATURAL_PATH_INSUFFICIENT" not in issue_ids(report)

    card["data"]["character_book"]["entries"].append(
        entry_template(
            1,
            comment="事件·死键",
            content="这是一个独立事件，包含前提、进入、动作和后果。",
            constant=False,
            enabled=True,
            keys=["事件库", "种子库"],
            role="common_content",
        )
    )
    report = validator.validate_card_report(
        str(write_card(tmp_path, card, "meta-label.json")), profile="leyu-production"
    )
    ids = issue_ids(report)
    assert "TRIGGER_META_LABEL_ONLY" in ids



def test_infer_entry_role_legacy_entries_is_non_mutating(load_script_module):
    validator = load_script_module("validate_card.py")
    feature = entry_template(
        0,
        comment="场景边界铁律·选开功能",
        content="{{user}}不能跨越场景边界。",
        constant=True,
        enabled=True,
    )
    before = copy.deepcopy(feature)
    assert validator.infer_entry_role(feature) == "feature_toggle"
    assert feature == before


def test_neutral_greeting_dialogue_pronoun_is_not_narrative_error(load_script_module, tmp_path):
    validator = load_script_module("validate_card.py")
    card = make_card(
        [
            entry_template(
                0,
                comment="南问天身份选开",
                content="{{user}}当前扮演南问天。",
                constant=True,
                enabled=False,
                role="identity_toggle",
            )
        ],
        greeting="南向晚站在院门前。\n\n「你回来了。」南向晚看向南问天。",
    )
    report = validator.validate_card_report(
        str(write_card(tmp_path, card)), profile="leyu-production"
    )
    assert "G_NEUTRAL_GREETING_PRONOUN" not in issue_ids(report)
