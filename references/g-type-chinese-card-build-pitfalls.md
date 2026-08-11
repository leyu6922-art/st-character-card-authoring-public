# G型/中文卡构建陷阱（2026-07-18 最新·含T112/T113）

> 道家仙子美母·人宗篇 G型卡构建过程中发现的7个陷阱，按严重度排序。

## T93: match_whole_words 必须设为 False（中文卡·致命坑）

**问题**：Python re 的 `\W` 不匹配中文字符（CJK字符在 Python 3 默认 Unicode 模式下是 `\w`）。validate_card 的 `_matches_key()` 用 `r'(?:^|\W)(' + key + r')(?:$|\W)'` 做 whole-word 匹配——"寰冲"后面跟"和"时，"和"是 `\w` 不是 `\W`，匹配失败。

**症状**：greeting 中明明有关键词（grep 确认），validate 却报"核心角色/威胁档案所有开场白均不触发"。逐条 debug 才发现 `re.search` 返回 None。

**修复**：所有条目 `extensions.match_whole_words = False`。中文没有空格分词，word-boundary 匹配天然不适用。

**验证**：
```python
import re
key = '寰冲'
haystack = '寰冲和寰宇两兄弟从后院走来'
# match_whole_words=True 时：
re.search(r'(?:^|\W)(寰冲)(?:$|\W)', haystack)  # → None ❌
# match_whole_words=False 时：
'寰冲' in haystack  # → True ✅
```

## T94: data.extensions 必须有6个字段

v3 规格要求 `data.extensions`（注意是 `data` 层级，不是条目层级）包含：

```python
card["data"]["extensions"] = {
    "world": "",                    # 世界书绑定。空=未绑定，ST无法加载内嵌世界书
    "depth_prompt": {"prompt": "", "depth": 4, "role": "system"},
    "position": 0,
    "fav": False,
    "talkativeness": "0.5",
    "creator_notes": ""
}
```

**注意**：`world` 字段为空字符串 `""` 是**正常状态**——嵌入世界书的实际绑定机制是 `data.character_book` 存在，而非 `world` 字段指向（2026-07-17 道家仙子美母实证：6张参考卡全部 `world=''` 或省略，世界书正常加载）。真正的危险是 `data.character_book` 本身缺失。T94 的目的是确保 `extensions` 对象结构完整（ST 加载卡时读取这些字段），`world` 字段存在即可，值可以为空。

## T95: 条目 extensions 要求精确31字段

validate_card.py line 190-197 定义了 `required_ext_fields`，共31个。常见遗漏：

```python
def make_extensions(pos_val=4):
    return {
        "position": pos_val,          # 0=before_char, 4=after_char
        "exclude_recursion": False,
        "display_index": 0,
        "probability": 100,
        "useProbability": True,
        "depth": 4,
        "selective": False,
        "selectiveLogic": 0,
        "case_sensitive": False,
        "match_whole_words": False,   # 🚨 中文卡必须False
        "use_group_scoring": False,
        "automation_id": "",          # 常遗漏
        "role": 0,                    # 常遗漏
        "vectorized": False,          # 常遗漏
        "sticky": 0,
        "cooldown": 0,
        "delay": 0,
        "scan_depth": 100,            # 常遗漏
        "match_persona_description": True,
        "match_character_description": True,
        "match_character_personality": True,
        "match_character_depth_prompt": False,
        "match_scenario": True,
        "match_creator_notes": True,
        "triggered": False,
        "group": "",
        "group_override": False,
        "group_weight": 100,
        "prevent_recursion": True,
        "delay_until_recursion": False,  # 常遗漏
        "addMemo": True
    }
```

## T96: 条目必需字段命名

validate_card.py line 199-202 定义了 `required_entry_fields`：

```
{id, keys, secondary_keys, comment, content, constant, selective,
 addMemo, insertion_order, enabled, position, use_regex, extensions}
```

**易错命名**：
- `secondary_keys`（不是 `keysecondary`）
- `insertion_order`（不是 `order`）
- `addMemo`（不是 `add_memo`，必须 True 否则世界书不链接）

## T97: 选开身份条目 keys 必须=[]

选开模式靠 ST 世界书 UI 手动启用，不依赖关键词触发。`constant=true + enabled=false` 的条目 keys 必须为空数组。validate 会报错。

## T98: execute_code 中文长字符串截断

execute_code 工具的 Python 沙箱对长中文字符串有隐式截断。症状：content 写入后字数远少于预期（如目标1500字实际只写入300字）。

