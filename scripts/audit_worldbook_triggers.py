#!/usr/bin/env python3
"""
Worldbook trigger reachability audit for SillyTavern character cards.

Outputs a Markdown report that explains which worldbook entries are triggered by
first_mes / alternate_greetings, why they trigger, and which entries are at risk
of false positives, dead triggers, or token pollution.

Usage:
    python scripts/audit_worldbook_triggers.py <card.json> [-o report.md]

Designed to match SillyTavern v1.18 world-info.js trigger behavior closely:
- primary key must match first;
- top-level entry.selective controls secondary matching;
- secondary_keys only participate when top-level selective=true and non-empty;
- selective=true + secondary_keys=[] falls back to primary-only;
- extensions.selective alone does not enable selective logic;
- selectiveLogic: 0 AND_ANY, 1 NOT_ALL, 2 NOT_ANY, 3 AND_ALL;
- /regex/flags keys are supported approximately via Python re.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from lib.stage_routing import parse_stage_title, parse_title, title_matches
from lib.worldbook_matcher import MatchResult, entry_trigger_match, match_key, parse_regex_from_string

ROUTE_STAGE_TEXT_RE = re.compile(r"\bROUTE_STAGE=P(\d+)\b")


def _stage_number_from_text(text: str) -> Optional[int]:
    """Extract the stage number from greeting/source text via the shared grammar.

    Uses the canonical lib/stage_routing TITLE_RE (both title forms, including
    suffixed variants) first, then the external ROUTE_STAGE marker.
    """
    matches = title_matches(text or "")
    if matches:
        stage, _title = parse_title(matches[0])
        if stage == "MENU":
            return None
        return int(stage[1:])
    marker = ROUTE_STAGE_TEXT_RE.search(text or "")
    if marker:
        return int(marker.group(1))
    return None


def _stage_number_from_key(key: object) -> Optional[int]:
    """Extract the stage number from an entry key via the shared grammar."""
    parsed = parse_stage_title(str(key))
    if parsed:
        if parsed[0] == "MENU":
            return None
        return int(parsed[0][1:])
    marker = re.match(r"ROUTE_STAGE=P(\d+)$", str(key).strip())
    if marker:
        return int(marker.group(1))
    return None

HARD_GENERIC_KEYS = {"你", "我", "他", "她", "它", "家", "人"}
SOFT_GENERIC_KEYS = {
    "学校", "教室", "老师", "社团", "房间", "地方", "这里", "那里",
    "前辈", "同学", "男生", "女生", "体育馆", "唱歌", "客厅", "卧室", "浴室",
}
GENERIC_PROBES = [
    "我要回家。",
    "学校今天很安静。",
    "老师让我去教室。",
    "有人在房间里唱歌。",
    "你看见那个人了吗？",
    "这里有很多人。",
    "他和她都在那个地方。",
]

LOGIC_NAMES = {0: "AND_ANY", 1: "NOT_ALL", 2: "NOT_ANY", 3: "AND_ALL"}


@dataclass
class EntryAudit:
    entry: Dict[str, Any]
    source_matches: Dict[str, MatchResult] = field(default_factory=dict)
    probe_matches: Dict[str, MatchResult] = field(default_factory=dict)
    risks: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    @property
    def eid(self) -> Any:
        return self.entry.get("id", "?")

    @property
    def comment(self) -> str:
        return str(self.entry.get("comment", ""))

    @property
    def keys(self) -> List[str]:
        value = self.entry.get("keys", self.entry.get("key", []))
        if isinstance(value, str):
            return [value]
        return [str(k) for k in value if k] if isinstance(value, list) else []

    @property
    def secondary_keys(self) -> List[str]:
        return [str(k) for k in self.entry.get("secondary_keys", []) if k]

    @property
    def is_constant(self) -> bool:
        return bool(self.entry.get("constant"))

    @property
    def is_enabled(self) -> bool:
        return bool(self.entry.get("enabled", True))

    @property
    def selective(self) -> bool:
        return self.entry.get("selective") is True

    @property
    def selective_logic(self) -> int:
        logic = self.entry.get("selectiveLogic", self.entry.get("extensions", {}).get("selectiveLogic", 0))
        try:
            return int(logic)
        except Exception:
            return 0

    @property
    def ext_selective(self) -> Optional[bool]:
        ext = self.entry.get("extensions", {}) or {}
        if "selective" not in ext:
            return None
        return ext.get("selective") is True

    @property
    def content_len(self) -> int:
        return len(str(self.entry.get("content", "")))

    @property
    def role(self) -> str:
        explicit = (self.entry.get("extensions") or {}).get("entry_role")
        return str(explicit) if explicit else "inferred"

    @property
    def natural_path_types(self) -> str:
        text = " ".join([self.comment, *self.keys, str(self.entry.get("content", ""))[:500]])
        groups = {
            "人物": ("人物", "角色", "档案", "关系", "南问天", "南向晚", "陆雪儿", "红莲", "莫埃"),
            "场景": ("地点", "场景", "院门", "院子", "青云村", "主屋", "山路", "殿", "厨房"),
            "行动": ("动作", "敲门", "走", "来到", "闯入", "战斗", "反抗", "操", "征服", "冲突"),
        }
        return "/".join(name for name, markers in groups.items() if any(m in text for m in markers)) or "-"

    @property
    def meta_label_only(self) -> bool:
        labels = {"事件库", "种子库", "描写库", "语料库", "对话库", "人物档案", "角色档案", "设定", "感官", "氛围", "档案"}
        return bool(self.keys) and all(k in labels for k in self.keys)


def markdown_escape(text: Any) -> str:
    s = str(text)
    s = s.replace("\n", "<br>").replace("|", "\\|")
    return s


def shorten(text: Any, limit: int = 34) -> str:
    s = str(text).replace("\n", " ").strip()
    if len(s) <= limit:
        return s
    return s[: max(0, limit - 1)] + "…"


def load_card(path: Path) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as f:
        card = json.load(f)
    data = card.get("data", card)
    cb = data.get("character_book") or card.get("character_book") or {}
    entries = cb.get("entries", [])
    if isinstance(entries, dict):
        entries = list(entries.values())
    if not isinstance(entries, list):
        raise ValueError("character_book.entries is not a list/dict")
    return card, data, entries


ENTRY_ROLES = {"identity_toggle", "feature_toggle", "system_constant", "common_content"}


def infer_entry_role(entry: Dict[str, Any]) -> str:
    explicit = (entry.get("extensions") or {}).get("entry_role")
    if explicit in ENTRY_ROLES:
        return explicit
    content = str(entry.get("content", ""))
    comment = str(entry.get("comment", ""))
    if entry.get("constant") and not entry.get("enabled", True) and "{{user}}" in content:
        return "identity_toggle"
    if entry.get("constant") and entry.get("enabled", True) and not entry.get("keys", []):
        if any(marker in comment or marker in content for marker in ("剧情导演", "场景边界", "功能开关")):
            return "feature_toggle"
        return "system_constant"
    return "common_content"


def infer_content_type(entry: Dict[str, Any]) -> str:
    role = infer_entry_role(entry)
    if role == "identity_toggle":
        return "G型身份选开"
    if role == "feature_toggle":
        return "功能开关"
    if role == "system_constant":
        return "系统/常驻"
    if role == "common_content":
        comment = str(entry.get("comment", ""))
        if "事件" in comment or "种子" in comment:
            return "自然事件"
        if "场景" in comment or "地点" in comment:
            return "场景"
        if "语料" in comment or "描写" in comment:
            return "辅助素材"
        return "共享内容"
    comment = str(entry.get("comment", ""))
    if entry.get("constant"):
        if "➡️" in comment:
            return "分段标记"
        return "系统/常驻"
    if not entry.get("enabled", True):
        if "事件" in comment or "种子" in comment:
            return "事件种子"
        return "禁用模块"
    for label, kws in [
        ("人物", ["角色", "档案", "性格", "描写库", "语料"]),
        ("场景", ["场景", "地点", "教室", "家", "KTV", "更衣室", "包间"]),
        ("关系", ["关系", "矩阵", "×"]),
        ("事件", ["事件", "剧情", "节点"]),
        ("规则", ["规则", "系统", "状态", "OOC", "文风", "反顺从"]),
    ]:
        if any(k in comment for k in kws):
            return label
    return "触发条目"


def infer_trigger_intent(entry: Dict[str, Any]) -> str:
    role = infer_entry_role(entry)
    explicit_role = (entry.get("extensions") or {}).get("entry_role")
    comment = str(entry.get("comment", ""))
    if explicit_role == "identity_toggle":
        return "G型选开身份"
    if explicit_role == "feature_toggle":
        return "功能开关（默认常驻，可UI关闭）"
    if explicit_role == "system_constant":
        return "系统常驻"
    if explicit_role == "common_content":
        if "事件" in comment or "种子" in comment:
            return "自然事件·OR触发"
        if "场景" in comment or "地点" in comment:
            return "自然场景触发"

    if entry.get("constant") and not entry.get("enabled", True) and "{{user}}" in str(entry.get("content", "")):
        return "G型选开身份"
    if entry.get("constant"):
        return "常驻规则"
    if not entry.get("enabled", True):
        return "手动/条件模块"
    if entry.get("selective") is True and entry.get("secondary_keys"):
        return "范围绑定/阶段限定"
    if entry.get("selective") is True and not entry.get("secondary_keys"):
        return "primary-only（selective空副词）"
    return "primary-only"


def analyze_entries(entries: List[Dict[str, Any]], sources: List[Tuple[str, str]]) -> List[EntryAudit]:
    audits: List[EntryAudit] = []
    for entry in entries:
        ea = EntryAudit(entry=entry)
        for label, text in sources:
            ea.source_matches[label] = entry_trigger_match(entry, text)
        for probe in GENERIC_PROBES:
            ea.probe_matches[probe] = entry_trigger_match(entry, probe)
        classify_risks(ea, sources)
        audits.append(ea)
    return audits


def classify_risks(ea: EntryAudit, sources: List[Tuple[str, str]]) -> None:
    e = ea.entry
    if ea.is_constant:
        if ea.keys and ea.is_enabled:
            ea.risks.append("常驻条目keys非空")
            ea.suggestions.append("常驻规则条目应 keys=[]；选开身份除外且应 enabled=false")
        return

    if not ea.is_enabled:
        return

    keys = ea.keys
    sec = ea.secondary_keys
    hard = [k for k in keys if k in HARD_GENERIC_KEYS or len(k) <= 1]
    soft = [k for k in keys if k in SOFT_GENERIC_KEYS]
    scoped = ea.selective and bool(sec)

    if hard:
        ea.risks.append(f"硬泛key: {', '.join(hard)}")
        ea.suggestions.append("删除单字/代词泛key，改为专名或范围绑定")
    if soft and not scoped:
        ea.risks.append(f"软泛key未范围绑定: {', '.join(soft)}")
        ea.suggestions.append("软泛场景词建议用顶层selective=true + secondary_keys=[上级范围]")

    if sec and not ea.selective:
        ea.risks.append("secondary_keys被忽略")
        ea.suggestions.append("若副词用于缩小范围，补顶层selective=true；若只是备注，清空secondary_keys")

    if ea.ext_selective is True and not ea.selective and sec:
        ea.risks.append("仅extensions.selective=true")
        ea.suggestions.append("ST读取顶层selective；补顶层selective=true并同步extensions.selective")
    elif ea.ext_selective is not None and ea.ext_selective != ea.selective:
        ea.risks.append("顶层/extension selective不一致")
        ea.suggestions.append("同步顶层selective与extensions.selective，避免维护误判")

    explicit_role = (e.get("extensions") or {}).get("entry_role")
    is_natural_or_event = (
        explicit_role == "common_content"
        and ("事件" in str(e.get("comment", "")) or "种子" in str(e.get("comment", "")))
        and ea.is_enabled
    )
    if len(keys) >= 4 and str(e.get("content", "")).count("【") >= 3 and not scoped:
        if is_natural_or_event:
            ea.risks.append("OR自然事件并行触发（已接受）")
            ea.suggestions.append("本卡明确采用多个自然关键词OR匹配；该并行触发策略已接受。共享key、并行加载和估算负载仅作诊断，不改死key、不改阶段AND锁")
        else:
            ea.risks.append("多主题大条目")
            ea.suggestions.append("按角色/威胁对象拆分，或用selective限定作用域")

    # Triggered by hard generic only in real greetings.
    for label, mr in ea.source_matches.items():
        if mr.ok and mr.primary_hits and all(k in HARD_GENERIC_KEYS or len(k) <= 1 for k in mr.primary_hits):
            ea.risks.append(f"{label}仅靠硬泛key触发")
            ea.suggestions.append("这类触发属于噪声加载，必须改key")

    # Probe-trigger false positive.
    probe_hits = [probe for probe, mr in ea.probe_matches.items() if mr.ok]
    if probe_hits and (hard or soft or not scoped):
        ea.risks.append(f"普通句反证可触发{len(probe_hits)}次")
        ea.suggestions.append("用普通聊天反证清理泛key；避免无关上下文加载")

    # 下面两段风险分类都会用到 comment/content；必须在 if 外初始化，
    # 否则当 keys 为空或已有开场白触发时，后续“档案后缀死 key”检查会引用未定义变量。
    comment = str(e.get('comment', ''))
    content = str(e.get('content', ''))

    if keys and not any(mr.ok for mr in ea.source_matches.values()):
        # 区分核心档案/冷门条目。
        # 工具/助手卡（如萧谴写卡助手）的“角色生成/世界观创作/开场白生成”条目
        # 本来就应该由明确命令触发，首轮不触发不是死 key，不要误报为角色档案缺自然名。
        command_words = ['生成', '创建', '构建', '打造', '创立', '设计', '制定', '拟定', '修改', '删除', '发帖']
        is_tool_command = (
            any(kw in comment for kw in ['助手', '创作', '生成', '一键发帖', '标签数据源'])
            or (keys and all(any(cmd in str(k) for cmd in command_words) for k in keys))
        )
        # “描写库/语料库/深度档案（专用key按需）”通常就是二层按需素材，
        # 不要求首轮由自然名触发；自然名应触发的是速览/基础档案。
        is_on_demand_library = any(kw in comment for kw in [
            '描写库', '语料库', '对话库', '行为库', '反应库', '外表描写', '外貌',
            '深度档案', '专用key', '按需', '心理描写库'
        ])
        is_core_profile = (
            not is_tool_command
            and not is_on_demand_library
            and any(kw in comment for kw in ['基础档案', '角色档案', '威胁档案', '档案', '威胁', '角色'])
            and len(content) > 500
        )
        is_scene = any(kw in comment for kw in ['场景', '地点'])
        is_seed = '事件' in comment or '种子' in comment
        if is_core_profile:
            ea.risks.append("🔴 核心角色/威胁档案所有开场白均不触发 — 必须修复")
            ea.suggestions.append("核心档案 primary key 必须包含自然角色名；当前key可能为人工复合词或从未出现在greeting中")
        elif is_scene:
            ea.risks.append("场景条目所有开场白均不触发")
            ea.suggestions.append("若该场景不在任何greeting中出现，可保留按需触发；否则在对应greeting中提及场景名")
        elif is_seed:
            # 事件种子不触发是正常的
            pass
        else:
            ea.risks.append("所有开场白均不触发")
            ea.suggestions.append("若期望首轮可用，把关键词写入对应greeting；若中后期按需触发，可保留并备注")

    # 🆕 检测核心档案仅有「档案」后缀 key（死 key，2026-07-15新增）
    # 例外：显式标注“专用key/按需/深度档案”的二层素材，这是速览+深度档案模式的预期设计。
    if ('专用key' not in comment and '按需' not in comment and '深度档案' not in comment
            and ('档案' in comment or '威胁' in comment)
            and keys and all(('档案' in str(k) or '设定' in str(k) or '资料' in str(k)) for k in keys)):
        has_natural = any(
            kw in str(k) for k in keys for kw in ['角色', '威胁', '性格', '描写', '语料']
        )
        if not has_natural or all('档案' in str(k) for k in keys):
            ea.risks.append("🔴 核心档案仅有'档案'后缀key，无自然角色名key → 死key风险")
            ea.suggestions.append("核心档案必须至少有一个自然角色名/常用称呼作为primary key（如'雪乃''雪之下'）；'档案'后缀只能作为备用/深度按需key")


def source_trigger_summary(audits: List[EntryAudit], sources: List[Tuple[str, str]]) -> Dict[str, Dict[str, Any]]:
    constants = [a for a in audits if a.is_constant and a.is_enabled]
    const_chars = sum(a.content_len for a in constants)
    out: Dict[str, Dict[str, Any]] = {}
    for label, _text in sources:
        triggered = [a for a in audits if (not a.is_constant) and a.source_matches.get(label, MatchResult(False)).ok]
        trigger_chars = sum(a.content_len for a in triggered)
        out[label] = {
            "constant_count": len(constants),
            "triggered_count": len(triggered),
            "tokens": (const_chars + trigger_chars) // 2,
            "entries": triggered,
        }
    return out


def format_hits(ea: EntryAudit, label: str) -> str:
    mr = ea.source_matches.get(label, MatchResult(False))
    if not mr.ok:
        return "-"
    p = "/".join(mr.primary_hits[:3]) if mr.primary_hits else "?"
    if mr.secondary_hits:
        sec = "/".join(mr.secondary_hits[:2])
        if ea.selective and ea.secondary_keys:
            return f"✅ {p} + {sec}"
        return f"✅ {p}（副词命中但未参与: {sec}）"
    return f"✅ {p}"


def make_report(card_path: Path, card: Dict[str, Any], data: Dict[str, Any], entries: List[Dict[str, Any]], audits: List[EntryAudit], sources: List[Tuple[str, str]]) -> str:
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    card_name = data.get("name") or card.get("name") or card_path.stem
    file_size_kb = card_path.stat().st_size / 1024

    constants = [a for a in audits if a.is_constant]
    enabled_constants = [a for a in audits if a.is_constant and a.is_enabled]
    enabled = [a for a in audits if a.is_enabled]
    disabled = [a for a in audits if not a.is_enabled]
    selective = [a for a in audits if a.selective]
    with_sec_no_sel = [a for a in audits if a.secondary_keys and not a.selective and not a.is_constant]
    ext_only = [a for a in audits if a.ext_selective is True and not a.selective and a.secondary_keys]
    risky = [a for a in audits if a.risks]
    hard_risky = [a for a in risky if any("🔴" in r or "硬泛" in r or "仅extensions" in r or "仅靠硬泛" in r for r in a.risks)]

    summary = source_trigger_summary(audits, sources)

    lines: List[str] = []
    lines.append(f"# 世界书触发审计报告 — {card_name}")
    lines.append("")
    lines.append(f"> 生成时间：{now}  ")
    lines.append(f"> 卡文件：`{card_path}`  ")
    lines.append(f"> 审计脚本：`audit_worldbook_triggers.py`（ST v1.18 源码对齐触发模拟）")
    lines.append("")

    lines.append("## 1. 总览")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|---|---:|")
    lines.append(f"| 文件大小 | {file_size_kb:.1f} KB |")
    lines.append(f"| 世界书条目 | {len(entries)} |")
    lines.append(f"| 常驻条目（enabled） | {len(enabled_constants)} |")
    lines.append(f"| 常驻条目（含禁用选开） | {len(constants)} |")
    lines.append(f"| enabled=true | {len(enabled)} |")
    lines.append(f"| enabled=false | {len(disabled)} |")
    lines.append(f"| selective=true | {len(selective)} |")
    lines.append(f"| 有secondary但顶层selective=false | {len(with_sec_no_sel)} |")
    lines.append(f"| 仅extensions.selective=true且有secondary | {len(ext_only)} |")
    lines.append(f"| 有风险条目 | {len(risky)} |")
    lines.append(f"| 硬风险条目 | {len(hard_risky)} |")
    lines.append("")

    lines.append("## 2. 每个 greeting 的初始触发负载")
    lines.append("")
    lines.append("| Source | 常驻 | 触发 | 估算负载* | 判定 | 触发条目 |")
    lines.append("|---|---:|---:|---:|---|---|")
    lines.append("")
    lines.append("> *估算负载为脚本按字符粗略折算的诊断值，不等于API实际input tokens。ST实际请求应以Prompt Itemization/API usage为准。高负载本身不是错误，优先检查泛key、无关污染、递归链和实际截断。")
    lines.append("")
    for label, _ in sources:
        info = summary[label]
        tokens = info["tokens"]
        if tokens > 50000:
            verdict = "🟣 超大上下文"
        elif tokens > 8000:
            verdict = "🟡 高负载"
        elif tokens > 5000:
            verdict = "🟡 中负载"
        else:
            verdict = "✅ 轻负载"
        sample = ", ".join(f"[{a.eid}]{shorten(a.comment, 12)}" for a in info["entries"][:10])
        if len(info["entries"]) > 10:
            sample += f", ...+{len(info['entries'])-10}"
        lines.append(f"| {markdown_escape(label)} | {info['constant_count']} | {info['triggered_count']} | {tokens} | {verdict} | {markdown_escape(sample or '-')} |")
    lines.append("")

    lines.append("## 3. 风险条目清单")
    lines.append("")
    if risky:
        lines.append("| ID | 条目 | 类型 | 触发意图 | 风险 | 建议 |")
        lines.append("|---:|---|---|---|---|---|")
        for a in sorted(risky, key=lambda x: (0 if any("硬" in r or "仅extensions" in r for r in x.risks) else 1, str(x.eid))):
            lines.append(
                f"| {a.eid} | {markdown_escape(shorten(a.comment, 32))} | {infer_content_type(a.entry)} | "
                f"{infer_trigger_intent(a.entry)} | {markdown_escape('; '.join(dict.fromkeys(a.risks)))} | "
                f"{markdown_escape('; '.join(dict.fromkeys(a.suggestions)))} |"
            )
    else:
        lines.append("未发现触发风险。")
    lines.append("")

    lines.append("## 4. 逐条触发矩阵")
    lines.append("")
    header = ["ID", "条目", "entry_role", "自然路径", "类型", "intent", "keys", "secondary", "sel", "enabled"] + [label for label, _ in sources] + ["风险"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---:" if i == 0 else "---" for i in range(len(header))]) + "|")
    for a in audits:
        if not a.is_enabled:
            source_cells = ["禁用" for _ in sources]
        elif a.is_constant:
            source_cells = ["常驻" for _ in sources]
        else:
            source_cells = [format_hits(a, label) for label, _ in sources]
        cells = [
            str(a.eid),
            markdown_escape(shorten(a.comment, 30)),
            markdown_escape(a.role),
            markdown_escape(a.natural_path_types),
            infer_content_type(a.entry),
            infer_trigger_intent(a.entry),
            markdown_escape("/".join(a.keys[:4]) + ("…" if len(a.keys) > 4 else "")),
            markdown_escape("/".join(a.secondary_keys[:3]) + ("…" if len(a.secondary_keys) > 3 else "")),
            f"{a.selective}({LOGIC_NAMES.get(a.selective_logic, a.selective_logic)})" if a.selective else "False",
            str(a.is_enabled),
            *[markdown_escape(c) for c in source_cells],
            markdown_escape("; ".join(dict.fromkeys(a.risks)) or "-"),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("## 5. 普通句反证测试")
    lines.append("")
    lines.append("以下普通聊天句用于发现泛 key 误触发：")
    lines.append("")
    lines.append("| 普通句 | 会触发的条目 |")
    lines.append("|---|---|")
    for probe in GENERIC_PROBES:
        hits = [a for a in audits if a.probe_matches[probe].ok]
        sample = ", ".join(f"[{a.eid}]{shorten(a.comment, 16)}({ '/'.join(a.probe_matches[probe].primary_hits[:2]) })" for a in hits[:12])
        if len(hits) > 12:
            sample += f", ...+{len(hits)-12}"
        lines.append(f"| {markdown_escape(probe)} | {markdown_escape(sample or '-')} |")
    lines.append("")

    # === 🆕 5b. 阶段路由专项分析（2026-07-26） ===
    stage_entries = [
        a for a in audits
        if any(
            str(k).startswith("【开场：") or str(k).startswith("ROUTE_STAGE=")
            for k in a.keys
        )
    ]
    if stage_entries:
        lines.append("## 5b. 阶段路由专项分析")
        lines.append("")
        lines.append("### 阶段包触发矩阵")
        lines.append("")
        header_cols = ["阶段包", "预期触发"] + [label for label, _ in sources]
        lines.append("| " + " | ".join(header_cols) + " |")
        lines.append("|" + "|".join(["---"] * len(header_cols)) + "|")

        for a in stage_entries:
            expected = a.keys[:2] if a.keys else ["?"]
            cells = [
                markdown_escape(shorten(a.comment, 25)),
                markdown_escape("/".join(expected)),
            ]
            for label, source_text in sources:
                match = a.source_matches.get(label)
                if match and match.ok:
                    cells.append("✅")
                else:
                    cells.append("—")
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

        # 跨阶段误触发检测
        cross_stage_problems = []
        for label, source_text in sources:
            if not source_text:
                continue
            # 提取源文本的阶段标记（共享 grammar）
            src_stage = _stage_number_from_text(source_text)
            if src_stage is None:
                continue
            # 检查被触发的阶段包
            for a in stage_entries:
                match = a.source_matches.get(label)
                if not (match and match.ok):
                    continue
                for k in a.keys:
                    entry_stage = _stage_number_from_key(k)
                    if entry_stage is not None:
                        if entry_stage > src_stage:
                            cross_stage_problems.append(
                                f"{label} (P{src_stage}) 触发了 P{entry_stage} 阶段包 [{a.eid}] {a.comment[:25]}"
                            )
                        elif entry_stage < src_stage:
                            pass  # 前期阶段被后期greeting触发可以接受
        if cross_stage_problems:
            lines.append("### ⚠️ 跨阶段误触发")
            lines.append("")
            for p in cross_stage_problems:
                lines.append(f"- 🔴 {p}")
            lines.append("")
        else:
            lines.append("### ✅ 未检测到跨阶段误触发")
            lines.append("")

        # 孤儿阶段包
        orphan_stage = [a for a in stage_entries if not any(
            a.source_matches.get(label) and a.source_matches[label].ok
            for label, _ in sources
        )]
        if orphan_stage:
            lines.append("### ⚠️ 孤儿阶段包（无 greeting 触发）")
            lines.append("")
            for a in orphan_stage:
                lines.append(f"- 🟡 [{a.eid}] {a.comment[:30]} keys={a.keys}")
            lines.append("")

    lines.append("## 6. 下一步修复建议")
    lines.append("")
    lines.append("### 自然事件 OR 触发策略")
    lines.append("")
    lines.append("对于 `entry_role=common_content` 且 comment 含事件/种子的条目，本卡明确采用多个自然关键词按 OR 匹配。共享角色 key、事件并行加载和估算触发负载仅作诊断，不自动建议改成死 key、阶段 AND 锁或删除自然别名。")
    lines.append("")
    if hard_risky:
        lines.append("优先修复硬风险：")
        for a in hard_risky[:20]:
            lines.append(f"- **[{a.eid}] {a.comment}**：{'; '.join(dict.fromkeys(a.risks))} → { '; '.join(dict.fromkeys(a.suggestions)) }")
        lines.append("")
    if with_sec_no_sel:
        ids = ", ".join(str(a.eid) for a in with_sec_no_sel[:30])
        lines.append(f"- 有 secondary 但顶层 selective=false 的条目：{ids}。决定是清空 secondary，还是改为顶层 selective=true 做范围绑定。")
    high_load = [label for label, info in summary.items() if info["tokens"] > 5000]
    if high_load:
        lines.append(f"- 触发负载偏高的入口：{', '.join(high_load)}。修复泛 key / 拆分大条目后再复测。")
    xuankai_disabled = [a for a in audits if a.is_constant and not a.is_enabled and ('{{user}}' in str(a.entry.get('content', '')) or '选开' in a.comment)]
    if xuankai_disabled:
        lines.append(f"- 检测到 {len(xuankai_disabled)} 个G型选开身份条目：这些条目不靠关键词触发，需在ST世界书UI手动启用；每次只启用一个身份。")
    lines.append("- 如可进入ST，最终以 Prompt Itemization / <Lore> / API usage / 官方 countTokens 为准；脚本估算只用于定位泛key、死key和无关污染。")
    if not hard_risky and not with_sec_no_sel and not high_load:
        lines.append("- 未发现必须立刻修复的触发问题；可按内容质量继续审查。")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("**铁律**：绿灯≠触发；启用≠加载；secondary_keys≠自动生效；extensions.selective≠顶层selective。")
    lines.append("")
    return "\n".join(lines)


def stage_route_findings(audits: List[EntryAudit], sources: List[Tuple[str, str]]) -> tuple[list[str], list[str]]:
    """Return machine-consumable native-stage binding errors and warnings.

    A complete Greeting title declares the stage.  It must therefore be used as
    the baseline even if no entry currently binds it; otherwise a misbound pack
    can suppress the very audit intended to reject it.
    """
    required_packs = ("\u9636\u6bb5\u6838\u5fc3", "\u6210\u4eba\u4f53\u9a8c", "\u573a\u666f\u4f53\u9a8c", "\u4e8b\u4ef6\u5e93")
    errors: list[str] = []
    warnings: list[str] = []
    for label, source_text in sources:
        if not source_text:
            continue
        matches = title_matches(source_text)
        if matches:
            stage, title = parse_title(matches[0])
            if stage == "MENU":
                # 图鉴 MENU 是独立菜单入口（HTML 开场页），不属于阶段，不要求四包绑定。
                continue
            bound = [
                audit for audit in audits
                if not audit.is_constant and audit.is_enabled and title in audit.keys
            ]
            found = {
                pack for pack in required_packs
                if any(pack in audit.comment for audit in bound)
            }
            missing = set(required_packs) - found
            if missing:
                errors.append(f"STAGE_PACK_TITLE_UNBOUND {label}({stage}) missing={sorted(missing)}")
            for audit in bound:
                comment_match = re.search(r"(?:^|_)P(\d+)(?:$|_)", audit.comment)
                if comment_match and stage != "MENU" and int(comment_match.group(1)) != int(stage[1:]):
                    errors.append(
                        f"STAGE_CROSS_TRIGGER {label}({stage}) -> "
                        f"[{audit.eid}] {audit.comment[:30]}(P{comment_match.group(1)})"
                    )
            continue
        source_stage = _stage_number_from_text(source_text)
        if source_stage is None:
            continue
        stage_entries = [
            audit for audit in audits
            if any(str(key).upper() == f"ROUTE_STAGE=P{source_stage}" for key in audit.keys)
        ]
        if not stage_entries:
            warnings.append(f"STAGE_EXTERNAL_ROUTE_NO_PACK {label}(P{source_stage})")
    for audit in audits:
        if not re.search(r"(?:^|_)P\d+(?:$|_)", audit.comment):
            continue
        if not any(title_matches(key) for key in audit.keys):
            continue
        if not any(match.ok for match in audit.source_matches.values()):
            warnings.append(f"STAGE_ORPHAN_PACK [{audit.eid}] {audit.comment[:30]} keys={audit.keys}")
    return list(dict.fromkeys(errors)), list(dict.fromkeys(warnings))

def build_sources(data: Dict[str, Any]) -> List[Tuple[str, str]]:
    sources = [("first_mes", data.get("first_mes", "") or "")]
    for i, g in enumerate(data.get("alternate_greetings", []) or []):
        sources.append((f"alternate[{i}]", g or ""))
    for i, g in enumerate(data.get("group_only_greetings", []) or []):
        sources.append((f"group_only[{i}]", g or ""))
    return sources


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit SillyTavern worldbook trigger reachability and false positives.")
    parser.add_argument("card", help="Path to character card JSON")
    parser.add_argument("-o", "--output", help="Write Markdown report to this path. Defaults to stdout.")
    args = parser.parse_args(argv)

    card_path = Path(args.card).expanduser()
    card, data, entries = load_card(card_path)
    sources = build_sources(data)
    audits = analyze_entries(entries, sources)
    report = make_report(card_path, card, data, entries, audits, sources)

    if args.output:
        out = Path(args.output).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Wrote trigger audit report: {out}")
    else:
        print(report)
    stage_errors, _stage_warnings = stage_route_findings(audits, sources)
    return 1 if stage_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
