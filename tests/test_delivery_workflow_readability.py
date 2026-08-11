from __future__ import annotations


def test_skill_exposes_manifest_runner_in_its_quick_entrypoints(skill_root):
    text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    quick_index = text.split("## 1. 卡片原型选择", 1)[0]

    assert "build_manifest.json" in quick_index
    assert "run_delivery.py" in quick_index
    assert "manifest-driven-delivery.md" in quick_index


def test_skill_does_not_require_redundant_confirmation_after_high_confidence_auto_classification(skill_root):
    text = (skill_root / "SKILL.md").read_text(encoding="utf-8")

    assert "自动选择高置信原型" in text
    assert "必须先完成 §1.0 原型判定并获用户确认" not in text


def test_greeting_layer_audit_is_documented_as_appendix_only(skill_root):
    text = (skill_root / "SKILL.md").read_text(encoding="utf-8")

    assert "greeting_mode=prose_plus_director_appendix" in text
    assert "纯`player_prose`/纯`ai_trigger`卡不执行这个专项" in text


def test_greeting_person_and_length_rules_follow_manifest_mode(skill_root):
    text = (skill_root / "SKILL.md").read_text(encoding="utf-8")

    assert "禁止套用固定的“第二人称你”" in text
    assert "仅 `greeting_mode=player_prose` 且规划书确认第二人称时" in text
    assert "`ai_trigger` 不适用该字数规则" in text
    assert '**{{user}}视角**：开场白和正文必须用"你"' not in text
    assert "每个greeting ≥1400字。" not in text


def test_semantic_module_branch_is_explicit_and_ordered(skill_root):
    skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    workflow = (skill_root / "references/workflows/card-assembly-and-delivery-pipeline.md").read_text(encoding="utf-8")
    manifest = (skill_root / "references/workflows/manifest-driven-delivery.md").read_text(encoding="utf-8")
    semantic_ref = (skill_root / "references/design-patterns/semantic-modular-open-card-architecture.md").read_text(encoding="utf-8")

    quick_index = skill.split("## 1. 卡片原型选择", 1)[0]
    for token in ("semantic-module-manifest.example.json", "semantic_manifest", "run_delivery.py"):
        assert token in quick_index
    assert workflow.index("运行组装器产出候选卡") < workflow.index("semantic_manifest") < workflow.index("run_delivery.py")
    assert "scripts/audit_semantic_modules.py" in workflow
    assert "未填该字段时，统一 Runner 会按 legacy/non-semantic 路径跳过新门控" in workflow
    assert manifest.count("| `semantic_manifest` |") == 1
    assert "两份 manifest 的字段所有权" in semantic_ref
    assert "source_scope.canonical_sources" in semantic_ref
    assert "architecture_mode` 不会自动改写 `routing_mode" in semantic_ref


def test_discord_rules_scan_publish_text_not_card_json(skill_root):
    text = (skill_root / "SKILL.md").read_text(encoding="utf-8")

    assert "仅发布简介/帖子需要扫描平台违禁词；不扫描角色卡 JSON 正文" in text
    assert "平台只审核将要发布的简介/帖子，不审核角色卡 JSON" in text
    assert "全卡违禁词扫描" not in text
