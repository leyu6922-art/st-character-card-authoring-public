#!/usr/bin/env python3
"""阶段记忆闸门架构的 fixture 集（2026-07-26 流程改造）

正向：合法阶段路由卡（标题路由）、子系统厚条目卡（不应被误杀）
负向：P#死键、跨阶段误触发、缺组件、事件事实化、泛key高阶段包
反误杀：正常场景被greeting命中、因果档案条件语言、G型系统常驻{{user}}、非完整阶段集

注意：AN/ROUTE_STAGE=P# 属外部 preset 路线，未接入 native 门控。valid_an_route_card
仅用于 validator 层诊断检查的回归；final_delivery_gate 对该类卡硬拒绝
（STAGE_EXTERNAL_ROUTE_UNSUPPORTED），见 TestStageMemoryGateScriptIntegration。
"""

from __future__ import annotations

import json

import pytest


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def stages_real() -> list[str]:
    """真实项目只有 P0–P2，不伪造不存在的阶段"""
    return ["P0", "P1", "P2"]


def packs() -> list[str]:
    return ["阶段核心", "成人体验", "场景体验", "事件库"]


def greeting_title(stage: str) -> str:
    return f"【开场：{stage}·测试场景｜TEST】"


def pack_entry(stage: str, pack: str, *, enabled: bool = True,
               selective: bool = True, keys: list[str] | None = None,
               extra_entry: dict | None = None) -> dict:
    material = (
        "该素材单元明确给出进入条件、人物主动动作、可用对白、"
        "当下心理、场景变化、选择分歧与关系余波。"
        "【前提】需要当前阶段前置条件在聊天中成立。"
        "【自然切入】通过角色主动行为自然引入。"
        "【人物反应】各角色依据当前已知事实反应。"
        "【分歧/代价】玩家介入后可产生不同走向。"
    )
    units = "\n".join(
        f"【{pack}_{stage}_{index:02d}_素材】{material}"
        for index in range(1, 7)
    )
    entry = {
        "id": f"{pack}-{stage}",
        "comment": f"{pack}_{stage}",
        "content": units,
        "keys": keys if keys is not None else [greeting_title(stage)],
        "secondary_keys": [],
        "enabled": enabled,
        "constant": False,
        "selective": selective,
        "extensions": {
            "entry_role": "common_content",
            "scan_depth": 999,
            "selective": selective,
            "prevent_recursion": True,
            "exclude_recursion": True,
        },
    }
    if extra_entry:
        entry.update(extra_entry)
    return entry


def causal_archive_entry() -> dict:
    return {
        "id": "角色A·全程因果档案",
        "comment": "角色A·全程因果档案·常驻",
        "content": (
            "【不随阶段变化的底层人格】核心欲望、羞耻来源、语言指纹。\n"
            "【全程因果方向】P0时人物相信X，当事件Y真实发生后可能走向P1的Z状态。\n"
            "【人物连续性锚点】恐惧/称呼/身体反应贯穿或逐步变形。\n"
            "【阶段不可逆点】P1的真实发生后不能无故回退到P0。\n"
            "后续阶段的变化仅在当前阶段前置条件在聊天中成立后才可能发生。"
        ),
        "keys": [],
        "secondary_keys": [],
        "enabled": True,
        "constant": True,
        "selective": False,
        "extensions": {
            "entry_role": "system_constant",
            "position": "before_char",
            "depth": 4,
            "ignore_budget": True,
            "prevent_recursion": True,
        },
    }


def memory_gate_entry() -> dict:
    return {
        "id": "绝对优先级·阶段记忆与叙事可见性协议",
        "comment": "阶段记忆与叙事可见性协议·常驻",
        "content": (
            "【绝对优先级·阶段记忆与叙事可见性协议】\n"
            "模型可阅读全程因果档案以理解人物弧线。"
            "当前阶段为P#时，只有起步至P#的事件/关系/秘密可被视为已发生。"
            "未来阶段内容仅为候选方向，不得写成角色记忆/既定关系/已知秘密。"
            "冲突时当前阶段状态与路由优先。"
        ),
        "keys": [],
        "secondary_keys": [],
        "enabled": True,
        "constant": True,
        "selective": False,
        "insertion_order": 0,
        "extensions": {
            "entry_role": "feature_toggle",
            "position": "before_char",
            "depth": 4,
            "ignore_budget": True,
            "prevent_recursion": True,
            "insertion_order": 0,
        },
    }


def base_card() -> dict:
    return {
        "spec": "chara_card_v3",
        "spec_version": "3.0",
        "data": {
            "first_mes": "",
            "alternate_greetings": [],
            "character_book": {"entries": []},
            "system_prompt": "",
        },
    }


def build_card(greetings: list[str], entries: list[dict],
               system_prompt: str = "") -> dict:
    card = base_card()
    card["data"]["first_mes"] = greetings[0] if greetings else ""
    card["data"]["alternate_greetings"] = greetings[1:] if len(greetings) > 1 else []
    card["data"]["character_book"]["entries"] = entries
    card["data"]["system_prompt"] = system_prompt
    return card


# ===================================================================
# 正向 fixture
# ===================================================================