**修复**：用 `write_file` 工具先写中文内容到 .json/.txt 文件，再用 `terminal` 的 python 读取并组装。

## T99: 全角中文标点导致 execute_code SyntaxError

中文全角句号 `。`、引号 `「」` 等在 execute_code 的字符串字面量中触发 `SyntaxError: invalid character '。' (U+3002)`。

**修复**：中文长文本一律用 `write_file` 写入 .json/.txt 文件，不在 execute_code 中嵌入。

### T110: validate_card "字"计数是全字符而非仅中文（2026-07-18·种孕武道大会实证）

**问题**：validate_card 报告 "first_mes 仅 764 字（应≥1400）" 中的"字"实际是**全字符计数**（含标点、空格、换行、emoji），不是仅中文汉字。初次扩充时按纯中文字数估算，导致3轮迭代才达标。

**验证**：
```python
text = "啪啪啪啪啪啪啪啪啪啪啪啪啪啪啪啪啪啪啪啪啪❤～！！"
# 纯中文: 21字
# validate_card计数: 26字（含❤和～和！和！）
len(text)  # → 26
```

**修复**：扩充greeting时用 `len(text)` 估算，不要用 `sum(1 for c in text if '\u4e00' <= c <= '\u9fff')`。目标1400字 = 1400个总字符（含标点/空格/emoji）。

**经验数据**：中文NTR小说风格的greeting，1400总字符约等于1100-1200纯中文字。

### T111: Combined content文件拆分数必须与---分隔符精确匹配（2026-07-18·种孕武道大会实证）

**问题**：组装脚本用 `content.split('---')` 将合并的content文件拆分为多个条目，然后用索引 `[0]`, `[1]`, ... 访问各部分。如果文件中实际的 `---` 分隔符数量少于脚本预期的索引，会触发 `IndexError: list index out of range`。

**实证**：entry_22_27.txt 含5个 `---` 分隔符（6部分），但脚本中 `parts_22_27[5]` 越界——实际只有5部分（分隔符不产生额外部分，两端的空白部分被 `if p.strip()` 过滤掉）。

**修复**：
1. 写完combined文件后立即运行 `python -c "parts=[p.strip() for p in open(f).read().split('---') if p.strip()]; print(len(parts))"` 验证拆分数
2. 组装脚本中用 `assert len(parts_N) >= expected_count` 做防御
3. 或者用命名分隔符（如 `=== ENTRY N ===`）替代 `---`，避免与内容中可能的 `---` 冲突

---

### T114: 用户说"只需要X"时严格只做X（2026-07-19·艳母矩阵文档实证）

**问题**：用户要求"加厚文档，150kb以上"。我写了58KB的13个新章节（调教策略对比、行为链模板库、心理独白语料库、场景描写语料库、120章事件时间线等），覆盖了用户未要求的内容。用户回复："只需要补充和五个核心男性的关系就可以"。

**根因**：过度交付——预判用户需要"全方位扩展"，但用户实际只需要"关系部分扩展"。

**规则**：
1. 当用户说"只需要补充X"时，**严格只补充X**，不要添加用户未提及的内容
2. 150KB是总目标，但**内容范围由用户指定**——不要用无关内容凑字数
3. 如果只补充X就达到目标，很好；如果不够，**问用户**是否要补充其他内容
4. 不要假设"加厚=全方位扩展"——"加厚"可以只加厚某一部分

**后续教训**（同一session）：用户进一步缩小范围——"去除肖斌，只保留核心四人"。说明用户对角色重要性有清晰层级划分。不要假设所有提及的角色都是"核心"。

---

## assemble_card 脚本检查清单

组装 G型卡时，脚本必须验证：
1. `data.extensions` 含 `world` 字段（T94）和 `addMemo` 字段（T113）
2. 每条 entry 的 `extensions` 含全部31字段（T95）
3. 常驻条目 `keys=[]`（T97）
4. 选开条目 `keys=[]` + `constant=true` + `enabled=false`（T97）
5. 所有条目 `match_whole_words=False`（T93·中文卡）
6. 字段名：`secondary_keys` / `insertion_order` / `addMemo`（T96）
7. 顶层 v3 字段：`creatorcomment` / `avatar` / `talkativeness` / `fav` / `tags` / `create_date` / `data.mes_example`
8. Combined content文件拆分数与脚本索引匹配（T111）
9. Greeting用 `len(text)` 而非纯中文字数估算是否达标（T110）
10. 选开条目 comment 必须含"选开"二字否则 validate 不识别（T102）
11. Primary keys 必须是精准短语/专有名词，不能是单字泛词（T112）
12. 无3+条目共享同一关键词（T112 关键词重叠审查）

