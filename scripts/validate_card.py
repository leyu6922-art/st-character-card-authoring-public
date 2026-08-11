#!/usr/bin/env python3
"""
角色卡自动验证脚本 v5.2（CCv3 core + Leyu-production 交付门控；共享 World Info matcher）
在 execute_code 中 exec(open(...).read()) 后调用 validate_card(path)。
"""
import json, re, os, sys, argparse
from collections import Counter

from lib.card_issues import Issue, ValidationReport, stable_legacy_rule_id
from lib.validation_profiles import CCV3_CORE, LEYU_PRODUCTION, PROFILES, validate_ccv3_core
from lib.worldbook_matcher import entry_trigger_match as shared_entry_trigger_match, simulate_recursive_activation
from lib.stage_memory import phase_memory_anchor_issues
from lib.stage_routing import (
    bound_titles_by_stage,
    card_entries,
    declared_titles_by_stage,
    has_native_stage_routing,
    primary_keys,
)


ENTRY_ROLES = {"identity_toggle", "feature_toggle", "system_constant", "common_content"}
PLAYER_AGENCY_FEATURE_MODES = {"narrative_director", "player_agency_boundary"}
META_LABEL_KEYS = {"事件库", "种子库", "描写库", "语料库", "对话库", "人物档案", "角色档案", "设定", "感官", "氛围", "档案"}
NATURAL_PATH_MARKERS = {
    "character": ("人物", "角色", "档案", "关系", "南问天", "南向晚", "陆雪儿", "红莲", "莫埃"),
    "scene": ("地点", "场景", "院门", "院子", "青云村", "主屋", "山路", "殿", "厨房"),
    "action": ("动作", "敲门", "走", "来到", "闯入", "战斗", "反抗", "操", "征服", "冲突"),
}


def _is_stage_routed_entry(entry: dict) -> bool:
    """Stage packs deliberately route from a Greeting title/route marker, not natural OR keys."""
    comment = str(entry.get("comment", ""))
    keys = [str(key) for key in entry.get("keys", []) if key]
    return (
        bool(re.search(r"(?:阶段|事件库)[_·：:]?P\d+", comment))
        or any(re.search(r"(?:【开场：P\d+|ROUTE_STAGE=P\d+|阶段：P\d+)", key) for key in keys)
    )


def _event_seed_key_errors(entries: list[dict]) -> list[str]:
    """Require three distinct natural primary keys for independently triggerable seeds.

    Native stage packs are exempt: their Greeting title is an intentional exact route.
    ``secondary_keys`` are not counted because they are AND filters rather than independent
    natural paths in SillyTavern.
    """
    errors: list[str] = []
    for entry in entries:
        comment = str(entry.get("comment", ""))
        is_seed = "事件" in comment or "种子" in comment
        if not is_seed or entry.get("constant") or not entry.get("enabled", True):
            continue
        if _is_stage_routed_entry(entry):
            continue
        keys = [re.sub(r"\s+", "", str(key)) for key in entry.get("keys", []) if str(key).strip()]
        distinct = list(dict.fromkeys(keys))
        if len(distinct) < 3:
            errors.append(
                f"EVENT_SEED_KEY_COUNT 条目[{entry.get('id')}] '{comment[:25]}': "
                f"普通事件/种子条目至少需要3个不同的自然primary keys，当前{distinct}；"
                "阶段Greeting/route条目例外。"
            )
    return errors


def _narrative_text_without_dialogue(text: str) -> str:
    """Dialogue may naturally contain second-person address; identity narration may not."""
    text = str(text)
    text = re.sub(r"「[^」]*」", "", text)
    text = re.sub(r"“[^”]*”", "", text)
    text = re.sub(r'"[^"\n]*"', "", text)
    return text


def infer_entry_role(entry: dict) -> str:
    """Infer a runtime role without mutating a legacy entry."""
    explicit = (entry.get("extensions") or {}).get("entry_role")
    if explicit in ENTRY_ROLES:
        return explicit
    content = str(entry.get("content", ""))
    comment = str(entry.get("comment", ""))
    if entry.get("constant") and not entry.get("enabled", True) and "{{user}}" in content:
        return "identity_toggle"
    if entry.get("constant") and entry.get("enabled", True) and not entry.get("keys", []):
        if any(k in comment or k in content for k in ("剧情导演", "场景边界", "功能开关")):
            return "feature_toggle"
        return "system_constant"
    return "common_content"


def is_opt_in_player_agency_feature(entry: dict) -> bool:
    """The two player-agency modes are valid disabled manual feature toggles."""
    extensions = entry.get("extensions") or {}
    return (
        infer_entry_role(entry) == "feature_toggle"
        and extensions.get("feature_mode") in PLAYER_AGENCY_FEATURE_MODES
    )


def _natural_path_types(entry: dict) -> set[str]:
    text = " ".join([str(entry.get("comment", "")), *[str(k) for k in entry.get("keys", [])], str(entry.get("content", ""))[:500]])
    return {kind for kind, markers in NATURAL_PATH_MARKERS.items() if any(marker in text for marker in markers)}


def _validate_g_entry_contract(entries, errors, warnings):
    has_g_signal = any(
        (entry.get("extensions") or {}).get("entry_role") in ENTRY_ROLES
        or (entry.get("constant") and not entry.get("enabled", True) and "{{user}}" in str(entry.get("content", "")))
        for entry in entries
    )
    if not has_g_signal:
        return
    for entry in entries:
        role = infer_entry_role(entry)
        if (entry.get("extensions") or {}).get("entry_role") not in ENTRY_ROLES:
            warnings.append(f"G_ENTRY_ROLE_INFERRED 条目[{entry.get('id')}] '{entry.get('comment','')[:25]}': 推断为{role}，建议迁移")
        if role == "identity_toggle":
            bad = []
            if not entry.get("constant"): bad.append("constant=true")
            if entry.get("enabled", True): bad.append("enabled=false")
            if entry.get("keys"): bad.append("keys=[]")
            if entry.get("secondary_keys"): bad.append("secondary_keys=[]")
            if entry.get("selective") is not False: bad.append("selective=false")
            if "{{user}}" not in str(entry.get("content", ""))[:300]: bad.append("前300字定义{{user}}")
            if "你" in _narrative_text_without_dialogue(str(entry.get("content", ""))):
                errors.append(
                    f"G_IDENTITY_TOGGLE_RAW_YOU 条目[{entry.get('id')}]: "
                    "身份选开叙述层不得用‘你’指代玩家，必须明确写{{user}}或固定玩家名；角色对白除外。"
                )
            if bad: errors.append(f"G_IDENTITY_TOGGLE_SCHEMA 条目[{entry.get('id')}]: 违反{', '.join(bad)}")
        elif role == "feature_toggle":
            feature_mode = (entry.get("extensions") or {}).get("feature_mode")
            expected_enabled = feature_mode not in PLAYER_AGENCY_FEATURE_MODES
            if not (
                entry.get("constant")
                and entry.get("enabled", True) is expected_enabled
                and not entry.get("keys")
                and not entry.get("secondary_keys")
                and entry.get("selective") is False
            ):
                enabled_text = "enabled=true" if expected_enabled else "enabled=false"
                errors.append(
                    f"G_FEATURE_TOGGLE_SCHEMA 条目[{entry.get('id')}]: "
                    f"功能开关必须constant=true/{enabled_text}/keys=[]/secondary_keys=[]/selective=false"
                )
        elif role == "system_constant":
            if not (entry.get("constant") and entry.get("enabled", True) and not entry.get("keys")):
                errors.append(f"G_SYSTEM_CONSTANT_SCHEMA 条目[{entry.get('id')}]: 系统常驻必须constant=true/enabled=true/keys=[]")
        elif role == "common_content":
            if "{{user}}" in str(entry.get("content", "")):
                errors.append(f"G_COMMON_CONTENT_USER_LEAK 条目[{entry.get('id')}]: common_content不得含{{{{user}}}}")
            keys = [str(k) for k in entry.get("keys", []) if k]
            if keys and all(k in META_LABEL_KEYS for k in keys):
                errors.append(f"TRIGGER_META_LABEL_ONLY 条目[{entry.get('id')}]: keys全为元标签{keys}")
            if ("事件" in str(entry.get("comment", "")) or "种子" in str(entry.get("comment", ""))) and entry.get("enabled", True):
                paths = _natural_path_types(entry)
                if len(paths) < 2:
                    warnings.append(f"EVENT_NATURAL_PATH_INSUFFICIENT 条目[{entry.get('id')}]: 自然路径仅{sorted(paths)}")