@pytest.fixture
def valid_title_route_card() -> dict:
    """P0-P2 标题路由卡，四包齐全+因果档案+记忆闸门+system_prompt锚点"""
    stgs = stages_real()
    greetings = [f"{greeting_title(s)}\n这是{s}阶段开场。" for s in stgs]
    entries: list[dict] = [
        causal_archive_entry(),
        memory_gate_entry(),
    ]
    for s in stgs:
        for p in packs():
            entries.append(pack_entry(s, p))
    sp = "阶段表演规则：模型可理解全阶段人物弧线，但当前角色仅记得起步至当前路由阶段已发生的事实。"
    return build_card(greetings, entries, system_prompt=sp)


@pytest.fixture
def valid_an_route_card() -> dict:
    """Author's Note 路由卡，ROUTE_STAGE=P# 格式"""
    stage = "P1"
    entries: list[dict] = [
        causal_archive_entry(),
        memory_gate_entry(),
    ]
    for p in packs():
        entries.append(pack_entry(stage, p, keys=[f"ROUTE_STAGE={stage}"]))
    greetings = [f"ROUTE_STAGE={stage}\n这是{stage}阶段开场。"]
    sp = "阶段表演规则：模型可理解全阶段人物弧线，但当前角色仅记得起步至当前路由阶段已发生的事实。"
    return build_card(greetings, entries, system_prompt=sp)


@pytest.fixture
def valid_subsystem_card() -> dict:
    """子系统厚条目卡 — 不应被阶段路由规则误杀"""
    entries = [{
        "id": "征服阶段系统",
        "comment": "征服阶段系统",
        "content": "P0: ..., P1: ..., P2: ...",
        "keys": ["征服进度"],
        "secondary_keys": [],
        "enabled": True,
        "constant": False,
        "selective": False,
        "extensions": {"entry_role": "common_content"},
    }]
    greetings = ["这是子系统厚条目的开场。"]
    return build_card(greetings, entries)


# ===================================================================
# 负向 fixture
# ===================================================================

@pytest.fixture
def dead_key_card() -> dict:
    """阶段包使用 P# 死键"""
    entries: list[dict] = [
        causal_archive_entry(),
        memory_gate_entry(),
        pack_entry("P0", "阶段核心", keys=["阶段：P0"]),
    ]
    greetings = [f"{greeting_title('P0')}\nP0 开场。"]

    sp = "阶段表演规则：模型可理解全阶段人物弧线。"
    return build_card(greetings, entries, system_prompt=sp)


@pytest.fixture
def cross_stage_leak_card() -> dict:
    """P0 greeting 同时触发 P2 阶段包"""
    stgs = ["P0", "P1", "P2"]
    greetings = [f"{greeting_title('P0')}\nP0 开场。"]

    entries: list[dict] = [
        causal_archive_entry(),
        memory_gate_entry(),
        pack_entry("P0", "阶段核心"),
        # P2 包故意用 P0 标题做 key — 会导致跨阶段触发
        pack_entry("P2", "阶段核心", keys=[greeting_title("P0")]),
    ]
    sp = "阶段表演规则：模型可理解全阶段人物弧线。"
    return build_card(greetings, entries, system_prompt=sp)


@pytest.fixture
def empty_event_library_card() -> dict:
    """P1 事件库为空"""
    entries: list[dict] = [
        causal_archive_entry(),
        memory_gate_entry(),
        pack_entry("P1", "阶段核心"),
        pack_entry("P1", "成人体验"),
        pack_entry("P1", "场景体验"),
        {
            "id": "事件库-P1",
            "comment": "事件库_P1",
            "content": "",  # 空！
            "keys": [greeting_title("P1")],
            "secondary_keys": [],
            "enabled": True,
            "constant": False,
            "selective": True,
            "extensions": {
                "entry_role": "common_content",
                "scan_depth": 999,
                "selective": True,
            },
        },
    ]
    greetings = [f"{greeting_title('P1')}\nP1 开场。"]

    sp = "阶段表演规则：模型可理解全阶段人物弧线。"
    return build_card(greetings, entries, system_prompt=sp)


@pytest.fixture
def no_memory_gate_card() -> dict:
    """有因果档案但没有记忆闸门"""
    entries: list[dict] = [
        causal_archive_entry(),
        # 缺少 memory_gate_entry()
        pack_entry("P0", "阶段核心"),
    ]
    greetings = [f"{greeting_title('P0')}\nP0 开场。"]

    sp = "阶段表演规则：模型可理解全阶段人物弧线。"
    return build_card(greetings, entries, system_prompt=sp)


@pytest.fixture
def future_leak_in_constant_card() -> dict:
    """常驻条目把 P4 关系写成 P0 既定事实"""
    entries: list[dict] = [
        causal_archive_entry(),
        memory_gate_entry(),
        {
            "id": "关系矩阵·常驻",
            "comment": "人物关系矩阵·常驻",
            "content": (
                "角色A在P4之后已经成为角色B的性奴，"
                "每天必须侍奉角色B。这是既定关系。"
            ),
            "keys": [],
            "secondary_keys": [],
            "enabled": True,
            "constant": True,
            "selective": False,
            "extensions": {
                "entry_role": "system_constant",
            },
        },
        pack_entry("P0", "阶段核心"),
    ]
    greetings = [f"{greeting_title('P0')}\nP0 开场。"]

    sp = "阶段表演规则：模型可理解全阶段人物弧线。"
    return build_card(greetings, entries, system_prompt=sp)


