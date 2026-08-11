# SillyTavern 脚本化模式参考

## 来源
示例玄幻项目卡v2.0脚本化实装（2026-07-05），对标参考卡"参考卡v4.2"（469条/2986KB）。

## 参考卡脚本条目清单

| id | 条目名 | 字数 | 功能 |
|----|--------|------|------|
| 48699 | output_format | 909 | `<Format>`强制UpdateVariable输出 |
| 624630 | [mvu_update]变量更新规则 | 7500 | YAML格式变量定义(type/range/check) |
| 740185 | 命定系统-读者核心 | 31142 | `<%_ _%>`完整预处理脚本(getLocalVar/setLocalVar) |
| 188432 | [DLC][事件][神选者] | 5115 | 概率触发+信号容器+阶段链 |
| 40188 | [DLC][事件]入口 | 1172 | 条件触发+事件开始+UpdateVariable |
| 53707 | [DLC][事件]本体 | 5476 | 阶段分支+选择等待+checkPoint |

## 模式1: 预处理脚本（@@preprocessing）

常驻条目，每轮对话开始前自动执行。

```
<%_
// Step 1: 读取所有变量
const wq_soul = Number(getMessageVar('stat_data.王启.灵魂损耗', {defaults: 0}));
const nfy_stage = getMessageVar('stat_data.角色D.阶段', {defaults: '异变'});
// ... 更多变量

// Step 2: 变量初始化（首次运行）
if (typeof getMessageVar('stat_data.天道种子') === 'undefined') {
  setMessageVar('stat_data.天道种子', {'角色D': {'腐蚀度': 0, '状态': '纯白'}});
}

// Step 3: 检测链（按优先级P0→P8）
let notifications = [];

// P0: BAD END检测
if (wq_soul >= 100) {
  notifications.push('🔴 BAD END 1：灵魂崩溃！');
}

// P1-P8: 各种跃迁检测
// ...

// Step 4: 输出通知
if (notifications.length > 0) {
_%>
<action_info>
  {预处理通知}
<%_ notifications.forEach(n => { _%>
  | <%- n %> |
<%_ }); _%>
</action_info>
<%_
}
_%>
```

### 关键函数

- `getMessageVar(path, {defaults: fallback})` — 读取变量，不存在时返回默认值
- `setMessageVar(path, value)` — 写入变量
- `Number()` — 确保数值类型比较正确
- `typeof ... === 'undefined'` — 检测变量是否首次运行

### 检测链优先级

| 优先级 | 检测项 | 效果 |
|--------|--------|------|
| P0 | 灵魂崩溃(>=100) | BAD END，停止所有检测 |
| P1 | 噩梦升级(30/50/70/90阈值) | 噩梦等级+1 |
| P2 | 相机进化(使用次数+灵魂损耗) | 初期→中期→后期 |
| P3 | 角色阶段跃迁(堕落度+条件) | 异变→堕落→觉醒 |
| P4 | 新角色线启动(前置角色阶段) | 角色A/厉红霞线开始 |
| P5 | 苦主风险检测(异常计数) | 风险等级升降 |
| P6 | 天道种子腐蚀联动 | 太一觉醒进度 |
| P7 | 万魔之主觉醒 | 5颗种子完全腐蚀+堕落90 |
| P8 | 变量更新(本轮变化) | 灵魂损耗/堕落度等 |

## 模式2: UpdateVariable输出格式

常驻条目，强制AI每次回复末尾输出变量更新。

```
<Format>
Force_Structured_output:
  output_rule:
    - 每次回复末尾必须插入<UpdateVariable>标签
    - 只更新本轮实际变化的变量
    - JSON Patch必须用[]包裹
    - 预处理脚本已自动更新的变量不需要手动重复
  output_format:
    <UpdateVariable>
    <Analysis>
    分析本轮剧情变化
    </Analysis>
    [
      {"op": "replace", "path": "/stat_data/王启/灵魂损耗", "value": <新值>}
    ]
    </UpdateVariable>
</Format>
```

### JSON Patch路径格式