def _validate_leyu_production_legacy(path, target_size_kb=None, greeting_mode="player_prose"):
    errors = []
    warnings = []

    # 1. JSON解析
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            card = json.load(f)
    except Exception as e:
        return False, [f"JSON解析失败: {e}"], []

    fsize = os.path.getsize(path)

    # 2. 文件大小
    if target_size_kb:
        if fsize < target_size_kb * 1024 * 0.8:
            warnings.append(f"文件大小 {fsize/1024:.1f}KB < 目标 {target_size_kb}KB×80%")
        elif fsize >= target_size_kb * 1024:
            pass  # OK

    # 3. Leyu-production requires the CCv3 root envelope, but never treats
    # exporter mirrors or data.spec/data.spec_version as universal schema rules.
    if not isinstance(card, dict) or 'spec' not in card or 'data' not in card:
        errors.append("缺少 spec 或 data 顶层字段")
        return False, errors, warnings
    if card.get('spec') != 'chara_card_v3':
        errors.append(f"spec应为chara_card_v3，实际为{card.get('spec')}")
    data = card['data']
    if not isinstance(data, dict):
        errors.append("data必须是对象")
        return False, errors, warnings

    # A top-level/data mirror is checked only when an exporter stored both copies.
    # data.spec and data.spec_version are non-CCv3 compatibility extras: preserve
    # them if present, but do not require or assert unverified ST importer behavior.

    # character_version / alternate_greetings are optional v3 top-level mirrors, but if
    # a card stores both copies they must remain byte-for-byte equivalent.  Otherwise
    # importer/UI behavior depends on which mirror a consumer reads.
    sync_fields = [
        'name', 'description', 'personality', 'scenario', 'first_mes', 'mes_example',
        'character_version', 'alternate_greetings',
    ]
    for field in sync_fields:
        if field in card and field in data and card.get(field) != data.get(field):
            errors.append(f"顶层.{field} 与 data.{field} 不一致（以data层为准同步；镜像字段漂移会导致ST显示/导入版本不一致）")

    # 4. 关键字段
    for field in ['name', 'description', 'first_mes', 'alternate_greetings']:
        if field not in data:
            errors.append(f"data.{field} 缺失")

    # 5. mes_example 必须存在（v3格式要求）
    if 'mes_example' not in data:
        errors.append("data.mes_example 缺失（v3必须有，空字符串即可）")

    # 5b. post_history_instructions 必须存在
    if 'post_history_instructions' not in data:
        errors.append("data.post_history_instructions 缺失（v3必须有，空字符串即可）")

    # 6. group_only_greetings
    if 'group_only_greetings' not in data:
        warnings.append("data.group_only_greetings 缺失")

    # 7. alternate_greetings 位置
    if 'extensions' in data and 'alternate_greetings' in data.get('extensions', {}):
        errors.append("alternate_greetings 误放在 extensions 里（应在 data 层）")

    # 8. Greeting mode: player prose keeps the established 1400-character floor.
    # Appendix and trigger modes have their own focused audits and must not pad
    # natural text merely to satisfy a generic structural validator.
    greeting_modes = {"player_prose", "prose_plus_director_appendix", "ai_trigger"}
    if greeting_mode not in greeting_modes:
        errors.append(f"GREETING_MODE_UNKNOWN: 不支持的greeting_mode={greeting_mode}")
        greeting_mode = "player_prose"
    fm = data.get('first_mes', '')
    if not str(fm).strip():
        errors.append("GREETING_EMPTY: first_mes不能为空")
    if greeting_mode == "player_prose" and len(fm) < 1400:
        errors.append(f"first_mes 仅 {len(fm)} 字（player_prose应≥1400）")

    alt = data.get('alternate_greetings', [])
    if not isinstance(alt, list):
        errors.append("alternate_greetings必须是数组")
        alt = []
    for i, g in enumerate(alt):
        if not str(g).strip():
            errors.append(f"GREETING_EMPTY: alternate[{i}]不能为空")
        if greeting_mode == "player_prose" and len(g) < 1400:
            errors.append(f"alternate[{i}] 仅 {len(g)} 字（player_prose应≥1400）")

    # 9-10. 开场白emoji检查
    def check_emoji(text, label):
        issues = []
        for ch in text:
            if ord(ch) > 0xFFFF:
                issues.append(f"U+{ord(ch):04X}({ch})")
                break
        return issues

    emoji = check_emoji(fm, "first_mes")
    if emoji:
        errors.append(f"first_mes 含emoji: {emoji[0]}")

    for i, g in enumerate(alt):
        emoji = check_emoji(g, f"alt[{i}]")
        if emoji:
            errors.append(f"alt[{i}] 含emoji: {emoji[0]}")

    # 10b. 开场白重复/补字灌水检查（T48/T77）
    def check_greeting_repetition(text, label):
        reps = []
        if not text:
            return reps
        if re.search(r'pad_to|重复补字|填充占位|机械填充', text, re.I):
            reps.append(('error', f"{label} 含构建残留词（pad_to/重复补字/填充）"))
        # HTML 消息（内嵌 UI 开场页）的标签行天然重复，跳过文本行级重复/旁白/句子检查
        if text.lstrip().lower().startswith('<html>'):
            return reps
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        line_counts = Counter(lines)
        for line, count in line_counts.items():
            if count >= 3 and len(line) >= 8:
                reps.append(('error', f"{label} 同一行重复{count}次: {line[:40]}"))
                break
        for a, b in zip(lines, lines[1:]):
            if a == b and len(a) >= 8:
                reps.append(('error', f"{label} 存在连续重复行: {a[:40]}"))
                break
        narration = re.findall(r'【(?:旁白|系统)：[^】]{8,}】', text)
        n_counts = Counter(narration)
        for sent, count in n_counts.items():
            if count >= 2:
                sev = 'error' if count >= 3 else 'warning'
                reps.append((sev, f"{label} 同一句旁白/系统提示重复{count}次: {sent[:50]}"))
                break
        sentences = [s.strip() for s in re.split(r'[。！？!?\n]+', text) if len(s.strip()) >= 12]
        if len(sentences) >= 10:
            c = Counter(sentences)
            dup = sum(v - 1 for v in c.values() if v > 1)
            ratio = dup / max(1, len(sentences))
            if ratio > 0.25:
                reps.append(('error', f"{label} 重复句比例过高 {ratio:.0%}（疑似补字灌水）"))
            elif ratio > 0.15:
                reps.append(('warning', f"{label} 重复句比例偏高 {ratio:.0%}，需人工确认不是拼接重复"))
        return reps

    for label, text in [('first_mes', fm)] + [(f'alternate[{i}]', g) for i, g in enumerate(alt)]:
        for sev, msg in check_greeting_repetition(text, label):
            (errors if sev == 'error' else warnings).append(msg)

    # 10c. 开场白完整性/可读性检查（2026-07-16：低阶模型交付门控）
    def check_greeting_completeness(text, label):
        issues = []
        if not text:
            return issues
        stripped = text.strip()
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n+', stripped) if p.strip()]
        if len(stripped) >= 1400 and len(paragraphs) < 5:
            issues.append(('warning', f"{label} 非空段落仅{len(paragraphs)}段（建议≥5段；一整段密集文本在ST中可读性差）"))
        if len(stripped) >= 1400 and '\n\n' not in stripped and len(stripped) > 1800:
            issues.append(('warning', f"{label} 疑似一整段密集文本（≥1800字符且无空行分段）"))
        tail = stripped[-1] if stripped else ''
        if tail in {'，', '、', '：', ':', '；', ';', ','}:
            issues.append(('error', f"{label} 结尾停在'{tail}'，疑似截断/半句，必须回源修复"))
        elif stripped.endswith(('……', '…')):
            issues.append(('warning', f"{label} 结尾为省略号，需人工确认不是截断半句"))
        bracket_pairs = [('“', '”'), ('「', '」'), ('『', '』'), ('（', '）'), ('【', '】'), ('《', '》')]
        unbalanced = []
        for left, right in bracket_pairs:
            if stripped.count(left) != stripped.count(right):
                unbalanced.append(f"{left}{right}")
        if unbalanced:
            issues.append(('warning', f"{label} 引号/括号数量不平衡: {', '.join(unbalanced)}（需人工确认是否截断或复制漏尾）"))
        return issues

    for label, text in [('first_mes', fm)] + [(f'alternate[{i}]', g) for i, g in enumerate(alt)]:
        for sev, msg in check_greeting_completeness(text, label):
            (errors if sev == 'error' else warnings).append(msg)

    # JSON \uXXXX escapes are valid serialisation, not card-content leakage.
    # Do not reject them: default json.dumps() uses them and json.load() decodes them safely.

    # 12. character_book
    cb = data.get('character_book', {})
    if not cb:
        warnings.append("无 character_book")
        return len(errors) == 0, errors, warnings

    entries = cb.get('entries', [])

    # G型选开/自然触发契约：显式entry_role优先，旧卡仅推断并给迁移warning。
    _validate_g_entry_contract(entries, errors, warnings)

    # 13. 条目格式检查
    required_ext_fields = {
        'position', 'exclude_recursion', 'display_index', 'probability', 'useProbability',
        'depth', 'selective', 'selectiveLogic', 'case_sensitive', 'match_whole_words',
        'use_group_scoring', 'automation_id', 'role', 'vectorized', 'sticky', 'cooldown',
        'delay', 'scan_depth', 'match_persona_description', 'match_character_description',
        'match_character_personality', 'match_character_depth_prompt', 'match_scenario',
        'match_creator_notes', 'triggered', 'group', 'group_override', 'group_weight',
        'prevent_recursion', 'delay_until_recursion', 'addMemo'
    }
    required_entry_fields = {
        'id', 'keys', 'secondary_keys', 'comment', 'content', 'constant', 'selective',
        'addMemo', 'insertion_order', 'enabled', 'position', 'use_regex', 'extensions'
    }
    for e in entries:
        eid = e.get('id', '?')
        comment = e.get('comment', '')[:30]
        problems = []

        missing_entry = sorted(required_entry_fields - set(e.keys()))
        if missing_entry:
            problems.append(f"缺少顶层字段: {missing_entry}")

        if 'keysecondary' in e and 'secondary_keys' not in e:
            problems.append("用了 keysecondary（应为 secondary_keys）")
        if 'order' in e and 'insertion_order' not in e:
            problems.append("用了 order（应为 insertion_order）")

        ext = e.get('extensions', {})
        if not ext:
            problems.append("extensions 为空（应有31个字段）")
        else:
            missing_ext = sorted(required_ext_fields - set(ext.keys()))
            if missing_ext:
                problems.append(f"extensions缺少字段: {missing_ext}（应有31个字段）")

        if 'addMemo' not in e:
            problems.append("缺少 addMemo 字段")

        if problems:
            errors.append(f"条目[{eid}] '{comment}': {'; '.join(problems)}")

    # 13b. addMemo 全量检测（2026-07-13·v4.6新增）
    # T31/T34: 全部addMemo=False → 世界书在ST中完全不链接，致命问题
    addmemo_false = [e['id'] for e in entries if not e.get('addMemo', False)]
    if addmemo_false and len(addmemo_false) == len(entries):
        errors.append(f"🔴 全部 {len(entries)} 条目的 addMemo=False —— 世界书在ST中完全不链接！必须全部设为True（含双重写入：entry顶层+extensions内）")
    elif addmemo_false:
        warnings.append(f"⚠️ {len(addmemo_false)}/{len(entries)} 条目的 addMemo=False（建议全部True。全部False=世界书不链接）")

    # 13c. addMemo 双重写入检测（T34）
    # ST可能读取extensions内的addMemo而非entry顶层
    ext_addmemo_missing = [e['id'] for e in entries
                          if e.get('addMemo') and not e.get('extensions', {}).get('addMemo')]
    if ext_addmemo_missing:
        warnings.append(f"⚠️ {len(ext_addmemo_missing)}条目的extensions内缺addMemo（T34双重写入缺失）。修复：for e in entries: e['extensions']['addMemo'] = True")

    # 14. enabled状态（事件种子库/选开身份条目的禁用是合理的）
    for e in entries:
        if not e.get('enabled', True):
            comment = e.get('comment', '')
            is_xuankai_identity = infer_entry_role(e) == "identity_toggle"
            is_opt_in_feature = is_opt_in_player_agency_feature(e)
            if '事件' in comment or '种子' in comment:
                warnings.append(f"条目[{e.get('id')}] 被禁用 (enabled=false)——事件种子库，设计如此")
            elif not (is_xuankai_identity or is_opt_in_feature):
                errors.append(f"条目[{e.get('id')}] 被禁用 (enabled=false)——非事件种子/非选开身份条目不应禁用")

    # 15. ID连续性
    ids = [e.get('id', -1) for e in entries]
    if len(set(ids)) != len(ids):
        errors.append(f"条目ID有重复")
    expected = list(range(len(ids)))
    if ids != expected:
        errors.append(f"条目ID不连续: {ids[:5]}... ≠ {expected[:5]}...")

    # 16. 常驻条目数量
    constants = [e for e in entries if e.get('constant')]
    if len(constants) > 15:
        warnings.append(f"常驻条目 {len(constants)} 个（建议≤15）")

    # 17. 条目emoji
    for e in entries:
        content = e.get('content', '')
        for ch in content:
            if ord(ch) > 0xFFFF:
                errors.append(f"条目[{e.get('id')}] 含emoji: U+{ord(ch):04X}")
                break

    # 18. 开场白未误入世界书（豁免：格式指令条目含<maintext>标签但含'TXT格式'/'输出格式'等结构化标识的不算开场白）
    for e in entries:
        content = e.get('content', '')
        if '<maintext>' in content[:100] and len(content) > 1000:
            if '输出格式' not in content and 'TXT格式' not in content and '正文格式' not in content:
                warnings.append(f"条目[{e.get('id')}] 可能含开场白内容（<maintext>在content前100字，且不是格式指令条目）")

    # 19. 条目内容重复
    contents = [(e.get('id'), e.get('comment',''), e.get('content','')[:500]) for e in entries]
    for i, (id1, c1, txt1) in enumerate(contents):
        for j, (id2, c2, txt2) in enumerate(contents):
            if j <= i or len(txt1) < 100 or len(txt2) < 100:
                continue
            words1 = set(txt1.split())
            words2 = set(txt2.split())
            if len(words1) > 10 and len(words2) > 10:
                overlap = len(words1 & words2) / min(len(words1), len(words2))
                if overlap > 0.8:
                    warnings.append(f"条目内容高度相似: '{c1[:20]}' vs '{c2[:20]}' ({overlap*100:.0f}%)")

    # 20. 人物关系一致性预警（T76：无主语亲属词导致关系错位）
    # 典型错误：在詹姆条目写“自己的妹妹/亲妹妹”实际应为“林子睿的妹妹”；
    # 在麦克条目写“亲生母亲”实际应为“林子睿的母亲”。自动检查只做预警，要求人工对照§2.4关系锚点表。
    relation_risk_patterns = [
        r'自己的妹妹', r'自己的姐姐', r'自己的母亲', r'自己的父亲',
        r'亲妹妹', r'亲姐姐', r'亲生母亲', r'亲生父亲',
        r'麦克的母亲', r'詹姆的妹妹', r'姐姐侍妾'
    ]
    relation_explicit_exceptions = [r'南问天的亲生母亲', r'X的亲生母亲']
    for e in entries:
        content = e.get('content', '')
        comment = e.get('comment', '')[:30]
        for pat in relation_risk_patterns:
            if re.search(pat, content) and not any(re.search(exc, content) for exc in relation_explicit_exceptions):
                warnings.append(
                    f"条目[{e.get('id')}] '{comment}': 高风险人物关系短语'{pat}'，"
                    "需对照人物关系矩阵确认参照对象；优先改成'X的妹妹/母亲/父亲'等绝对关系锚点"
                )
                break

    # 20b. 角色档案关系锚点提示（新卡建议）
    for e in entries:
        comment = e.get('comment', '')
        if any(k in comment for k in ['基础档案', '角色档案']) and '关系锚点' not in e.get('content', '')[:300]:
            warnings.append(f"条目[{e.get('id')}] '{comment[:30]}': 角色档案前300字缺少【关系锚点】段，容易产生血缘/归属错位")

    # 21. SP-数据库兼容性
    if len(entries) > 50:
        const_count = len([e for e in entries if e.get('constant')])
        warnings.append(f"SP-数据库兼容性: {len(entries)}条目 > 50，常驻{const_count}条，风险高。用户需调大 maxEntriesPerChannel.tableFill 到50-80（SP-数据库）")

    # JSON \UXXXXXXXX escapes are also legal serialisation details. Content-level
    # Unicode display checks belong to a future explicit compatibility profile.

    # 23. 非模板条目状态栏字符
    status_markers = ['📅', '⏰', '📍', '👤', '💭', '👗', '🍆', '🌸', '🍒']
    for e in entries:
        content = e.get('content', '')
        comment = e.get('comment', '')
        # 豁免条件：(1)状态栏条目 或 (2)格式增强条目 或 (3)含明确格式模板标识
        if '状态栏' in comment or '格式增强' in comment or '输出格式' in content[:500]:
            continue
        for marker in status_markers:
            if marker in content:
                warnings.append(f"条目[{e.get('id')}] 含状态栏字符 {marker}")
                break

    # 24. 关键词重叠
    all_keys = []
    for e in entries:
        all_keys.extend(e.get('keys', []))
    key_counts = Counter(all_keys)
    overlapping = [(k, v) for k, v in key_counts.items() if v >= 3]
    if overlapping:
        for k, v in overlapping[:5]:
            warnings.append(f"关键词 '{k}' 被 {v} 个条目共享（可能导致截断）")

    # 25. character_book metadata is legal CCv3/ST export data. It is intentionally
    # preserved by builds and migrations; do not warn merely because it is present.

    # 26. 常驻条目必须 keys=[]。疑似G型选开身份跳过这里，统一交给选开专项报更准确错误，避免重复报错。
    for e in entries:
        comment = e.get('comment', '')
        content = e.get('content', '')
        is_likely_xuankai = ('选开' in comment or ('身份' in comment and '{{user}}' in content[:500]))
        if e.get('constant') and e.get('keys') and not is_likely_xuankai:
            errors.append(f"条目[{e.get('id')}] '{e.get('comment','')[:25]}': 常驻条目必须keys=[]，当前有{len(e['keys'])}个关键词（会导致截断）")

    # 27. 独立事件/种子必须有至少三条可独立命中的自然路径。
    # Greeting 标题/route marker 阶段包是精确路由，明确豁免。
    errors.extend(_event_seed_key_errors(entries))

    # 28. first_mes token load is reported by the shared-matcher audit in check 31b.
    # Do not keep a second primary-key-only simulation here.
    const_entries_list = [e for e in entries if e.get('constant')]
    const_chars = sum(len(e.get('content', '')) for e in const_entries_list)
    entry_map = {e['id']: e for e in entries}

    # 28. 通用关键词检测
    generic_patterns = set()
    for e in entries:
        if e.get('constant'):
            continue
        for k in e.get('keys', []):
            if len(k) <= 1:
                generic_patterns.add((e['id'], e.get('comment', '')[:25], k))
    if generic_patterns:
        for eid, comment, k in list(generic_patterns)[:3]:
            warnings.append(f"条目[{eid}] '{comment}': 关键词'{k}'过短，可能误触发")

    # 29. 递归触发链检查（prevent_recursion=False的条目数）
    recursive_problems = []
    for e in entries:
        if e.get('constant'):
            continue
        ext = e.get('extensions', {})
        pr = ext.get('prevent_recursion', None)
        if pr is False:
            recursive_problems.append(e['id'])

    if recursive_problems:
        errors.append(f"递归触发链风险: {len(recursive_problems)}条触发条目的prevent_recursion=False（会导致链式触发→截断）")

    # 30. selective检查（ST读取顶层selective；extensions.selective只是兼容副本，不参与触发）
    selective_missing = []
    ext_only_selective = []
    selective_mismatch = []
    for e in entries:
        if e.get('constant'):
            continue
        top_sel = e.get('selective') is True
        ext_sel = e.get('extensions', {}).get('selective') is True
        if top_sel != ext_sel and 'selective' in e.get('extensions', {}):
            selective_mismatch.append(e.get('id'))
        if e.get('secondary_keys') and not top_sel:
            selective_missing.append(e['id'])
            if ext_sel:
                ext_only_selective.append(e['id'])

    if selective_missing:
        warnings.append(
            f"{len(selective_missing)}条有secondary_keys但顶层selective!=true（ST会忽略secondary_keys；"
            f"若这些副关键词用于限定触发范围，必须改为顶层selective=true，否则会误触发）"
        )
    if ext_only_selective:
        errors.append(
            f"{len(ext_only_selective)}条只有extensions.selective=true但顶层selective!=true："
            f"ST源码读取顶层selective，extensions.selective不能启用副关键词AND逻辑。样例ID={ext_only_selective[:8]}"
        )
    if selective_mismatch:
        warnings.append(
            f"{len(selective_mismatch)}条顶层selective与extensions.selective不一致（ST按顶层selective触发；建议双字段同步）。样例ID={selective_mismatch[:8]}"
        )

    # 31. 递归触发模拟：所有匹配语义统一由 shared matcher 决定。
    non_recursive_triggered, recursive_triggered = simulate_recursive_activation(entries, fm)

    # 计算token负载
    non_rec_chars = sum(len(entry_map[eid].get('content', '')) for eid in non_recursive_triggered)
    rec_chars = sum(len(entry_map[eid].get('content', '')) for eid in recursive_triggered)

    non_rec_total = const_chars + non_rec_chars
    rec_total = const_chars + rec_chars

    # 如果递归触发条目数 > 非递归的2倍，警告
    if len(recursive_triggered) > len(non_recursive_triggered) * 2 and len(recursive_triggered) > 10:
        errors.append(f"递归触发链风险: 非递归{len(non_recursive_triggered)}条({non_rec_total//2}tokens) → 递归{len(recursive_triggered)}条({rec_total//2}tokens)。必须修复prevent_recursion！")
    elif len(recursive_triggered) > len(non_recursive_triggered) + 5:
        warnings.append(f"递归触发可能: 非递归{len(non_recursive_triggered)}条 → 递归{len(recursive_triggered)}条（+{len(recursive_triggered)-len(non_recursive_triggered)}条）")

    # 31b. 世界书触发可达性/误触发审计（2026-07-15·v4.7）
    # 绿灯/启用 ≠ 已触发。ST实际扫描 chat history（当前greeting + 用户/AI消息）。
    # 非selective条目只看primary keys，secondary_keys会被忽略。
    trigger_sources = [('first_mes', fm)] + [(f'alternate[{i}]', g) for i, g in enumerate(alt)]
    hard_generic_keys = {'你', '我', '他', '她', '它', '家', '人'}
    soft_generic_keys = {
        '学校', '教室', '老师', '社团', '房间', '地方', '这里', '那里',
        '前辈', '同学', '男生', '女生', '体育馆', '唱歌'
    }

    # A. 禁止硬泛词做primary key：会把无关场景误触发成绿灯常驻。
    for e in entries:
        if e.get('constant') or not e.get('enabled', True):
            continue
        keys = [k for k in e.get('keys', []) if k]
        hard_hits = [k for k in keys if k in hard_generic_keys or len(k) <= 1]
        soft_hits = [k for k in keys if k in soft_generic_keys]
        if hard_hits:
            errors.append(
                f"条目[{e.get('id')}] '{e.get('comment','')[:25]}': primary key过泛{hard_hits}，"
                f"会在普通聊天中误触发。改为复合短语/专名（如'比企谷家'、'家中派对'），不要用单字泛词。"
            )
        is_scope_bound = e.get('selective') is True and bool(e.get('secondary_keys'))
        if soft_hits and not is_scope_bound:
            warnings.append(
                f"条目[{e.get('id')}] '{e.get('comment','')[:25]}': primary key较泛{soft_hits}，"
                f"且未用顶层selective+secondary做范围绑定；需确认不是误触发来源。"
            )

    # B. 每个开场白独立模拟真实初始触发；alternate 也会成为独立会话的greeting。
    for label, source_text in trigger_sources:
        if not source_text:
            continue
        triggered_detail = []
        for e in entries:
            match = shared_entry_trigger_match(e, source_text)
            if match.ok and not e.get('constant'):
                primary_hits, secondary_hits = match.primary_hits, match.secondary_hits
                triggered_detail.append((e.get('id'), e.get('comment', ''), primary_hits, secondary_hits, len(e.get('content', ''))))

        trigger_chars = sum(item[4] for item in triggered_detail)
        total_trigger_chars = const_chars + trigger_chars
        est_trigger_tokens = total_trigger_chars // 2
        if triggered_detail:
            sample = ', '.join(f"[{eid}]{comment[:12]}" for eid, comment, *_ in triggered_detail[:8])
            if len(triggered_detail) > 8:
                sample += f", ...+{len(triggered_detail)-8}"
            if est_trigger_tokens > 8000:
                warnings.append(
                    f"{label}触发负载较高: {len(const_entries_list)}常驻+{len(triggered_detail)}触发="
                    f"{est_trigger_tokens} tokens（诊断项，不再作为硬错误；是否需要优化取决于ST上下文、模型上下文、是否截断以及触发内容是否有用）。触发条目: {sample}"
                )
            elif est_trigger_tokens > 5000:
                warnings.append(
                    f"{label}触发负载偏高: {len(const_entries_list)}常驻+{len(triggered_detail)}触发="
                    f"{est_trigger_tokens} tokens（诊断项；高token本身不是错误，重点检查是否为泛key噪声或无关条目污染）。触发条目: {sample}"
                )

            # 如果某条只靠硬泛词命中，说明是明确误触发。
            for eid, comment, primary_hits, _secondary_hits, _clen in triggered_detail:
                if primary_hits and all((k in hard_generic_keys or len(k) <= 1) for k in primary_hits):
                    errors.append(
                        f"{label}误触发: 条目[{eid}] '{comment[:25]}' 仅由泛key{primary_hits}命中。"
                        f"这类绿灯不是有效引用，而是噪声加载。"
                    )

    # C. 多主题大条目：任一key命中会加载整包内容，容易把无关NPC/威胁塞进prompt。
    for e in entries:
        if e.get('constant') or not e.get('enabled', True):
            continue
        keys = [k for k in e.get('keys', []) if k]
        content = e.get('content', '')
        if len(keys) >= 4 and content.count('【') >= 3 and not e.get('selective'):
            warnings.append(
                f"条目[{e.get('id')}] '{e.get('comment','')[:25]}': 多主题大条目+多个keys，"
                f"任一关键词命中都会加载整包内容。建议按角色/威胁对象拆分，或使用selective限定。"
            )

    # D. enabled但没有任何开场白能触发：区分核心档案/场景/事件种子，避免死key和误修并存。
    def _is_on_demand_library(comment):
        return any(kw in comment for kw in ['描写库', '语料库', '对话库', '行为库', '反应库', '深度档案', '专用key', '按需'])

    def _is_core_profile_entry(entry):
        c = entry.get('comment', '')
        return (
            not _is_on_demand_library(c)
            and any(kw in c for kw in ['核心', '基础档案', '角色档案', '威胁档案', '人物档案'])
            and len(entry.get('content', '')) > 500
        )

    for e in entries:
        if e.get('constant') or not e.get('enabled', True):
            continue
        ever_triggered = any(shared_entry_trigger_match(e, source_text).ok for _label, source_text in trigger_sources)
        if not ever_triggered and e.get('keys'):
            comment = e.get('comment', '')
            if _is_core_profile_entry(e):
                errors.append(
                    f"条目[{e.get('id')}] '{comment[:25]}': 核心角色/威胁档案所有开场白均不触发。"
                    f"核心档案必须有自然角色名/常用称呼触发，或拆成中厚速览+深度档案。"
                )
            elif '事件' in comment or '种子' in comment:
                pass  # 手动事件种子不触发是预期
            else:
                warnings.append(
                    f"条目[{e.get('id')}] '{comment[:25]}': 所有开场白均不触发。"
                    f"若这是中后期/按需条目可接受；若期望首轮可用，需要把关键词写入对应greeting/chat。"
                )

    # E. 核心档案死key：不能只有“角色名档案/设定”这类正常聊天不会出现的人工key。
    artificial_suffixes = ('档案', '设定', '资料')
    for e in entries:
        if e.get('constant') or not e.get('enabled', True):
            continue
        comment = e.get('comment', '')
        keys = [str(k) for k in e.get('keys', []) if k]
        if _is_core_profile_entry(e) and keys and all(any(suf in k for suf in artificial_suffixes) for k in keys):
            errors.append(
                f"条目[{e.get('id')}] '{comment[:25]}': 核心档案keys全部是人工复合词{keys}，无自然角色名key → 死key风险。"
                f"至少保留一个自然角色名/常用称呼；若token受限，用自然名触发中厚速览。"
            )

    # 32. secondary_keys质量检查（2026-07-05 优化：太泛的副关键词无效）
    generic_sec_keys = {'角色', '设定', '场景', '详细', '系统', '规则', '模板', '世界', '关系', '原著'}
    bad_sec_key_entries = []
    for e in entries:
        if e.get('constant'):
            continue
        sec_keys = e.get('secondary_keys', [])
        if sec_keys and all(k in generic_sec_keys for k in sec_keys):
            bad_sec_key_entries.append((e['id'], e.get('comment', '')[:30], sec_keys))

    if bad_sec_key_entries:
        for eid, comment, keys in bad_sec_key_entries[:3]:
            warnings.append(f"条目[{eid}] '{comment}': secondary_keys太泛{keys}，selective筛选无效")

    # 33. position字符串→数字映射一致性（2026-07-10）
    POS_MAP = {'before_char': 0, 'after_char': 4, 'before_def': 2, 'after_def': 3, 'at_depth': 4}
    for e in entries:
        top_pos = e.get('position')
        ext_pos = e.get('extensions', {}).get('position')
        if isinstance(top_pos, str) and top_pos in POS_MAP:
            expected_num = POS_MAP[top_pos]
            if ext_pos != expected_num:
                errors.append(f"条目[{e.get('id')}] position不一致: top='{top_pos}'(expect {expected_num}), ext.position={ext_pos}")

    # 34. display_index与id一致性（2026-07-10）
    for e in entries:
        di = e.get('extensions', {}).get('display_index')
        eid = e.get('id')
        if di is not None and eid is not None and di != eid:
            warnings.append(f"条目[{eid}] display_index={di} ≠ id={eid}")

    # 35. use_regex字段检查（顶层必填已在check13中硬性检查；这里仅提示非True值）
    for e in entries:
        if 'use_regex' in e and e.get('use_regex') is not True:
            warnings.append(f"条目[{e.get('id')}] use_regex={e.get('use_regex')}（建议统一True）")

    # 36. 模板13检查：角色条目应有"场景反应差异"段（2026-07-11 大型结构化卡模板合规）
    for e in entries:
        comment = e.get('comment', '')
        content = e.get('content', '')
        if '性格' in comment or '角色' in comment:
            if len(content) > 500 and '场景反应差异' not in content and '对苦主' not in content:
                warnings.append(f"条目[{e.get('id')}] '{comment[:25]}': 角色条目缺少'场景反应差异'段（模板13建议：对苦主/对NTR对象/对外人的行为差异）")
                break  # 只报第一个

    # 37. 模板14检查：NTR/剧情卡应有节奏控制条目（2026-07-11）
    tags = card.get('tags', []) + data.get('tags', [])
    tag_str = ' '.join(tags).lower()
    if any(t in tag_str for t in ['ntr', 'ntl', '剧情', '恶堕']):
        has_rhythm = False
        for e in entries:
            content = e.get('content', '')
            if '循环模式' in content or '叙事节奏' in content:
                has_rhythm = True
                break
        if not has_rhythm:
            warnings.append("NTR/剧情卡缺少叙事节奏控制条目（模板14建议：铺垫→紧张→NTR→余韵→日常循环）")

    # 38. 模板16检查：文风锚点应有四类感官（2026-07-11）
    for e in entries:
        content = e.get('content', '')
        if '文风锚点' in e.get('comment', '') or '感官锚点' in content:
            senses = ['视觉', '听觉', '嗅觉', '触觉']
            missing = [s for s in senses if s not in content]
            if missing:
                warnings.append(f"条目[{e.get('id')}] 文风锚点缺少感官类型: {missing}（模板16要求四类感官锚点）")
            break

    # 39. 模板17检查：NTR/A型卡应有反顺从常驻条目（2026-07-11）
    prototype_a = any(t in tag_str for t in ['ntr', '恶堕', '寝取'])
    if prototype_a:
        has_anti = False
        for e in entries:
            if e.get('constant') and ('反顺从' in e.get('content', '') or '玩家不是万能的' in e.get('content', '') or 'NPC有自己的意志' in e.get('content', '')):
                has_anti = True
                break
        if not has_anti:
            warnings.append("NTR/恶堕卡缺少反顺从常驻条目（模板17建议：NPC拒绝策略层次→解释→引导→锁死）")

    # 40. 模板18检查：状态行为标志应有阶段跃迁"门"（2026-07-11）
    for e in entries:
        comment = e.get('comment', '')
        content = e.get('content', '')
        if '状态行为' in comment or '堕落状态' in comment:
            if '阶段跃迁' not in content and '屈服期' not in content:
                warnings.append(f"条目[{e.get('id')}] '{comment[:25]}': 状态行为标志缺少阶段跃迁定义（模板18建议：用具体行为作为'门'）")
                break

    # 41. 模板19检查：场景条目应有安全等级（2026-07-11）
    for e in entries:
        comment = e.get('comment', '')
        content = e.get('content', '')
        if '场景' in comment and ('安全等级' not in content and 'S级' not in content and 'C级' not in content):
            if len(content) > 200:  # 只检查有实质内容的场景条目
                warnings.append(f"条目[{e.get('id')}] '{comment[:25]}': 场景条目缺少安全等级定义（模板19建议：S/A/B/C/D级+事件概率）")
                break  # 只报第一个

    # === G 型多视角卡专用检查（2026-07-13 POC验证后新增） ===

    # 收集所有greeting文本（first_mes + alternates）。必须在G型/选开两类检查之前定义；
    # 选开模式没有selective条目，但check 47也需要扫描greeting。
    all_greetings = [data.get('first_mes', '')] + data.get('alternate_greetings', [])
    xuankai_entries = [
        e for e in entries
        if e.get('constant') and not e.get('enabled', True)
        and ('选开' in e.get('comment', '') or '{{user}}' in e.get('content', ''))
        and (e.get("extensions") or {}).get("entry_role") not in ENTRY_ROLES
    ]

    # 检测是否为G型 greeting 模式卡：不能只看selective=true。
    # 普通世界书也会大量使用selective做地点/场景二级限定（大型结构化卡就是典型）。
    # 只有greeting首行出现身份/视角标记时，才运行G型专项检查。
    selective_entries = [e for e in entries if e.get('selective') is True]
    first_lines = [(g.split('\n')[0] if '\n' in g else g[:120]) for g in all_greetings if g and g.strip()]
    is_greeting_mode_g = bool(selective_entries) and any(
        ('【▎身份' in line or '身份：' in line or '身份:' in line) and ('视角' in line or '苦主' in line or '寝取' in line or 'NTL' in line)
        for line in first_lines
    )

    # G-Common：Greeting模式与选开模式都必须检查共用层零{{user}}。
    # 选开模式没有selective视角段；如果只在greeting-mode里跑check 43，会漏掉共用层视角残留。
    is_g_type = is_greeting_mode_g or bool(xuankai_entries)
    if is_g_type:
        xuankai_ids = {e.get('id') for e in xuankai_entries}
        system_comment_kw = ['OOC', '系统', '状态栏', '文风', '规则', '防护', '锚点', '叙事', '反顺从']
        for e in entries:
            if e.get('id') in xuankai_ids:
                continue  # 选开身份条目必须含{{user}}
            comment = e.get('comment', '')
            role = infer_entry_role(e)
            if role in {"feature_toggle", "system_constant"}:
                continue
            if e.get('selective'):
                continue  # greeting模式视角层可以含{{user}}

            is_system_constant = e.get('constant') and (
                any(kw in comment for kw in system_comment_kw)
                or '➡️' in comment
                or '分段' in comment
            )
            if is_system_constant:
                continue  # 只有系统/分段常驻可描述当前玩家/视角
            if any(kw in comment for kw in system_comment_kw):
                continue
            content = e.get('content', '')
            if '{{user}}' in content:
                errors.append(
                    f"[G型-Common] 条目[{e.get('id')}] '{comment[:25]}': "
                    f"共用层条目content含{{{{user}}}}引用。"
                    f"（G型铁律：角色/事件/场景/语料条目零{{{{user}}}}，用具体角色名；"
                    f"非系统常驻也不能豁免）"
                )

    if selective_entries and is_greeting_mode_g:

        # 42. G型：视角段secondary_keys应与至少一个greeting有交集。
        # ST源码细节：selective=true但secondary_keys为空时，会退化为primary-only，不是死触发；
        # 但对G型视角隔离来说这会丧失二级隔离，因此给warning。
        for e in selective_entries:
            eid = e.get('id')
            sec_keys = [k for k in e.get('secondary_keys', []) if k]
            if not sec_keys:
                warnings.append(
                    f"[G型] 条目[{eid}] selective=true但secondary_keys为空：ST会按primary-only触发，不会死触发；"
                    f"但若这是视角段，缺少secondary会降低身份隔离可靠性。"
                )
                continue

            found = any(any(k in g for k in sec_keys) for g in all_greetings)
            if not found:
                errors.append(
                    f"[G型] 条目[{eid}] '{e.get('comment','')[:25]}': "
                    f"secondary_keys={sec_keys} 在所有greeting中均不出现。"
                    f"（selective AND逻辑：secondary必须在greeting/chat中出现才能触发。"
                    f"POC教训：'苦主视角'≠'苦主体感'，一字之差全断）"
                )

        # 43. G型共用层零{{user}} 已由上方 G-Common 覆盖（Greeting/选开两种模式共用）。

        # 44. G型：每个身份至少2条视角段
        identity_groups = {}
        for e in selective_entries:
            sec_keys = e.get('secondary_keys', [])
            if sec_keys:
                identity = sec_keys[0]
                identity_groups.setdefault(identity, []).append(e['id'])

        for identity, eids in identity_groups.items():
            if len(eids) < 2:
                warnings.append(
                    f"[G型] 身份'{identity}'仅{len(eids)}条视角段（条目{eids}）。"
                    f"（G型建议：每个可扮演身份至少2条视角段——1条感官+1条心理）"
                )

        # 45. G型：每个greeting首行应含对应身份的关键词
        all_viewpoint_keys = set()
        for e in selective_entries:
            all_viewpoint_keys.update(k for k in e.get('keys', []) if k)
            all_viewpoint_keys.update(k for k in e.get('secondary_keys', []) if k)

        for gi, g in enumerate(all_greetings):
            if not g.strip():
                continue
            first_line = g.split('\n')[0] if '\n' in g else g[:100]
            label = 'first_mes' if gi == 0 else f'alt[{gi-1}]'
            if not any(k in first_line for k in all_viewpoint_keys):
                warnings.append(
                    f"[G型] {label}首行未命中任何视角段关键词。"
                    f"首行: '{first_line[:60]}...'"
                    f"（G型建议：greeting首行格式 【▎身份：XXX】 key1 key2 key3）"
                )

    # === 🆕 选开模式专项检查（checks 46-47）===
    # 先扫所有疑似身份条目，避免“comment写选开但enabled=true/constant=false”漏检。
    maybe_xuankai_entries = [
        e for e in entries
        if infer_entry_role(e) == "identity_toggle"
        and (e.get("extensions") or {}).get("entry_role") not in ENTRY_ROLES
    ]
    for e in maybe_xuankai_entries:
        comment = e.get('comment', '')
        content = e.get('content', '')
        if not e.get('constant'):
            errors.append(f"[选开模式] 条目[{e.get('id')}] '{comment[:25]}': 身份/选开条目必须constant=true")
        if e.get('enabled', True):
            errors.append(f"[选开模式] 条目[{e.get('id')}] '{comment[:25]}': 身份/选开条目必须enabled=false，避免多身份默认同时加载")
        if e.get('keys'):
            errors.append(f"[选开模式] 条目[{e.get('id')}] '{comment[:25]}': 身份/选开条目必须keys=[]，选开模式靠ST世界书UI手动启用，不靠关键词触发")
        if '{{user}}' not in content[:500]:
            errors.append(f"[选开模式] 条目[{e.get('id')}] '{comment[:25]}': 身份/选开条目前500字必须明确定义{{{{user}}}}身份")

    if xuankai_entries:
        # 46. 选开条目应在comment中标注「选开」
        for e in xuankai_entries:
            comment = e.get('comment', '')
            content = e.get('content', '')
            if '选开' not in e.get('comment', ''):
                errors.append(
                    f"[选开模式] 条目[{e.get('id')}] '{e.get('comment','')[:25]}': "
                    f"constant+enabled=false+含{{{{user}}}}，疑似选开条目但comment缺「选开」标注。"
                    f"玩家在ST中无法识别可启用身份。"
                )
            if '{{user}}' not in content[:300]:
                errors.append(
                    f"[选开模式] 条目[{e.get('id')}] '{comment[:25]}': "
                    f"content前300字未明确定义{{{{user}}}}身份。选开身份条目必须自足定义当前玩家。"
                )
            if e.get('selective') is True or e.get('secondary_keys'):
                errors.append(
                    f"[选开模式] 条目[{e.get('id')}] '{comment[:25]}': "
                    f"不得混用selective/secondary_keys；选开模式靠ST世界书UI手动启用，不靠关键词AND触发。"
                )

        # 47. 选开模式 greeting 不应含身份标记首行
        hard_identity_patterns = [
            r'你作为(?:苦主|征服者|寝取者|NTL|守护者|原配|丈夫|男友)',
            r'作为(?:苦主|征服者|寝取者|NTL|守护者)的你',
            r'你是(?:苦主|征服者|寝取者|NTL|守护者)',
        ]
        soft_identity_patterns = [
            r'你本该', r'你的(?:女友|妻子|母亲|妈妈|姐姐|妹妹|恋人)',
            r'你刚(?:放学|下班|回家)', r'你冷笑着走向', r'你终于要夺走',
        ]
        for gi, g in enumerate(all_greetings):
            if not g.strip():
                continue
            first_line = g.split('\n')[0] if '\n' in g else g[:100]
            scan_head = g[:800]
            identity_markers = ['【▎身份', '身份：', '身份:', '苦主视角', '寝取者视角', 'NTL视角', '征服者视角']
            label = 'first_mes' if gi == 0 else f'alt[{gi-1}]'
            if any(marker in first_line for marker in identity_markers):
                warnings.append(
                    f"[选开模式] {label}首行含身份标记「{first_line[:40]}...」。"
                    f"选开模式 greeting 应视角中性，身份标记是 greeting 模式用的。"
                )
            for pat in hard_identity_patterns:
                m = re.search(pat, scan_head)
                if m:
                    errors.append(
                        f"[选开模式] {label} 含明确身份锁死句「{m.group(0)}」。"
                        f"选开模式 greeting 必须舞台中性，不得预设{{{{user}}}}是苦主/征服者/守护者。"
                    )
                    break
            else:
                for pat in soft_identity_patterns:
                    m = re.search(pat, scan_head)
                    if m:
                        warnings.append(
                            f"[选开模式] {label} 疑似身份锁死短语「{m.group(0)}」，需人工确认是否仍为舞台中性。"
                        )
                        break

    # === 🆕 阶段路由与阶段记忆检查（48–57，2026-07-26） ===

    # Native routing is declared by a complete Greeting title, not by whether an
    # entry already binds that title.  This prevents the detection predicate from
    # depending on the binding property it is meant to audit.
    native_titles = declared_titles_by_stage(card)
    bound_titles = bound_titles_by_stage(card)
    has_native_routing = has_native_stage_routing(card)
    if bound_titles and not has_native_routing:
        orphaned = ", ".join(
            f"{stage}:{sorted(titles)[0]}" for stage, titles in sorted(bound_titles.items())
        )
        warnings.append(
            "STAGE_TITLE_KEY_ORPHANED: World Info primary key含完整阶段标题，但Greeting没有对应声明；"
            f"未将卡误判为原生阶段卡。疑似残留绑定：{orphaned}"
        )
    has_external_route = any(
        str(k).startswith("ROUTE_STAGE=")
        for e in entries for k in primary_keys(e)
    )
    has_stage_routing = has_native_routing or has_external_route

    # 也检查是否有死键风格的阶段标记
    dead_stage_keys = set()
    for e in entries:
        for k in (e.get("keys") or []):
            ks = str(k)
            if re.match(r'^(阶段：P\d+|P\d+阶段|阶段P\d+)$', ks):
                dead_stage_keys.add(ks)

    is_stage_card = has_stage_routing or bool(dead_stage_keys)

    if is_stage_card:
        # 49. 混合路由检测
        if has_stage_routing and dead_stage_keys:
            errors.append(
                f"STAGE_ROUTE_SOURCE_AMBIGUOUS: 同时使用标题路由和阶段死键{list(dead_stage_keys)[:3]}。"
                f"必须二选一：全部用标题路由或全部用ROUTE_STAGE=P#格式。"
            )

        # 50. 死键检查：阶段包唯一key是阶段标签/事件库/语料库
        for e in entries:
            if e.get("constant") or not e.get("enabled", True):
                continue
            keys = [str(k) for k in e.get("keys", []) if k]
            if keys and all(
                re.match(r'^(阶段：P\d+|事件库|种子库|描写库|语料库|对话库|档案|设定)$', k)
                for k in keys
            ):
                comment = e.get("comment", "")[:30]
                errors.append(
                    f"STAGE_ROUTE_DEAD_KEY 条目[{e.get('id')}] '{comment}': "
                    f"keys={keys}为人工元标签，不会出现在自然对话中 → 死键。"
                    f"阶段包换Greeting完整标题；普通条目换自然角色名/地点/动作词。"
                )

        # 51. 因果档案存在检查（只认 comment：记忆闸门 content 会提及“全程因果档案”，
        # 扫 content 会被闸门自身文案击穿产生假绿；与 enrichment 层判定口径一致）
        has_causal_archive = any(
            "全程因果档案" in str(e.get("comment", ""))
            for e in entries if e.get("constant")
        )
        if not has_causal_archive:
            errors.append(
                "STAGE_CAUSAL_ARCHIVE_MISSING: 阶段路由卡缺少「核心人物·全程因果档案」常驻条目。"
                "该条目让AI理解人物完整成长方向，避免阶段间人物断裂。"
            )

        # 52. 记忆闸门存在检查
        has_memory_gate = any(
            "阶段记忆" in str(e.get("comment", ""))
            or "阶段记忆与叙事可见性" in str(e.get("content", ""))[:100]
            for e in entries if e.get("constant")
        )
        if not has_memory_gate:
            errors.append(
                "STAGE_MEMORY_GATE_MISSING: 阶段路由卡缺少「绝对优先级·阶段记忆与叙事可见性协议」常驻条目。"
                "该协议阻止AI把未来阶段内容提前表演成角色记忆。"
            )

        # 53. system_prompt 压缩锚点：与阶段合同共用同一规则和稳定 rule_id。
        for issue in phase_memory_anchor_issues(str(data.get("system_prompt", ""))):
            errors.append(issue.render())

        # 53b. Constant entries are visible in every Greeting.  Apart from the
        # two memory components, they must not present a future P-stage state as
        # an already-established fact.
        protected_memory_comments = ("全程因果档案", "阶段记忆与叙事可见性协议")
        future_as_fact = re.compile(r"P\d+(?:之后|以后|阶段)?[^。！？]{0,48}(?:已经|成为|既定|必须)")
        for e in entries:
            if not e.get("constant") or not e.get("enabled", True):
                continue
            comment = str(e.get("comment", ""))
            if any(marker in comment for marker in protected_memory_comments):
                continue
            if future_as_fact.search(str(e.get("content", ""))):
                errors.append(
                    f"STAGE_FUTURE_LEAK_CONSTANT 条目[{e.get('id')}] '{comment[:30]}': "
                    "常驻条目把未来P阶段关系/状态写成既定事实；移入对应阶段包或改为条件候选语义"
                )

        # 54–55. Native title declarations are the authoritative stage set.  For
        # every declared stage, each four-pack role must be bound to that stage's
        # exact Greeting title; ordinary words in a greeting cannot substitute.
        if has_native_routing:
            required_packs = {"阶段核心", "成人体验", "场景体验", "事件库"}
            for stage, declared_titles in native_titles.items():
                if stage == "MENU":
                    # 图鉴 MENU 是独立菜单入口（HTML 开场页），不属于 P0-P6 阶段，
                    # 不要求四包绑定。
                    continue
                found_packs: set[str] = set()
                bound_entries = []
                for e in entries:
                    if e.get("constant") or not e.get("enabled", True):
                        continue
                    bound = set(primary_keys(e)) & declared_titles
                    if not bound:
                        continue
                    bound_entries.append(e)
                    comment = str(e.get("comment", ""))
                    for pack in required_packs:
                        if pack in comment:
                            found_packs.add(pack)
                missing = required_packs - found_packs
                if missing:
                    errors.append(
                        f"STAGE_PACK_INCOMPLETE: {stage}阶段缺少完整标题绑定的四包{missing}。"
                        "每阶段必须齐全：阶段核心/成人体验/场景体验/事件库。"
                    )
                for e in bound_entries:
                    if any(pack in str(e.get("comment", "")) for pack in required_packs):
                        content = str(e.get("content", ""))
                        if len(content.strip()) < 30:
                            comment = str(e.get("comment", ""))[:30]
                            errors.append(
                                f"STAGE_PACK_EMPTY 条目[{e.get('id')}] '{comment}': 阶段包内容为空或过短"
                            )
        else:
            # External routes are rejected by final_delivery_gate, but retain the
            # legacy local empty-pack diagnostic for direct validator callers.
            stage_pack_entries = [
                e for e in entries
                if not e.get("constant") and e.get("enabled", True)
                and any(str(k).startswith("ROUTE_STAGE=") for k in primary_keys(e))
            ]
            external_stage_packs: dict[str, set[str]] = {}
            for e in stage_pack_entries:
                for key in primary_keys(e):
                    marker = re.fullmatch(r"ROUTE_STAGE=(P\d+)", key)
                    if marker:
                        stage = marker.group(1)
                        found = external_stage_packs.setdefault(stage, set())
                        comment = str(e.get("comment", ""))
                        for pack in ("阶段核心", "成人体验", "场景体验", "事件库"):
                            if pack in comment:
                                found.add(pack)
                if len(str(e.get("content", "")).strip()) < 30:
                    errors.append(
                        f"STAGE_PACK_EMPTY 条目[{e.get('id')}] '{str(e.get('comment', ''))[:30]}': 阶段包内容为空或过短"
                    )
            for stage, found in external_stage_packs.items():
                missing = {"阶段核心", "成人体验", "场景体验", "事件库"} - found
                if missing:
                    errors.append(f"STAGE_PACK_INCOMPLETE: {stage}阶段缺少四包{missing}。")

        # 56. 高阶段包泛key检测
        for e in entries:
            if e.get("constant") or not e.get("enabled", True):
                continue
            comment = str(e.get("comment", ""))
            # 只检查 stage_pack 类条目
            if not any(pack in comment for pack in ("阶段核心", "成人体验", "场景体验", "事件库")):
                continue
            keys = [str(k) for k in e.get("keys", []) if k]
            broad_keys = {"客厅", "吃饭", "晚上", "床上", "卧室", "沙发", "厨房", "妈妈", "爸爸", "妹妹"}
            hits = [k for k in keys if k in broad_keys]
            if hits:
                errors.append(
                    f"STAGE_HIGH_PHASE_BROAD_KEY 条目[{e.get('id')}] '{comment[:25]}': "
                    f"阶段包使用高频泛key{hits}，会导致早期阶段误触发后期内容。"
                    f"阶段包只能用Greeting标题或ROUTE_STAGE=P#触发。"
                )

        # 57. 事件候选语义检查
        for e in entries:
            if not e.get("enabled", True):
                continue
            comment = str(e.get("comment", ""))
            if "事件库" not in comment and "事件种子" not in comment:
                continue
            content = e.get("content", "")
            # 检查既定史措辞
            fact_markers = ["已经被", "此后每次", "从此以后", "固定会", "角色已经接受", "已经成为"]
            found = [m for m in fact_markers if m in content]
            if found:
                warnings.append(
                    f"STAGE_EVENT_FACT_LANGUAGE 条目[{e.get('id')}] '{comment[:25]}': "
                    f"事件库含既定史措辞{found}。事件种子应使用候选语言：'当X条件成立后'/'可能发生Y'。"
                )
            # 检查是否有候选语义标记
            candidate_markers = ["前提", "自然切入", "人物反应", "分歧", "代价", "候选"]
            has_candidate = any(m in content for m in candidate_markers)
            if not has_candidate and len(content.strip()) > 100:
                warnings.append(
                    f"STAGE_EVENT_NOT_CANDIDATE 条目[{e.get('id')}] '{comment[:25]}': "
                    f"事件库缺少候选语义标记（前提/切入/反应/分歧），可能被AI当作既定历史。"
                )

    passed = len(errors) == 0
    return passed, errors, warnings


