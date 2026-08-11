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
