# Author's Note 单一权威阶段路由（跨预设可靠方案）

> **状态**：2026-07-18·艳母的荒唐赌约 v1.17.1 中首次完整实施并验证
> **核心问题**：无变量递进式世界书在依赖 AI 状态栏/greeting 注释/自然语言 key 做阶段路由时，不同 ST 预设环境下触发不可靠。
> **本方案**：将阶段权威状态源从 AI 输出侧迁移到用户/基础设施侧——Author's Note 中的 `ROUTE_STAGE=P#` 是唯一权威阶段状态。

> **⚠️ 路线边界（2026-07-26）**：本路线属**配套预设外部路线**。不进入 native 独立卡的 stage-entry-contract（`route_source` 仅 `greeting_title`，`author_note` 会被解析器拒绝）；`final_delivery_gate.py` 检测到 `ROUTE_STAGE=P#` 标记会硬拒绝（STAGE_EXTERNAL_ROUTE_UNSUPPORTED）；本文档流程不产生任何『已过交付门控』结论。

---

## 1. 为什么需要 Author's Note 路由？

### 1.1 ST 世界书触发铁律

世界书触发发生在模型看到 prompt **之前**：

```
ST 扫描聊天记录中的文本 keywords
→ 命中世界书条目
→ 把条目插入 <Lore> 段
→ 模型才看到这些内容
```

所以：
- AI **不会**主动触发世界书——它只能看到已经被触发的条目
- 世界书条目内容里的关键词**不会**递归触发自己
- 阶段路由必须依赖聊天记录中**真实存在的文本**作为锚点

### 1.2 greeting 注释方案的问题

`progressive-worldbook-design.md §3.4-3.5` 推荐在 greeting 中用 HTML 注释写阶段标记：

```html
<!-- 当前阶段：P1 第一赌约与赵勇征服 -->
```

这个方案有两个致命缺陷：

1. **掉出扫描深度**：几轮对话后 greeting 可能不再被 ST 扫描
2. **预设冲突**：如果 Author's Note 中设置了不同的阶段标记，ST 可能同时扫描到新旧标记

### 1.3 AI 状态栏方案的问题

要求 AI 每轮输出 `[当前阶段] P1` 或 `ROUTE_STAGE=P1`：

- 不同预设的输出格式完全不同（有的输出 XML 模板，有的输出 story_record，有的压根没有状态区）
- 预设优先级 > 角色卡世界书——角色卡**不能命令**预设输出特定格式
- v1.17 实测：用户的预设输出 `<content>/<story_record>/<aftertalk>/<math>` 结构，完全没有我们要求的状态栏

### 1.4 自然语言 key 方案的问题

用 `当前阶段：P2`、`三男加入`、`第二赌约` 等自然词做阶段条目 key：

- 这些词在自然角色扮演对话中**不会稳定出现**
- 讨论未来阶段时可能**误触发**（如 P1 中说"如果以后有第二赌约怎么办"→可能误触发 P2）
- 切换阶段无权威覆盖——旧标记残留不会被自动清除

### 1.5 核心结论

> 无变量世界书没有隐藏状态。阶段信息必须存在于 ST 能扫描到的可见文本中。
> 如果依赖 AI 输出这条路径不可靠（预设吞状态栏），那就只能依赖另一条路径：**用户侧或基础设施侧提供阶段锚点**。

---

## 2. Author's Note 单一权威方案

### 2.1 核心原则

```
Author's Note 中的 ROUTE_STAGE=P# = 唯一权威阶段状态源
```

其他所有来源全部降级：
- **greeting**：不再放可触发的路由 marker（AN 权威版）
- **AI 回复/story_record/状态栏**：不作为权威阶段状态——仅供叙事连续性参考
- **用户消息**：不作为持久阶段状态——只用于临时测试
- **Quick Reply**：可选配套，用 `/note ROUTE_STAGE=P#` 覆盖 AN

### 2.2 阶段主条目 key 设计

每个阶段主条目（P0-P6）的 keys **只含一个**：

