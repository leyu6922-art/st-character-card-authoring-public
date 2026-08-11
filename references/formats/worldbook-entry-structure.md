# 世界书条目结构参考

## 每个条目的Markdown格式

```markdown
## 条目 XX：条目名称

**类别**：人物/关系/世界观/地点/规则/文风/事件/秘密/设定/道具/状态
**分类**：原著设定 / 合理推演 / 扩展设定（或组合）
**关键词**：主触发词1、主触发词2、主触发词3
**次级关键词**：次触发词1、次触发词2
**常驻**：是/否
**优先级**：最高/高/中/低
**适用人物**：适用的人物名
**适用场景**：适用的场景类型
**适用剧情阶段**：适用的剧情阶段

### 正文

条目内容...
```

## 推荐条目目录（20-25条）

```
第一层：总控与规则（常驻）
  00 原著兼容总则          → 常驻，最高优先级
  01 自由创作总则          → 常驻，最高优先级
  02 原著文风与叙事总控    → 常驻，最高优先级

第二层：世界观（常驻）
  03 世界观与力量体系      → 常驻，高优先级
  04 主要地点              → 常驻，高优先级

第三层：核心人物（常驻或关键词触发）
  05-N 核心人物            → 常驻或关键词触发
  N+1-N+X 次要人物         → 关键词触发

第四层：关系与秘密（关键词触发）
  关系条目                 → 常驻或关键词触发
  秘密条目                 → 关键词触发

第五层：关键设定（关键词触发）
  功法/道具/规则设定       → 关键词触发

第六层：事件（关键词触发/常驻）
  事件/地点扩展            → 关键词触发
  日常事件生成指南          → 常驻
  冲突事件生成指南          → 常驻

第七层：防OOC与状态（常驻）
  人物行为边界与OOC判定    → 常驻，高优先级
  状态管理模板             → 常驻
```

## 人物条目必含要素

- 基础身份 + 外貌
- 公开人格 vs 私下人格
- 核心欲望（表层/深层/最深层）
- 核心恐惧
- 条件化行为矩阵（情境→倾向→底线）
- 道德边界
- 羞耻点与敏感点
- 自我合理化方式
- 说谎方式 / 冲突方式
- 不同人物面前的行为差异
- 独处/压力/极端状态下的表现
- 可以逐渐改变 vs 不能瞬间改变的部分
- OOC判定标准
- 语言指纹（标志性称呼、口头禅、不同情绪下的典型台词）

## 关系条目必含要素

- 双方公开态度 vs 真实态度
- 权力结构（表面 vs 实际）
- 信任/依赖/恐惧/利益
- 共同秘密 vs 单向秘密
- 历史转折点
- 关系升级条件 / 恶化条件
- 当前阶段不会发生的行为

## 常驻 vs 关键词触发 选择指南

**常驻（constant: true）**：
- 总控规则、文风控制
- 核心主角
- 最重要的关系（如母子关系）
- 日常/冲突事件指南
- OOC判定规则
- 状态管理

**关键词触发（constant: false）**：
- 次要人物
- 特定关系（如师徒禁忌）
- 秘密和阴谋
- 特定设定（功法、道具）
- 扩展地点和事件

## JSON关键字段（独立世界书）

| 字段 | 说明 |
|------|------|
| uid | 唯一数字ID |
| key | 主关键词数组 |
| keysecondary | 次要关键词数组 |
| comment | 条目标题/备注 |
| content | 条目正文内容 |
| constant | true=常驻, false=关键词触发 |
| selective | true=需同时匹配主次关键词 |
| order | 排序优先级（数字越大越靠前） |
| position | 0=角色定义前, 1=角色定义后 |
| depth | 注入深度（对话历史中的位置） |
| probability | 激活概率(0-100) |

## character_book 字段映射（内嵌世界书）

**⚠️ 字段名与独立世界书不同！** 将独立世界书转为 character_book 时必须做字段映射：

