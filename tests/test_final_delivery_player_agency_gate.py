from __future__ import annotations

import json


def legacy_boundary_entry() -> dict:
    return {
        "id": 1,
        "comment": "玩家行动边界与场景悬停",
        "content": (
            "说话 台词 发言 回答 思考 内心 判断 决定 选择 同意 拒绝 移动 进入 离开 场景 "
            "行动 使用物品 接受邀约 完成调查 未观察 未获知 未知 记忆 时间 阶段 切换 跳过 "
            "优先 自动推进剧情 接管点 等待{{user}}"
        ),
        "constant": True,
        "enabled": False,
        "keys": [],
        "secondary_keys": [],
        "selective": False,
        "position": "before_char",
        "extensions": {
            "entry_role": "feature_toggle",
            "feature_mode": "player_agency_boundary",
            "position": 0,
            "depth": 4,
            "ignore_budget": True,
            "exclude_recursion": True,
        },
    }


def test_final_delivery_gate_requires_player_agency_modes_by_default(load_script_module):
    gate = load_script_module("final_delivery_gate.py")
    option_strings = {
        option
        for action in gate.build_parser()._actions
        for option in action.option_strings
    }
    assert "--legacy-player-agency-modes" in option_strings
    assert "--require-player-agency-modes" in option_strings
    assert "--require-player-boundary" in option_strings


def test_final_delivery_gate_runs_player_agency_audit(load_script_module, tmp_path):
    gate = load_script_module("final_delivery_gate.py")
    card = tmp_path / "legacy.json"
    card.write_text('{"data":{"character_book":{"entries":[]}}}', encoding="utf-8")
    result = gate.run_player_agency_modes(card, require_modes=True)
    assert result.status == "FAIL"
    assert any("PLAYER_AGENCY_MODES_MISSING" in message for message in result.errors)


def test_g_prototype_automatically_requires_modes_but_legacy_flag_can_exempt(load_script_module, tmp_path, monkeypatch):
    gate = load_script_module("final_delivery_gate.py")
    card = tmp_path / "legacy.json"
    card.write_text('{"data":{"character_book":{"entries":[]}}}', encoding="utf-8")

    def passed(name: str):
        return gate.GateResult(name, "PASS")

    monkeypatch.setattr(gate, "run_validate", lambda _path: passed("validate"))
    monkeypatch.setattr(gate, "run_audit", lambda _path, _dir: passed("trigger"))
    monkeypatch.setattr(gate, "run_enrichment", lambda *_args: passed("enrichment"))
    monkeypatch.setattr(gate, "run_build_sync", lambda *_args: passed("build"))
    monkeypatch.setattr(gate, "scan_forbidden", lambda *_args, **_kwargs: passed("scan"))

    assert gate.main([str(card), "--prototype", "G", "-o", str(tmp_path / "g.md")]) == 1
    assert gate.main([
        str(card), "--prototype", "G", "--legacy-player-agency-modes", "-o", str(tmp_path / "legacy.md"),
    ]) == 0

    old_boundary_card = tmp_path / "old-boundary.json"
    old_boundary_card.write_text(json.dumps({
        "data": {"character_book": {"entries": [legacy_boundary_entry()]}},
    }), encoding="utf-8")
    assert gate.main([
        str(old_boundary_card),
        "--prototype", "G",
        "--legacy-player-agency-modes",
        "-o", str(tmp_path / "old-boundary.md"),
    ]) == 0


def test_final_delivery_gate_can_require_boundary_without_director(load_script_module, tmp_path):
    gate = load_script_module("final_delivery_gate.py")
    card = tmp_path / "legacy.json"
    card.write_text('{"data":{"character_book":{"entries":[]}}}', encoding="utf-8")

    result = gate.run_player_agency_modes(card, require_modes=False, require_boundary=True)
    assert result.status == "FAIL"
    assert any("PLAYER_AGENCY_MODES_MISSING" in message for message in result.errors)


def test_final_delivery_cli_forwards_always_on_requirement(load_script_module, tmp_path, monkeypatch):
    gate = load_script_module("final_delivery_gate.py")
    card = tmp_path / "card.json"
    card.write_text('{"data":{"character_book":{"entries":[]}}}', encoding="utf-8")
    captured = {}

    def passed(name: str):
        return gate.GateResult(name, "PASS")

    def capture_agency(*_args, **kwargs):
        captured.update(kwargs)
        return passed("agency")

    monkeypatch.setattr(gate, "run_player_agency_modes", capture_agency)
    monkeypatch.setattr(gate, "run_validate", lambda *_args, **_kwargs: passed("validate"))
    monkeypatch.setattr(gate, "run_audit", lambda *_args, **_kwargs: passed("trigger"))
    monkeypatch.setattr(gate, "run_enrichment", lambda *_args, **_kwargs: passed("enrichment"))
    monkeypatch.setattr(gate, "run_build_sync", lambda *_args, **_kwargs: passed("build"))
    monkeypatch.setattr(gate, "scan_forbidden", lambda *_args, **_kwargs: passed("scan"))

    assert gate.main([
        str(card), "--require-player-boundary", "-o", str(tmp_path / "report.md"),
    ]) == 0
    assert captured["require_boundary"] is True
    assert captured["require_boundary_always_on"] is True


def test_final_delivery_cli_rejects_incomplete_policy_manifest(load_script_module, tmp_path, monkeypatch):
    gate = load_script_module("final_delivery_gate.py")
    card = tmp_path / "card.json"
    card.write_text('{"data":{"character_book":{"entries":[]}}}', encoding="utf-8")
    policy = tmp_path / "fake-policy.json"
    policy.write_text(json.dumps({
        "schema_version": 2,
        "event_mode": "open_situation_seed",
        "corpus_mode": "curated_anchor_set",
        "route_policy": "player_led",
    }), encoding="utf-8")

    def passed(name: str):
        return gate.GateResult(name, "PASS")

    monkeypatch.setattr(gate, "run_validate", lambda *_args, **_kwargs: passed("validate"))
    monkeypatch.setattr(gate, "run_player_agency_modes", lambda *_args, **_kwargs: passed("agency"))
    monkeypatch.setattr(gate, "run_audit", lambda *_args, **_kwargs: passed("trigger"))
    monkeypatch.setattr(gate, "run_build_sync", lambda *_args, **_kwargs: passed("build"))
    monkeypatch.setattr(gate, "scan_forbidden", lambda *_args, **_kwargs: passed("scan"))

    status = gate.main([
        str(card),
        "--policy-manifest", str(policy),
        "-o", str(tmp_path / "report.md"),
    ])

    assert status == 1