```json
["ROUTE_STAGE=P0"]
["ROUTE_STAGE=P1"]
["ROUTE_STAGE=P2"]
["ROUTE_STAGE=P3"]
["ROUTE_STAGE=P4"]
["ROUTE_STAGE=P5"]
["ROUTE_STAGE=P6"]
```

**坚决删除的 key 类型**：
- `当前阶段：P#`（自然语言，不够机器友好）
- `三男加入`、`第二赌约`、`温泉山庄` 等自然词（容易在讨论未来时误触发）
- `P# 阶段名`（如 `P2 新赌约`）

保持参数：
```
enabled = true
constant = false
selective = false
secondary_keys = []
sticky = 0
prevent_recursion = true
match_whole_words = false
```

### 2.3 阶段依赖条目的 secondary key 设计

所有关系、场景、事件条目的 secondary_keys **只含对应 `ROUTE_STAGE=P#`**：

```json
// P2 关系条目
{
  "keys": ["赵勇", "兄弟"],           // primary: 角色/事件自然词
  "secondary_keys": ["ROUTE_STAGE=P2"], // secondary: 唯一阶段锚点
  "selective": true
}
```

**不再保留**：`当前阶段：P2`、`【阶段锚点：P2】`、`[STAGE:P2]`——统一为 `ROUTE_STAGE=P#` 单一格式。

场景条目如果跨多个阶段，secondary 写全对应阶段：
```json
// 刘宇家（全阶段可用）
"secondary_keys": ["ROUTE_STAGE=P0", "ROUTE_STAGE=P1", ..., "ROUTE_STAGE=P6"]

// 温泉山庄（仅 P3 和 P6 可用）
"secondary_keys": ["ROUTE_STAGE=P3", "ROUTE_STAGE=P6"]
```

### 2.4 greeting marker 策略

**AN 权威版**：greeting **不保留任何**可触发的阶段 marker。

删除内容：
- `ROUTE_STAGE=P#` 行
- `ROUTE_STATE` HTML 注释块
- `<!-- 当前阶段：PX ... -->` 注释
- 隐藏注释中的 `当前阶段：PX`

保留：greeting 的剧情正文不变，只删除路由标记文本。

**后果**：greeting CJK 字数下降约 250-350 字/条（主要是注释中的中文）。这是已知 trade-off——greeting 不再承担阶段标记职能。

如果必须保留 greeting 冷启动 marker（如社区发布版），必须在报告中明确标注为"兼容发布版"而非"AN 单一权威版"，并说明 AN 与 greeting 冲突时 ST 可能双触发。

### 2.5 OOC/系统条目改写

OOC 条目（id=0）中的阶段路由规则必须改为 AN 单一权威：

```
【Author's Note单一权威路由】

本卡阶段状态以当前聊天 Author's Note 中唯一一行 ROUTE_STAGE=P# 为准。

世界书触发发生在模型看到 Prompt 之前，因此 AI 输出的状态栏、story_record、正文总结都不是权威阶段状态。

如果 Author's Note 为空或缺少 ROUTE_STAGE=P#，则阶段条目可能不加载；
AI 应进入"无路由降级状态"：只按常驻规则和已加载人物/场景写，不得擅自推断当前阶段。

如果 Author's Note 同时出现多个 ROUTE_STAGE=P#，这是配置错误；
AI 不得混用阶段，应提示用户保留一个阶段锚点。

AI 不得自行修改 ROUTE_STAGE；
阶段切换由用户手动修改 Author's Note 或 Quick Reply 的 /note 命令完成。

AI 可以在剧情上提示"已具备进入下一阶段的条件"，但不得自动跨阶段。
```

状态栏条目（id=3）从"要求 AI 输出固定状态栏"改为"路由使用说明与连续性记录"。

---

## 3. Author's Note 使用说明（供最终用户）

### 3.1 基础用法

在当前聊天 Author's Note 中写入且**只写入一行**：

```
ROUTE_STAGE=P1
```

### 3.2 可选阶段