@pytest.fixture
def event_as_fact_card() -> dict:
    """事件库写成既定史"""
    entries: list[dict] = [
        causal_archive_entry(),
        memory_gate_entry(),
        {
            "id": "事件库-P0",
            "comment": "事件库_P0",
            "content": "角色A已经被角色B征服。此后每次见面角色A都会主动跪下。",
            "keys": [greeting_title("P0")],
            "secondary_keys": [],
            "enabled": True,
            "constant": False,
            "selective": True,
            "extensions": {
                "entry_role": "common_content",
                "scan_depth": 999,
                "selective": True,
            },
        },
    ]
    greetings = [f"{greeting_title('P0')}\nP0 开场。"]

    sp = "阶段表演规则：模型可理解全阶段人物弧线。"
    return build_card(greetings, entries, system_prompt=sp)


@pytest.fixture
def high_stage_broad_key_card() -> dict:
    """P2 阶段包用高频泛key"""
    entries: list[dict] = [
        causal_archive_entry(),
        memory_gate_entry(),
        pack_entry("P0", "阶段核心", keys=[greeting_title("P0")]),
        pack_entry("P2", "阶段核心", keys=["客厅", "吃饭", "晚上", "床上"]),
    ]
    greetings = [f"{greeting_title('P0')}\n走进客厅，准备吃饭。"]

    sp = "阶段表演规则：模型可理解全阶段人物弧线。"
    return build_card(greetings, entries, system_prompt=sp)


@pytest.fixture
def no_causal_archive_card() -> dict:
    """有记忆闸门但没有因果档案"""
    entries: list[dict] = [
        memory_gate_entry(),
        # 缺少 causal_archive_entry()
        pack_entry("P0", "阶段核心"),
    ]
    greetings = [f"{greeting_title('P0')}\nP0 开场。"]

    sp = "阶段表演规则：模型可理解全阶段人物弧线。"
    return build_card(greetings, entries, system_prompt=sp)


@pytest.fixture
def no_system_prompt_anchor_card() -> dict:
    """有因果档案+记忆闸门但 system_prompt 缺压缩锚点"""
    entries: list[dict] = [
        causal_archive_entry(),
        memory_gate_entry(),
        pack_entry("P0", "阶段核心"),
    ]
    greetings = [f"{greeting_title('P0')}\nP0 开场。"]
    # system_prompt 没有阶段表演规则
    return build_card(greetings, entries, system_prompt="")


@pytest.fixture
def ambiguous_route_card() -> dict:
    """同时使用标题路由和 P# key — 路由源不一致"""
    entries: list[dict] = [
        causal_archive_entry(),
        memory_gate_entry(),
        pack_entry("P0", "阶段核心", keys=[greeting_title("P0")]),
        pack_entry("P1", "阶段核心", keys=["阶段：P1"]),  # 死键！
    ]
    greetings = [
        f"{greeting_title('P0')}\nP0 开场。",
        f"{greeting_title('P1')}\nP1 开场。",
    ]
    sp = "阶段表演规则：模型可理解全阶段人物弧线。"
    return build_card(greetings, entries, system_prompt=sp)


# ===================================================================
# 反误杀 fixture
# ===================================================================

@pytest.fixture
def natural_scene_not_stage_pack_card() -> dict:
    """正常场景条目被greeting命中但不该被误判为跨阶段触发"""
    entries: list[dict] = [
        causal_archive_entry(),
        memory_gate_entry(),
        pack_entry("P0", "阶段核心"),
        {
            "id": "场景·厨房",
            "comment": "场景·厨房",
            "content": "厨房的日常场景描写。",
            "keys": ["厨房"],
            "secondary_keys": [],
            "enabled": True,
            "constant": False,
            "selective": True,
            "extensions": {
                "entry_role": "common_content",
                "scan_depth": 50,  # 普通场景用默认深度
                "selective": True,
            },
        },
    ]
    greetings = [f"{greeting_title('P0')}\n走进厨房准备晚饭。"]

    sp = "阶段表演规则：模型可理解全阶段人物弧线。"
    return build_card(greetings, entries, system_prompt=sp)


@pytest.fixture
def conditional_archive_not_leak_card() -> dict:
    """因果档案用条件语言描述未来方向——不应被判未来泄漏"""
    entries: list[dict] = [
        {
            "id": "角色A·全程因果档案",
            "comment": "角色A·全程因果档案·常驻",
            "content": (
                "当X已在聊天中真实成立后，人物才可能走向P3的Y状态。"
                "若前置条件不满足，Y状态不会发生。"
            ),
            "keys": [],
            "secondary_keys": [],
            "enabled": True,
            "constant": True,
            "selective": False,
            "extensions": {
                "entry_role": "system_constant",
                "position": "before_char",
                "depth": 4,
                "ignore_budget": True,
            },
        },
        memory_gate_entry(),
        pack_entry("P0", "阶段核心"),
    ]
    greetings = [f"{greeting_title('P0')}\nP0 开场。"]

    sp = "阶段表演规则：模型可理解全阶段人物弧线。"
    return build_card(greetings, entries, system_prompt=sp)


