import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BASE_CARD = ROOT / "references" / "audit" / "fixtures" / "good_build_nested" / "good_build_nested.json"
SEMANTIC_TEMPLATE = ROOT / "templates" / "semantic-module-manifest.example.json"
RUNNER = ROOT / "scripts" / "run_delivery.py"


ROLE_TEXT = """# 角色模块：示例角色｜核心心理与性格

## 条目作用

描述稳定心理和现场反应。

## 核心锚点

- 核心需求：保持判断权。

## 触发与响应

根据现场压力选择试探、回避或有限回应。

## 具体表现

先观察，再回应；当信息不足时保留判断。

## 特质交叠

谨慎与好奇同时存在，压力会改变表达速度。

## 信息边界

只使用已经确认的信息。

## 不应误写

不替玩家决定，不把候选事件写成既成事实。

## 可开放变化

反应强度、信任程度和停留时间可以变化。"""

PLACE_TEXT = """# 地点模块：示例地点

## 条目作用

描述地点的可用范围。

## 地点定位

用于交谈、观察和自然进入。

## 启用时间

当前场景即可自然到达。

## 空间布局

入口、公开区和内侧空间彼此可观察。

## 自然入口

通过营业、门或熟人进入。

## 现实规则

门禁、旁观者和退出路径有效。

## 场景边界

不可逆结果需要互动前提。

## 剧情功能

承载调查和候选入口。

## 不应误写

不无前提切换地点，也不把观察结果写成已经发生的事实。

## 可开放变化

人员分布、停留顺序和可见物件可以变化。"""


def _cn_repeat(text: str, count: int) -> str:
    return text * count


def _entry(base: dict, *, comment: str, content: str, keys=None, constant=False) -> dict:
    entry = dict(base)
    entry.update(
        comment=comment,
        content=content,
        keys=list(keys or []),
        enabled=True,
        constant=constant,
        selective=not constant,
        extensions=dict(base.get("extensions") or {}),
    )
    entry["extensions"]["selective"] = not constant
    if comment == "剧情导演与事件推进协议":
        entry["extensions"]["ignore_budget"] = True
    return entry


def _make_project(tmp_path: Path, *, semantic: bool) -> tuple[Path, Path]:
    card = json.loads(BASE_CARD.read_text(encoding="utf-8-sig"))
    profile = _cn_repeat(
        "这是开放叙事舞台，玩家通过{{user}}行动，AI只扮演NPC与环境，不代写玩家决定。",
        12,
    )
    for target in (card, card.get("data", {})):
        target.update(
            description=profile,
            personality=_cn_repeat("角色以具体行为、语言和反应呈现。", 30),
            scenario=_cn_repeat("故事从可退出的现实场景开始，事件允许被打断或偏离。", 15),
            first_mes="\n\n".join(
                f"第{i + 1}个可观察片段：雨夜办公室里，林梦瑶在台灯旁把文件袋放在桌上，等待{{{{user}}}}回应，并保留退出路径。"
                for i in range(60)
            ),
        )

    source_entries = json.loads(
        (ROOT / "references" / "audit" / "fixtures" / "good_build_nested" / "build" / "all_entries.json").read_text(
            encoding="utf-8"
        )
    )
    by_comment = {entry["comment"]: entry for entry in source_entries}
    entries = [
        _entry(by_comment["系统规则"], comment="系统规则", content="世界规则保持具体，玩家行动由{{user}}决定。", constant=True),
        _entry(
            by_comment["核心角色档案：林梦瑶"],
            comment="核心角色档案：林梦瑶",
            content=by_comment["核心角色档案：林梦瑶"]["content"][:2500],
            keys=["林梦瑶"],
        ),
        _entry(
            by_comment["林梦瑶语料库"],
            comment="林梦瑶语料库",
            content=re.sub(
                r"([「“])",
                r"【林梦瑶→{{user}}·示例场景】\1",
                by_comment["林梦瑶语料库"]["content"][:650],
            ),
            keys=["文件袋"],
        ),
        _entry(
            by_comment["场景：雨夜办公室"],
            comment="场景：雨夜办公室",
            content=by_comment["场景：雨夜办公室"]["content"][:650]
            + "\n安全等级：B级；入口、旁观者、物件和退出路径均可观察。",
            keys=["办公室"],
        ),
        _entry(
            by_comment["身体与环境描写库"],
            comment="身体与环境描写库",
            content=by_comment["身体与环境描写库"]["content"][:700],
            keys=["台灯"],
        ),
        _entry(
            by_comment["系统规则"],
            comment="剧情导演与事件推进协议",
            content=_cn_repeat(
                "NPC不得替{{user}}发言、思考、判断、决定、选择、移动或完成行动；每次只推进一个可观察变化，然后等待接管。",
                10,
            ),
            constant=True,
        ),
    ]
    if semantic:
        entries.extend(
            [
                _entry(
                    by_comment["系统规则"],
                    comment="角色/示例角色/核心心理与性格",
                    content=ROLE_TEXT,
                    constant=True,
                ),
                _entry(
                    by_comment["系统规则"],
                    comment="世界观/地点/示例地点",
                    content=PLACE_TEXT,
                    constant=True,
                ),
            ]
        )
    for index, entry in enumerate(entries):
        entry["id"] = index
        entry["insertion_order"] = index
        entry.setdefault("extensions", {})["display_index"] = index
    card.setdefault("data", {}).setdefault("character_book", {})["entries"] = entries
    card_path = tmp_path / "card.json"
    card_path.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")

    build_manifest = {
        "schema_version": 1,
        "prototype": "A",
        "routing_mode": "flat",
        "runtime_driver": "native_st",
        "runtime_state": {"authority": "none"},
        "greeting_mode": "player_prose",
        "narrative_mode": "open_sandbox",
        "content_mode": "non_r18",
        "require_build": False,
    }
    if semantic:
        semantic_manifest = json.loads(SEMANTIC_TEMPLATE.read_text(encoding="utf-8-sig"))
        semantic_manifest.update(
            characters={"示例角色": {"entity_id": "char_example", "modules": ["核心心理与性格"]}},
            world_modules=["世界观/地点/示例地点"],
            projections=[
                {
                    "semantic_ref": "世界观/地点/示例地点",
                    "runtime_role": "scene",
                    "flat": {"load": "selective"},
                }
            ],
            module_records={
                "角色/示例角色/核心心理与性格": {
                    "module_type": "character_psychology",
                    "text_profile": "semantic_markdown_v1",
                    "content_schema": "character_psychology_v1",
                    "contract_profile": "open_semantic_module_v1",
                },
                "世界观/地点/示例地点": {
                    "module_type": "place",
                    "text_profile": "semantic_markdown_v1",
                    "content_schema": "place_v1",
                    "contract_profile": "open_semantic_module_v1",
                },
            },
        )
        semantic_path = tmp_path / "semantic-module-manifest.json"
        semantic_path.write_text(json.dumps(semantic_manifest, ensure_ascii=False), encoding="utf-8")
        build_manifest["semantic_manifest"] = semantic_path.name

    manifest_path = tmp_path / "build_manifest.json"
    manifest_path.write_text(json.dumps(build_manifest, ensure_ascii=False), encoding="utf-8")
    return card_path, manifest_path


