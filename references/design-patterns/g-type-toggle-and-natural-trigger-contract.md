# G型选开、自然触发与玩家代理权契约

本文件定义 G 型及任何含玩家身份选开的卡片，如何把“自动推进”与“玩家接管”做成可审计功能。它是生产策略，不改变 CCv3 基础 schema。

## 1. 条目职责

`extensions.entry_role` 只允许四类：

| 角色 | 标准结构 | 用途 |
|---|---|---|
| `identity_toggle` | `constant=true, enabled=false, keys=[]` | 玩家手动选择的身份；身份间互斥。 |
| `feature_toggle` | `constant=true, enabled=false, keys=[]` | 手动启用的玩法功能；不参与身份互斥。 |
| `system_constant` | `constant=true, enabled=true, keys=[]` | 始终加载的身份底座、OOC、文风、关系矩阵。 |
| `common_content` | 自然 key / selective 按职责声明 | 角色、场景、事件、语料等共享内容。 |

新卡的 `feature_toggle` 不再默认启用。旧卡若维持历史行为，可在最终门控显式传 `--legacy-player-agency-modes`，但不得把它用于新构建。

## 2. 始终开启的最小身份底座

即使两个玩法功能均关闭，`system_constant` 仍必须明确：

```text
当前选中的身份由玩家扮演。AI只扮演非玩家NPC、环境和可观察后果；不得冒充当前玩家身份。
```

这不是场景悬停模式，不能删掉。它只防止模型把玩家误当成旁白、镜头或可由 AI 代管的 NPC。

## 3. 强制双选开条目

每张新建的 G 型/玩家身份卡都从 `templates/player-agency-modes.example.json` 复制两条条目，并由 `make_entry()` 补齐本项目所需的完整 extensions 字段。

### A. 自动推进剧情

```text
extensions.entry_role = feature_toggle
extensions.feature_mode = narrative_director
enabled = false
```

启用后只授权 **NPC、环境和候选事件** 主动引入变化：

- 每次只展开一个主要事件；
- 候选事件在实际进入剧情前不等于既成事实；
- 不展示菜单、不使用元叙事“触发事件”；
- 不替玩家生成台词、心理、决定、移动或关键行动；
- 当前玩家已主动推进的路线优先。

### B. 玩家行动边界与场景悬停

```text
extensions.entry_role = system_constant
extensions.feature_mode = player_agency_boundary
extensions.enforcement = always_on
enabled = true
```

此条合并旧的“场景悬停铁律”和“玩家行动边界”，作为玩家主导路线的常驻边界。它必须覆盖七类禁止项：

1. 玩家台词/回答；
2. 玩家思想、内心和判断；
3. 玩家决定、选择、同意与拒绝；
4. 玩家移动、进入、离开与换场；
5. 玩家使用物品、接受邀约、完成调查或关键动作；
6. 玩家未观察/未获知事实进入记忆、判断或台词；
7. 时间跳过、阶段切换、互动结束与关系结果锁定。

每轮必须停在 NPC 动作、环境变化、问题、证据或对话刚递到玩家面前的接管点。不要只写“不能替玩家决定”这一句；它不足以约束模型。

## 4. 组合与优先级

| 自动推进 | 玩家边界/悬停 | 行为 |
|:---:|:---:|---|
| 关 | 关 | 普通响应；不强制插入事件。 |
| 开 | 关 | NPC/环境可主动推进一个事件；不冒充玩家。 |
| 关 | 开 | 严格接管；场景停在玩家行动窗口。 |
| 开 | 开 | NPC可主动推进，但边界条目优先，涉及玩家即悬停。 |

边界条目正文必须写出“优先于自动推进剧情”。不能只依靠条目排序推断优先级。

## 5. 自动门控

新卡的正式交付命令默认执行该合同：

```bash
python scripts/audit_player_agency_modes.py "<final-card.json>" --require
python scripts/final_delivery_gate.py "<final-card.json>" --prototype G
```

`final_delivery_gate.py` 在 `--prototype G` 时自动要求双选开合同；其他新卡必须显式传 `--require-player-agency-modes`。缺少任一条、默认启用、字段不是高优先级、边界禁止项过薄、导演越权或未声明优先级都会失败。仅历史卡可显式使用：

```bash
python scripts/final_delivery_gate.py "<legacy-card.json>" --legacy-player-agency-modes
```

## 6. 事件与自然 key

自然事件仍使用 `common_content`，而非 `feature_toggle`：人物、地点、物件、动作等自然入口至少覆盖两条路径。`事件库`、`种子库`、`描写库`等内部标签不能做唯一 key。导演条目只授权调用当前已经加载的候选素材，不替代事件条目的自然触发与阶段隔离。

## 7. 验收

- [ ] 一次只启用一个 `identity_toggle`；
- [ ] 两个 `feature_mode` 均存在且 `enabled=false`；
- [ ] 两条均为 `before_char / ext.position=0 / depth>=4 / ignore_budget=true / exclude_recursion=true`；
- [ ] 常驻身份底座仍存在，且不把玩家写成旁白；
- [ ] 边界条目覆盖七类禁止项并写明玩家接管点；
- [ ] 导演条目只推进 NPC、环境和一个候选事件；
- [ ] 双开时，边界条目优先；
- [ ] `audit_player_agency_modes.py --require` 与最终门控均通过；
- [ ] 静态通过后，在 ST Prompt Itemization 确认手动启用的功能条目实际进入 Prompt；运行时验证不得由静态绿灯替代。