| Anchor | 阶段 | 说明 |
|---|---|---|
| `ROUTE_STAGE=P0` | 基准线/序章 | 赌约前/日常 |
| `ROUTE_STAGE=P1` | 第一阶段 | 初始事件/首次介入 |
| `ROUTE_STAGE=P2` | 第二阶段 | 范围扩展 |
| `ROUTE_STAGE=P3` | 第三阶段 | 半公开场景 |
| `ROUTE_STAGE=P4` | 第四阶段 | 协议/规则化 |
| `ROUTE_STAGE=P5` | 第五阶段 | 漏洞/多方博弈 |
| `ROUTE_STAGE=P6` | 第六阶段 | 风险突破/公开化 |

### 3.3 切换阶段

1. 打开 Author's Note
2. 把 `ROUTE_STAGE=P1` 替换为 `ROUTE_STAGE=P2`
3. 保存

**严禁**：追加第二行、同时保留两个 ROUTE_STAGE、在 AN 中混入其他内容。

### 3.4 快捷键（Quick Reply 可选配套）

```text
/note ROUTE_STAGE=P1
```

注意：`/note` 会覆盖整个 Author's Note。

---

## 4. 验证方法

### 4.1 AN 路由模拟测试

必须跑 7 个核心测试：

| # | AN | 聊天正文 | 预期 |
|---|---|---|---|
| T1 | P0 | 普通对话 | 只触发 P0 |
| T2 | P2 | 回忆 P0 阶段 | P0 **不触发** |
| T3 | P1 | 讨论 P6 未来词 | P4/P6 **不触发** |
| T4 | P2（模拟切换） | 切阶段后对话 | 只触发 P2 |
| T5 | P1+P2 双 marker | 配置错误场景 | 检测到双触发 |
| T6 | 空 | 普通对话 | P0-P6 **均不触发** |
| T7 | P1 | 多角色名同时出现 | 只触发 P1 阶段依赖 |

### 4.2 验收门槛

```
阶段主条目 keys 只含 ROUTE_STAGE=P# ✅
阶段依赖 secondary 只含 ROUTE_STAGE=P# ✅
AN=P2 时 P0 不触发 ✅
AN=P1 + 未来词时 P4/P6 不触发 ✅
AN 多 marker 被检测 ✅
清空 AN 时阶段条目掉线 ✅
greeting 不含 ROUTE_STAGE=P# 或 当前阶段：P# ✅
sticky > 0 的阶段条目 = 0 ✅
```

### 4.3 实机验证方法

1. 在 ST 中设置 Author's Note = `ROUTE_STAGE=P1`
2. 发送测试消息
3. 用 **Prompt Itemization** 或 **WorldInfoInfo 扩展** 检查 `<Lore>` 段中的激活条目
4. 确认只有 P1 阶段条目被加载，P0/P2-P6 不在激活列表中

---

## 5. 已知限制与降级处理

| 限制 | 说明 |
|---|---|
| greeting 不提供阶段路由 | 冷启动需用户手动设置 AN |
| AN 为空时不自动提示 | 用户须自行意识到阶段未设置 |
| AN 双 marker 不自动否决 | ST 会同时触发两个阶段，需用户手动修复 |
| 阶段切换无历史记录 | 不会记住之前是哪个阶段 |
| 事件包需手动触发 | 专属 event marker（如 `ROUTE_EVENT=P1-E03`）须聊天中出现 |
| greeting 字数下降 | AN 权威版删除 HTML 注释中的约 250-350 CJK 字 |

---

## 6. 与 greeting 注释方案的对比

| 维度 | greeting 注释方案（v1.17） | AN 单一权威方案（v1.17.1） |
|---|---|---|
| 冷启动 | 自动（greeting 注释） | 需手动设置 AN |
| 长对话维持 | 不可靠（注释掉出扫描深度） | 可靠（AN 持续在扫描范围内） |
| 预设兼容 | 差（依赖 AI 输出状态栏） | 优（不依赖任何 AI 输出格式） |
| 阶段隔离 | 中（自然词可能误触发） | 优（唯一机器 marker） |
| 错误模式 | 双阶段同时触发 | 双 marker 被检测但需手动修复 |
| 用户体验 | 不用配置 | 需理解 AN 概念 |
| 社区发布友好度 | 高 | 中（需附使用说明） |

