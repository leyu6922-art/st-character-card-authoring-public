from __future__ import annotations


def feature_mode(entry_id: int, mode: str) -> dict:
    return {
        "id": entry_id,
        "comment": "玩家代理权功能开关",
        "content": "{{user}}相关规则。",
        "constant": True,
        "enabled": False,
        "keys": [],
        "secondary_keys": [],
        "selective": False,
        "extensions": {
            "entry_role": "feature_toggle",
            "feature_mode": mode,
        },
    }


def test_player_agency_feature_modes_are_valid_when_default_disabled(load_script_module):
    validator = load_script_module("validate_card.py")
    errors: list[str] = []
    warnings: list[str] = []

    validator._validate_g_entry_contract(
        [
            feature_mode(0, "narrative_director"),
            feature_mode(1, "player_agency_boundary"),
        ],
        errors,
        warnings,
    )

    assert not [error for error in errors if error.startswith("G_FEATURE_TOGGLE_SCHEMA")]


def test_legacy_feature_toggle_still_requires_enabled(load_script_module):
    validator = load_script_module("validate_card.py")
    errors: list[str] = []
    warnings: list[str] = []

    validator._validate_g_entry_contract(
        [feature_mode(0, "legacy_optional_feature")], errors, warnings
    )

    assert any(error.startswith("G_FEATURE_TOGGLE_SCHEMA") for error in errors)


def test_disabled_player_agency_modes_are_not_reported_as_illegal_disabled_entries(load_script_module, tmp_path):
    import json

    validator = load_script_module("validate_card.py")
    card_path = tmp_path / "card.json"
    card_path.write_text(
        json.dumps({"data": {"character_book": {"entries": [
            feature_mode(0, "narrative_director"),
            feature_mode(1, "player_agency_boundary"),
        ]}}}),
        encoding="utf-8",
    )

    _passed, errors, _warnings = validator._validate_leyu_production_legacy(str(card_path))

    assert not [error for error in errors if "非事件种子/非选开身份条目不应禁用" in error]
