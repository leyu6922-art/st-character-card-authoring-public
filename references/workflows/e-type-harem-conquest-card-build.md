# E型·禁忌后宫征服卡构建模式（2026-07-17·高考假期卡实证）

## 适用场景

小说以{{user}}（男主）为第一人称，征服多个女性角色。无NTR、无系统、无异能。女性角色之间无嫉妒/竞争关系。

## 典型结构

| 层级 | 条目类型 | 数量 | constant | position |
|------|---------|------|----------|----------|
| 系统 | OOC保护+世界书规则 | 1 | true | before_char |
| 系统 | 状态栏·征服进度 | 1 | true | before_char |
| 系统 | {{user}}身份 | 1 | true | after_char |
| 角色 | 女性角色档案(N个) | N | false | after_char |
| 角色 | 男性NPC档案 | 1-3 | false | after_char |
| 场景 | 关键地点 | 2-4 | false | after_char |
| 事件 | 关键剧情节点 | 5-10 | false | after_char |
| 系统 | 征服度系统 | 1 | false | after_char |
| 系统 | 安全等级系统 | 1 | false | after_char |
| 语料 | 女性语料库(N个) | N | false | after_char |
| 描写 | 独立描写库 | 1 | false | after_char |

**典型总条目**：20-30条

## 征服度系统设计

替代"堕落度"（NTR/恶堕用），用"征服进度"追踪每女性独立进度：

```
Lv.0 未接触 → Lv.1 试探 → Lv.2 越界 → Lv.3 突破 → Lv.4 臣服 → Lv.5 沉溺
```

- 每女性独立追踪，互不影响
- 等级只能递进不能回退
- 回复末尾简短标注当前进度

## 安全等级系统

```
🟢 私密（无人在场）→ 完整行为，无限制
🟡 半公开（可能有人）→ 手交/口交/偷摸，不能完整进行
🟢 公开（有外人）→ 眼神/暗示/偷摸，不能有明显动作
```

## 开场白设计原则

每条greeting聚焦一个女性角色的一个关键场景：
- 第一段：场景设定+氛围渲染
- 第二段：{{user}}心理+对女性的观察
- 第三段：事件推进+第一个接触点
- 第四段：悬念/中断/未完成（不直接完成征服）

## 关键Pitfall

- T100: {{user}}身份条目comment不要含"身份"二字
- T101: content中不要用emoji，用文字标记
- T102: 中文primary key至少2字
- T103: 语料库≥500中文字（5模块）
- T104: 必须有独立描写库

## 验证流程

```bash
# 1. 构建
python build/assemble_card.py

# 2. 结构验证
python scripts/validate_card.py card.json --target-size-kb N

# 3. 加料自检
python scripts/enrichment_self_check.py card.json

# 4. 最终门控
python scripts/final_delivery_gate.py card.json --project-dir . --prototype E
```
