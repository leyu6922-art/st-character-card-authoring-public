from __future__ import annotations

import copy
import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "references" / "audit" / "fixtures"


def make_card(keys):
    return {
        "spec": "chara_card_v3",
        "spec_version": "3.0",
        "data": {
            "first_mes": "Greeting",
            "alternate_greetings": [],
            "system_prompt": "system",
            "post_history_instructions": "post",
            "scenario": "scenario",
            "extensions": {
                "regex_scripts": [
                    {"scriptName": "route", "findRegex": "a", "replaceString": "b", "placement": [5], "disabled": False}
                ]
            },
            "character_book": {
                "entries": [
                    {
                        "id": 0,
                        "comment": "same",
                        "content": "same body",
                        "keys": keys,
                        "secondary_keys": [],
                        "constant": False,
                        "enabled": True,
                        "selective": False,
                        "insertion_order": 100,
                        "position": "after_char",
                        "use_regex": False,
                        "extensions": {"position": 4, "display_index": 0, "triggered": False},
                    }
                ]
            },
        },
    }


def test_build_sync_fails_when_only_entry_keys_drift(load_script_module, tmp_path):
    sync = load_script_module("check_build_sync.py")
    project = tmp_path / "project"
    (project / "build").mkdir(parents=True)
    final_path = project / "card.json"
    final_path.write_text(json.dumps(make_card(["final-key"])), encoding="utf-8")
    (project / "build" / "all_entries.json").write_text(
        json.dumps(make_card(["build-key"])["data"]["character_book"]["entries"]), encoding="utf-8"
    )

    status, issues, _notes = sync.check_build_sync(final_path, project, require_build=True)

    assert status == "FAIL"
    assert any("[BUILD_ENTRY_KEYS_DRIFT]" in issue for issue in issues)


def test_build_sync_static_only_does_not_execute_project_builder(load_script_module, tmp_path):
    sync = load_script_module("check_build_sync.py")
    project = tmp_path / "project"
    (project / "build").mkdir(parents=True)
    final_path = project / "card.json"
    final_path.write_text(json.dumps(make_card(["same-key"])), encoding="utf-8")
    (project / "build" / "all_entries.json").write_text(
        json.dumps(make_card(["same-key"])["data"]["character_book"]["entries"]), encoding="utf-8"
    )
    (project / "assemble_card.py").write_text(
        "from pathlib import Path\nPath('builder-executed.txt').write_text('unexpected')\n", encoding="utf-8"
    )

    status, issues, notes = sync.check_build_sync(final_path, project, require_build=True)

    assert status == "WARN"
    assert issues == []
    assert not (project / "builder-executed.txt").exists()
    assert any("STATIC_ONLY" in note for note in notes)


def test_build_reproducibility_requirement_stays_unverified_without_execution(load_script_module, tmp_path):
    sync = load_script_module("check_build_sync.py")
    project = tmp_path / "project"
    (project / "build").mkdir(parents=True)
    final_path = project / "card.json"
    final_path.write_text(json.dumps(make_card(["same-key"])), encoding="utf-8")
    (project / "build" / "all_entries.json").write_text(
        json.dumps(make_card(["same-key"])["data"]["character_book"]["entries"]), encoding="utf-8"
    )
    (project / "assemble_card.py").write_text("print('builder')\n", encoding="utf-8")

    status, issues, notes = sync.check_build_sync(
        final_path, project, require_build=True, reproducibility_required=True
    )

    assert status == "WARN"
    assert issues == []
    assert any("DECLARED_UNVERIFIED" in note for note in notes)


def test_execute_builder_uses_environment_allowlist(load_script_module, tmp_path, monkeypatch):
    sync = load_script_module("check_build_sync.py")
    project = tmp_path / "project"
    (project / "build").mkdir(parents=True)
    final_path = project / "card.json"
    final_path.write_text(json.dumps(make_card(["same-key"])), encoding="utf-8")
    (project / "build" / "all_entries.json").write_text(
        json.dumps(make_card(["same-key"])["data"]["character_book"]["entries"]), encoding="utf-8"
    )
    monkeypatch.setenv("PUBLIC_RELEASE_TEST_SECRET", "test-secret-123")
    (project / "assemble_card.py").write_text(
        "import os\nraise RuntimeError(os.getenv('PUBLIC_RELEASE_TEST_SECRET', 'MISSING'))\n",
        encoding="utf-8",
    )

    status, issues, _notes = sync.check_build_sync(
        final_path, project, require_build=True, execute_builder=True
    )

    assert status == "FAIL"
    joined = " ".join(issues)
    assert "MISSING" in joined
    assert "test-secret-123" not in joined