---

---

## T107: 渐进式卡开场白禁止模板套话批量生成（2026-07-18·艳母v1_1实证）

**问题**：构建渐进式（阶段式）角色卡时，子代理或批量脚本用同一模板生成全部开场白——只切换HTML阶段注释，正文内容完全相同（相同开头句、相同角色描述段、相同编号列表1-10且7-10重复1-4）。

**症状**：
- 所有开场白开头都是同一句话（如"夜色和屋内灯光把场景切成两层"）
- 角色描述段逐字相同（"赵勇的存在像一束阳光，骆鹏的存在像阴影……"）
- 编号段落1-10中7-10是1-4的完全复制
- 只有`<!-- 当前阶段：PX -->`注释不同

**根因**：构建脚本/子代理用模板变量替换阶段标记，但没有从原文对应章节提取实际场景内容。

**修复**：
1. 每条开场白必须指定对应的原文章节（P0→ch1, P1→ch3, P4→ch55等）
2. 从对应章节提取关键场景、对话、人物互动作为正文
3. 每条开场白的开头句、场景、对话必须不同
4. 去掉编号列表（1-10），用叙事体直接进入场景
5. 每条正文600-800字即可（目标是进入场景，不是展示全部素材）

**验证**：生成后用Python检查——任意两条greeting的前100字若相似度>80%则判定为模板重复。

---

## T106: search_files 工具对 utf-8-sig 中文文件可能失效（2026-07-18·艳母的荒唐赌约实证）

**症状**：`search_files(pattern='协议', path='第100章.txt')` 返回0，但 `python -c "open(f).read().count('协议')"` 返回4。同一批文件中某些关键词（如"陆寒林"）能搜到，另一些（如"浪奴""192""协议"）搜不到，行为不一致。

**修复/替代方案**：CJK 文本验证一律用 Python 脚本：

```python
import os
d = '/path/to/novel/dir'
for f in os.listdir(d):
    if not f.endswith('.txt'): continue
    with open(os.path.join(d, f), encoding='utf-8-sig') as fh:
        text = fh.read()
        count = text.count('目标词')
        if count > 0:
            idx = text.index('目标词')
            ctx = text[max(0,idx-30):idx+50]
            print(f'{f}: {count}x → ...{ctx}...')
```

**关键规则**：
- **不要**依赖 search_files 的 content 模式做 CJK 文本的精确验证
- **用** Python `str.count()` 做频次统计
- **用** Python `str.index()` + 切片做上下文提取
- search_files 的 files 模式（按文件名搜索）不受影响，可正常使用

---

## E型禁忌后宫卡专属陷阱（2026-07-17·高考后的假期实证）

### T100: E型卡 secondary_keys 必须全部清空

**问题**：E型（禁忌后宫征服卡）不使用 selective AND 逻辑——所有条目 `selective=false`。当 `selective=false` 时，ST 完全忽略 `secondary_keys` 字段。但构建脚本模板中习惯性填入 secondary_keys（如场景词、人物词），导致27条 audit_worldbook_triggers warnings。

**修复**：E型卡所有非常驻条目的 `secondary_keys=[]`。用 primary keys 本身做范围限定（如用"小城家"而非"家"）。

**对比**：G型卡→secondary_keys 用于视角隔离（必须填）；E型卡→secondary_keys 无用（必须清空）；NTR卡→按需填+设selective=true。

### T101: Emoji 二次污染——内容扩充后必须重跑清理

初始构建时已清理 emoji，但后续扩充/重写内容文件时会重新带入。emoji 清理必须在**所有内容最终确定后**执行，不能只做一次。

### T102: validate_card 选开误报——{{user}}身份条目的 comment 含"身份"（2026-07-18 A型卡+种孕武道大会卡双重实证）

**问题**：validate_card check 46 用 `('选开' in comment) or ('身份' in comment and '{{user}}' in content[:500])` 检测选开条目。对A型NTR苦主卡，{{user}}身份条目（如"小岐·{{user}}身份"）是 constant=true+enabled=true 的正常常驻条目，不是选开条目，但 comment 含"身份"+ content[:500] 含 {{user}} → 触发误报。

**2026-07-18·种孕武道大会实证（反向案例）**：当设置 `enabled=false` 后，validate 报"条目[2] 被禁用 (enabled=false)——非事件种子/非选开身份条目不应禁用"。修复：comment 必须含"选开"二字才能让 validate 识别为合法的选开身份条目。最终修复：comment = "选开·OOC·{{user}}身份·丁枫" + enabled=false → 通过。

