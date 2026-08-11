#!/usr/bin/env python3
"""
加料自检脚本 v5.1 — 交付前检查角色卡内容厚度与可用性。

在跑完 validate_card.py 与 audit_worldbook_triggers.py 之后、交付用户之前运行。
硬门控与 SKILL.md §3.5 对齐：严格/legacy 模式下任何 🔴 或 ≥3 个 🟡 均不可交付；开放精选锚点模式只把 🔴 作为失败。
"""

import argparse
import json
import re
import sys
from pathlib import Path

from lib.stage_memory import phase_memory_anchor_issues
from lib.stage_routing import declared_titles_by_stage, primary_keys
from lib.narrative_contracts import load_validated_content_policy


def cn_len(text: str) -> int:
    """Count Chinese characters only."""
    return sum(1 for c in str(text) if '\u4e00' <= c <= '\u9fff')


def corpus_quote_mapping_violations(content: str) -> list[str]:
    """Every quoted corpus line needs a speaker→recipient label in its local material unit."""
    text = str(content)
    violations: list[str] = []
    covered_spans: list[tuple[int, int]] = []
    for match in re.finditer(r"【([^】]+)】([^【]*)", text, flags=re.S):
        label, body = match.group(1), match.group(2)
        covered_spans.append(match.span(2))
        if "→" in label:
            continue
        violations.extend(re.findall(r"[「“]([^」”]+)[」”]", body))
    for quote in re.finditer(r"[「“]([^」”]+)[」”]", text):
        if not any(start <= quote.start() < end for start, end in covered_spans):
            violations.append(quote.group(1))
    return list(dict.fromkeys(violations))


def profile_field_issues(data: dict) -> list[str]:
    """Keep model-visible card fields substantive rather than tag-only placeholders."""
    requirements = {"description": 300, "personality": 180, "scenario": 180}
    issues: list[str] = []
    for field, minimum in requirements.items():
        actual = cn_len(data.get(field, ""))
        if actual < minimum:
            issues.append(f"角色卡{field}仅{actual}中文字，需≥{minimum}中文字并写明核心人物、玩法和关系起点")
    return issues


def profile_context_issues(data: dict) -> list[str]:
    """Check that the card's model-visible first layer establishes world and agency."""
    profile = "\n".join(str(data.get(field, "")) for field in ("description", "personality", "scenario", "system_prompt"))
    issues: list[str] = []
    if not any(marker in profile for marker in ("世界", "背景", "舞台", "港区", "国度", "故事")):
        issues.append("角色卡首层说明缺少世界/舞台概况")
    if "{{user}}" not in profile and "玩家" not in profile:
        issues.append("角色卡首层说明缺少{{user}}/玩家身份与可行动边界")
    has_ai_actor = any(marker in profile for marker in ("AI", "NPC", "旁白", "模型"))
    has_boundary = any(marker in profile for marker in ("不代写", "不得替", "只扮演", "只写", "边界"))
    if not (has_ai_actor and has_boundary):
        issues.append("角色卡首层说明缺少AI/NPC扮演范围与不代写边界")
    return issues


def is_xuankai_identity(e: dict) -> bool:
    comment = e.get('comment', '')
    return (
        e.get('constant')
        and not e.get('enabled', True)
        and '{{user}}' in e.get('content', '')
        and ('选开' in comment or '身份' in comment)
    )


def is_opt_in_director_mode(e: dict) -> bool:
    """A disabled feature toggle replaces the historical always-on director protocol."""
    ext = e.get('extensions') or {}
    return (
        e.get('constant') is True
        and ext.get('entry_role') == 'feature_toggle'
        and ext.get('feature_mode') == 'narrative_director'
    )


def is_role_profile(e: dict) -> bool:
    comment = e.get('comment', '')
    if any(kw in comment for kw in ['描写库', '语料库', '对话库', '行为库', '反应库', '深度档案', '专用key', '按需']):
        return False
    return any(kw in comment for kw in ['角色档案', '基础档案', '性格档案', '人物档案', '威胁档案', '核心女主', '核心角色', '角色设定'])


