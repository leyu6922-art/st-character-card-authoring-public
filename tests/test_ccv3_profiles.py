from __future__ import annotations

import copy
import json
from pathlib import Path


def issue_ids(report):
    return {issue.rule_id for issue in report.issues}


def test_ccv3_core_accepts_standard_data_without_mirrors(load_script_module):
    validator = load_script_module("validate_card.py")
    report = validator.validate_card_report(
        "tests/fixtures/valid_ccv3_core_minimal.json", profile="ccv3-core"
    )

    assert report.ok
    assert issue_ids(report) == set()


def test_ccv3_core_requires_every_standard_data_field(load_script_module):
    validator = load_script_module("validate_card.py")
    report = validator.validate_card_report(
        "tests/fixtures/invalid_ccv3_missing_data_field.json", profile="ccv3-core"
    )

    assert not report.ok
    assert "CCV3_REQUIRED_DATA_FIELD_MISSING" in issue_ids(report)
    assert any(issue.path == "data.creator_notes" for issue in report.issues)


def test_leyu_manual_toggle_contract_is_machine_readable(load_script_module, tmp_path):
    validator = load_script_module("validate_card.py")
    source = json.loads(
        (Path(__file__).resolve().parent / "fixtures" / "valid_leyu_manual_toggle.json").read_text(encoding="utf-8")
    )

    valid_path = tmp_path / "valid.json"
    valid_path.write_text(json.dumps(source), encoding="utf-8")
    valid_report = validator.validate_card_report(str(valid_path), profile="leyu-production")
    assert valid_report.ok
    assert "MANUAL_TOGGLE_KEYS_NONEMPTY" not in issue_ids(valid_report)

    invalid = copy.deepcopy(source)
    invalid["data"]["character_book"]["entries"][0]["keys"] = ["{{user}}"]
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text(json.dumps(invalid), encoding="utf-8")
    invalid_report = validator.validate_card_report(str(invalid_path), profile="leyu-production")

    assert "MANUAL_TOGGLE_KEYS_NONEMPTY" in issue_ids(invalid_report)
    issue = next(i for i in invalid_report.issues if i.rule_id == "MANUAL_TOGGLE_KEYS_NONEMPTY")
    assert issue.path.endswith("entries[0].keys")
    assert issue.profile == "leyu-production"


def test_leyu_production_also_enforces_ccv3_core(load_script_module, tmp_path):
    validator = load_script_module("validate_card.py")
    source = json.loads(
        (Path(__file__).resolve().parent / "fixtures" / "valid_leyu_manual_toggle.json").read_text(encoding="utf-8")
    )
    del source["data"]["creator_notes"]
    path = tmp_path / "missing-core-field.json"
    path.write_text(json.dumps(source), encoding="utf-8")

    report = validator.validate_card_report(str(path), profile="leyu-production")

    assert not report.ok
    issue = next(issue for issue in report.issues if issue.rule_id == "CCV3_REQUIRED_DATA_FIELD_MISSING")
    assert issue.path == "data.creator_notes"
    assert issue.profile == "leyu-production"


def test_ccv3_numbers_reject_boolean_values(load_script_module):
    validator = load_script_module("validate_card.py")
    source = json.loads(
        (Path(__file__).resolve().parent / "fixtures" / "valid_ccv3_core_minimal.json").read_text(encoding="utf-8")
    )
    source["data"]["character_book"]["scan_depth"] = True
    source["data"]["character_book"]["entries"][0]["insertion_order"] = False

    report = validator.validate_ccv3_core(source)

    assert not report.ok
    assert "CCV3_LOREBOOK_FIELD_TYPE" in issue_ids(report)
    assert "CCV3_ENTRY_FIELD_TYPE" in issue_ids(report)


def test_ccv3_optional_data_and_entry_fields_are_typed_when_present(load_script_module):
    validator = load_script_module("validate_card.py")
    source = json.loads(
        (Path(__file__).resolve().parent / "fixtures" / "valid_ccv3_core_minimal.json").read_text(encoding="utf-8")
    )
    data = source["data"]
    data.update(
        {
            "nickname": 7,
            "creator_notes_multilingual": {"en": 8},
            "source": [9],
            "creation_date": True,
            "modification_date": False,
            "assets": [{"type": "icon", "uri": 10, "name": "main", "ext": "png"}],
        }
    )
    data["character_book"]["entries"][0].update(
        {"case_sensitive": "yes", "name": 11, "priority": True, "comment": 12}
    )

    report = validator.validate_ccv3_core(source)

    assert not report.ok
    ids = issue_ids(report)
    assert "CCV3_OPTIONAL_DATA_FIELD_TYPE" in ids
    assert "CCV3_CREATOR_NOTES_MULTILINGUAL_VALUE_TYPE" in ids
    assert "CCV3_SOURCE_ITEM_TYPE" in ids
    assert "CCV3_ASSET_FIELD_TYPE" in ids
    assert "CCV3_ENTRY_OPTIONAL_FIELD_TYPE" in ids
