from __future__ import annotations

import json


APPENDIX = """\n---\n\n> **导演附录｜当前阶段背景**\n>\n> *以下内容用于维持阶段事实，不是角色台词。*\n>\n> **当前可见**：测试\n>\n> **玩家接管点**：等待玩家输入。"""


# 40 repetitions produce 1480 CJK characters after the title is removed.
PROSE = "林家的窗外落着细雨，厨房里的水声断断续续，李彤彤把文件压在茶杯下面，抬头看向门口。" * 40


def make_card(body: str, appendix: str = APPENDIX) -> dict:
    greeting = "【开场：P0·测试】\n" + body + appendix
    return {"data": {"first_mes": greeting, "alternate_greetings": []}}


def write_card(tmp_path, name: str, card: dict):
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    return path


def test_greeting_layer_audit_accepts_separate_prose_and_appendix(tmp_path, load_script_module):
    audit = load_script_module("audit_greeting_layers.py")
    result = audit.audit_one(make_card(PROSE)["data"]["first_mes"], "first_mes", 1400, 1800)
    assert result["passed"], result["issues"]
    assert result["body_cjk"] == 1480
    assert result["appendix_chars"] > 0


def test_greeting_layer_audit_accepts_build_greetings_mapping(load_script_module):
    audit = load_script_module("audit_greeting_layers.py")
    greetings = audit.get_greetings({"P0": "【开场：P0】\n" + PROSE + APPENDIX})
    assert greetings == [("P0", "【开场：P0】\n" + PROSE + APPENDIX)]


def test_greeting_layer_audit_rejects_director_language_in_body(load_script_module):
    audit = load_script_module("audit_greeting_layers.py")
    greeting = make_card(PROSE.replace("文件", "当前阶段文件"))["data"]["first_mes"]
    result = audit.audit_one(greeting, "first_mes", 1400, 1800)
    assert not result["passed"]
    assert any(issue["code"] == "BODY_POLLUTED" for issue in result["issues"])


def test_greeting_layer_audit_rejects_short_body_even_with_appendix(load_script_module):
    audit = load_script_module("audit_greeting_layers.py")
    result = audit.audit_one(make_card("李彤彤坐在门边。")["data"]["first_mes"], "first_mes", 1400, 1800)
    assert not result["passed"]
    assert any(issue["code"] == "BODY_TOO_SHORT" for issue in result["issues"])


def test_stage_brief_standard_accepts_eight_dimensions(load_script_module):
    audit = load_script_module("audit_greeting_layers.py")
    appendix = "\n---\n\n**导演附录·P0**\n\n" + "\n\n".join(
        f"> **【{label}】** " + "当前阶段有具体人物、动作、信息和后果描述。" * 6
        for label in audit.STAGE_BRIEF_DIMENSIONS
    )
    result = audit.audit_one(
        make_card(PROSE, appendix=appendix)["data"]["first_mes"],
        "first_mes",
        1400,
        1800,
        "stage_brief_v1",
    )
    assert result["passed"], result["issues"]


def test_stage_brief_standard_rejects_missing_dimensions(load_script_module):
    audit = load_script_module("audit_greeting_layers.py")
    appendix = "\n---\n\n**导演附录·P0**\n\n> **【当前节点】** 当前阶段有具体人物、动作、信息和后果描述。"
    result = audit.audit_one(
        make_card(PROSE, appendix=appendix)["data"]["first_mes"],
        "first_mes",
        1400,
        1800,
        "stage_brief_v1",
    )
    assert not result["passed"]
    missing = [issue["message"] for issue in result["issues"] if issue["code"] == "APPENDIX_DIMENSION_MISSING"]
    assert "人物状态" in " ".join(missing)


def test_final_gate_runs_greeting_layer_audit_when_flagged(tmp_path, load_script_module):
    gate = load_script_module("final_delivery_gate.py")
    card_path = write_card(tmp_path, "good", make_card(PROSE))
    result = gate.run_greeting_layer_audit(card_path)
    assert result.status == "PASS", result.errors
    assert gate.build_parser().parse_args([str(card_path), "--greeting-layer-audit"]).greeting_layer_audit


def test_final_gate_greeting_audit_blocks_polluted_card(tmp_path, load_script_module):
    gate = load_script_module("final_delivery_gate.py")
    card_path = write_card(tmp_path, "polluted", make_card(PROSE.replace("文件", "当前阶段文件")))
    result = gate.run_greeting_layer_audit(card_path)
    assert result.status == "FAIL"
    assert any("BODY_POLLUTED" in error for error in result.errors)