| 独立世界书 | character_book | 说明 |
|------|------|------|
| uid | id | 数字ID |
| key | keys | 主关键词数组 |
| keysecondary | secondary_keys | 次要关键词数组 |
| order | insertion_order | 排序优先级 |
| disable | enabled | **布尔反转！** disable=true → enabled=false |
| position (int 0/1) | position (string) | 0→"before_char", 1→"after_char" |
| (无) | use_regex | 新增，设为 true |
| (无) | extensions | 新增，完整扩展对象 |

每个 entry 的 `extensions` 必须包含（历史导出示例，仅供字段识别；新卡以 scripts/fix_card_format.py DEFAULT_EXTENSIONS / validate_card.py required_ext_fields 为准）：
```json
{
  "position": 1,
  "exclude_recursion": false,
  "display_index": 0,
  "probability": 100,
  "useProbability": true,
  "depth": 4,
  "selectiveLogic": 0,
  "outlet_name": "",
  "group": "",
  "group_override": false,
  "group_weight": 100,
  "prevent_recursion": true,
  "delay_until_recursion": false,
  "scan_depth": null,
  "match_whole_words": null,
  "use_group_scoring": false,
  "case_sensitive": null,
  "automation_id": "",
  "role": 0,
  "vectorized": false,
  "sticky": null,
  "cooldown": null,
  "delay": null,
  "match_persona_description": false,
  "match_character_description": false,
  "match_character_personality": false,
  "match_character_depth_prompt": false,
  "match_scenario": false,
  "match_creator_notes": false,
  "triggers": [],
  "ignore_budget": false
}
```

> **当前权威字段**：以 `scripts/validate_card.py` 的 `required_ext_fields` 与 `scripts/fix_card_format.py` 的 `DEFAULT_EXTENSIONS` 为准。历史导出中的 `outlet_name/triggers/ignore_budget` 可作为兼容字段保留，但新卡至少必须含 `addMemo/selective/triggered/prevent_recursion` 等 required 字段。

`character_book` 顶层结构（注意：没有 `extensions`/`scan_depth`/`token_budget` 等独立世界书字段）：
```json
{
  "character_book": {
    "name": "世界书名称",
    "entries": [ ... ]
  }
}
```

---

## ✅ 正确JSON条目格式（实测验证，能跑的卡统一使用此格式）

```python
# ✅ 正确格式（实测验证，能跑的卡统一使用此格式）
{
    "id": 1,
    "keys": ["关键词1", "关键词2"],
    "secondary_keys": [],            # ← 不是 keysecondary！
    "comment": "条目标题",
    "content": "条目正文",
    "constant": True,
    "selective": False,
    "addMemo": True,                 # ← 必须有
    "insertion_order": 0,            # ← 不是 order！
    "enabled": True,
    "position": "after_char",
    "use_regex": True,               # ← 必须有
    "extensions": {                  # ← 必须有31个字段，不能是空对象！
        "position": 4,
        "exclude_recursion": False,
        "display_index": 0,          # 每个条目不同，递增
        "probability": 100,
        "useProbability": True,
        "depth": 4,                  # 常驻条目用4，触发条目用1
        "selectiveLogic": 0,
        "outlet_name": "",
        "group": "",
        "group_override": False,
        "group_weight": 100,
        "prevent_recursion": True,          # 所有条目都必须True，禁止触发条目递归链
        "delay_until_recursion": False,
        "scan_depth": None,
        "match_whole_words": None,
        "use_group_scoring": False,
        "case_sensitive": None,
        "automation_id": "",
        "role": 0,
        "vectorized": False,
        "sticky": 0,
        "cooldown": 0,
        "delay": 0,
        "match_persona_description": False,
        "match_character_description": False,
        "match_character_personality": False,
        "match_character_depth_prompt": False,
        "match_scenario": False,
        "match_creator_notes": False,
        "triggers": [],
        "ignore_budget": False
    }
}
```

**⚠️ 重大Pitfall：空extensions导致搭配世界书时截断！**

实测案例（叶无云堕落版）：条目使用`extensions:{}`（空对象）时，单独导入角色卡可以出开场白，但搭配外挂世界书后连开场白都无法生成。改为31字段extensions后恢复正常。