def _legacy_issue(message, severity):
    """Bridge v5.1 text diagnostics to v5.2 structured reports without a rewrite."""
    entry_match = re.search(r"条目\[([^\]]+)\]", message)
    entry_ref = entry_match.group(1) if entry_match else "*"
    path = "data.character_book.entries" if entry_ref == "*" else f"data.character_book.entries[{entry_ref}]"
    rule_map = (
        ("G_IDENTITY_TOGGLE_SCHEMA", "G_IDENTITY_TOGGLE_SCHEMA", "G_IDENTITY_TOGGLE_SCHEMA", path),
        ("G_FEATURE_TOGGLE_SCHEMA", "G_FEATURE_TOGGLE_SCHEMA", "G_FEATURE_TOGGLE_SCHEMA", path),
        ("G_SYSTEM_CONSTANT_SCHEMA", "G_SYSTEM_CONSTANT_SCHEMA", "G_SYSTEM_CONSTANT_SCHEMA", path),
        ("G_COMMON_CONTENT_USER_LEAK", "G_COMMON_CONTENT_USER_LEAK", "G_COMMON_CONTENT_USER_LEAK", path),
        ("TRIGGER_META_LABEL_ONLY", "TRIGGER_META_LABEL_ONLY", "TRIGGER_META_LABEL_ONLY", path),
        ("EVENT_NATURAL_PATH_INSUFFICIENT", "EVENT_NATURAL_PATH_INSUFFICIENT", "EVENT_NATURAL_PATH_INSUFFICIENT", path),
        ("G_ENTRY_ROLE_INFERRED", "G_ENTRY_ROLE_INFERRED", "G_ENTRY_ROLE_INFERRED", path),
        ("STAGE_ROUTE_DEAD_KEY", "", "STAGE_ROUTE_DEAD_KEY", path),
        ("STAGE_ROUTE_SOURCE_AMBIGUOUS", "", "STAGE_ROUTE_SOURCE_AMBIGUOUS", path),
        ("STAGE_CAUSAL_ARCHIVE_MISSING", "", "STAGE_CAUSAL_ARCHIVE_MISSING", path),
        ("STAGE_MEMORY_GATE_MISSING", "", "STAGE_MEMORY_GATE_MISSING", path),
        ("STAGE_MEMORY_ANCHOR_TOO_SHORT", "", "STAGE_MEMORY_ANCHOR_TOO_SHORT", "data.system_prompt"),
        ("STAGE_MEMORY_RULE_LABEL_MISSING", "", "STAGE_MEMORY_RULE_LABEL_MISSING", "data.system_prompt"),
        ("STAGE_MEMORY_ONLY_REMEMBERS_ANCHOR_MISSING", "", "STAGE_MEMORY_ONLY_REMEMBERS_ANCHOR_MISSING", "data.system_prompt"),
        ("STAGE_TITLE_KEY_ORPHANED", "", "STAGE_TITLE_KEY_ORPHANED", path),
        ("STAGE_SYSTEM_PROMPT_ANCHOR_MISSING", "", "STAGE_SYSTEM_PROMPT_ANCHOR_MISSING", path),
        ("STAGE_PACK_INCOMPLETE", "", "STAGE_PACK_INCOMPLETE", path),
        ("STAGE_PACK_EMPTY", "", "STAGE_PACK_EMPTY", path),
        ("STAGE_HIGH_PHASE_BROAD_KEY", "", "STAGE_HIGH_PHASE_BROAD_KEY", path),
        ("STAGE_EVENT_FACT_LANGUAGE", "", "STAGE_EVENT_FACT_LANGUAGE", path),
        ("STAGE_EVENT_NOT_CANDIDATE", "", "STAGE_EVENT_NOT_CANDIDATE", path),
        ("[选开模式]", "必须keys=[]", "MANUAL_TOGGLE_KEYS_NONEMPTY", f"{path}.keys"),
        ("[选开模式]", "必须constant=true", "MANUAL_TOGGLE_CONSTANT_FALSE", f"{path}.constant"),
        ("[选开模式]", "必须enabled=false", "MANUAL_TOGGLE_ENABLED_TRUE", f"{path}.enabled"),
        ("[选开模式]", "不得混用selective/secondary_keys", "MANUAL_TOGGLE_SELECTIVE_MIXED", path),
        ("条目ID有重复", "", "LEYU_ENTRY_ID_DUPLICATE", "data.character_book.entries"),
        ("条目ID不连续", "", "LEYU_ENTRY_ID_NOT_CONTIGUOUS", "data.character_book.entries"),
        ("常驻条目必须keys=[]", "", "LEYU_CONSTANT_KEYS_NONEMPTY", f"{path}.keys"),
        ("含emoji", "", "LEYU_SUPPLEMENTARY_UNICODE", path),
    )
    for required, qualifier, rule_id, issue_path in rule_map:
        if required in message and (not qualifier or qualifier in message):
            return Issue(rule_id, severity, issue_path, message, LEYU_PRODUCTION, severity == "warning")
    prefix = "LEYU_WARNING" if severity == "warning" else "LEYU_ERROR"
    return Issue(stable_legacy_rule_id(prefix, message), severity, path, message, LEYU_PRODUCTION, severity == "warning")


