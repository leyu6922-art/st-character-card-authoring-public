# 推荐预设自动路由 — 阶段世界书触发模式

> **定位：** 与 AN 单一权威路由（`an-single-authority-stage-routing.md`）并列的发布版路由模式。
> **适用场景：** 发布角色卡时搭配一套推荐预设，让普通用户无需手动设置 Author's Note。
> **核心思想：** AI 每轮在正文前输出 `<route_state>` 机器标签，ST 扫描该标签触发世界书阶段过滤。
> **⚠️ 路线边界（2026-07-26）：** 本路线属配套预设外部路线——不进入 native 独立卡的 stage-entry-contract（`route_source` 仅 `greeting_title`），`final_delivery_gate.py` 检测到 `ROUTE_STAGE=P#` 会硬拒绝（STAGE_EXTERNAL_ROUTE_UNSUPPORTED），本文档流程不产生任何『已过交付门控』结论。

---

## 适用条件

使用本模式前，必须确认：

1. 你有一套愿意搭配发布的推荐预设
2. 该预设不会吞掉角色卡要求输出的内容（常见问题：预设 Core 输出格式覆盖了卡内状态栏）
3. 你愿意维护两套版本：预设自动路由版 + AN 权威兜底版

---

## 核心架构

### 角色卡侧

**阶段主条目**（每个阶段一条）：

```json
{
  "id": 10,
  "keys": ["ROUTE_STAGE=P0"],
  "selective": false,
  "secondary_keys": [],
  "extensions": {
    "selective": false,
    "scan_depth": 2,
    "match_whole_words": false,
    "sticky": 0,
    "position": 0
  }
}
```

**阶段依赖条目**（关系/场景/事件，以 P3 为例）：

```json
{
  "id": 21,
  "keys": ["骆鹏", "大鹏"],
  "secondary_keys": ["ROUTE_STAGE=P3"],
  "selective": true,
  "extensions": {
    "selective": true,
    "selectiveLogic": 0,
    "scan_depth": 2,
    "match_whole_words": false,
    "sticky": 0,
    "probability": 100,
    "useProbability": true
  }
}
```

所有阶段依赖条目的 `secondary_keys` 统一使用 `ROUTE_STAGE=P#`，不用自然语言阶段名（如"当前阶段：P3"）。

### Greeting 冷启动

每条 greeting 起始位置输出 `<route_state>` 块，不写 HTML 注释（因为推荐预设可能启用了 HTML 注释去除 regex）：

```xml
<route_state>
ROUTE_MODE=PRESET
ROUTE_STAGE=P0
</route_state>

<!-- 后续正文从下一行开始 -->
```

每个 greeting 对应自己的阶段，映射关系：

| greeting | 阶段 |
|---|---|
| first_mes | P0 |
| alt[0] | P1 |
| alt[1] | P2 |
| alt[2] | P3 |
| alt[3] | P4 |
| alt[4] | P5 |
| alt[5]/alt[6] | P6 |

### OOC / 状态栏条目

OOC 条目写入路由铁律：

```
【推荐预设自动路由铁律】
当前阶段由最近有效的 <route_state> 中唯一 ROUTE_STAGE=P# 决定。
<route_state> 是机器锚点，不属于正文剧情，不得让角色朗读。
如果用户用自然语言要求切阶段（如"进入P2"），AI 本轮写入新 ROUTE_STAGE。
切阶段下一轮生效：本轮世界书仍按旧阶段加载。
AI 不得自行跳阶段。
```

---

## 推荐预设侧

### 核心改动

在推荐预设中做**最小必要改动**，不破坏原预设功能：

1. **初始化一个专用变量**，不抢已有共享变量（如 `status_top`）

   在变量初始化组（通常是最早的 system prompt）中追加：

   ```
   {{setvar::route_state_top::}}
   ```

2. **新增一个 route_state 输出 prompt**，放在 Core 之前。内容包含 10 条规则：

   ```
   {{setvar::route_state_top::
   <route_state_rule>
   每轮输出正文时，必须在 ### 正文 后、正文主体前输出且只输出一个 <route_state> 块：

   <route_state>
   ROUTE_MODE=PRESET
   ROUTE_STAGE=P0/P1/P2/P3/P4/P5/P6
   </route_state>

   规则：
   1. ROUTE_STAGE 必须是 P0-P6 之一。
   2. 默认沿用最近一条有效 <route_state> 中的 ROUTE_STAGE。
   3. 如果本轮是开场，且 greeting 中存在 <route_state>，沿用 greeting 的 ROUTE_STAGE。
   4. 只有用户用自然语言明确要求切阶段时，才改变 ROUTE_STAGE。
   5. 切阶段从下一轮世界书开始稳定生效。
   6. AI 不得自行跳阶段，只能提示用户是否切换。
   7. 不要输出多个 ROUTE_STAGE。
   8. 不要把 route_state 写成 HTML 注释。
   9. 不要在 route_state 中加入 ROUTE_SCENE/ROUTE_HINT 等自然语言字段。
   10. route_state 是机器锚点，不属于正文，不得让角色朗读。
   </route_state_rule>
   }}
   ```