**⚠️ 重大Pitfall：character_book层级不要多余字段！**

能跑的卡（炎黄改版）的`character_book`只有`entries`和`name`两个字段。不要添加`description`/`scan_depth`/`token_budget`/`recursive_scanning`/`extensions`——这些字段可能导致ST解析异常。

## ⚠️ 条目position设置：OOC防护和状态栏必须before_char（2026-07-07 示例玄幻项目案例）

大多数条目用 `position: "after_char"`（extensions.position=4），但以下条目必须用 `position: "before_char"`（extensions.position=0）：

| 条目类型 | position | 理由 |
|----------|----------|------|
| OOC防护/绝对规则 | before_char | 必须在角色扮演内容之前注入，否则防护失效 |
| 状态栏系统模板 | before_char | 状态栏规则需要在角色定义之前被AI看到 |
| 其他所有条目 | after_char | 默认位置 |

```python
# OOC防护条目
{
    "position": "before_char",
    "extensions": {"position": 0, ...}  # 0 = before_char
}
# 其他条目
{
    "position": "after_char",
    "extensions": {"position": 4, ...}  # 4 = after_char
}
```

⚠️ 实测发现（示例玄幻项目）：88条全部after_char，OOC防护在角色扮演内容之后注入，理论上防护效果减弱。修复后改为before_char，不影响其他条目。

## ⚠️ Pitfall: `enabled` 必须在条目顶层（2026-07-05 示例玄幻项目案例）

**问题**：条目只在 `extensions.enabled=True` 设置，但SillyTavern读取的是**条目顶层**的 `enabled` 字段。缺失顶层 `enabled` 导致所有条目显示为灰色（禁用）。

**错误**：
```python
entry = {
    "id": 0,
    "keys": ["关键词"],
    "content": "...",
    "extensions": {"enabled": True}  # ← ST不读这个！
}
# → 酒馆世界书编辑器显示灰色（禁用）
```

**正确**：
```python
entry = {
    "id": 0,
    "keys": ["关键词"],
    "content": "...",
    "enabled": True,  # ← 顶层！ST读这个
    "extensions": {"enabled": True}  # ← 也保留，双保险
}
```

**验证方法**：导入后在酒馆世界书编辑器中检查——所有条目应显示绿色（启用）开关，不是灰色。

## ⚠️ Pitfall: 条目格式字段名错误（2026-07-05 二次修正）

**旧SKILL.md曾记录**：条目用`keysecondary`/`order`/空`extensions:{}`，并称`secondary_keys`/`insertion_order`是"错误字段名"。
**实测结论**：这个说法本身是错的！能正常运行的卡（炎黄改版47条目、示例角色项目136条目）统一用`secondary_keys`/`insertion_order`/31字段extensions。

正确格式如下：

```python
# ✅ 正确格式（实测验证，能跑的卡统一使用）
# ⚠️ T80铁律：extensions必须含addMemo/selective/triggered三字段，否则validate_card全量报错
def make_entry(entry_id, keys, secondary_keys, comment, content,
               constant=False, insertion_order=0, enabled=True,
               position="after_char"):
    pos_val = 0 if position == "before_char" else 4
    return {
        "id": entry_id,
        "keys": keys,
        "secondary_keys": secondary_keys,  # ← 不是 keysecondary
        "comment": comment,
        "content": content,
        "constant": constant,
        "enabled": enabled,
        "selective": False,
        "addMemo": True,
        "insertion_order": insertion_order,  # ← 不是 order
        "position": position,
        "use_regex": True,
        "extensions": {
            "position": pos_val,
            "exclude_recursion": False,
            "display_index": entry_id,
            "probability": 100,
            "useProbability": True,
            "depth": 4 if constant else 1,
            "selectiveLogic": 0,
            "outlet_name": "",
            "group": "",
            "group_override": False,
            "group_weight": 100,
            "prevent_recursion": True,  # 所有条目都必须True
            "delay_until_recursion": False,
            "scan_depth": None,
            "match_whole_words": None,
            "use_group_scoring": False,
            "case_sensitive": None,
            "automation_id": "",
            "role": 0,
            "vectorized": False,
            "sticky": 0,
            "cooldown": 0,
            "delay": 0,
            "match_persona_description": False,
            "match_character_description": False,
            "match_character_personality": False,
            "match_character_depth_prompt": False,
            "match_scenario": False,
            "match_creator_notes": False,
            "triggers": [],
            "ignore_budget": False,
            # T80必填三字段（2026-07-16绿冠星空卡38/38全量报错实证）
            "addMemo": True,
            "selective": False,
            "triggered": True
        }
    }
```

