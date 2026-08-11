from __future__ import annotations

import json
import sys

import pytest


def player_agency_director() -> dict:
    return {
        "id": 0,
        "comment": "选开·自动推进剧情",
        "content": "NPC、环境和候选事件可推进一个主要事件；不得替{{user}}说话、思考、选择或行动。",
        "constant": True,
        "enabled": False,
        "keys": [],
        "secondary_keys": [],
        "selective": False,
        "position": "before_char",
        "extensions": {
            "entry_role": "feature_toggle",
            "feature_mode": "narrative_director",
            "position": 0,
            "depth": 4,
            "ignore_budget": True,
        },
    }


def test_opt_in_director_mode_satisfies_director_protocol_gate(load_script_module, tmp_path):
    checker = load_script_module("enrichment_self_check.py")
    card = tmp_path / "card.json"
    card.write_text(
        json.dumps({"data": {"character_book": {"entries": [player_agency_director()]}}}),
        encoding="utf-8",
    )

    issues = checker.check_card(str(card), verbose=False, prototype="G")

    assert not [
        message for severity, message in issues
        if severity == "🔴" and "缺少【剧情导演与事件推进协议】常驻条目" in message
    ]


def _minimal_policy_card(tmp_path):
    card = tmp_path / "policy-card.json"
    card.write_text(
        json.dumps(
            {
                "data": {
                    "description": "世界舞台与当前关系。玩家可以调查、保护、谈判或改写未来路线。",
                    "personality": "角色会根据可观察线索和玩家输入变化，但不预设唯一结局。",
                    "scenario": "当前场景保留开放入口，AI只写NPC、环境和可观察后果，不代写玩家。",
                    "system_prompt": "AI只扮演NPC和环境，遵守事实边界与玩家代理权。",
                    "character_book": {
                        "entries": [
                            {
                                "id": 1,
                                "comment": "事件种子·门口异常",
                                "content": "可观察线索。",
                                "enabled": False,
                                "constant": False,
                                "extensions": {"entry_role": "event_candidate"},
                            }
                        ]
                    },
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return card


def test_open_curated_policy_does_not_require_split_corpus_fixed_seed_or_director(load_script_module, tmp_path):
    checker = load_script_module("enrichment_self_check.py")
    card = _minimal_policy_card(tmp_path)

    issues = checker.check_card(
        str(card),
        verbose=False,
        event_mode="open_situation_seed",
        corpus_mode="curated_anchor_set",
        route_policy="player_led",
    )
    messages = [message for _severity, message in issues]

    assert not any(severity == "🔴" and "缺少语料库条目" in message for severity, message in issues)
    assert not any(severity == "🔴" and "事件种子[1]" in message for severity, message in issues)
    assert not any(severity == "🔴" and "缺少【剧情导演与事件推进协议】" in message for severity, message in issues)
    assert any("精选锚点模式" in message for message in messages)


def test_legacy_policy_keeps_old_content_red_lines(load_script_module, tmp_path):
    checker = load_script_module("enrichment_self_check.py")
    card = _minimal_policy_card(tmp_path)

    issues = checker.check_card(str(card), verbose=False, prototype="B")
    red_messages = [message for severity, message in issues if severity == "🔴"]

    assert any("缺少语料库条目" in message for message in red_messages)
    assert any("事件种子[1]" in message for message in red_messages)
    assert any("缺少【剧情导演与事件推进协议】" in message for message in red_messages)


def test_incomplete_policy_manifest_is_rejected(load_script_module, tmp_path):
    checker = load_script_module("enrichment_self_check.py")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 2, "event_mode": "open_situation_seed"}), encoding="utf-8")

    with pytest.raises(ValueError, match="PROTOTYPE_REQUIRED"):
        checker.load_quality_policy(manifest)


def _write_complete_open_manifest(tmp_path):
    narrative = tmp_path / "narrative.json"
    narrative.write_text(
        json.dumps({
            "schema_version": 1,
            "narrative_mode": "open_sandbox",
            "event_mode": "open_situation_seed",
            "event_policy": "candidate_pool",
            "transition_policy": "none",
            "facts": {},
            "events": {},
        }),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({
            "schema_version": 2,
            "prototype": "A",
            "runtime_driver": "native_st",
            "narrative_mode": "open_sandbox",
            "event_mode": "open_situation_seed",
            "corpus_mode": "curated_anchor_set",
            "route_policy": "player_led",
            "sandbox_scope": "focused",
            "event_policy": "candidate_pool",
            "transition_policy": "none",
            "narrative_contract": narrative.name,
            "runtime_state": {
                "authority": "none",
                "update_mode": "manual",
                "contract": "",
                "recovery_policy": "greeting_baseline",
                "reliability": "best_effort",
            },
        }),
        encoding="utf-8",
    )
    return manifest


def test_open_curated_cli_allows_soft_warnings_but_not_reds(load_script_module, tmp_path, monkeypatch):
    checker = load_script_module("enrichment_self_check.py")
    card = _minimal_policy_card(tmp_path)
    manifest = tmp_path / "open-manifest.json"
    manifest = _write_complete_open_manifest(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["enrichment_self_check.py", str(card), "--manifest", str(manifest)],
    )

    with pytest.raises(SystemExit) as exit_info:
        checker.main()

    assert exit_info.value.code == 0