- 用 `/` 分隔，对应JSON嵌套结构
- `/stat_data/王启/灵魂损耗` → `stat_data.王启.灵魂损耗`
- 替代操作：`{"op": "replace", "path": "...", "value": ...}`
- 数组追加：`{"op": "add", "path": "/stat_data/事件/已完成事件/-", "value": "事件名"}`

## 模式3: 变量更新规则（结构化YAML）

参考卡用YAML-like格式定义每个变量的type/range/check，让AI知道何时更新、更新多少。

```
variables_update_rules:
  王启:
    灵魂损耗:
      type: number, range: 0~100
      check: 相机初期+10~15 / 中期+5~8 / 后期+3~5
    噩梦等级:
      type: number, range: 0~4
      check: 根据灵魂损耗自动升级，由预处理脚本处理
  角色D:
    堕落度:
      type: number, range: 0~100
      check:
        - 轻微接触: +5
        - 亲密接触: +10
        - 性交: +10~15
        - 特殊行为: 额外+5
```

## 模式4: 事件条目（条件触发+阶段分支）

事件条目默认 `enabled: False`，触发时才启用。

```
<%_
// 检查是否满足触发条件
const completedEvents = getMessageVar('stat_data.事件.已完成事件', {defaults: []});
if (!completedEvent.includes("事件名") && getMessageVar('stat_data.事件.开启', {defaults: false}) != true) {
  const item = getMessageVar('stat_data.主角.背包.关键道具', {defaults: null});
  if (item != null) {
_%>
<event>
<!-- checkPoint -->
事件描述和互动内容...

<!-- SYSTEM_COMMAND_START -->
事件开始，必须在<UpdateVariable>中更新：
  将'事件.阶段'的值设置为'下一阶段'
<!-- SYSTEM_COMMAND_END -->
</event>
<%_
  }
}
_%>
```

## 模式5: 中间路线预处理（阈值+提示，不自动触发）

当用户要求"开放性"设计时，预处理脚本不自动触发阶段跃迁，只在阈值满足时输出提示。

```javascript
<%_
// 读取变量
const nfy_fall = Number(getMessageVar('stat_data.角色D.堕落度', {defaults: 0}));
const wq_camera_use = Number(getMessageVar('stat_data.王启.相机使用次数', {defaults: 0}));
const nfy_stage = getMessageVar('stat_data.角色D.阶段', {defaults: '异变'});

let notifications = [];

// 硬性游戏机制（保留自动触发）
if (wq_soul >= 100) {
  notifications.push('🔴 BAD END：灵魂崩溃！');
}

// 跃迁提示（不自动触发，只提示AI）
if (nfy_fall >= 50 && wq_camera_use >= 5 && nfy_stage === '异变') {
  notifications.push('💡 角色D阶段跃迁条件已满足（堕落度>=50, 相机>=5）。AI可考虑在合适的剧情场景中演绎转变。');
  // 注意：不调用 setMessageVar 修改阶段！
  // AI根据提示和当前场景自行判断是否在UpdateVariable中更新阶段
}
_%>
```

### 关键区别

| 线性模式 | 中间路线模式 |
|---------|------------|
| `setMessageVar('stat_data.角色D.阶段', '堕落')` | 只输出提示，不自动修改 |
| 条件满足=必然发生 | 条件满足=可以发生 |
| AI没有选择 | AI判断是否在当前场景中演绎 |

### 适用场景

- 用户说"开放点""让用户自己探索""不要锁死剧情"
- 角色卡基于小说但不想复述小说剧情
- 需要多周目可玩性

## 从伪代码转换的检查清单

将现有伪代码条目转为实装时，检查：

1. [ ] 所有"读取变量"改为 `getMessageVar('stat_data.X.Y', {defaults: ...})`
2. [ ] 所有"更新变量"改为 `setMessageVar('stat_data.X.Y', newValue)`
3. [ ] 所有"IF条件"改为 `if (val >= threshold) { ... }`
4. [ ] 数值比较前用 `Number()` 确保类型正确
5. [ ] 首次运行初始化用 `typeof ... === 'undefined'` 检测
6. [ ] 通知输出用 `<action_info>` + `notifications.push()` 模式
7. [ ] 条目设为 `constant: True`（预处理脚本必须常驻）
8. [ ] 添加关键词 `keys: ['预处理', '脚本', '@@preprocessing']`