def validate_card_report(path, target_size_kb=None, profile=LEYU_PRODUCTION, greeting_mode="player_prose"):
    """Return stable Issue objects; production is CCv3 core plus Leyu gates."""
    if profile not in PROFILES:
        return ValidationReport(profile, [
            Issue("PROFILE_UNKNOWN", "error", "profile", f"unknown profile: {profile}", profile)
        ])
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            card = json.load(handle)
    except Exception as exc:
        return ValidationReport(profile, [
            Issue("CCV3_JSON_PARSE_FAILED", "error", "$", str(exc), profile)
        ])

    core_report = validate_ccv3_core(card)
    if profile == CCV3_CORE:
        return core_report

    _passed, errors, warnings = _validate_leyu_production_legacy(
        path,
        target_size_kb=target_size_kb,
        greeting_mode=greeting_mode,
    )
    core_issues = [
        Issue(issue.rule_id, issue.severity, issue.path, issue.message, LEYU_PRODUCTION, issue.blocking)
        for issue in core_report.issues
    ]
    return ValidationReport(
        LEYU_PRODUCTION,
        core_issues
        + [_legacy_issue(message, "error") for message in errors]
        + [_legacy_issue(message, "warning") for message in warnings],
    )


def validate_card(path, target_size_kb=None, profile=LEYU_PRODUCTION, greeting_mode="player_prose"):
    """Backward-compatible tuple API used by existing delivery scripts."""
    report = validate_card_report(
        path,
        target_size_kb=target_size_kb,
        profile=profile,
        greeting_mode=greeting_mode,
    )
    return report.ok, [issue.render() for issue in report.errors], [issue.render() for issue in report.warnings]