def is_ntr_relationship_entry(e: dict) -> bool:
    """只识别真正的NTR关系/矩阵条目，避免把“NTR叙事节奏规则”等系统条目误杀。"""
    comment = e.get('comment', '')
    if '×' in comment:
        return True
    relationship_markers = ['NTR关系', 'NTR线', 'NTR矩阵', '关系矩阵', '攻略线', '侵犯史', '堕落线']
    if any(kw in comment for kw in relationship_markers):
        return True
    if 'NTR' in comment and any(kw in comment for kw in ['关系', '矩阵', '攻略', '侵犯', '堕落轨迹']):
        return True
    return False


def is_r18_material_entry(e: dict) -> bool:
    """R18空壳检查只抽查核心素材条目，避免把心理/机制事件误当肉戏素材。"""
    comment = e.get('comment', '')
    content = e.get('content', '')
    if e.get('constant') and any(kw in comment for kw in ['系统', 'OOC', '状态栏', '文风', '规则', '反顺从']):
        return False
    always_material = [
        '核心角色', '角色档案', '基础档案', '核心女主', 'NTR关系', 'NTR线', '关系矩阵', '×',
        '描写库', '身体', '语料库', '对话库', '场景', '氛围'
    ]
    if any(kw in comment for kw in always_material):
        return True
    if '事件' in comment:
        scope = comment + content[:1000]
        r18_event_markers = [
            'R18', 'NTR', '性爱', '性交', '肉戏', '侵犯', '被侵犯', '插入', '顶入', '抽插', '内射',
            '龟头', '肉壁', '小穴', '阴道', '乳房', '乳尖', '湿润', '肉体', '媚黑', '调教', '沉沦', '堕落'
        ]
        return any(kw in scope for kw in r18_event_markers)
    return False


def r18_material_score(content: str) -> dict:
    """启发式判断“抽象规则 vs 可复用素材”，不是敏感词计数。"""
    buckets = {
        '动作链': [
            '靠近', '按住', '压住', '拉住', '抬起', '推开', '贴近', '触碰', '抚摸', '撕开', '抓住', '进入', '退开', '挣扎',
            '插入', '顶住', '抵住', '摩擦', '套弄', '含住', '舔', '吻', '抱', '顶入', '抽插', '射', '内射', '压上去', '撞击', '推进'
        ],
        '语言链': [
            '「', '」', '“', '”', "'", '"', '命令', '挑衅', '拒绝', '求饶', '嘴硬', '低声', '喘息', '台词', '声音', '回答',
            '说道', '低声说', '喘着', '求你', '不要', '继续', '叫出声', '呢喃', '哀求'
        ],
        '身体反应': [
            '呼吸', '颤抖', '脸红', '腰', '腿', '手指', '表情', '姿态', '发软', '发烫', '僵住', '湿', '疼',
            '龟头', '肉壁', '小穴', '阴道', '乳房', '乳尖', '下腹', '湿润', '紧致', '包裹', '颤栗', '内壁', '体液', '精子'
        ],
        '场景链': ['办公室', '卧室', '浴室', '教室', '门', '窗', '灯', '沙发', '床', '桌', '走廊', '监控', '风险', '安全等级', '宿舍', '别墅', '校长室', '训练场'],
        '阶段链': ['初期', '中期', '后期', '阶段', '成功', '失败', '半成功', '代价', '后续', '升级', '反噬', '堕落跃迁', '突破', '第一次', '事后', '临界点', '终点'],
    }
    abstract_words = ['应当', '必须', '需要', '保持', '避免', '确保', '禁止', '不得', '逐渐', '成人张力', '性张力', '氛围', '规则', '机制', '原则']
    bucket_hits = {name: sum(content.count(w) for w in words) for name, words in buckets.items()}
    abstract_count = sum(content.count(w) for w in abstract_words)
    active_buckets = [name for name, count in bucket_hits.items() if count > 0]
    return {'abstract': abstract_count, 'active_buckets': active_buckets, 'bucket_hits': bucket_hits}


def seed_three_path_level(prototype: str, three_path: str = 'auto') -> str:
    mode = (three_path or 'auto').lower()
    if mode in {'hard', 'soft', 'none'}:
        return mode
    proto = (prototype or '').upper()
    if proto in {'B', 'D'} or '守护' in (prototype or ''):
        return 'hard'
    if proto == 'C' or '攻擂' in (prototype or '') or '成长' in (prototype or ''):
        return 'soft'
    if proto == 'G':
        return 'auto'  # 只对含守护/破局/阻止等攻防语义的事件软检查
    return 'none'


