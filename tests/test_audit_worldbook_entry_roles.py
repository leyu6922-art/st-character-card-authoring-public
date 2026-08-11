from __future__ import annotations


def test_entry_role_intents_and_or_event_policy(load_script_module):
    audit = load_script_module("audit_worldbook_triggers.py")

    assert audit.infer_trigger_intent({
        "extensions": {"entry_role": "feature_toggle"},
        "comment": "剧情导演协议·功能开关",
        "constant": True,
        "enabled": True,
        "keys": [],
    }) == "功能开关（默认常驻，可UI关闭）"

    assert audit.infer_trigger_intent({
        "extensions": {"entry_role": "identity_toggle"},
        "comment": "身份·南问天选开",
        "constant": True,
        "enabled": False,
        "keys": [],
    }) == "G型选开身份"

    assert audit.infer_trigger_intent({
        "extensions": {"entry_role": "common_content"},
        "comment": "事件·P0·初见",
        "constant": False,
        "enabled": True,
        "selective": True,
        "secondary_keys": [],
        "keys": ["南向晚", "院门", "敲门"],
    }) == "自然事件·OR触发"

    assert audit.infer_trigger_intent({
        "extensions": {"entry_role": "common_content"},
        "comment": "场景·青云村",
        "constant": False,
        "enabled": True,
        "selective": True,
        "secondary_keys": [],
        "keys": ["青云村"],
    }) == "自然场景触发"


def test_legacy_audit_classification_is_preserved(load_script_module):
    audit = load_script_module("audit_worldbook_triggers.py")
    assert audit.infer_trigger_intent({
        "comment": "旧版场景条目",
        "constant": False,
        "enabled": True,
        "selective": True,
        "secondary_keys": ["范围"],
        "keys": ["房间"],
    }) == "范围绑定/阶段限定"


def test_or_event_policy_is_explicit_and_does_not_require_secondary_keys(load_script_module):
    audit = load_script_module("audit_worldbook_triggers.py")
    entry = {
        "extensions": {"entry_role": "common_content"},
        "comment": "事件·自然触发",
        "constant": False,
        "enabled": True,
        "selective": True,
        "secondary_keys": [],
        "keys": ["南问天", "院门", "敲门"],
    }
    assert audit.infer_trigger_intent(entry) == "自然事件·OR触发"
    assert entry["secondary_keys"] == []


def test_or_event_diagnostic_does_not_recommend_split_or_and_lock(load_script_module):
    audit = load_script_module("audit_worldbook_triggers.py")
    entry = {
        "extensions": {"entry_role": "common_content"},
        "comment": "事件·多路径自然触发",
        "content": "【前提】南问天回到院门。\n【进入】莫埃敲门。\n【动作】南向晚走向主屋。\n【后果】冲突继续。",
        "constant": False,
        "enabled": True,
        "selective": True,
        "secondary_keys": [],
        "keys": ["南问天", "南向晚", "莫埃", "院门", "主屋", "敲门"],
    }
    sources = [("probe", "南问天回到院门，莫埃敲门")]
    entry_audit = audit.analyze_entries([entry], sources)[0]
    suggestions = "；".join(entry_audit.suggestions)
    risks = "；".join(entry_audit.risks)
    assert "多主题大条目" not in risks
    assert "拆分" not in suggestions
    assert "selective限定" not in suggestions
    assert "OR" in risks
    assert "已接受" in suggestions