**⚠️ T80 Pitfall 复发（2026-07-16·绿冠星空卡）**：手写make_entry()时遗漏addMemo/selective/triggered三字段→validate_card对38/38条目全量报错。根因：make_entry模板代码中没有这三个字段，agent照抄模板→集体缺失。**修复后模板已包含三字段。**

**⚠️ execute_code三引号与中文引号冲突（2026-07-16实证）**：在execute_code中用Python三引号定义包含中文对话的字符串时，中文对话中的引号（如"老公"）会与外层三引号冲突→SyntaxError。**解法**：(1)用write_file工具直接写中文内容到.txt文件，不经过execute_code内联；(2)或用单引号+转义；(3)或用dict逐条写入避免三引号嵌套。

**⚠️ Unicode转义导致validate_card报错（2026-07-16实证）**：条目content中包含Python代码模式如`'\u4e00' <= c <= '\u9fff'`时，json.dumps会保留这些\uXXXX转义→validate_card报"raw JSON含字面\uXXXX转义"。**解法**：写入JSON前，将content中的`\\u4e00`等替换为实际Unicode字符。

**用错字段名的后果**：
- `keysecondary`（错误）→ ST可能忽略次要关键词
- `order`（错误）→ ST可能忽略排序
- 空`extensions:{}` → **搭配世界书时连开场白都无法生成！**（实测：叶无云堕落版）

## 角色卡JSON结构（必须是v3格式！参照道家仙子美母.json）

```python
card = {
    # ===== 顶层字段（v3必须有，从data层复制）=====
    "name": "角色名",
    "description": "...",           # 与data层重复
    "personality": "...",           # 与data层重复
    "scenario": "...",              # 与data层重复
    "first_mes": "...",             # 与data层重复
    "mes_example": "",              # 必须有（空字符串即可）
    "creatorcomment": "",           # 必须有
    "avatar": "none",               # 必须有
    "talkativeness": "0.5",         # 必须有
    "fav": False,                   # 必须有
    "tags": [],                     # 必须有
    "create_date": "2026-07-05",    # 必须有
    "spec": "chara_card_v3",        # ⚠️ 必须是v3！不是v2
    "spec_version": "3.0",          # ⚠️ 必须是3.0
    # ===== data层 =====
    "data": {
        "name": "角色名",
        "description": "...",
        "personality": "...",
        "scenario": "...",
        "first_mes": "...",
        "mes_example": "",              # data层也必须有
        "system_prompt": "...",
        "post_history_instructions": "",# 必须有（空字符串即可）
        "tags": [],
        "creator": "",
        "creator_notes": "",
        "character_version": "",
        "alternate_greetings": ["开场白1", "开场白2"],
        "group_only_greetings": [],
        "extensions": {
            "depth_prompt": {"prompt": "", "depth": 4, "token_budget": 500},
            "fav": False
        },
        "character_book": {
            "name": "角色名-世界书",
            "entries": entries    # list格式，用 make_entry() 构建
            # ⚠️ 只需 name + entries，不要加其他字段
        }
    }
}
```

**⚠️ v3格式必须包含的字段**：
- **顶层15字段**：name, description, personality, scenario, first_mes, mes_example, creatorcomment, avatar, talkativeness, fav, tags, create_date, spec, spec_version, data
- **data层**：mes_example（空字符串）, post_history_instructions（空字符串）
- **character_book**：只需 name + entries
- **条目**：secondary_keys（不是keysecondary）, insertion_order（不是order）, extensions（31字段）, addMemo, use_regex
