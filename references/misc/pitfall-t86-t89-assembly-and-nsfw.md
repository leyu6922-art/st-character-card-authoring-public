### T86: DEFAULT_EXT缺少字段+字段名错误（2026-07-16·催眠助理卡实证·T80升级）

**症状**：assemble_card.py的DEFAULT_EXT字典只有旧版字段（如`automationId`驼峰命名、`groupOverride`、`scanDepth`等），validate_card.py v5.1报所有79条条目extensions缺少14个字段。

**根因**：validate_card.py v5.1的`required_ext_fields`（31字段）与旧版DEFAULT_EXT不匹配：
- 旧字段名用驼峰（`automationId`）→ 应改为蛇形（`automation_id`）
- 旧字段名用驼峰（`groupOverride`）→ 应改为蛇形（`group_override`）
- 缺少14个新字段：`case_sensitive`, `match_whole_words`, `use_group_scoring`, `match_persona_description`, `match_character_description`, `match_character_personality`, `match_character_depth_prompt`, `match_scenario`, `match_creator_notes`, `delay_until_recursion`, `position`(ext层), `selective`(ext层), `triggered`, `addMemo`

**v5.1完整required_ext_fields**（31字段）：
```python
{
    "position": 4, "exclude_recursion": False, "display_index": 0,
    "probability": 100, "useProbability": True, "depth": 4,
    "selective": False, "selectiveLogic": 0, "case_sensitive": False,
    "match_whole_words": None, "use_group_scoring": False,
    "automation_id": "", "role": None, "vectorized": False,
    "sticky": None, "cooldown": None, "delay": None, "scan_depth": None,
    "match_persona_description": None, "match_character_description": None,
    "match_character_personality": None, "match_character_depth_prompt": None,
    "match_scenario": None, "match_creator_notes": None,
    "triggered": True, "group": "", "group_override": False,
    "group_weight": 100, "prevent_recursion": True,
    "delay_until_recursion": False, "addMemo": True,
}
```

**v5.1完整required_entry_fields**（条目顶层，13字段）：
```python
{"id", "keys", "secondary_keys", "comment", "content", "constant",
 "selective", "addMemo", "insertion_order", "enabled", "position",
 "use_regex", "extensions"}
```

**铁律**：每次构建新卡，先用validate_card.py确认extensions完整，再写内容。DEFAULT_EXT必须与validate_card.py的required_ext_fields完全对齐。

---

### T87: assemble_card.py在execute_code中exec()路径解析失败（2026-07-16实证）

**症状**：用`exec(open('assemble_card.py').read())`在execute_code中运行组装脚本时，`os.path.dirname(os.path.abspath(__file__))`中的`__file__`未定义或指向sandbox临时目录→CONTENT_DIR解析到错误路径→所有content文件"Missing"→输出JSON条目content全空。

**根因**：execute_code在sandbox中执行，`__file__`不指向实际脚本路径。`os.path.abspath(__file__))`解析到sandbox临时目录而非实际build目录。

**修复**：组装脚本必须通过terminal工具执行，不能通过execute_code的exec()：
```python
# ❌ 错误：execute_code中exec
exec(open('/path/to/assemble_card.py').read())
# ✅ 正确：terminal中执行
terminal('cd /path/to/build && python assemble_card.py')
```

**铁律**：任何需要`__file__`路径解析的Python脚本，必须通过terminal工具执行，不能在execute_code中exec()。

---

### T88: alt_greeting中文字符计数不含标点（2026-07-16实证）

**症状**：alt_greeting文本`len()`返回2000+字符，但validate_card.py报"仅1150字（应≥1400）"。

**根因**：validate_card.py的字数统计只计算中文字符（`\u4e00`-`\u9fff`），不含标点、数字、英文、空格、换行。中文标点（，。！？、：；""''【】）也不计入。

**比例关系**：中文文本中汉字约占总字符的55-70%（含大量标点/格式时更低）。2000总字符≈1100-1400中文字。

**修复策略**：
- 目标写到2500+总字符以确保≥1400中文字
- 追加段落时优先添加实质性叙事内容，而非标点密集的对话
- 验证用：`sum(1 for c in text if '\u4e00' <= c <= '\u9fff')`

---

### T89: C型/非NTR卡的NSFW内容集成（2026-07-16·催眠助理卡实证）

**症状**：C型征服者成长卡按传统做法只写机制（贡献点/系统/权限/阶段），整张卡变成"游戏设计文档"——与T83（守护卡零NSFW）同类问题。

**根因**：C型卡没有NTR场景作为NSFW内容来源，agent容易只聚焦"成长机制"而忽略NSFW描写。但C型卡的本质是R18+征服体验——被征服女性的身体描写、性行为过程、催眠控制效果、征服后的场景才是核心内容。

**C型NSFW集成铁律**：
1. 角色档案必须含：身体描写+性行为模式+原文NSFW对话+催眠/控制反应差异
2. 事件种子必须含：具体性场景展开（不是"解锁新权限"而是"解锁后做了什么"）
3. 关系条目必须含：性关系演变史+具体性行为历史+催眠玩法
4. 语料库必须含：NSFW台词+身体描写素材+催眠描写
5. 随机表必须含：性相关随机事件（不只是"羞辱口嗨"）

**C型特有NSFW来源**：
- 原著中被控制者不知情的身体反应描写（核心恐怖感+性刺激）
- 催眠状态下的被动服从vs清醒时的抗拒（对比产生张力）
- 系统升级=NSFW玩法升级（每次解锁新权限都有对应的性场景）
- 成长线每个阶段都有"可执行的NSFW行为范围"

**与T83的区别**：T83是守护卡（威胁NPC要做什么），T89是征服者卡（{{user}}要做什么）。本质相同——NSFW内容是核心体验而非附属装饰。