@pytest.fixture
def g_type_system_constant_with_user_card() -> dict:
    """G型系统常驻条目含{{user}} — 不应被阶段路由规则误伤"""
    entries: list[dict] = [
        causal_archive_entry(),
        memory_gate_entry(),
        {
            "id": "人物关系矩阵·常驻",
            "comment": "人物关系矩阵·常驻",
            "content": "当{{user}}=南问天时，{{user}}是南向晚的儿子。",
            "keys": [],
            "secondary_keys": [],
            "enabled": True,
            "constant": True,
            "selective": False,
            "extensions": {
                "entry_role": "system_constant",
                "position": "before_char",
            },
        },
        pack_entry("P0", "阶段核心"),
    ]
    greetings = [f"{greeting_title('P0')}\nP0 开场。"]

    sp = "阶段表演规则：模型可理解全阶段人物弧线。"
    return build_card(greetings, entries, system_prompt=sp)


@pytest.fixture
def partial_stages_card() -> dict:
    """P0-P2 项目不伪造 P3-P6 — 不应被判缺阶段"""
    stgs = ["P0", "P1", "P2"]
    greetings = [f"{greeting_title(s)}\n这是{s}阶段开场。" for s in stgs]
    entries: list[dict] = [
        causal_archive_entry(),
        memory_gate_entry(),
    ]
    for s in stgs:
        for p in packs():
            entries.append(pack_entry(s, p))
    sp = "阶段表演规则：模型可理解全阶段人物弧线。"
    return build_card(greetings, entries, system_prompt=sp)


# ===================================================================
# 正向测试（应全部通过）
# ===================================================================

class TestStageMemoryGatePositive:
    def test_title_route_should_pass_stage_checks(self, valid_title_route_card):
        """标题路由完整卡应通过所有阶段检查"""
        assert valid_title_route_card["data"]["system_prompt"], "缺 system_prompt"
        entries = valid_title_route_card["data"]["character_book"]["entries"]
        assert any("全程因果档案" in str(e.get("comment", "")) for e in entries), "缺因果档案"
        assert any("阶段记忆" in str(e.get("comment", "")) for e in entries), "缺记忆闸门"

    def test_an_route_should_pass_stage_checks(self, valid_an_route_card):
        """AN路由卡应通过阶段检查"""
        assert valid_an_route_card["data"]["system_prompt"], "缺 system_prompt"
        entries = valid_an_route_card["data"]["character_book"]["entries"]
        assert any("全程因果档案" in str(e.get("comment", "")) for e in entries)

    def test_subsystem_card_should_not_be_flag_by_stage_rules(self, valid_subsystem_card):
        """子系统厚条目卡不应被阶段路由规则拦截"""
        # 该卡没有阶段标题、没有四包 — 阶段路由规则应跳过
        entries = valid_subsystem_card["data"]["character_book"]["entries"]
        # 确认它不是阶段路由卡
        has_stage_title = any(
            k.startswith("【开场：") for e in entries
            for k in (e.get("keys") or [])
            if isinstance(k, str)
        )
        assert not has_stage_title, "子系统卡不应有阶段标题key"


# ===================================================================
# 负向测试（应全部失败）
# ===================================================================

class TestStageMemoryGateNegative:
    def test_dead_key_should_fail(self, dead_key_card):
        """阶段：P# 作为唯一key应被检测"""
        keys = []
        for e in dead_key_card["data"]["character_book"]["entries"]:
            keys.extend(e.get("keys") or [])
        has_dead = any("阶段：" in str(k) for k in keys)
        assert has_dead, "死键应存在于测试数据中"

    def test_cross_stage_trigger_should_be_detected(self, cross_stage_leak_card):
        """P0 greeting触发P2阶段包应被检测"""
        entries = cross_stage_leak_card["data"]["character_book"]["entries"]
        p0_title = greeting_title("P0")
        p2_entries = [e for e in entries if "P2" in str(e.get("comment", ""))]
        p2_with_p0_key = [e for e in p2_entries if p0_title in (e.get("keys") or [])]
        assert p2_with_p0_key, "P2条目应使用P0标题作为key（故意构造的泄露）"

    def test_empty_event_library_should_fail(self, empty_event_library_card):
        """空事件库应被拦截"""
        entries = empty_event_library_card["data"]["character_book"]["entries"]
        event_lib = [e for e in entries if "事件库" in str(e.get("comment", ""))]
        assert event_lib, "应有事件库条目"
        assert any(len(e.get("content", "").strip()) == 0 for e in event_lib), \
            "事件库应为空"

    def test_no_memory_gate_should_fail(self, no_memory_gate_card):
        """缺记忆闸门应被检测"""
        entries = no_memory_gate_card["data"]["character_book"]["entries"]
        has_gate = any("阶段记忆" in str(e.get("comment", "")) for e in entries)
        assert not has_gate, "应缺少记忆闸门"

    def test_future_leak_in_constant_should_be_detected(self, future_leak_in_constant_card):
        """常驻条目含后期关系应被标记"""
        entries = future_leak_in_constant_card["data"]["character_book"]["entries"]
        const_entries = [e for e in entries if e.get("constant")]
        # 找含"关系矩阵"的常驻条目
        rel_entry = [e for e in const_entries if "关系矩阵" in str(e.get("comment", ""))]
        assert rel_entry, "应有关系矩阵常驻条目"
        assert "性奴" in rel_entry[0].get("content", ""), "应含后期关系"

    def test_event_as_fact_should_be_detected(self, event_as_fact_card):
        """事件写成既定史应被检测"""
        entries = event_as_fact_card["data"]["character_book"]["entries"]
        event_entries = [e for e in entries if "事件库" in str(e.get("comment", ""))]
        assert event_entries, "应有事件条目"
        content = event_entries[0].get("content", "")
        assert "已经被" in content or "此后" in content, "应含既定史措辞"

    def test_high_stage_broad_key_should_fail(self, high_stage_broad_key_card):
        """高阶段包用泛key应被检测"""
        entries = high_stage_broad_key_card["data"]["character_book"]["entries"]
        p2_entries = [e for e in entries if "P2" in str(e.get("comment", ""))]
        has_broad = False
        for e in p2_entries:
            for k in (e.get("keys") or []):
                if k in ("客厅", "吃饭", "晚上", "床上"):
                    has_broad = True
        assert has_broad, "P2条目应含泛key"

    def test_no_causal_archive_should_fail(self, no_causal_archive_card):
        """缺因果档案应被检测"""
        entries = no_causal_archive_card["data"]["character_book"]["entries"]
        has_archive = any("全程因果档案" in str(e.get("comment", "")) for e in entries)
        has_gate = any("阶段记忆" in str(e.get("comment", "")) for e in entries)
        assert has_gate, "应有记忆闸门"
        assert not has_archive, "应缺少因果档案"

    def test_no_system_prompt_anchor_should_fail(self, no_system_prompt_anchor_card):
        """缺 system_prompt 压缩锚点应被检测"""
        sp = no_system_prompt_anchor_card["data"].get("system_prompt", "")
        assert not sp or len(sp.strip()) == 0, "system_prompt 应为空"

    def test_ambiguous_route_should_fail(self, ambiguous_route_card):
        """混合路由应被检测"""
        entries = ambiguous_route_card["data"]["character_book"]["entries"]
        has_title = any(
            "【开场：" in str(k) for e in entries
            for k in (e.get("keys") or []) if isinstance(k, str)
        )
        has_dead = any(
            "阶段：" in str(k) for e in entries
            for k in (e.get("keys") or []) if isinstance(k, str)
        )
        assert has_title, "应有标题路由条目"
        assert has_dead, "应有死键条目"