## 示例玄幻项目实装数据

| 项目 | 修改前（伪代码） | 修改后（实装） |
|------|-----------------|---------------|
| 条目数 | 4个（id=5,6,85,99） | 3个（id=133,134,135） |
| 总字数 | 5,102字 | 9,217字 |
| 预处理脚本 | 1,133字自然语言 | 5,180字<%_ _%>脚本 |
| 变量规则 | 1,052字描述 | 2,863字YAML+Format |
| 输出格式 | 无 | 1,174字UpdateVariable强制 |
| 检测链覆盖 | P0-P5（部分） | P0-P8（完整含天道种子+万魔之主） |

---

## ⚠️ 预设+模型兼容性是变量系统能否工作的关键（2026-07-08 实测确认）

变量系统（预处理脚本+UpdateVariable）依赖AI按特定格式输出。如果预设为模型A设计但用模型B跑，变量系统会完全失效：
- **预处理脚本（@@preprocessing）**：ST宏引擎执行，与AI模型无关，**始终工作**
- **UpdateVariable输出**：依赖AI输出`<UpdateVariable>[...]</UpdateVariable>`标签。如果模型不遵循预设的输出格式要求，会输出裸JSON（无标签包裹），ST无法解析，**变量永远不更新**
- **正则隐藏脚本**：只影响显示层，不影响ST后台解析。`<UpdateVariable>`被正则隐藏后，ST仍会正常解析和更新变量

**实测案例**：梦鲸思客预设（为DeepSeek设计）+ Gemini模型 → AI输出裸JSON而非`<UpdateVariable>`包裹 → 变量不更新。换回DeepSeek后正常工作。

**建议**：如果用户使用的预设有变量系统，确认预设的目标模型与实际使用的模型匹配。不匹配时变量系统形同虚设。

## ⚠️ 游戏机制模板的P0-P3预设兼容性分级（2026-07-09 模板库v2.0）

**做卡时选择游戏机制模板，必须先检查预设兼容性。** 模板库已按P0-P3分级：

| 等级 | 含义 | 依赖项 | 使用条件 |
|------|------|--------|----------|
| 🟢 P0 | 纯文本通用 | 无 | 任何预设都能用，优先选择 |
| 🟡 P1 | 格式依赖 | 常见格式规则 | 低风险，大多数预设兼容 |
| 🟠 P2 | 功能依赖 | constant:true等 | 中风险，需确认预设支持 |
| 🔴 P3 | 脚本依赖 | MVU/getMessageVar | 高风险，仅在确认预设开启MVU时使用 |

**19个模板的兼容性分布**：17个P0🟢、1个P1🟡、1个P3🔴（变量追踪脚本）

**决策树**：
```
做卡需要游戏机制？
├─ 状态栏/好感度/NPC行动/风险检测/心理操控/道具进化/旁白/开场白/特征库/BAD END
│   └─ 全部P0🟢，直接用
├─ 事件驱动系统
│   └─ 用纯文本种子库模式（P0🟢），不要用变量触发模式（P3🔴）
└─ 变量追踪/预处理脚本
    └─ 确认预设开启MVU？是→用P3模板；否→降级为纯文本阶段描述
```

**降级方案**：变量追踪→阶段行为描述；脚本触发→纯文本种子库；正则格式→方括号格式；变量阈值→行为描述

详见 `references/game-mechanics-template-library.md` 的预设兼容性速查表。

## ⚠️ 设计哲学选择：修复冲突 vs 删除机制（2026-07-09 用户明确指示）

**当角色卡的机制（变量系统、UpdateVariable、预处理脚本等）与用户使用的预设有大量冲突时，优先考虑删除这些机制，而非添加兼容覆盖条目。**