---

## 7. 适用场景

> ⚠️ 路线边界（2026-07-26）：无论下列哪种场景，本路线均为配套预设外部路线——不进入 native 独立卡的 stage-entry-contract，`final_delivery_gate.py` 检测到 `ROUTE_STAGE=P#` 会硬拒绝（STAGE_EXTERNAL_ROUTE_UNSUPPORTED），本文档流程不产生任何『已过交付门控』结论。

**推荐使用 AN 单一权威方案**：
- 个人使用，预设不固定的场景
- 需要跨多个预设测试/比较的场景
- 追求触发可靠性而非"零配置"的场景
- 已确认预设会吞状态栏的场景

**可保留 greeting 注释方案**：
- 社区发布，目标用户可能不理解 AN 概念
- 已知目标预设兼容状态栏格式
- 短对话（<20 轮），greeting 不会掉出扫描深度

---

## 8. 实施后的 validate 收口微修（关键坑）

### 8.1 问题

AN 权威版从 greeting 中删除 HTML 注释中的路由标记（`ROUTE_STAGE=P#`、`当前阶段：P#`、`ROUTE_STATE` 块），这些注释含有约 250-350 中文字/条。删除后 greeting 的 validate_card.py 字数检查会从 "≥1400 通过" 下降到 "1000-1200 失败"。

**这不是可以忽略的 errors**——validate_card.py 的 greeting 字数检查是交付门槛。AN 路由方案实施后必须追加一轮 **收口微修**。

### 8.2 收口微修工作流（两步走）

**第一步**：实施 AN 路由（按本文 §2 全部修改）

**第二步**：单独补足 greeting 字数（本 section）

### 8.3 补写规则

每条不足 1400 字的 greeting 补 **150-300 中文字**，补在结尾或场景转折处。

补写内容**必须**：
- 写原场景当下的动作、表情、心理、环境声音、用户干预点
- 匹配原有文风和叙事节奏
- 为用户留出第一轮接话空间

补写内容**严禁**：
- 写 ROUTE_STAGE/ROUTE_STATE/当前阶段：P# 等路由 marker
- 写 Author's Note 使用说明或配置指引
- 引入未来阶段词作为剧情事实
- 改变开场核心事件或把开场改写成新剧情
- 使用机械补字段或重复模板套话

### 8.4 Quick Reply 文档残留清理（配套）

AN 权威版实施后，Quick Reply 配套文档中常残留"聊天消息格式 ROUTE_STAGE"等旧方案的备选写法，**必须一并清理**：

删除：`或使用聊天消息格式 ROUTE_STAGE=P0`、`或在聊天中发送消息然后手动复制到 AN`

替换为：`不建议把 ROUTE_STAGE=P# 作为普通聊天消息发送。聊天消息锚点会留在历史记录中，可能与 Author's Note 产生冲突。`

### 8.5 验收标准

收口完成后必须：

```
validate_card.py errors = 0  ← 硬门槛
所有 greeting 不含 ROUTE_STAGE/ROUTE_STATE/当前阶段：P# 残留
QR/使用说明文档不含聊天消息 ROUTE_STAGE 残留
世界书路由架构完全不变（条目数、keys、secondary 与 AN 路由版一致）
```

### 8.6 实施案例

艳母的荒唐赌约 v1.17.1 → v1.17.1a：
- 7 条 greeting 从 1183-1330 字补到 1503-1603 字
- 补写方向：P0 客厅张力、P1 路灯沉默、P2 "收不住了"对白、P3 用户干预窗口、P4 电梯压迫、"不是游戏"认知转变、P6 危机管理+博弈列表
- QR 文档中两处聊天消息 ROUTE_STAGE 残留已清理

---

> *创建时间：2026-07-18 · 首次实施：艳母的荒唐赌约 v1.17.1*
> *收口微修案例：v1.17.1 → v1.17.1a（2026-07-18）*
> *关联文件：progressive-worldbook-design.md、no-variable-route-marker-audit.md*
