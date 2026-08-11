# 世界书触发审计报告 — good_basic

> 生成时间：2026-07-16 16:11:29
> 卡文件：`C:\tmp\hard_term_card_synced.json`
> 审计脚本：`audit_worldbook_triggers.py`（ST v1.18 源码对齐触发模拟）

## 1. 总览

| 指标 | 数值 |
|---|---:|
| 文件大小 | 129.2 KB |
| 世界书条目 | 7 |
| 常驻条目（enabled） | 1 |
| 常驻条目（含禁用选开） | 1 |
| enabled=true | 6 |
| enabled=false | 1 |
| selective=true | 1 |
| 有secondary但顶层selective=false | 0 |
| 仅extensions.selective=true且有secondary | 0 |
| 有风险条目 | 3 |
| 硬风险条目 | 0 |

## 2. 每个 greeting 的初始触发负载

| Source | 常驻 | 触发 | 估算负载* | 判定 | 触发条目 |
|---|---:|---:|---:|---|---|

> *估算负载为脚本按字符粗略折算的诊断值，不等于API实际input tokens。ST实际请求应以Prompt Itemization/API usage为准。高负载本身不是错误，优先检查泛key、无关污染、递归链和实际截断。

| first_mes | 1 | 2 | 3840 | ✅ 轻负载 | [1]核心角色档案：林梦瑶, [3]场景：雨夜办公室 |
| alternate[0] | 1 | 2 | 3840 | ✅ 轻负载 | [1]核心角色档案：林梦瑶, [3]场景：雨夜办公室 |
| alternate[1] | 1 | 2 | 3840 | ✅ 轻负载 | [1]核心角色档案：林梦瑶, [3]场景：雨夜办公室 |

## 3. 风险条目清单

| ID | 条目 | 类型 | 触发意图 | 风险 | 建议 |
|---:|---|---|---|---|---|
| 2 | 林梦瑶语料库 | 人物 | primary-only | 所有开场白均不触发 | 若期望首轮可用，把关键词写入对应greeting；若中后期按需触发，可保留并备注 |
| 5 | 身体与环境描写库 | 人物 | primary-only | 所有开场白均不触发 | 若期望首轮可用，把关键词写入对应greeting；若中后期按需触发，可保留并备注 |
| 6 | NTR关系：林梦瑶×对手 | 关系 | primary-only | 所有开场白均不触发 | 若期望首轮可用，把关键词写入对应greeting；若中后期按需触发，可保留并备注 |

## 4. 逐条触发矩阵

| ID | 条目 | 类型 | intent | keys | secondary | sel | enabled | first_mes | alternate[0] | alternate[1] | 风险 |
|---:|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 系统规则 | 系统/常驻 | 常驻规则 |  |  | False | True | 常驻 | 常驻 | 常驻 | - |
| 1 | 核心角色档案：林梦瑶 | 人物 | primary-only | 林梦瑶 |  | False | True | ✅ 林梦瑶 | ✅ 林梦瑶 | ✅ 林梦瑶 | - |
| 2 | 林梦瑶语料库 | 人物 | primary-only | 林梦瑶语料 |  | False | True | - | - | - | 所有开场白均不触发 |
| 3 | 场景：雨夜办公室 | 场景 | 范围绑定/阶段限定 | 办公室/雨夜 | 林梦瑶 | True(AND_ANY) | True | ✅ 办公室 + 林梦瑶 | ✅ 办公室 + 林梦瑶 | ✅ 办公室 + 林梦瑶 | - |
| 4 | 事件种子：文件袋攻防 | 事件种子 | 手动/条件模块 |  |  | False | False | 禁用 | 禁用 | 禁用 | - |
| 5 | 身体与环境描写库 | 人物 | primary-only | 描写库 |  | False | True | - | - | - | 所有开场白均不触发 |
| 6 | NTR关系：林梦瑶×对手 | 关系 | primary-only | 林梦瑶关系 |  | False | True | - | - | - | 所有开场白均不触发 |

## 5. 普通句反证测试

以下普通聊天句用于发现泛 key 误触发：

| 普通句 | 会触发的条目 |
|---|---|
| 我要回家。 | - |
| 学校今天很安静。 | - |
| 老师让我去教室。 | - |
| 有人在房间里唱歌。 | - |
| 你看见那个人了吗？ | - |
| 这里有很多人。 | - |
| 他和她都在那个地方。 | - |

## 6. 下一步修复建议

- 如可进入ST，最终以 Prompt Itemization / <Lore> / API usage / 官方 countTokens 为准；脚本估算只用于定位泛key、死key和无关污染。
- 未发现必须立刻修复的触发问题；可按内容质量继续审查。

---

**铁律**：绿灯≠触发；启用≠加载；secondary_keys≠自动生效；extensions.selective≠顶层selective。
