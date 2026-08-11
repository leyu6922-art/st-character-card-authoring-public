# 治理报告委派模式（Governance Report Delegation）

When a card audit produces findings that are too large to fix in one session, write a structured governance report that another Hermes window can read and execute directly.

## When to Use

- Card has 10+ optimization items across multiple categories
- Fixes require careful per-entry analysis (key conflicts, selective optimization)
- User wants to delegate execution to a new window while preserving context

## Report Structure

```markdown
# {Card Name} 治理报告（遗留优化项）

> 本文档供下一轮修复窗口读取。上一轮已完成所有🔴必修项，本轮处理🟡优化项。

卡当前状态：{条目数}条 | {大小}KB | {N}条constant(~{X}K tokens)

---

## 一、{问题类别A}（{数量}个关键词被{N}条共享）

### 问题原因
{为什么会出现这个问题，根因分析}

### 冲突分级
{按严重程度分组，每组列出关键词→涉及条目→建议处理}

### 执行规则
1. {具体的修复规则，带优先级}
2. {不要做什么（避免误伤）}

### 预期收益
- {量化收益：省多少token，减少多少冲突}

---

## 二、{问题类别B}
...

## 执行优先级

| 优先级 | 项目 | 工作量 | 预期收益 |
|--------|------|--------|----------|
| 1 | ... | ... | ... |

建议执行顺序：{从小到大，逐步优化}

## 注意事项
1. {关键pitfall}
2. {备份建议}
```

## Key Principles

1. **用 comment 而非 ID 作为引用** — ID 可能在合并/修复后变化，comment 更稳定
2. **列出具体条目和建议** — 不要只说"优化 keys"，要列出每个 key 的当前条目和建议改法
3. **分级处理** — 3+条共享 vs 2条共享，收益不同，不要一刀切
4. **量化收益** — 每个优化项标注预期省多少 token
5. **先小后大** — 建议执行顺序从简单到复杂

## Cross-Window Verification

When receiving a governance report from another window:

1. **验证 ID 映射** — 报告中的 ID 可能与当前卡不一致，用 comment 交叉验证
2. **验证结论** — 用代码确认每个发现，不靠记忆
3. **标注每项** — ✓确认 / ❌误报 / ⚠️需确认
4. **补充遗漏** — 对方可能漏掉某些问题（如预处理脚本死代码）

**⚠️ Pitfall: 条目编号混淆**

对方报告中可能用 `entry[X]`（数组索引）而非 `ID=X`（条目 id 字段）。数组索引和条目 id 不一定相同（因为有 ID 空洞）。必须建立映射表再验证。

**⚠️ Pitfall: 验证代码变量引用 bug**

验证循环中 `e` 变量可能引用上一轮循环的值，导致输出错误数据。每轮循环必须重新赋值 `e = entry_dict[eid]`。

## Example: Modao Card Governance Report

示例玄幻项目治理报告（4736字）覆盖3个优化项：
1. Key冲突治理（38个关键词→按3+条共享分级→建议只改10个）
2. Selective优化（23条候选→按类型分组→建议暂缓）
3. 前世记忆变量（规则定义了但无入口→3个修复方案→推荐方案B）

报告写入参考资料目录后，另一个窗口读取并执行了方案1和3，方案2暂缓。