示例玄幻项目的教训：87条目/582KB中，变量追踪系统（getvar/setvar脚本、UpdateVariable标签、预处理脚本）占了大量条目和token，但：
- 预设MVU模块全部OFF → UpdateVariable是死代码
- 预设的正则和规则会覆盖system_prompt中的指令 → 兼容覆盖条目效果不可靠
- 每个预设的冲突点不同 → 不可能写一个通用的兼容覆盖条目

**决策树**：
```
变量/脚本机制与预设冲突？
├─ 是 → 该预设是否支持MVU/变量系统？
│   ├─ 支持 → 保留变量系统，按预设要求调整格式
│   └─ 不支持 → 删除变量系统，改为纯文本描述型规则
│       └─ 用世界书常驻条目描述"堕落度/阶段/风险"的概念和行为模板
│          （AI靠自然语言理解"堕落度>=50"，不靠脚本检测）
└─ 否 → 保留变量系统
```

**删除后的替代方案**：
- 预处理脚本 → 删除，阶段跃迁由AI根据剧情自然判断
- UpdateVariable标签 → 删除，数值变化由AI在叙事中体现
- 变量更新规则 → 保留为纯文本行为指南（"堕落度高时，角色会更主动"）
- 状态栏模板 → 保留，AI根据上下文自行填充数值（不精确但够用）
- 事件触发系统 → 改为故事种子库（enabled=False），AI可选触发

**优势**：
- 减少条目数和token负载（删除10-15个变量相关条目）
- 与任何预设都不冲突（纯文本规则被所有预设支持）
- 降低维护成本（不用逐个预设做兼容覆盖）

**何时保留变量系统**：
- 用户明确要求"精确数值追踪"
- 用户使用的预设支持MVU模块（如大型结构化卡预设）
- 角色卡与预设是配套设计的（不是通用卡）

## 伪代码 vs 实装代码的区别

| 维度 | 伪代码（自然语言） | 实装代码（<%_ _%>脚本） |
|------|-------------------|----------------------|
| 可靠性 | AI可能忽略或误判 | 每轮自动执行，100%可靠 |
| 变量读写 | "读取当前状态" | `getMessageVar('stat_data.X.Y', {defaults: 0})` |
| 条件检测 | "IF堕落度>=50" | `if(val >= 50) { setMessageVar(...) }` |
| 输出 | 无 | `<action_info>` 通知面板 |

## 脚本标签语法

```javascript
<%_
// JavaScript代码块（_表示去掉前后空白）
const val = Number(getMessageVar('stat_data.角色.变量', {defaults: 0}));
if (val >= threshold) {
  setMessageVar('stat_data.角色.变量', newVal);
  notifications.push('⚠️ 通知内容');
}
_%>
```

## ⚠️ Pitfall: typeof getMessageVar === 'undefined' 永远为false（2026-07-07 示例玄幻项目案例）

当 `getMessageVar` 带 `{defaults}` 参数时，变量不存在时返回 defaults 值，**不是 undefined**。所以 `typeof getMessageVar(...) === 'undefined'` 永远为 false，初始化代码永远不会执行。

```javascript
// ❌ 死代码：getMessageVar 有 defaults 时永远不返回 undefined
if (typeof getMessageVar('stat_data.天道种子') === 'undefined') {
  setMessageVar('stat_data.天道种子', {...});  // 永远不执行！
}

// ❌ 同样死代码：即使不传 defaults，ST 的 getMessageVar 也可能返回空字符串而非 undefined
if (typeof getMessageVar('stat_data.天道种子') === 'undefined') { ... }

// ✅ 正确：用标记变量判断是否已初始化
if (!getMessageVar('stat_data._天道种子_已初始化')) {
  setMessageVar('stat_data.天道种子', {...});
  setMessageVar('stat_data._天道种子_已初始化', true);
}
```

**检测方法**：搜索预处理脚本中所有 `typeof getMessageVar` 调用，逐一检查是否有 defaults 参数。如果有，该检查是死代码。

**实测影响（示例玄幻项目）**：天道种子初始化代码从未执行过。好消息是默认值0是合理的初始值，所以不影响运行——但代码意图没有正确落地。