**受影响卡型**：
- G型选开卡：✅ 真正的选开条目，check 46 正确触发
- A型NTR苦主卡：❌ {{user}}身份条目被误判为选开条目
- E型禁忌后宫卡：❌ 同理，{{user}}身份条目被误判
- 任何非G型卡的 {{user}} 定义条目：❌ 只要 comment 含"身份"就误判

**修复方案**（按优先级）：
1. **改 comment 避开关键词**（推荐）：将 comment 中的"身份"替换为具体角色定位词
   - `【角色：小岐·{{user}}身份】` → `【角色：小岐·{{user}}苦主】`
   - `{{user}}身份·阿城` → `{{user}}·阿城·丈夫`
   - 原则：用"苦主""丈夫""征服者"等具体身份词替代泛化的"身份"
2. **改 content 前500字不含 {{user}}**（备选）：将 {{user}} 引用移到 content 后半部分，但会降低角色定义的可读性

**对比**：
| 卡型 | {{user}}条目 | check 46结果 | 是否需要修 |
|------|-------------|-------------|----------|
| G型选开 | constant=true, enabled=false, comment含"选开" | 正确触发 | 不需要 |
| A型苦主 | constant=true, enabled=true, comment含"身份" | ❌误报 | 需要改comment |
| A型苦主 | constant=true, enabled=true, comment含"苦主" | ✅不触发 | 不需要 |

**2026-07-18·呆萌迟钝的女友可瑄 实证**：A型NTR苦主卡，entry 2 comment="【角色：小岐·{{user}}身份】" → validate报 `[选开模式] 条目[2] 身份/选开条目必须enabled=false`。改comment为"【角色：小岐·{{user}}苦主】"后通过。

### T103: E型卡征服度系统（6级）

E型卡用**征服进度**替代堕落度：0未接触→1试探→2越界→3突破→4臣服→5沉溺。每个女性独立追踪。

### T104: E型卡安全等级系统

私密（门关好/无限制）→半公开（周围有人/口交偷摸）→公开（有外人/仅眼神暗示）。

### T105: 内容厚度差距管理

计划目标在初始构建时经常达不到40-80%。修复：初始瞄准80%+目标；构建后立即比对；角色档案必含10项（身份/双人格/欲望/行为矩阵/语言指纹/场景差异/剧情节点/身体描写/对话引用≥5/行为模板≥3）。

**2026-07-18·可瑄卡实证（审查报告实录）**：初始构建125KB/11,793字，仅达规划180KB/55,000字的21%。所有条目是「梗概+bullet point」格式，缺少原文素材。核心问题：
- **零原文对话引用** — 规划要求每条角色条目8+对话引用，实际0条
- **行为模板无条件分支** — 只有概述性描述，没有「情境→行为→底线」的具体矩阵
- **场景反应差异缺失** — 没有「对苦主/对NTR对象/对外人」的行为差异描写

**铁律：条目必须含CONCRETE USABLE CONTENT，不是抽象规则**。AI无法执行指南，只能执行已经写好的文本。每个条目必须包含：
1. 原文对话引用（直接从小说中提取，用「」标注，≥5条/角色条目）
2. 具体行为模板（带条件触发：「当X发生时→角色会做Y→但不会做Z」）
3. 场景反应差异（同一角色在不同情境下的不同表现，≥3种情境）
4. 语言指纹（标志性称呼/口头禅/不同情绪下的典型台词）
5. NTR关系条目也需≥600字（含侵犯阶段演变史+行为链+触发关键词）

**加厚工作流（修正版）**：
1. 先读完全部原文章节（用 `encoding='utf-8-sig'` 去BOM）
2. 对每个条目，从原文中搜索相关段落（用 Python `str.count()` 而非 search_files，参见T106）
3. 直接引用原文对话和场景描写（用「」标注）
4. 用原文素材填充行为模板和场景反应差异
5. 不要先写大纲再填充——直接从原文中提取素材写入条目

### T112: 泛关键词导致多条目误触发（2026-07-18·可瑄卡实证）

**问题**：条目的 primary keys 使用了过于泛化的词（如「检查」「朋友」「监控」「教室」「课后」），导致不相关的场景触发这些条目。

