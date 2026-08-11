from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_migration_is_non_destructive_and_preserves_lorebook_metadata(load_script_module, tmp_path):
    migrator = load_script_module("migrate_card.py")
    source = {
        "spec": "chara_card_v3",
        "spec_version": "3.0",
        "data": {
            "name": "Legacy",
            "character_book": {
                "name": "book",
                "description": "keep",
                "scan_depth": 99,
                "token_budget": 123,
                "recursive_scanning": False,
                "extensions": {"export_marker": True},
                "entries": [
                    {
                        "id": "stable-id",
                        "key": ["legacy"],
                        "keysecondary": [],
                        "content": "body",
                        "constant": False,
                        "disable": False,
                        "extensions": {"prevent_recursion": False},
                    }
                ],
            },
        },
    }
    source_path = tmp_path / "legacy.json"
    output_path = tmp_path / "legacy.migrated.json"
    source_path.write_text(json.dumps(source), encoding="utf-8")

    result = migrator.migrate_card(source_path, output_path)

    assert source_path.read_text(encoding="utf-8") == json.dumps(source)
    assert result.output_path == output_path
    migrated = json.loads(output_path.read_text(encoding="utf-8"))
    book = migrated["data"]["character_book"]
    assert book["description"] == "keep"
    assert book["scan_depth"] == 99
    assert book["token_budget"] == 123
    assert book["recursive_scanning"] is False
    assert book["extensions"] == {"export_marker": True}
    assert book["entries"][0]["id"] == "stable-id"
    assert book["entries"][0]["extensions"]["prevent_recursion"] is False


def test_atomic_writer_is_parseable_no_bom_and_backs_up_replaced_file(load_script_module, tmp_path):
    writer = load_script_module("atomic_write_json.py")
    output_path = tmp_path / "card.json"
    output_path.write_text('{"old":true}', encoding="utf-8")

    result = writer.atomic_write_json({"new": True}, output_path, backup=True)

    raw = output_path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert json.loads(raw.decode("utf-8")) == {"new": True}
    assert result.sha256
    assert result.backup_path is not None
    assert json.loads(result.backup_path.read_text(encoding="utf-8")) == {"old": True}


def test_atomic_writer_cli_validates_selected_profile(load_script_module, tmp_path):
    writer = load_script_module("atomic_write_json.py")
    source = tmp_path / "source.json"
    output = tmp_path / "output.json"
    fixture = Path(__file__).resolve().parent / "fixtures" / "valid_ccv3_core_minimal.json"
    source.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    assert writer.main([str(source), str(output), "--validate-profile", "ccv3-core"]) == 0
    assert output.is_file()


def test_migration_rejects_st_only_positions_and_invalid_core_output(load_script_module, tmp_path):
    migrator = load_script_module("migrate_card.py")
    assert migrator.normalize_position(0) == "before_char"
    assert migrator.normalize_position(1) == "after_char"
    for unsupported_position in (2, 3, 4):
        with pytest.raises(ValueError, match="position"):
            migrator.migrated_card(
                {
                    "data": {
                        "character_book": {
                            "entries": [{"id": 0, "position": unsupported_position}],
                        }
                    }
                }
            )

    invalid_source = {
        "data": {
            "character_book": {
                "entries": [{"id": 0, "keys": [42], "content": "body"}],
            }
        }
    }
    source_path = tmp_path / "invalid-source.json"
    output_path = tmp_path / "invalid-output.json"
    source_path.write_text(json.dumps(invalid_source), encoding="utf-8")

    with pytest.raises(ValueError, match="CCV3"):
        migrator.migrate_card(source_path, output_path)
    assert not output_path.exists()
