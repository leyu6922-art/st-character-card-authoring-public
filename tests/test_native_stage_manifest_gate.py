from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SIBLING_SCRIPTS = Path(__file__).resolve().parents[2] / "standalone-card-stage-routing" / "scripts"

pytestmark = pytest.mark.skipif(
    not SIBLING_SCRIPTS.is_dir(),
    reason="sibling skill standalone-card-stage-routing not checked out (single-skill CI layout)",
)


def load_native_stage_auditor():
    """Load the sibling auditor against its OWN lib copy.

    Isolates sys.modules['lib']: previously a single-file run failed with
    ModuleNotFoundError, while full-suite runs silently resolved the main
    skill's cached lib instead of the sibling's — sibling lib drift would have
    stayed invisible to this test.
    """
    path = SIBLING_SCRIPTS / "audit_native_stage_architecture.py"
    saved = {name: sys.modules.pop(name) for name in list(sys.modules) if name == "lib" or name.startswith("lib.")}
    sys.path.insert(0, str(SIBLING_SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("native_stage_manifest_auditor", path)
        assert spec and spec.loader, f"cannot import {path}"
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if sys.path and sys.path[0] == str(SIBLING_SCRIPTS):
            sys.path.pop(0)
        for name in [n for n in sys.modules if n == "lib" or n.startswith("lib.")]:
            sys.modules.pop(name)
        sys.modules.update(saved)


def manifest():
    """A minimal manifest that the sibling architecture auditor understands."""
    return {
        "route_mode": "native_greeting_title",
        "stages": ["P0", "P1", "P2", "P3", "P4", "P5"],
        "required_packs": ["阶段核心", "成人体验", "场景体验", "事件库"],
        "min_units_per_pack": 6,
    }


def title(stage: str) -> str:
    return f"【开场：阶段{stage}｜{stage}】"


def stage_entry(category: str, stage: str) -> dict:
    content = "\n".join(
        f"【{category}_{stage}_{index:02d}_单元】阶段限定且可直接调用的具体素材。"
        for index in range(1, 7)
    )
    return {
        "comment": f"{category}_{stage}",
        "content": content,
        "keys": [title(stage)],
        "secondary_keys": [],
        "constant": False,
        "enabled": True,
        "selective": True,
        "extensions": {"scan_depth": 999, "prevent_recursion": True},
    }


def valid_p0_to_p5_card() -> dict:
    stages = manifest()["stages"]
    greetings = [f"{title(stage)}\n该阶段的独立叙事正文。" for stage in stages]
    entries = [
        stage_entry(category, stage)
        for stage in stages
        for category in manifest()["required_packs"]
    ]
    return {
        "first_mes": greetings[0],
        "data": {
            "first_mes": greetings[0],
            "alternate_greetings": greetings[1:],
            "character_book": {"entries": entries},
        },
    }


def test_p0_to_p5_manifest_accepts_complete_native_stage_card():
    auditor = load_native_stage_auditor()

    result = auditor.audit_card(valid_p0_to_p5_card(), manifest=manifest())

    assert result.failures == []


def test_manifest_rejects_analysis_provenance_in_model_visible_content():
    auditor = load_native_stage_auditor()
    card = valid_p0_to_p5_card()
    card["data"]["character_book"]["entries"][0]["content"] += "\n【源文档：12_阶段状态快照.md】"

    result = auditor.audit_card(card, manifest=manifest())

    assert any("分析层" in failure for failure in result.failures)


def test_manifest_rejects_stage_package_bound_to_another_stage_title():
    auditor = load_native_stage_auditor()
    card = valid_p0_to_p5_card()
    p0_core = card["data"]["character_book"]["entries"][0]
    p0_core["keys"] = [title("P1")]

    result = auditor.audit_card(card, manifest=manifest())

    assert any("阶段核心_P0 key" in failure for failure in result.failures)