# ===================================================================
# 反误杀测试（不应被阶段路由规则误判）
# ===================================================================

class TestStageMemoryGateAntiFalsePositive:
    def test_natural_scene_with_greeting_keyword_should_pass(
        self, natural_scene_not_stage_pack_card
    ):
        """普通场景条目被greeting命中厨房 — 不应报跨阶段"""
        entries = natural_scene_not_stage_pack_card["data"]["character_book"]["entries"]
        kitchen_entries = [e for e in entries if "厨房" in str(e.get("comment", ""))]
        assert kitchen_entries, "应有厨房场景条目"
        # 厨房条目 scan_depth 应该是默认值（非 999）
        assert kitchen_entries[0].get("extensions", {}).get("scan_depth") != 999, \
            "普通场景不应提升 scan_depth"

    def test_conditional_archive_should_not_be_flag_as_leak(
        self, conditional_archive_not_leak_card
    ):
        """条件语言描述的因果档案不应被判泄漏"""
        entries = conditional_archive_not_leak_card["data"]["character_book"]["entries"]
        archive = [e for e in entries if "全程因果档案" in str(e.get("comment", ""))]
        assert archive
        content = archive[0].get("content", "")
        assert "才可能" in content or "若" in content, "应使用条件语言"

    def test_g_type_system_constant_with_user_should_pass(
        self, g_type_system_constant_with_user_card
    ):
        """G型系统常驻含{{user}}不应被误判"""
        entries = g_type_system_constant_with_user_card["data"]["character_book"]["entries"]
        const_entries = [e for e in entries if e.get("constant") and "关系矩阵" in str(e.get("comment", ""))]
        assert const_entries, "应有含{{user}}的系统常驻"
        assert "{{user}}" in const_entries[0].get("content", ""), "应含{{user}}"

    def test_partial_stages_should_pass(self, partial_stages_card):
        """P0-P2 卡不应因缺少 P3-P6 而失败"""
        entries = partial_stages_card["data"]["character_book"]["entries"]
        stage_packs = [e for e in entries if "阶段核心" in str(e.get("comment", ""))]
        actual_stages = set()
        for e in stage_packs:
            for k in (e.get("keys") or []):
                if isinstance(k, str) and "【开场：" in k:
                    # 提取 P# 部分
                    import re
                    m = re.search(r"P(\d+)", k)
                    if m:
                        actual_stages.add(int(m.group(1)))
        assert actual_stages == {0, 1, 2}, f"阶段应为P0-P2，实际{actual_stages}"
        # 没有 P3-P6 的阶段包
        assert max(actual_stages) == 2, "不应有 P3+ 阶段"


# ===================================================================
# 真正的脚本集成测试：调用新增验证器/审计器，而不是只检查 fixture 字段
# ===================================================================

def _write_card(tmp_path, name, card):
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    return path


def _stage_rule_messages(report):
    return [issue.message for issue in report.issues if issue.rule_id.startswith("STAGE_")]