3. **Core 插槽**：在 `{{getvar::status_top}}` 前插入 `{{getvar::route_state_top}}`

   ```
   ### 正文
   {{getvar::route_state_top}}     ← 新增
   {{getvar::status_top}}          ← 保留（日期卡片等不变）
   {{getvar::ui_anti_empty}}
   {{getvar::Manual}}
   ${正文...}
   ```

4. **新增显示隐藏 regex**，只隐藏界面显示、不改变 outgoing prompt：

   | 字段 | 值 |
   |---|---|
   | scriptName | `route_state-显示隐藏` |
   | findRegex | `/<route_state>[\s\S]*?<\/route_state>/g` |
   | replaceString | `""` |
   | disabled | `False` |
   | promptOnly | `False`（=只隐藏显示，不影响 outgoing） |

> ⚠️ **不要关闭原预设的 HTML 注释去除 regex**——它可能被其他功能依赖。我们的 route_state 不使用 HTML 注释，因此不受影响。

---

## 阶段切换规则

| 用户操作 | AI 行为 |
|---|---|
| 自然语言 "进入P2" | 本轮输出 `ROUTE_STAGE=P2`，世界书仍按 P1 生成 |
| 下一轮 | ST 扫描到新 ROUTE_STAGE=P2，P2 世界书触发 |
| 讨论未来词 "九局五胜怎么办" | route_state 不变，P4/P6 不触发 |
| Swipe / Regenerate / Continue | 必须都输出 route_state（通过 prompt trigger 留空确保覆盖全部生成类型） |

---

## 错误标记

不要在 greeting 或 route_state 中写：

- ❌ HTML 注释 `<!-- ROUTE_STAGE=P1 -->`（会被 preset regex 删除）
- ❌ 中文阶段名 `当前阶段：P1`（会被 AI 认为可朗读）
- ❌ 多字段 `ROUTE_SCENE=xxx`（扩大误触发面）
- ❌ AI 正文朗读 `<route_state>` 内容

---

## 与 AN 单一权威路由的关系

| 维度 | AN 单一权威版 | 推荐预设自动路由版 |
|---|---|---|
| 阶段来源 | Author's Note 中的 ROUTE_STAGE | AI 输出的 `<route_state>` |
| 对预设要求 | 无（所有预设通用） | 必须使用配套预设 |
| 用户配置 | 需要手动设置 AN | 导入预设即可，零配置 |
| 续航可靠性 | 高（AN 不被预设/模型影响） | 中（依赖推荐预设输出） |
| 发布友好度 | 低（需要用户理解 AN 设置） | 高（导入即用） |
| 维护成本 | 只维护一张卡 | 同时维护卡 + 预设 |

**建议双版本发布：**

- 主推：推荐预设自动路由版（v1.17.2）
- 兜底：AN 单一权威版（v1.17.1a）

---

## 静态验收清单

执行修改后检查：

```
- validate_card.py errors=0
- enrichment_self_check 0🔴（可接受少量🟡）
- audit_worldbook_triggers 硬风险=0
- greeting 不含 HTML 注释式 route_state
- greeting 含 <route_state> 且每条只有一个 ROUTE_STAGE
- 阶段主条目 keys 只含 ROUTE_STAGE=P#
- 阶段依赖 secondary 只含 ROUTE_STAGE=P#
- 阶段相关条目 scan_depth=2
- 所有 extensions.match_whole_words=false
- sticky>0=0
- 旧 secondary 格式（当前阶段：PX）= 0
- 预设侧 route_state_top 初始化存在
- 预设侧 route_state prompt enabled=true
- 预设侧 Core 含 {{getvar::route_state_top}}
- 预设侧 HTML注释-去除 保持原状
```

---

## 实机测试清单

1. P0-P6 开场冷启动（greeting 带 route_state）
2. 下一轮"继续"（route_state 续航）
3. P1 讨论 P4/P6 未来词（不误触发）
4. 自然语言切阶段（"进入P2"）
5. Swipe / Regenerate / Continue（全部输出 route_state）
6. 删除最后一条后重发（回退处理）
7. WorldInfoInfo 只显示当前阶段条目