def _run(card_path: Path, manifest_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), str(card_path), "--manifest", str(manifest_path), *extra],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_positive_delivery_runs_full_runner_to_final_gate(tmp_path):
    card, manifest = _make_project(tmp_path, semantic=True)
    result = _run(card, manifest)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "semantic module audit: RUN" in output
    assert "semantic text audit: RUN" in output
    assert "semantic coverage: modern text modules audited: 2" in output
    assert "final verdict: 可交付" in output


def test_cli_legacy_delivery_skips_semantic_audits(tmp_path):
    card, manifest = _make_project(tmp_path, semantic=False)
    result = _run(card, manifest)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "semantic module audit: SKIP" in output
    assert "semantic text audit: SKIP" in output
    assert "final verdict: 可交付" in output


@pytest.mark.parametrize(
    ("manifest_body", "expected_code"),
    [
        ("{not-json", "DELIVERY_MANIFEST_JSON_INVALID"),
        (json.dumps({"schema_version": 3}), "DELIVERY_MANIFEST_SCHEMA_INVALID"),
        (json.dumps({"schema_version": 1, "prototype": "A", "semantic_manifest": "missing.json"}), "SEMANTIC_MANIFEST_NOT_FOUND"),
    ],
)
def test_cli_configuration_errors_have_stable_json_codes(tmp_path, manifest_body, expected_code):
    card, manifest = _make_project(tmp_path, semantic=False)
    manifest.write_text(manifest_body, encoding="utf-8")
    result = _run(card, manifest, "--format", "json")
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == expected_code


def test_cli_missing_build_manifest_has_stable_json_code(tmp_path):
    card, manifest = _make_project(tmp_path, semantic=False)
    manifest.unlink()
    result = _run(card, manifest, "--format", "json")
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "DELIVERY_MANIFEST_NOT_FOUND"


def test_cli_malformed_semantic_manifest_has_stable_json_code(tmp_path):
    card, manifest = _make_project(tmp_path, semantic=False)
    semantic = tmp_path / "semantic-module-manifest.json"
    semantic.write_text("{not-json", encoding="utf-8")
    body = json.loads(manifest.read_text(encoding="utf-8"))
    body["semantic_manifest"] = semantic.name
    manifest.write_text(json.dumps(body), encoding="utf-8")
    result = _run(card, manifest, "--format", "json")
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "SEMANTIC_MANIFEST_JSON_INVALID"


def test_cli_non_object_card_does_not_traceback(tmp_path):
    card, manifest = _make_project(tmp_path, semantic=True)
    card.write_text("[]", encoding="utf-8")
    result = _run(card, manifest)
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert "SEMANTIC_AUDIT_INPUT_ERROR" in output
    assert "Traceback" not in output


def test_summarize_coverage_reports_all_migration_categories(load_script_module):
    module = load_script_module("audit_semantic_modules.py")
    card = {
        "data": {
            "character_book": {
                "entries": [
                    {"comment": "角色/示例角色/核心心理与性格"},
                    {"comment": "世界观/地点/示例地点"},
                    {"comment": "事件/候选/雨夜拜访"},
                    {"comment": "普通条目"},
                ]
            }
        }
    }
    manifest = {
        "text_profile": "semantic_markdown_v1",
        "characters": {"示例角色": {"modules": ["核心心理与性格"]}},
        "world_modules": ["世界观/地点/示例地点"],
        "module_records": {
            "角色/示例角色/核心心理与性格": {
                "text_profile": "semantic_markdown_v1",
            }
        },
    }
    coverage = module.summarize_coverage(card, manifest)
    assert coverage == {
        "modern_text_modules_audited": 1,
        "legacy_semantic_modules_audited": 2,
        "non_semantic_entries_ignored": 1,
        "unregistered_formal_namespace_modules": 1,
    }