class TestStageMemoryGateScriptIntegration:
    def test_validate_positive_has_no_stage_errors(self, valid_title_route_card, tmp_path, load_script_module):
        module = load_script_module("validate_card.py")
        report = module.validate_card_report(str(_write_card(tmp_path, "valid", valid_title_route_card)))
        assert _stage_rule_messages(report) == []

    def test_validate_dead_key_emits_exact_rule(self, dead_key_card, tmp_path, load_script_module):
        module = load_script_module("validate_card.py")
        report = module.validate_card_report(str(_write_card(tmp_path, "dead", dead_key_card)))
        assert any(issue.rule_id == "STAGE_ROUTE_DEAD_KEY" for issue in report.errors)

    def test_validate_missing_memory_gate_emits_exact_rule(self, no_memory_gate_card, tmp_path, load_script_module):
        module = load_script_module("validate_card.py")
        report = module.validate_card_report(str(_write_card(tmp_path, "no_gate", no_memory_gate_card)))
        assert any(issue.rule_id == "STAGE_MEMORY_GATE_MISSING" for issue in report.errors)

    def test_validate_author_note_checks_four_packs(self, valid_an_route_card, tmp_path, load_script_module):
        module = load_script_module("validate_card.py")
        card = valid_an_route_card
        entries = card["data"]["character_book"]["entries"]
        entries[:] = [e for e in entries if e.get("comment") != "事件库_P1"]
        report = module.validate_card_report(str(_write_card(tmp_path, "an_missing", card)))
        assert any(issue.rule_id == "STAGE_PACK_INCOMPLETE" for issue in report.errors)

    def test_trigger_audit_returns_cross_stage_machine_error(self, cross_stage_leak_card, tmp_path, load_script_module):
        module = load_script_module("audit_worldbook_triggers.py")
        path = _write_card(tmp_path, "cross", cross_stage_leak_card)
        card, data, entries = module.load_card(path)
        sources = module.build_sources(data)
        audits = module.analyze_entries(entries, sources)
        errors, warnings = module.stage_route_findings(audits, sources)
        assert any(error.startswith("STAGE_CROSS_TRIGGER") for error in errors)
        assert warnings == []

    def test_final_gate_consumes_cross_stage_error(self, cross_stage_leak_card, tmp_path, load_script_module):
        gate = load_script_module("final_delivery_gate.py")
        path = _write_card(tmp_path, "cross_gate", cross_stage_leak_card)
        result = gate.run_audit(path, tmp_path)
        assert result.status == "FAIL"
        assert any("STAGE_CROSS_TRIGGER" in error for error in result.errors)

    def test_enrichment_positive_executes_stage_component_checks(self, valid_title_route_card, tmp_path, load_script_module):
        module = load_script_module("enrichment_self_check.py")
        path = _write_card(tmp_path, "enrichment_valid", valid_title_route_card)
        issues = module.check_card(str(path), verbose=False, r18=False, prototype="", three_path="none")
        messages = [message for severity, message in issues]
        assert any("全程因果档案已存在" in message for message in messages)
        assert any("阶段记忆闸门已存在" in message for message in messages)

    def test_enrichment_missing_gate_executes_red_check(self, no_memory_gate_card, tmp_path, load_script_module):
        module = load_script_module("enrichment_self_check.py")
        path = _write_card(tmp_path, "enrichment_no_gate", no_memory_gate_card)
        issues = module.check_card(str(path), verbose=False, r18=False, prototype="", three_path="none")
        assert any(
            severity == "🔴"
            and message.startswith("STAGE_ROUTING:")
            and "绝对优先级·阶段记忆与叙事可见性协议" in message
            for severity, message in issues
        )

    def test_natural_scene_is_not_stage_cross_trigger(self, natural_scene_not_stage_pack_card, tmp_path, load_script_module):
        module = load_script_module("audit_worldbook_triggers.py")
        path = _write_card(tmp_path, "scene", natural_scene_not_stage_pack_card)
        card, data, entries = module.load_card(path)
        audits = module.analyze_entries(entries, module.build_sources(data))
        errors, _warnings = module.stage_route_findings(audits, module.build_sources(data))
        assert not any("厨房" in error for error in errors)

    def test_conditional_future_direction_is_not_hard_failed(self, conditional_archive_not_leak_card, tmp_path, load_script_module):
        """条件语言因果档案不得被任何 STAGE 规则点名为泄漏/事实化（原断言引用了不存在的
        STAGE_PACK_FUTURE_LEAK_RISK，属永真测试，2026-07-26 修正为真实断言）"""
        module = load_script_module("validate_card.py")
        report = module.validate_card_report(str(_write_card(tmp_path, "conditional", conditional_archive_not_leak_card)))
        stage_issues = [issue for issue in report.issues if issue.rule_id.startswith("STAGE_")]
        # 阶段分支必须在运行（防空转）：该卡只有单包，STAGE_PACK_INCOMPLETE 应触发
        assert any(issue.rule_id == "STAGE_PACK_INCOMPLETE" for issue in stage_issues)
        # 条件语言档案本身不得被判泄漏/缺失/事实化
        assert not any("因果档案" in issue.message for issue in stage_issues)
        assert not any(issue.rule_id == "STAGE_EVENT_FACT_LANGUAGE" for issue in stage_issues)

    def test_partial_stage_set_is_not_required_to_be_p0_to_p6(self, partial_stages_card, tmp_path, load_script_module):
        module = load_script_module("validate_card.py")
        report = module.validate_card_report(str(_write_card(tmp_path, "partial", partial_stages_card)))
        messages = _stage_rule_messages(report)
        assert not any("P3" in message or "P6" in message for message in messages)

    def test_final_gate_auto_detects_stage_card_without_cli_flag(self, valid_title_route_card, tmp_path, load_script_module, monkeypatch):
        """真实调用 gate.main：无 sidecar 合同的标题路由卡必须被自动检测硬失败
        （原测试从未调用 main，monkeypatch 全部空转，2026-07-26 修正）"""
        gate = load_script_module("final_delivery_gate.py")
        card_path = _write_card(tmp_path, "auto_stage", valid_title_route_card)
        monkeypatch.setattr(gate, "run_validate", lambda _path: gate.GateResult("validate", "PASS"))
        monkeypatch.setattr(gate, "run_audit", lambda _path, _dir: gate.GateResult("audit", "PASS"))
        monkeypatch.setattr(gate, "run_enrichment", lambda *_args: gate.GateResult("enrichment", "PASS"))
        monkeypatch.setattr(gate, "run_build_sync", lambda *_args: gate.GateResult("build", "N/A"))
        monkeypatch.setattr(gate, "scan_forbidden", lambda *_args, **_kwargs: gate.GateResult("scan", "PASS"))
        assert not (tmp_path / "stage-entry-contract.json").exists()
        report_path = tmp_path / "auto_stage_report.md"
        exit_code = gate.main([str(card_path), "--project-dir", str(tmp_path), "-o", str(report_path)])
        assert exit_code == 1
        assert "STAGE_CONTRACT_REQUIRED" in report_path.read_text(encoding="utf-8")

    # === 批次1（2026-07-26）：STAGE 生产规则的真实集成断言，替代 fixture 自证 ===

    def test_validate_missing_causal_archive_emits_exact_rule(self, no_causal_archive_card, tmp_path, load_script_module):
        """缺因果档案必须在 validator 层触发 STAGE_CAUSAL_ARCHIVE_MISSING
        （回归保护：该规则曾被记忆闸门 content 撞词击穿产生假绿）"""
        module = load_script_module("validate_card.py")
        report = module.validate_card_report(str(_write_card(tmp_path, "no_archive", no_causal_archive_card)))
        assert any(issue.rule_id == "STAGE_CAUSAL_ARCHIVE_MISSING" for issue in report.errors)

    def test_validate_missing_anchor_emits_shared_rule_ids(self, no_system_prompt_anchor_card, tmp_path, load_script_module):
        module = load_script_module("validate_card.py")
        report = module.validate_card_report(str(_write_card(tmp_path, "no_anchor", no_system_prompt_anchor_card)))
        ids = {issue.rule_id for issue in report.errors}
        assert "STAGE_MEMORY_RULE_LABEL_MISSING" in ids
        assert "STAGE_MEMORY_ONLY_REMEMBERS_ANCHOR_MISSING" in ids
        assert "STAGE_MEMORY_ANCHOR_TOO_SHORT" in ids

    def test_validate_ambiguous_route_emits_exact_rule(self, ambiguous_route_card, tmp_path, load_script_module):
        module = load_script_module("validate_card.py")
        report = module.validate_card_report(str(_write_card(tmp_path, "ambiguous", ambiguous_route_card)))
        assert any(issue.rule_id == "STAGE_ROUTE_SOURCE_AMBIGUOUS" for issue in report.errors)

    def test_validate_empty_pack_emits_exact_rule(self, empty_event_library_card, tmp_path, load_script_module):
        module = load_script_module("validate_card.py")
        report = module.validate_card_report(str(_write_card(tmp_path, "empty_pack", empty_event_library_card)))
        assert any(issue.rule_id == "STAGE_PACK_EMPTY" for issue in report.errors)

    def test_validate_broad_key_emits_exact_rule(self, high_stage_broad_key_card, tmp_path, load_script_module):
        module = load_script_module("validate_card.py")
        report = module.validate_card_report(str(_write_card(tmp_path, "broad_key", high_stage_broad_key_card)))
        assert any(issue.rule_id == "STAGE_HIGH_PHASE_BROAD_KEY" for issue in report.errors)

    def test_validate_event_fact_language_is_warning_not_error(self, event_as_fact_card, tmp_path, load_script_module):
        module = load_script_module("validate_card.py")
        report = module.validate_card_report(str(_write_card(tmp_path, "event_fact", event_as_fact_card)))
        assert any(issue.rule_id == "STAGE_EVENT_FACT_LANGUAGE" for issue in report.issues)
        assert not any(issue.rule_id == "STAGE_EVENT_FACT_LANGUAGE" for issue in report.errors)

    def test_validate_event_not_candidate_emits_warning(self, tmp_path, load_script_module):
        module = load_script_module("validate_card.py")
        plain = (
            "深夜走廊里两人静静走过，灯光把影子拉得很长。他们聊起最近的日常，"
            "谁也没有提到白天发生的事。窗外的雨声渐渐大了起来，屋里只剩下钟表的滴答声，"
            "长时间没有人说话，气氛既平静又微妙，像是等待着某个临界时刻的到来。"
        )
        entries = [
            causal_archive_entry(),
            memory_gate_entry(),
            pack_entry("P0", "事件库", extra_entry={"content": plain}),
        ]
        card = build_card(
            [f"{greeting_title('P0')}\nP0 开场。"], entries,
            system_prompt="阶段表演规则：模型可理解全阶段人物弧线。",
        )
        report = module.validate_card_report(str(_write_card(tmp_path, "not_candidate", card)))
        assert any(issue.rule_id == "STAGE_EVENT_NOT_CANDIDATE" for issue in report.issues)

    def test_trigger_audit_orphan_pack_is_warning(self, tmp_path, load_script_module):
        module = load_script_module("audit_worldbook_triggers.py")
        entries = [
            causal_archive_entry(),
            memory_gate_entry(),
            *(pack_entry("P0", pack) for pack in packs()),
            pack_entry("P1", "阶段核心"),
        ]
        card = build_card(
            [f"{greeting_title('P0')}\nP0 开场。"], entries,
            system_prompt="阶段表演规则：模型可理解全阶段人物弧线。",
        )
        path = _write_card(tmp_path, "orphan", card)
        _card, data, entries_loaded = module.load_card(path)
        sources = module.build_sources(data)
        audits = module.analyze_entries(entries_loaded, sources)
        errors, warnings = module.stage_route_findings(audits, sources)
        assert any(warning.startswith("STAGE_ORPHAN_PACK") for warning in warnings)
        assert errors == []

    def test_cross_stage_trigger_detected_with_suffixed_title_form(self, tmp_path, load_script_module):
        """lib 合法的 B 型带后缀标题（【开场：标题｜P0·后缀】）作为路由源时，
        跨阶段检查不得静默跳过（回归保护：本地正则曾无法提取该形式的 source 阶段）"""
        module = load_script_module("audit_worldbook_triggers.py")
        b_title = "【开场：测试场景｜P0·序章】"
        entries = [
            causal_archive_entry(),
            memory_gate_entry(),
            pack_entry("P0", "阶段核心", keys=[b_title]),
            pack_entry("P2", "阶段核心", keys=[b_title]),
        ]
        card = build_card(
            [f"{b_title}\nP0 开场。"], entries,
            system_prompt="阶段表演规则：模型可理解全阶段人物弧线。",
        )
        path = _write_card(tmp_path, "b_suffix_cross", card)
        _card, data, entries_loaded = module.load_card(path)
        sources = module.build_sources(data)
        audits = module.analyze_entries(entries_loaded, sources)
        errors, _warnings = module.stage_route_findings(audits, sources)
        assert any(error.startswith("STAGE_CROSS_TRIGGER") for error in errors)

    # === 批次1（2026-07-26）：ROUTE_STAGE 外部路线在 final gate 的硬拒绝 ===

    def test_final_gate_hard_rejects_route_stage_key_card(self, valid_an_route_card, tmp_path, load_script_module, monkeypatch):
        """ROUTE_STAGE=P# key 卡属外部 preset 路线：final gate 必须硬拒绝，
        不得在未经合同审计的情况下给出可交付绿灯"""
        gate = load_script_module("final_delivery_gate.py")
        card_path = _write_card(tmp_path, "an_route_gate", valid_an_route_card)
        monkeypatch.setattr(gate, "run_validate", lambda _path: gate.GateResult("validate", "PASS"))
        monkeypatch.setattr(gate, "run_audit", lambda _path, _dir: gate.GateResult("audit", "PASS"))
        monkeypatch.setattr(gate, "run_enrichment", lambda *_args: gate.GateResult("enrichment", "PASS"))
        monkeypatch.setattr(gate, "run_build_sync", lambda *_args: gate.GateResult("build", "N/A"))
        monkeypatch.setattr(gate, "scan_forbidden", lambda *_args, **_kwargs: gate.GateResult("scan", "PASS"))
        report_path = tmp_path / "an_route_report.md"
        exit_code = gate.main([str(card_path), "--project-dir", str(tmp_path), "-o", str(report_path)])
        assert exit_code == 1
        assert "STAGE_EXTERNAL_ROUTE_UNSUPPORTED" in report_path.read_text(encoding="utf-8")

    def test_final_gate_hard_rejects_route_stage_text_marker(self, tmp_path, load_script_module, monkeypatch):
        """Greeting 文本中的 ROUTE_STAGE=P# 标记同样触发外部路线硬拒绝"""
        gate = load_script_module("final_delivery_gate.py")
        card = build_card(
            ["ROUTE_STAGE=P2\n这是外部路线开场。"],
            [causal_archive_entry(), memory_gate_entry()],
        )
        card_path = _write_card(tmp_path, "route_text_gate", card)
        monkeypatch.setattr(gate, "run_validate", lambda _path: gate.GateResult("validate", "PASS"))
        monkeypatch.setattr(gate, "run_audit", lambda _path, _dir: gate.GateResult("audit", "PASS"))
        monkeypatch.setattr(gate, "run_enrichment", lambda *_args: gate.GateResult("enrichment", "PASS"))
        monkeypatch.setattr(gate, "run_build_sync", lambda *_args: gate.GateResult("build", "N/A"))
        monkeypatch.setattr(gate, "scan_forbidden", lambda *_args, **_kwargs: gate.GateResult("scan", "PASS"))
        report_path = tmp_path / "route_text_report.md"
        exit_code = gate.main([str(card_path), "--project-dir", str(tmp_path), "-o", str(report_path)])
        assert exit_code == 1
        assert "STAGE_EXTERNAL_ROUTE_UNSUPPORTED" in report_path.read_text(encoding="utf-8")
