from __future__ import annotations

import json


def _good_greeting(audit):
    body = "【开场：P0·测试】\n" + "夜色压在窗纸上，人物在门边停住，等待局势进一步变化。" * 70
    appendix = "\n\n---\n\n**导演附录·P0**\n\n" + "\n\n".join(
        f"> **【{label}】** 当前阶段的人物、事实、信息边界、动作方向与潜在后果均已具体锁定。"
        * 4
        for label in audit.STAGE_BRIEF_DIMENSIONS
    )
    return body + appendix


def _write_project(tmp_path, greetings, card_greetings=None):
    project = tmp_path / "project"
    (project / "build").mkdir(parents=True)
    (project / "build" / "all_entries.json").write_text(
        json.dumps({"greetings": {f"P{i}": text for i, text in enumerate(greetings)}}, ensure_ascii=False),
        encoding="utf-8",
    )
    card_greetings = greetings if card_greetings is None else card_greetings
    (project / "card.json").write_text(
        json.dumps({"data": {"first_mes": card_greetings[0], "alternate_greetings": card_greetings[1:]}}, ensure_ascii=False),
        encoding="utf-8",
    )
    return project, project / "card.json"


def test_build_greeting_wiring_rejects_clean_rebuild_without_stage_appendix(load_script_module, tmp_path):
    audit = load_script_module("audit_greeting_layers.py")
    wiring = load_script_module("audit_greeting_build_wiring.py")
    body_only = "【开场：P0·测试】\n" + "夜色压在窗纸上，人物在门边停住，等待局势进一步变化。" * 70
    project, card = _write_project(tmp_path, [body_only])

    result = wiring.audit_build_wiring(card, project, 1400, 1800, "stage_brief_v1")

    assert result["status"] == "FAIL"
    assert any("BUILD_GREETING_SOURCE_INVALID" in item for item in result["errors"])
    assert any("APPENDIX_TOO_SHORT" in item for item in result["errors"])


def test_build_greeting_wiring_accepts_exact_stage_brief_source_and_artifact(load_script_module, tmp_path):
    audit = load_script_module("audit_greeting_layers.py")
    wiring = load_script_module("audit_greeting_build_wiring.py")
    greeting = _good_greeting(audit)
    project, card = _write_project(tmp_path, [greeting])

    result = wiring.audit_build_wiring(card, project, 1400, 1800, "stage_brief_v1")

    assert result["status"] == "PASS", result
    assert result["errors"] == []


def test_build_greeting_wiring_rejects_source_artifact_content_drift(load_script_module, tmp_path):
    audit = load_script_module("audit_greeting_layers.py")
    wiring = load_script_module("audit_greeting_build_wiring.py")
    source = _good_greeting(audit)
    artifact = source.replace("等待局势进一步变化", "已经替玩家做出决定", 1)
    project, card = _write_project(tmp_path, [source], [artifact])

    result = wiring.audit_build_wiring(card, project, 1400, 1800, "stage_brief_v1")

    assert result["status"] == "FAIL"
    assert any("BUILD_GREETING_CONTENT_DRIFT" in item for item in result["errors"])