**实证**：
- `"检查"` → ID 25（妇科检查事件）— 但「检查安全带」「搜身检查」也会命中
- `"朋友"` → ID 11（阿强）— 「好朋友」「男朋友」都会命中
- `"监控"` → ID 28（出租房场景）— 「监控画面」「装监控」都会命中
- `"教室"` → ID 29（瑜伽教室场景）— 普通「教室」也会命中
- `"课后"` → ID 23（KTV）— 但「课后加练」是ID 19的key

**修复**：用复合短语替代单字泛词：
- `"检查"` → `"妇科检查"`, `"医疗检查"`, `"男医生"`
- `"朋友"` → 删除或替换为具体人名 `"阿强"`
- `"监控"` → `"监控画面"`, `"出租房监控"`, `"回看录像"`
- `"教室"` → `"瑜伽教室"`, `"瑜伽机构"`
- `"课后"` → `"KTV"`, `"唱歌"`, `"醉酒"`

**规则**：primary keys 必须是**精准短语或专有名词**，不能是单字泛词。validate_card check 31B 会检测泛key（如「你」「我」「他」「家」「人」），但不覆盖所有中文泛词。构建时人工审查每个 key 是否会被不相关场景命中。

**关键词重叠审查**：构建完成后检查是否有多个条目共享同一关键词（validate 会报「关键词 X 被 N 个条目共享」）。3+条目共享同一key时，该key在任何场景中都会同时触发所有条目，造成token浪费。解决方案：用selective+secondary_keys做二级限定，或拆分为更精准的key。

### T113: data.extensions 必须含 addMemo 字段（2026-07-18·可瑄卡实证）

**问题**：T94 记录了 `data.extensions` 必须有 `world` 字段，但遗漏了 `addMemo` 字段。世界书条目有 `addMemo=True`，但 `data.extensions` 层级没有 `addMemo`，会影响 ST 的记忆功能。

**修复**：`data.extensions` 至少包含：
```python
card["data"]["extensions"] = {
    "world": "",           # 世界书绑定（空=正常，参见T94）
    "addMemo": True,       # ST记忆功能
    "depth_prompt": {"prompt": "", "depth": 4, "token_budget": 500},
    "fav": False
}
```

**与T94的关系**：T94记录了6个字段的完整列表，但实际构建时最容易遗漏的是 `world` 和 `addMemo`。本条作为T94的补充提醒。

### T108: 开场白不足1400字时的"场景延续扩展"技巧（2026-07-18·可瑄卡实证）

**问题**：初始构建的greeting不足1400字（validate_card硬门控），需要扩充但不能机械补字。

**修复**：在greeting末尾追加该场景的后续叙事——角色对话+心理描写+场景细节，让AI继续描写当前场景中尚未展开的部分。

**操作步骤**：
1. 检查当前greeting结尾停在哪个场景节点
2. 从对应原文章节中提取该场景之后的关键段落（对话/心理/互动）
3. 以叙事体续写100-400字，风格与原greeting一致
4. 不要引入新场景，只展开当前场景的细节

**实证**：可瑄卡3条greeting从1032-1319字扩展到1470-1953字。扩展内容包括：
- g2（瑜伽课）：追加豪哥手指继续探索+可瑄打电话给小岐的后续
- g3（深夜监控）：追加小岐回忆豪哥家访指导的画面+内心矛盾
- g4（火车）：追加小胖潘子交换+可瑄说梦话+第二天早上醒来

**反模式**：
- ❌ 用模板补字（"场景余波"段重复3遍）
- ❌ 引入新角色/新场景
- ❌ 复制粘贴其他greeting的段落

### T109: UTF-8 BOM 导致小说首段关键词提取失败（2026-07-18·可瑄卡实证）

**问题**：中文小说.txt文件用utf-8-sig编码（带BOM `\ufeff`）。用Python `re.findall()` 按段落分割后，第一段内容的开头含不可见BOM字节，导致该段的关键词匹配/对话提取失败。

**症状**：用 `re.findall(r'["「](.{4,100})["」]', text)` 提取对话时，大部分章节返回0条结果。原因不是正则错误，而是段落中混入了BOM字节导致引号匹配偏移。

**修复**：读取文件后先strip BOM：
```python
with open(path, 'r', encoding='utf-8-sig') as fh:  # utf-8-sig 自动去BOM
    text = fh.read()
```
或：
```python
with open(path, 'r', encoding='utf-8') as fh:
    text = fh.read().lstrip('\ufeff')  # 手动去BOM
```

**与T106的关系**：T106是search_files工具对utf-8-sig文件的content模式失效；T109是Python正则对BOM首段的匹配失败。同一根因（BOM），不同表现。统一用 `encoding='utf-8-sig'` 解决两者。