## ⚠️ Pitfall: 级联变量更新的缓存基值问题（2026-07-07 示例玄幻项目案例）

当预处理脚本中有多个 if-block 写入同一个变量时，如果所有 block 都使用脚本开头读取的缓存值，后面的 block 会覆盖前面的写入。

**错误模式**：
```javascript
<%_
const wq_cruelty = Number(getMessageVar('stat_data.王启.暴虐冲动', {defaults: 0}));

if (wq_soul >= 30 && wq_nightmare < 1) {
  setMessageVar('stat_data.王启.噩梦等级', 1);
  setMessageVar('stat_data.王启.暴虐冲动', wq_cruelty + 12);  // 0+12=12 ✓
}
if (wq_soul >= 50 && wq_nightmare < 2) {
  setMessageVar('stat_data.王启.噩梦等级', 2);
  setMessageVar('stat_data.王启.暴虐冲动', wq_cruelty + 12);  // 0+12=12 ✗ 应该是24！
}
_%>
```

**问题**：如果灵魂损耗从0直接跳到70（极端情况），4个 block 都用同一个 `wq_cruelty=0`，每次写入都是 `0+12=12`，后面的覆盖前面的。

**正确模式**：每个 block 写入前重新读取当前值：
```javascript
if (wq_soul >= 30 && wq_nightmare < 1) {
  setMessageVar('stat_data.王启.噩梦等级', 1);
  let _cur = Number(getMessageVar('stat_data.王启.暴虐冲动', {defaults: 0}));
  setMessageVar('stat_data.王启.暴虐冲动', _cur + 12);
}
if (wq_soul >= 50 && wq_nightmare < 2) {
  setMessageVar('stat_data.王启.噩梦等级', 2);
  let _cur = Number(getMessageVar('stat_data.王启.暴虐冲动', {defaults: 0}));
  setMessageVar('stat_data.王启.暴虐冲动', _cur + 12);  // 现在正确读取了12
}
```

**检测方法**：搜索脚本中所有 `setMessageVar` 调用，检查同一变量是否被多个 block 写入，且这些 block 是否共享同一个缓存基值。

## 变量读写函数

| 函数 | 作用 | 示例 |
|------|------|------|
| `getMessageVar(path, {defaults})` | 读取消息级变量 | `getMessageVar('stat_data.王启.灵魂损耗', {defaults: 0})` |
| `setMessageVar(path, value)` | 写入消息级变量 | `setMessageVar('stat_data.王启.噩梦等级', 1)` |
| `getLocalVar(path)` | 读取本地变量 | `getLocalVar('系统核心名')` |
| `setLocalVar(path, value)` | 写入本地变量 | `setLocalVar('系统名', '读者')` |

## 预处理脚本条目结构

预处理脚本是常驻条目（`constant=True`），每轮对话开始前自动执行。结构：

1. **Step 1: 读取所有变量** — 用 `getMessageVar()` 批量读取当前状态
2. **Step 2: 变量初始化** — 首次运行时设置默认值
3. **Step 3: 阶段跃迁检测** — 按优先级（P0→P8）检测各条件
4. **Step 4: 输出通知** — 有变化时输出 `<action_info>` 面板

## UpdateVariable输出格式

```xml
<UpdateVariable>
<Analysis>
分析本轮剧情变化，列出需要更新的变量
</Analysis>
[
  {"op": "replace", "path": "/stat_data/王启/灵魂损耗", "value": 45},
  {"op": "replace", "path": "/stat_data/角色D/阶段", "value": "堕落"}
]
</UpdateVariable>
```

## 预处理脚本 vs 手动更新的分工

| 类型 | 谁负责 | 示例 |
|------|--------|------|
| 阈值跃迁（阶段/等级/进化） | 预处理脚本自动 | 噩梦升级、相机进化、阶段跃迁 |
| 数值变化（堕落度/损耗/次数） | AI在UpdateVariable中手动 | 亲密互动+堕落度、使用相机+损耗 |
| 布尔标志（事件触发） | 预处理脚本自动 | 烛龙警告、最终决战 |