def main(argv=None):
    parser = argparse.ArgumentParser(description='Validate a SillyTavern character card JSON')
    parser.add_argument('card', help='card JSON path')
    parser.add_argument('--target-size-kb', type=int, default=None, help='optional target file size in KB for size warning')
    parser.add_argument('--profile', choices=PROFILES, default=LEYU_PRODUCTION, help='validation boundary (default: leyu-production)')
    parser.add_argument('--greeting-mode', choices=('player_prose', 'prose_plus_director_appendix', 'ai_trigger'), default='player_prose', help='apply the appropriate Greeting structural policy; player_prose keeps the 1400 minimum')
    parser.add_argument('--format', choices=('text', 'json'), default='text', help='machine-readable report output')
    args = parser.parse_args(argv)

    report = validate_card_report(
        args.card,
        target_size_kb=args.target_size_kb,
        profile=args.profile,
        greeting_mode=args.greeting_mode,
    )
    if args.format == 'json':
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(f'profile={report.profile}')
        print(f'passed={report.ok}')
        print(f'errors={len(report.errors)}')
        for issue in report.errors:
            print(f'ERROR: {issue.render()}')
        print(f'warnings={len(report.warnings)}')
        for issue in report.warnings:
            print(f'WARN: {issue.render()}')
    if report.errors:
        return 1
    if report.warnings:
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
