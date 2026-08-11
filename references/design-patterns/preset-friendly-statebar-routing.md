# 推荐预设 + route_state 自动路由（发布友好方案）

> 适用：递进式世界书/阶段路由卡在社区发布时，希望降低 Author's Note 手动配置门槛，又不引入 MVU/getvar/setvar。
> 修订：2026-07-18，根据《艳母的荒唐赌约》推荐预设实测审查修正。关键修正：不要用 HTML 注释承载 route_state；不要复用 status_top；不要把自动 Marker 与 AN Marker 设计成同聊天无缝混用。

---

## 1. 核心判断

Author's Note 单一权威路由是跨预设最稳方案，但用户体验不友好；推荐预设 + route_state 自动路由可以改善发布体验，前提是**明确绑定一套不会吞 route_state 的推荐预设**。

⚠️ 边界（2026-07-26）：以上 AN 稳定性论述仅适用于配套预设外部路线；native 独立卡不使用 AN/ROUTE_STAGE（`final_delivery_gate.py` 检测到 `ROUTE_STAGE=P#` 会硬拒绝，STAGE_EXTERNAL_ROUTE_UNSUPPORTED）。

正确发布结构：

```text
v1.17.2 推荐预设自动路由版：主推，低门槛
v1.17.1a AN 单一权威版：兜底，高兼容
```

不要把两种 Marker 来源混在同一聊天中宣称“无缝兜底”。

---

## 2. 不要使用 HTML 注释承载 route_state

很多 SillyTavern 预设会启用类似：

```regex
/<!--\s*([\s\S]*?)\s*-->/g
```

的“HTML注释-去除”Regex，并可能开启 outgoing prompt 处理。这样会删除：

```html
<!-- route_state
ROUTE_STAGE=P1
-->
```

导致模型上下文甚至 World Info 扫描都可能看不到 route_state。

推荐使用普通机器标签或方括号 marker。

首选：

```xml
<route_state>
ROUTE_MODE=PRESET
ROUTE_STAGE=P1
</route_state>
```

显示隐藏用专用 Regex：

```regex
/<route_state>[\s\S]*?<\/route_state>/g
```

设置：

```text
Alter Display: ON
Alter Outgoing Prompt: OFF
```

目标：

```text
聊天 raw：保留
模型上下文：保留
世界书扫描：可读取
用户界面：隐藏
```

---

## 3. 不要抢占 status_top，共用槽会冲突

许多预设已经用：

```text
{{setvar::status_top::}}
{{setvar::status_top::时间栏}}
{{getvar::status_top}}
```

管理时间栏/状态栏。新增路由系统不应复用这个共享变量，否则会出现：

```text
route_state 覆盖日期卡片
或
日期卡片覆盖 route_state
```

应新增专用变量：

```text
route_state_top
```

变量初始化组增加：

```text
{{setvar::route_state_top::}}
```

新增路由 prompt 设置：

```text
{{setvar::route_state_top::
<route_state_rule>
每轮在正文开始前输出且只输出一个 <route_state> 块。
格式：
<route_state>
ROUTE_MODE=PRESET
ROUTE_STAGE=P0/P1/P2/P3/P4/P5/P6
</route_state>
沿用最近有效阶段；只有用户明确要求切阶段时才改变。
</route_state_rule>
}}
```

Core 中改为：

```text
### 正文
{{getvar::route_state_top}}
{{getvar::status_top}}
{{getvar::ui_anti_empty}}
{{getvar::Manual}}
${正文……}
```

---

## 4. 自动版与 AN 版必须分模式

### 推荐预设自动版

```text
AI 每轮输出 <route_state>
不使用 Author's Note 阶段 Marker
用户用自然语言要求切阶段
切换从下一轮开始稳定生效
```

### AN 权威版

```text
AI 不输出 ROUTE_STAGE
Author's Note 是唯一阶段来源
```

不要在同一聊天同时存在：

```text
AI 自动 ROUTE_STAGE
+
AN ROUTE_STAGE
+
用户消息 ROUTE_STAGE
```

因为 World Info 没有“最新优先级”，只会看到多个字符串并可能同时触发多个阶段。

---

## 5. route_state 最小字段原则

第一版只放必要字段：

```xml
<route_state>
ROUTE_MODE=PRESET
ROUTE_STAGE=P1
</route_state>
```

不要提前加入：

```text
ROUTE_SCENE=刘宇家·客厅
ROUTE_HINT=第一赌约与赵勇征服
```

原因：这些自然语言字段可能扩大误触发面。事件路由完成前，`ROUTE_EVENT` 也默认不启用。

---

## 6. 世界书设置要求

角色卡自动版：

```text
阶段主条目 primary keys = ROUTE_STAGE=PX
阶段依赖条目 secondary_keys = ROUTE_STAGE=PX
per-entry extensions.scan_depth = 2
extensions.match_whole_words = false
顶层 selective/constant 与 extensions 同步
```

适用 scan_depth=2 的条目：

- 阶段主条目
- 阶段关系
- 阶段场景
- 阶段 NPC
- 阶段事件

不适用：常驻规则、基础人物档案。

发布说明必须要求：

```text
World Info → Minimum Activations = 0
```

否则 ST 可能忽略 scan_depth 继续向旧历史扫描，重新扫出旧阶段 marker。

---

## 7. 实测门槛

必须测试：

1. 普通发送；
2. Swipe；
3. Regenerate；
4. Continue；
5. 删除最后一条后重发；
6. 用户自然语言切阶段；
7. P1 中讨论 P4/P6 未来词；
8. 从旧聊天继续；
9. 换非推荐预设后确认自动续航失败，提示改用 AN 版。

路由 prompt 的 trigger 应留空，覆盖所有生成类型。

---

## 8. 发布文案口径

正确：

```text
推荐搭配附带预设使用。推荐预设会在每轮回复中保留 <route_state>，用于维持世界书阶段触发。若使用其他预设，请改用 AN 权威版。
```

错误：

```text
任意预设都能自动阶段推进。
AN 可以和自动 route_state 无缝混用。
```