def test_build_sync_normalizes_runtime_extension_noise(load_script_module, tmp_path):
    sync = load_script_module("check_build_sync.py")
    project = tmp_path / "project"
    (project / "build").mkdir(parents=True)
    final = make_card(["same-key"])
    built = make_card(["same-key"])["data"]["character_book"]["entries"]
    built[0]["extensions"].pop("display_index")
    built[0]["extensions"]["triggered"] = True
    final_path = project / "card.json"
    final_path.write_text(json.dumps(final), encoding="utf-8")
    (project / "build" / "all_entries.json").write_text(json.dumps(built), encoding="utf-8")

    status, issues, _notes = sync.check_build_sync(final_path, project, require_build=True)

    assert status == "WARN"  # no assembler is intentionally present in this probe
    assert issues == []


def test_build_sync_detects_metadata_drift_from_metadata_capable_source(load_script_module, tmp_path):
    sync = load_script_module("check_build_sync.py")
    project = tmp_path / "project"
    (project / "build").mkdir(parents=True)
    final = make_card(["same-key"])
    final["data"]["character_book"]["token_budget"] = 900
    build_book = copy.deepcopy(final["data"]["character_book"])
    build_book["token_budget"] = 1200
    final_path = project / "card.json"
    final_path.write_text(json.dumps(final), encoding="utf-8")
    (project / "build" / "all_entries.json").write_text(
        json.dumps({"character_book": build_book}), encoding="utf-8"
    )

    status, issues, _notes = sync.check_build_sync(final_path, project, require_build=True)

    assert status == "FAIL"
    assert any("[BUILD_LOREBOOK_METADATA_DRIFT]" in issue and "token_budget" in issue for issue in issues)


def test_good_build_nested_fixture_stays_green(load_script_module):
    """技能链唯一的嵌套 build-sync 正例 fixture 不得再烂掉：
    2026-07-26 曾因 validate_card 收紧（character_book 缺 extensions）在文档化
    正例命令上产生假红，且此前无任何测试引用该 fixture。允许 WARN（纯 entries
    源无法比较 book metadata 属固有设计），不允许 FAIL。"""
    sync = load_script_module("check_build_sync.py")
    project = FIXTURES / "good_build_nested"
    card = project / "good_build_nested.json"

    status, issues, notes = sync.check_build_sync(card, project, require_build=True, execute_builder=True)

    assert status in ("PASS", "WARN"), issues
    assert issues == []
    assert any("all_entries.json 与最终JSON entries一致" in note for note in notes)
    assert any("assemble验证通过" in note for note in notes)


def test_final_delivery_gate_exposes_explicit_builder_execution_flag(load_script_module):
    gate = load_script_module("final_delivery_gate.py")

    args = gate.build_parser().parse_args(["card.json", "--execute-builder", "--require-reproducible-build"])

    assert args.execute_builder is True
    assert args.require_reproducible_build is True


def test_build_sync_detects_lorebook_metadata_and_entry_semantic_drift(load_script_module):
    sync = load_script_module("check_build_sync.py")
    final = make_card(["same-key"])
    build = copy.deepcopy(final)
    final_book = final["data"]["character_book"]
    build_book = build["data"]["character_book"]
    final_book.update(
        {
            "name": "Final lorebook",
            "description": "Final metadata",
            "scan_depth": 42,
            "token_budget": 900,
            "recursive_scanning": True,
            "extensions": {"book_flag": "final"},
        }
    )
    build_book.update(
        {
            "name": "Build lorebook",
            "description": "Build metadata",
            "scan_depth": 99,
            "token_budget": 1200,
            "recursive_scanning": False,
            "extensions": {"book_flag": "build"},
        }
    )
    final_entry = final_book["entries"][0]
    build_entry = build_book["entries"][0]
    final_entry.update({"case_sensitive": True, "priority": 10, "name": "Final entry"})
    build_entry.update({"case_sensitive": False, "priority": 20, "name": "Build entry"})

    card_issues = sync.compare_card_fields(final, build)
    entry_issues = sync.compare_entries(final_book["entries"], build_book["entries"])

    for path in (
        "data.character_book.name",
        "data.character_book.description",
        "data.character_book.scan_depth",
        "data.character_book.token_budget",
        "data.character_book.recursive_scanning",
        "data.character_book.extensions.book_flag",
    ):
        assert any(path in issue for issue in card_issues)
    for field in ("case_sensitive", "priority", "name"):
        assert any(f".{field}:" in issue for issue in entry_issues)
