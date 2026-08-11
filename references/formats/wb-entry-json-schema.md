# 世界书条目JSON Schema + 节点/结局内容格式

> 来源：校园媚黑守护卡v2构建（2026-07-11）— 节点+结局+系统提示三类条目的完整实践

## 条目顶层结构

每个世界书条目是一个JSON对象，放在一个数组中。SillyTavern v3要求所有条目在 `data.entries` 下。

```json
{
  "id": 28,
  "keys": ["报到日", "黑人初遇", "节点1"],
  "secondary_keys": ["Node1", "夏倾月被骚扰"],
  "comment": "Node 1 报到日·黑人初遇",
  "content": "## Node 1 · ...（Markdown正文）",
  "constant": false,
  "selective": true,
  "insertion_order": 0,
  "enabled": true,
  "position": "after_char",
  "use_regex": false,
  "extensions": { ... }
}
```

## 三种条目类型配置模式

| 类型 | constant | selective | keys | 典型content长度 |
|------|----------|-----------|------|----------------|
| 剧情节点 | false | true | 节点名+角色名+事件关键词（5-8个） | 500-700 chars |
| 结局条目 | false | true | 结局名+END编号+结局类型关键词（3-5个） | 600-750 chars |
| 系统提示 | true | false | []（空数组） | 700-1000+ chars |

**关键规则：**
- `constant=true` 条目的 keys 必须是 `[]`——每轮都注入，不需要关键词触发
- `selective=true` 条目必须有 `secondary_keys`——ST用这些做精确匹配
- `position` 字段：`"after_char"` 对应 extensions.position=1，`"before_char"` 对应 0

## extensions完整模板（31字段）

子代理经常漏字段，合并脚本必须补全。以下是从已有卡片提取的标准模板：

```json
"extensions": {
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
  "prevent_recursion": false,
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

**注意：** `addMemo` 字段在某些ST版本中需要，v3 spec不一定有。构建时先用以上模板，合并后跑validate检查。

## 节点条目内容格式（v2混合选择格式）

每个节点条目的content必须遵循以下结构：

```markdown
## Node N · 节点名称

**时间线**: 周X·时段
**触发**: 触发条件说明

### 【叶云的观察】
2-3句环境描写+感官细节+原著台词引用。提供玩家做决策所需的情报线索。

### 【可选行动】
① 行动描述 ⚡风险 — 一句话影响提示
② 行动描述 ⚡风险 — 一句话影响提示
③ 行动描述 ⚡风险 — 一句话影响提示

💬 你也可以自由描述叶云的行动。
不做选择 = 随波逐流（一句话后果说明）

### 【状态变化】
- 选项①：数值变化
- 选项②：数值变化
- 选项③：数值变化
- 不作为：数值变化

原著对照：一句话说明原著中的默认结果。
```

**内容质量要求：**
- 观察段必须包含原著精确台词或精确描写（不是概括）
- 每个选项必须有⚡风险标识（低/中/高/极高）
- 状态变化必须有具体数值（+10、-5等）
- 总字数500-700 chars，不少于450

## 结局条目内容格式

每个结局条目的content必须包含三个部分：

```markdown
## END-N · 结局名称

### 【判定条件】
- 条件1（堕落度阈值、信任度阈值等）
- 条件2（心火诀等级、阻止事件次数等）
- ...（3-6个条件）

### 【叙事场景】
600+ chars的完整叙事场景。必须包含：
- 战斗/对决结果描写
- 2-3位女主的具体反应和台词
- 叶云的内心独白
- 感官细节（视觉/触觉/氛围）

### 【后续】
一段总结性文字，说明这个结局的长期后果。
```

**内容质量要求：**
- 叙事场景是核心，必须600+ chars
- 判定条件必须是可量化的数值阈值
- 台词引用原著风格但不必是原文
- 结局之间必须有清晰的质量梯度（完美>苦涩>残缺>孤独>苦主>堕落）

## 构建质量控制流程

1. **初始生成**：按schema生成所有条目，一次性写入JSON
2. **字数验证**：Python脚本检查每个条目的content长度，标记<450 chars的
3. **迭代扩展**：对短条目用patch精确替换content，补充场景描写和感官细节
4. **结构验证**：检查constant/selective/keys一致性、extensions完整性、ID连续性

```python
# 验证脚本模板
import json
with open('wb_nodes_endings.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
for e in data:
    clen = len(e['content'])
    status = 'OK' if clen >= 450 else 'SHORT'
    print(f"  ID {e['id']:2d} | {clen:4d} chars | {status} | {e['comment']}")
```

## 常见陷阱

1. **节点内容太概括**：只写"夏倾月被黑人侵犯"而不是引用原著具体台词和感官描写
2. **结局叙事太短**：判定条件+后续写了很多，核心叙事场景不到400 chars
3. **系统提示constant=false**：系统提示必须constant=true+keys=[]
4. **选项没有风险标识**：每个选项必须有⚡低/中/高/极高
5. **状态变化没有数值**：不能只写"信任增加"，必须写"+10"
6. **extensions缺失字段**：子代理生成时经常漏掉scan_depth、match_whole_words等null字段