def load_quality_policy(manifest_path: str | Path | None) -> dict[str, str]:
    """Load validated content-policy dimensions without changing legacy defaults."""
    defaults = {
        'event_mode': 'legacy_unspecified',
        'corpus_mode': 'legacy_unspecified',
        'route_policy': 'legacy_unspecified',
        'sandbox_scope': 'legacy_unspecified',
    }
    if not manifest_path:
        return defaults
    return load_validated_content_policy(manifest_path)


def check_card(
    card_path: str,
    verbose: bool = True,
    repair_mode: bool = False,
    r18: bool = False,
    prototype: str = '',
    three_path: str = 'auto',
    event_mode: str = 'legacy_unspecified',
    corpus_mode: str = 'legacy_unspecified',
    route_policy: str = 'legacy_unspecified',
    sandbox_scope: str = 'legacy_unspecified',
) -> list:
    with open(card_path, 'r', encoding='utf-8') as f:
        card = json.load(f)

    data = card.get('data', card)
    entries = data.get('character_book', {}).get('entries', [])
    issues = []

    def add(severity: str, msg: str):
        issues.append((severity, msg))

    # 模型可见的 description/personality/scenario 是角色卡的第一层入口，不能退化为标签。
    for issue in profile_field_issues(data):
        add('🟡', issue)
    for issue in profile_context_issues(data):
        add('🟡', issue)

    # === A. 角色条目深度 ===
    char_entries = [e for e in entries if not e.get('constant') and e.get('enabled') and is_role_profile(e)]
    for e in char_entries:
        cn = cn_len(e.get('content', ''))
        total = len(e.get('content', ''))
        cid, comment = e.get('id', '?'), e.get('comment', '')[:25]
        content = e.get('content', '')
        if event_mode == 'open_situation_seed' and corpus_mode == 'curated_anchor_set':
            concrete_signals = ['关系', '称谓', '语言', '行为', '触发', '场景', '反应', '台词', '锚点']
            signal_count = sum(content.count(signal) for signal in concrete_signals)
            if cn < 300 or signal_count < 2:
                add('🔴', f"开放角色条目[{cid}] '{comment}' 可调用锚点不足（{cn}中文字，具体关系/语言/行为信号={signal_count}）")
            else:
                add('✅', f"开放角色[{cid}] '{comment}' {cn}中文字，按具体锚点通过（不执行1500/2000字固定门槛）")
        elif cn < 1500:
            add('🔴', f"角色条目[{cid}] '{comment}' 仅{cn}中文字/{total}总字符 (需≥1500中文字)")
        elif cn < 2000:
            add('🟡', f"角色条目[{cid}] '{comment}' {cn}中文字/{total}总字符 (建议≥2000中文字)")
        else:
            add('✅', f"角色[{cid}] '{comment}' {cn}中文字 ✔")

    # === B. 语料库检查 ===
    corpus_entries = [e for e in entries if any(kw in e.get('comment', '') for kw in ['语料', '对话库', '台词'])]
    if not corpus_entries:
        if corpus_mode == 'curated_anchor_set':
            add('✅', "精选锚点模式：未拆分独立语料库；由角色档案/精选锚点承载语言参考，不执行固定语料库硬门槛")
        else:
            add('🔴', "缺少语料库条目 — AI没有对话参考素材")
    else:
        for e in corpus_entries:
            cn = cn_len(e.get('content', ''))
            cid = e.get('id', '?')
            if corpus_mode == 'curated_anchor_set':
                add('✅', f"精选锚点库[{cid}] {cn}中文字（不执行≥500字固定门槛）")
            elif cn >= 500:
                add('✅', f"语料库[{cid}] {cn}中文字 ✔")
            else:
                add('🟡', f"语料库[{cid}] {cn}中文字 (建议≥500)")
            unmapped_quotes = corpus_quote_mapping_violations(e.get('content', ''))
            if unmapped_quotes:
                sample = ' / '.join(f'「{quote[:30]}」' for quote in unmapped_quotes[:3])
                add('🔴', f"语料库[{cid}] 存在未标注说话人→对象的台词：{sample}")
            else:
                add('✅', f"语料库[{cid}] 台词均含说话人→对象标注 ✔")

    # === C. 场景条目深度 ===
    scene_entries = [
        e for e in entries
        if '场景' in e.get('comment', '')
        and e.get('enabled')
        and (e.get('extensions', {}).get('entry_role') not in {'feature_toggle', 'system_constant'})
    ]
    for e in scene_entries:
        cn = cn_len(e.get('content', ''))
        cid, comment = e.get('id', '?'), e.get('comment', '')[:20]
        has_safety = any(kw in e.get('content', '') for kw in ['安全等级', 'S级', 'A级', 'B级', 'C级', 'D级', '隐私'])
        if event_mode == 'open_situation_seed' and corpus_mode == 'curated_anchor_set':
            concrete_signals = ['物件', '声音', '气味', '动作', 'NPC', '入口', '可观察', '余波', '触发']
            signal_count = sum(e.get('content', '').count(signal) for signal in concrete_signals)
            if cn < 180 or signal_count < 2:
                add('🔴', f"开放场景[{cid}] '{comment}' 缺少可调用现场锚点（{cn}中文字，具体信号={signal_count}）")
            else:
                add('✅', f"开放场景[{cid}] {cn}中文字，现场锚点={signal_count}（不执行500字/安全等级固定门槛）")
        elif cn < 500:
            add('🔴', f"场景[{cid}] '{comment}' 仅{cn}中文字 (需≥500)")
        else:
            tag = '有安全等级' if has_safety else '无安全等级'
            add('✅', f"场景[{cid}] {cn}中文字 [{tag}]")
        if not has_safety and not (event_mode == 'open_situation_seed' and corpus_mode == 'curated_anchor_set'):
            add('🟡', f"场景[{cid}] '{comment}' 缺少安全等级定义")

    # === D. 事件种子深度（排除G型选开身份） ===
    if event_mode == 'open_situation_seed':
        seed_entries = [
            e for e in entries
            if not is_xuankai_identity(e)
            and (
                (e.get('extensions') or {}).get('entry_role') == 'event_candidate'
                or any(kw in e.get('comment', '') for kw in ['事件种子', '开放情境', '情境种子'])
            )
        ]
    else:
        seed_entries = [e for e in entries if not e.get('enabled', True) and not is_xuankai_identity(e)]
    for e in seed_entries:
        cn = cn_len(e.get('content', ''))
        cid, comment = e.get('id', '?'), e.get('comment', '')[:20]
        if event_mode == 'open_situation_seed':
            add('✅', f"开放情境种子[{cid}] '{comment}' 不执行固定字数/固定事件路径门槛")
        elif cn < 80:
            add('🔴', f"事件种子[{cid}] '{comment}' 仅{cn}中文字 (需≥80)")
        elif cn < 150:
            add('🟡', f"事件种子[{cid}] '{comment}' {cn}中文字 (建议≥150)")
        else:
            add('✅', f"种子[{cid}] '{comment}' {cn}中文字 ✔")

    # === E. 行为模板检查 ===
    for e in char_entries:
        content = e.get('content', '')
        template_lines = [l for l in content.split('\n') if l.strip().startswith('-') and '→' in l]
        behavior_signals = ['→', '当', '如果', '触发', '场景', '行为举例', '行为链']
        signal_count = sum(content.count(s) for s in behavior_signals)
        total = signal_count // 2 + len(template_lines)
        cid, comment = e.get('id', '?'), e.get('comment', '')[:15]
        if event_mode == 'open_situation_seed' and corpus_mode == 'curated_anchor_set':
            if total >= 1:
                add('✅', f"开放行为模板[{cid}] '{comment}' {total}个具体信号/链（不执行固定模板数量门槛）")
            else:
                add('🔴', f"开放行为模板[{cid}] '{comment}' 缺少触发→反应或行为链")
        elif total >= 3:
            add('✅', f"行为模板[{cid}] '{comment}' {total}个信号/链 ✔")
        else:
            add('🟡', f"行为模板[{cid}] '{comment}' 行为链偏少 ({total}个)")

    # === F. 描写库独立检查 ===
    desc_entries = [e for e in entries if '描写库' in e.get('comment', '') or '描写' in e.get('comment', '')]
    pure_desc = [e for e in desc_entries if '语料' not in e.get('comment', '') and '对话' not in e.get('comment', '')]
    if not pure_desc:
        if event_mode == 'open_situation_seed' and corpus_mode == 'curated_anchor_set':
            add('✅', "精选锚点模式：描写可由角色档案、场景条目或全局素材承载，不强制拆分独立描写库")
        else:
            add('🟡', "缺少独立描写库条目 (身体/感官/氛围不应和对话语料混在同一条)")
    else:
        for e in pure_desc:
            cn = cn_len(e.get('content', ''))
            cid = e.get('id', '?')
            if event_mode == 'open_situation_seed' and corpus_mode == 'curated_anchor_set':
                add('✅', f"开放描写锚点[{cid}] {cn}中文字（不执行≥500字固定门槛）")
            elif cn >= 500:
                add('✅', f"描写库[{cid}] {cn}中文字 ✔")
            else:
                add('🟡', f"描写库[{cid}] {cn}中文字 (建议≥500)")

    # === G. 阶段跃迁行为标志检查 ===
    stage_entries = [] if (
        event_mode == 'open_situation_seed' and corpus_mode == 'curated_anchor_set'
    ) else [
        e for e in entries
        if any(kw in e.get('comment', '') for kw in ['阶段', '堕落', '守护', '征服', '沉沦', '臣服', '屈服']) and e.get('enabled')
    ]
    for e in stage_entries:
        content = e.get('content', '')
        has_behavior = any(kw in content for kw in ['触发条件', '跃迁', '标志', '行为', '具体表现', '门', '阈值行为'])
        has_pure_numbers = bool(re.search(r'[>≥]\s*\d+', content))
        cid, comment = e.get('id', '?'), e.get('comment', '')[:15]
        if not has_behavior:
            add('🟡', f"阶段条目[{cid}] '{comment}' 缺少行为触发条件")
        if has_pure_numbers and not has_behavior:
            add('🔴', f"阶段条目[{cid}] '{comment}' 只用数值定义跃迁")
        if has_behavior:
            add('✅', f"阶段条目[{cid}] '{comment}' 行为触发条件 ✔")

    # === H. NTR关系条目深度 ===
    ntr_rel = [e for e in entries if is_ntr_relationship_entry(e)]
    for e in ntr_rel:
        cn = cn_len(e.get('content', ''))
        cid, comment = e.get('id', '?'), e.get('comment', '')[:25]
        if '矩阵' in comment:
            if cn >= 300:
                add('✅', f"NTR矩阵[{cid}] {cn}中文字 ✔")
            else:
                add('🟡', f"NTR矩阵[{cid}] {cn}中文字 (建议≥300)")
        else:
            if event_mode == 'open_situation_seed' and corpus_mode == 'curated_anchor_set':
                relation_signals = ['关系', '侵犯', '接近', '控制', '反应', '触发', '场景', '余波', '台词']
                signal_count = sum(e.get('content', '').count(signal) for signal in relation_signals)
                if cn < 250 or signal_count < 2:
                    add('🔴', f"开放NTR关系[{cid}] '{comment}' 可调用关系锚点不足（{cn}中文字，具体信号={signal_count}）")
                else:
                    add('✅', f"开放NTR关系[{cid}] '{comment}' {cn}中文字，按关系锚点通过（不执行600/1000字固定门槛）")
            elif cn < 600:
                add('🔴', f"NTR关系[{cid}] '{comment}' 仅{cn}中文字 (需≥600，含侵犯史/行为链/触发关键词)")
            elif cn < 1000:
                add('🟡', f"NTR关系[{cid}] '{comment}' {cn}中文字 (建议≥1000)")
            else:
                add('✅', f"NTR关系[{cid}] '{comment}' {cn}中文字 ✔")

    # === I. 速览厚度 + 档案死key粗筛 ===
    for e in entries:
        comment = e.get('comment', '')
        content = e.get('content', '')
        keys = [str(k) for k in e.get('keys', []) if k]
        cn = cn_len(content)
        cid = e.get('id', '?')
        if any(kw in comment for kw in ['速览', '简表', '概要']):
            if cn < 250:
                add('🔴', f"速览[{cid}] '{comment[:20]}' 仅{cn}中文字 (需≥250且自足，不依赖递归触发深度档案)")
            elif cn < 350:
                add('🟡', f"速览[{cid}] '{comment[:20]}' {cn}中文字 (建议≥350)")
        if is_role_profile(e) and keys and all(('档案' in k or '设定' in k or '资料' in k) for k in keys):
            add('🔴', f"角色档案[{cid}] '{comment[:20]}' keys全为人工复合词{keys}，无自然角色名key → 死key风险")

    # === J. 抽象规则/具体素材比例粗筛 ===
    abstract_words = ['应当', '必须', '需要', '保持', '避免', '确保', '禁止', '不得']
    concrete_signals = ['「', '」', '“', '”', '→', '当', '如果', '场景：', '台词', '原文', '行为链']
    for e in char_entries:
        content = e.get('content', '')
        abstract_count = sum(content.count(w) for w in abstract_words)
        concrete_count = sum(content.count(w) for w in concrete_signals)
        if abstract_count >= 10 and concrete_count < 5:
            add('🟡', f"条目[{e.get('id')}] '{e.get('comment','')[:20]}' 抽象规则偏多、具体素材偏少（可能不够可直接复用）")

    # === K. G型选开身份统计 ===
    xuankai = [e for e in entries if is_xuankai_identity(e)]
    for e in xuankai:
        if '选开' not in e.get('comment', ''):
            add('🟡', f"选开身份[{e.get('id')}] comment缺'选开'字样，不利于ST UI识别")
        if '{{user}}' not in e.get('content', '')[:500]:
            add('🔴', f"选开身份[{e.get('id')}] 前500字未明确定义{{user}}身份")

    # === L. 可选R18内容空壳检查（仅 --r18 启用，避免误杀普通卡/系统条目） ===
    if r18:
        r18_targets = [e for e in entries if is_r18_material_entry(e)]
        strong_material = 0
        for e in r18_targets:
            content = e.get('content', '')
            score = r18_material_score(content)
            cid, comment = e.get('id', '?'), e.get('comment', '')[:25]
            active = score['active_buckets']
            abstract_count = score['abstract']
            is_seed_entry = (not e.get('enabled', True) and not is_xuankai_identity(e))
            has_physical_chain = ('动作链' in active or '身体反应' in active)
            is_core_target = is_role_profile(e) or is_ntr_relationship_entry(e) or (is_seed_entry and has_physical_chain)
            is_soft_library = any(kw in e.get('comment', '') for kw in ['场景', '氛围', '描写库', '语料库', '对话库']) and not is_core_target
            if len(active) >= 4:
                strong_material += 1
                add('✅', f"R18素材[{cid}] '{comment}' 覆盖{len(active)}类链条: {'/'.join(active)}")
            elif abstract_count >= 10 and len(active) <= 2:
                if is_core_target:
                    add('🔴', f"R18空壳[{cid}] '{comment}' 抽象规则{abstract_count}处但具体动作/语言/身体/场景/阶段链仅{len(active)}类：{'/'.join(active) or '无'}")
                else:
                    sev_label = 'R18素材库偏抽象' if is_soft_library else 'R18素材偏抽象'
                    add('🟡', f"{sev_label}[{cid}] '{comment}' 抽象规则{abstract_count}处但具体链条仅{len(active)}类：{'/'.join(active) or '无'}")
            elif is_core_target and len(active) <= 2:
                add('🟡', f"R18核心素材[{cid}] '{comment}' 具体链条偏少，仅{len(active)}类：{'/'.join(active) or '无'}")
        if r18_targets and strong_material == 0:
            add('🔴', "R18内容空壳：核心角色/关系/事件/描写/语料中没有任何条目同时覆盖≥4类可复用链条（动作/语言/身体/场景/阶段）")

    # === M. 事件种子三路径检查（按原型启用，不全卡硬套） ===
    path_level = 'none' if event_mode == 'open_situation_seed' and three_path == 'auto' else seed_three_path_level(prototype or '', three_path=three_path)
    if path_level != 'none':
        # G型是多视角架构，不等于守护卡。为避免“无力阻止/身体攻防”等普通NTR措辞误触发，
        # auto只识别明确守护/破局/救援/反杀类事件；需要更宽检查时用 --three-path soft。
        g_attack_markers = ['守护', '破局', '救援', '反杀', '争夺', '保护', '营救', '拯救']
        for e in seed_entries:
            content = e.get('content', '')
            effective_level = path_level
            if path_level == 'auto':
                scope_text = e.get('comment', '') + content[:500]
                if not any(kw in scope_text for kw in g_attack_markers):
                    continue
                effective_level = 'soft'
            has_success = any(kw in content for kw in ['成功路径', '成功', '守护成功'])
            has_failure = any(kw in content for kw in ['失败路径', '失败', '守护失败'])
            has_partial = any(kw in content for kw in ['半成功', '代价', '后患', '反噬'])
            if not (has_success and has_failure and has_partial):
                sev = '🔴' if effective_level == 'hard' else '🟡'
                add(sev, f"事件种子[{e.get('id')}] '{e.get('comment','')[:20]}' 缺三路径（成功/失败/半成功代价）；prototype={prototype or '未指定'}")

    # === N. 剧情导演协议存在性检查 ===
    director_markers = ['导演', '推进协议', '剧情导演', '事件推进', '事件调用', '事件库调用', '事件引擎', '导演与事件']
    director_entries = []
    for e in entries:
        if not e.get('constant'):
            continue
        comment = e.get('comment', '')
        content = e.get('content', '')
        if is_opt_in_director_mode(e):
            director_entries.append(e)
            continue
        if any(kw in comment for kw in director_markers):
            director_entries.append(e)
            continue

        if any(kw in content[:200] for kw in ['绝对优先级·', '剧情导演', '事件推进协议']):
            director_entries.append(e)

    if director_entries:
        de = director_entries[0]
        de_id = de.get('id', '?')
        # verify essential settings
        pos_ok = de.get('position') == 'before_char' and de.get('extensions', {}).get('position') == 0
        depth_ok = de.get('extensions', {}).get('depth', 0) >= 4
        budget_ok = de.get('extensions', {}).get('ignore_budget', False)
        cn = cn_len(de.get('content', ''))
        warnings = []
        if not pos_ok:
            warnings.append('position非before_char')
        if not depth_ok:
            warnings.append('depth<4')
        if not budget_ok:
            warnings.append('ignore_budget=false')
        if cn < 300:
            warnings.append(f'仅{cn}中文字(建议≥500)')
        if warnings:
            add('🟡', f"导演协议[{de_id}] 存在但配置不完整: {'; '.join(warnings)}")
        else:
            add('✅', f"导演协议[{de_id}] 已存在，配置正确({cn}字) ✔")
    else:
        if route_policy == 'player_led':
            add('✅', "player_led开放卡：剧情导演不是必需常驻条目；由玩家输入、当前事实和可观察线索决定是否推进")
        else:
            add('🔴', "缺少【剧情导演与事件推进协议】常驻条目 — AI没有主动推进事件的指令")

    # === O. Native Greeting-title stage routing ===
    native_titles = declared_titles_by_stage(card)
    if native_titles:
        required_packs = ("\u9636\u6bb5\u6838\u5fc3", "\u6210\u4eba\u4f53\u9a8c", "\u573a\u666f\u4f53\u9a8c", "\u4e8b\u4ef6\u5e93")
        has_causal = any("\u5168\u7a0b\u56e0\u679c\u6863\u6848" in str(e.get("comment", "")) for e in entries if e.get("constant"))
        add("\u2705" if has_causal else "\U0001f534", "阶段记忆组件: 全程因果档案已存在 ✔" if has_causal else "STAGE_ROUTING: 缺少「核心人物·全程因果档案」常驻条目")
        has_gate = any("\u9636\u6bb5\u8bb0\u5fc6" in str(e.get("comment", "")) for e in entries if e.get("constant"))
        add("\u2705" if has_gate else "\U0001f534", "阶段记忆组件: 阶段记忆闸门已存在 ✔" if has_gate else "STAGE_ROUTING: 缺少「绝对优先级·阶段记忆与叙事可见性协议」常驻条目")
        prompt_issues = phase_memory_anchor_issues(str(data.get("system_prompt", "")))
        if not prompt_issues:
            add("\u2705", "阶段记忆组件: system_prompt压缩锚点已存在 ✔")
        else:
            add("\U0001f7e1", "STAGE_ROUTING: " + "; ".join(issue.render() for issue in prompt_issues))
        for stage, declared_titles in native_titles.items():
            if stage == "MENU":
                # 图鉴 MENU 是独立菜单入口，不属于阶段，不要求四包。
                continue
            bound = [
                e for e in entries
                if not e.get("constant") and e.get("enabled", True)
                and bool(set(primary_keys(e)) & declared_titles)
            ]
            found = {
                pack for pack in required_packs
                if any(pack in str(e.get("comment", "")) for e in bound)
            }
            missing = set(required_packs) - found
            if missing:
                add("\U0001f534", f"STAGE_ROUTING: {stage}阶段缺少完整标题绑定的四包{missing}")
            else:
                add("\u2705", f"STAGE_ROUTING: {stage}阶段四包齐全 ✔")
            for entry in bound:
                comment = str(entry.get("comment", ""))
                if any(pack in comment for pack in required_packs):
                    content = str(entry.get("content", ""))
                    if not content.strip():
                        add("\U0001f534", f"stage pack[{entry.get('id')}] is empty")
                    elif len(re.findall(r"【[^】]*?\u7d20\u6750】", content)) < 6 and "\u4e8b\u4ef6\u5e93" not in comment:
                        add("\U0001f7e1", f"stage pack[{entry.get('id')}] has fewer than six material units")
    reds = [m for s, m in issues if s == '🔴']
    yellows = [m for s, m in issues if s == '🟡']
    greens = [m for s, m in issues if s == '✅']

    if verbose:
        print(f"\n{'='*60}")
        print(f"加料自检报告 — {Path(card_path).name}")
        print(f"总条目: {len(entries)} | 角色条目: {len(char_entries)} | 事件种子: {len(seed_entries)} | 场景: {len(scene_entries)} | 选开身份: {len(xuankai)}")
        if r18 or prototype:
            print(f"门控参数: r18={r18} prototype={prototype or '未指定'}")
        if repair_mode:
            print("模式: repair-mode（仍保留全卡红线；新增/重写内容需重点看本报告）")
        print(f"{'='*60}")
        print(f"\n✅ 通过: {len(greens)}")
        for m in greens:
            print(f"  {m}")
        print(f"\n🟡 建议/软门控: {len(yellows)}")
        for m in yellows:
            print(f"  {m}")
        print(f"\n🔴 需修复: {len(reds)}")
        for m in reds:
            print(f"  {m}")
        print(f"\n{'='*60}")
        if reds:
            print("⚠️  发现 🔴 项 → 必须修复后才能交付")
        elif len(yellows) >= 3 and not (
            event_mode == 'open_situation_seed'
            and corpus_mode == 'curated_anchor_set'
        ):
            print("⚠️  🟡 ≥3 项 → 按 skill 红线必须修复，不能交付")
        elif yellows:
            print("🟡 少量建议项 → 可人工确认后交付")
        else:
            print("✅ 全部通过 → 可以交付")

    return issues


