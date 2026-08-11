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

每个 entry 的 `extensions` 必须包含（摘自实际酒馆导出）：
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

`character_book` 顶层结构（注意：没有 `extensions`/`scan_depth`/`token_budget` 等独立世界书字段）：
```json
{
  "character_book": {
    "name": "世界书名称",
    "entries": [ ... ]
  }
}
```