def main():
    parser = argparse.ArgumentParser(description='SillyTavern character-card enrichment self-check')
    parser.add_argument('card', help='card JSON path')
    parser.add_argument('--repair-mode', action='store_true', help='修卡模式：仍保留全卡红线，但报告标注为修卡回归')
    parser.add_argument('--r18', action='store_true', help='启用R18内容空壳启发式检查（只抽查核心素材条目，不全卡硬套）')
    parser.add_argument('--prototype', default='', help='卡型原型（如 A/B/C/D/E/G）；用于三路径等按原型门控')
    parser.add_argument('--three-path', choices=['auto', 'hard', 'soft', 'none'], default='auto', help='事件种子三路径门控：auto按原型/事件语义启用，或显式hard/soft/none')
    parser.add_argument('--manifest', help='optional Manifest v2; supplies event_mode/corpus_mode/route_policy without changing legacy defaults')
    args = parser.parse_args()

    card_path = args.card
    if not Path(card_path).exists():
        print(f"❌ 文件不存在: {card_path}")
        sys.exit(1)

    try:
        policy = load_quality_policy(args.manifest)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"❌ policy Manifest 无法读取: {exc}")
        sys.exit(1)
    issues = check_card(
        card_path,
        repair_mode=args.repair_mode,
        r18=args.r18,
        prototype=args.prototype,
        three_path=args.three_path,
        **policy,
    )
    reds = [m for s, m in issues if s == '🔴']
    yellows = [m for s, m in issues if s == '🟡']
    open_anchor_policy = (
        policy.get('event_mode') == 'open_situation_seed'
        and policy.get('corpus_mode') == 'curated_anchor_set'
    )
    sys.exit(1 if reds or (len(yellows) >= 3 and not open_anchor_policy) else 0)


if __name__ == '__main__':
    main()
