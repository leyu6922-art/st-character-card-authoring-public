> **历史/legacy 路线边界**：本文记录的是依赖 preset `ROUTE_STATE` / `ROUTE_STAGE=P#` 的外部软路由。它**不属于 native Greeting-title 阶段合同**，不得把 marker、HTML 注释或其 keys 直接复制进 native 生产卡。native 卡只使用完整 Greeting 标题精确绑定四包。

# 无变量阶段Marker路由：软状态胶囊、冲突裁决与v1.14清理模式

> **创建日期**：2026-07-18 · 艳母的荒唐赌约 v1.13→v1.14 实证
> **最后更新**：2026-07-18 · v1.14 全流程执行完成
> **架构定位**：无变量递进式卡 = 阶段Marker路由系统，不是持久变量状态机
> **关联文件**：progressive-worldbook-design.md、g-type-chinese-card-build-pitfalls.md、st-worldbook-triggering-behavior.md

---

## 1. 为什么需要这个模式

递进式世界书解决了"阶段隔离"问题后，仍有三个软污染源：

1. **核心字段泄漏**：`description/personality/scenario` 是常驻上下文——即使世界书隔离完美，这些字段提前写 P4-P6 内容，AI 首轮就"知道了"结局。
2. **Marker 漂移**：自然语言阶段标记（"当前阶段：P3"）可以被用户/AI 无意中触发——回忆旧阶段、讨论未来、闲聊都可能误命中。
3. **大条目泛key触发**：多主题大条目用泛词做 primary key，一次加载过多答案，且可能被不该命中的开场白触发。

无变量架构无法靠持久变量解决这些问题——但可以通过**软状态胶囊 + 冲突裁决 + 拆分降污染**大幅缓解。

---

## 2. 核心字段未来泄漏治理

### 2.1 问题

世界书隔离了 P0-P6 阶段条目，但 `description`/`personality`/`scenario` 是 ST 中始终存在的上下文。如果这些字段包含：

- 后期称呼（浪奴、192小时）
- 后期身份（骆鹏主人）
- 后期关系结论（谁最终压过谁）
- 完整故事链（P0→P6弧线）
- 结局方向
- 未来能力暗示（"后来会逐渐掌控规则"）

则 AI 在 P0 首轮就已经获得了全部剧情地图——阶段隔离形同虚设。

### 2.2 修复原则

#### description：只写跨阶段不变量

- ✅ 基础家庭背景、初始关系、外形辨识点
- ✅ 长期生活经历、人物稳定底色
- ✅ 初始矛盾和故事引擎的起点
- ❌ 后期称呼、后期控制关系、谁最终压过谁
- ❌ P4-P6 事件、完整故事链、结局方向
- ❌ "后来会逐渐……"类未来能力/关系暗示

**实证**：艳母 v1.13 description 含"浪奴""192小时""九局五胜"→ v1.14 删改为493字符的纯不变量版。

#### personality：只写人格发动机

- ✅ 核心需求、核心恐惧、防御机制、惯性误判
- ✅ 语言节奏、决策方式、面对压力的默认反应
- ❌ 完整阶段人格弧线（P0→P6递进变化应放在阶段条目中）
- ❌ 后期才出现的能力/关系/身份

**格式参考**：
```
【核心需求】……
【核心恐惧】……
【防御机制】……
【惯性误判】……
【语言节奏】……
【决策方式】……
```

#### scenario：写轻剧情 + 玩法协议

- ✅ 基础背景、故事引擎
- ✅ 阶段路由机制说明（ROUTE_STAGE=P#）
- ✅ 玩法协议（事件种子按需启用、NPC自主但不得跨阶段）
- ✅ 阶段概述（P0-P6一句话定位，但不写具体结局）
- ❌ 完整 P0-P6 剧情梗概、具体事件细节

### 2.3 泄漏审计检查项

不只是搜专有名词——还要检查六类泄漏：

| # | 泄漏类型 | 示例 | 检查方法 |
|---|---------|------|---------|
| 1 | 专有名词 | P6、浪奴、192小时 | 关键词匹配 |
| 2 | 后期身份 | "骆鹏主人""协议承受者" | Pattern: 后期角色定位词 |
| 3 | 后期能力 | "后来会逐渐掌控规则" | 未来时间副词+能力描述 |
| 4 | 后期动机 | "最终目的是反击" | 结局指向性动词语句 |
| 5 | 后期关系结论 | "赵勇最终退出竞争" | 关系终点判断句 |
| 6 | 结局方向 | "走向公开""沦为玩物" | 故事弧线终点描述 |

---

## 3. ROUTE_STATE 软状态胶囊

### 3.1 格式

在每条 greeting 开头插入 HTML 注释（约100字符）：

```html
<!--
ROUTE_STATE
ROUTE_STAGE=P1
ROUTE_EVENT=NONE
ROUTE_SCENE=刘宇家-客厅
ROUTE_NOTE=第一赌约与赵勇征服入口
-->
```

### 3.2 规则

1. 每条 greeting 只能有一个 `ROUTE_STAGE=P#`
2. `ROUTE_STAGE` 使用独立格式（区别于自然语言"当前阶段：P#"）
3. 事件 marker (`ROUTE_EVENT`) 可选，不强制每轮自动更新——无变量架构无法保证传递链
4. `ROUTE_STAGE` 与原有 `当前阶段：P#` 不得互相矛盾
5. v1.14 保留旧标记兼容，v1.18 可评估是否移除自然语言阶段 key

### 3.3 自动生成方法

```python
def detect_stage(text):
    m = re.search(r'当前阶段[：:]\s*P(\d)', text)
    if m:
        return f"P{m.group(1)}"
    # fallback: detect from content keywords
    if '火玫瑰' in text and '第一赌约' not in text: return 'P0'
    if '赵勇征服' in text: return 'P1'
    if '新赌约' in text or '三男' in text: return 'P2'
    if '温泉' in text: return 'P3'
    if '九局五胜' in text or '浪奴' in text: return 'P4'
    if '违约' in text: return 'P5'
    if '192小时' in text: return 'P6'
    return 'P0'
```

---

## 4. 阶段路由冲突裁决（OOC）

### 4.1 问题

同时出现多个阶段标记的可能来源：
- 旧 greeting 的 ROUTE_STATE
- 用户新输入的 ROUTE_STAGE
- 模型状态栏中的阶段名
- 回忆/讨论旧阶段
- 世界书条目内容中引用的阶段名

### 4.2 OOC 裁决规则

在 OOC 常驻条目（id=0）中加入：

```
【阶段路由裁决】
本卡是无变量阶段Marker路由系统，不是持久变量状态机。
AI每轮优先读取最近一条ROUTE_STATE胶囊或用户明确输入的ROUTE_STAGE=P#。
同一轮若出现多个阶段标记：
1. 用户本轮明确输入的ROUTE_STAGE优先；
2. 其次采用最近一条ROUTE_STATE；
3. 若无法判断最新阶段，保持上一轮阶段，不得自动跳阶段；
4. 回忆、讨论、规划中的未来阶段名不视为阶段切换；
5. 世界书若同时加载多个阶段条目，AI只执行最新ROUTE_STAGE对应阶段，其余视为背景噪音并忽略。
```

### 4.3 限制声明

此裁决是**软规则**——ST 触发层无法真正“最新优先”，这只是让 AI 倾向于遵守的 Prompt 指令。不要宣传为强变量系统。长对话后 Marker 可能漂移，需 v1.18 实测验证。

---

## 5. 大条目拆分模式：主体/响应/余波

### 5.1 触发条件

当某个条目同时满足以下条件时，必须拆分：
- 多主题（内容含≥3个【章节】段）
- 泛 key（如"沙发""赤裸""卧室"等通用词）
- 被多个 greeting 同时命中
- 一次性给模型过多答案（一次加载后事件无需推进）

### 5.2 拆分为三条事件包

```
事件包·PX-E0N·XX主体       → 前置条件、事件起点、推进阶梯(3-4拍)、干预窗口、状态变化
事件包·PX-E0N·用户响应矩阵  → 配合/拒绝/沉默/超阶段
事件包·PX-E0N·事件余波      → 当晚/次日/关系残留/外部残留/下一次见面钩子
```

**不拆成严格串联 A/B/C 状态机**——无变量架构无法保证 A→B→C 自动传递。

### 5.3 Key 策略

- 使用专属事件 marker：`事件节点：P1-E03`、`P1-E03`、`XX事件`
- **禁止**用普通人物名/地点名/家具名做大型事件的 primary key
- 全部 `selective=true` + `secondary_keys=[ROUTE_STAGE=P#, 当前阶段：P#]`
- 全部 `enabled=false`（用户手动启用或通过事件 marker 触发）
- 原条目禁用并标注 `[v1.14已废弃·拆分到idXX-XX]`

### 5.4 实证：艳母 ID 67

| 维度 | v1.13（问题） | v1.14（修复） |
|------|-------------|-------------|
| keys | `['沦陷', '阵地', '三个选择', '赤裸', '沙发']` | 拆为三条独立事件包 |
| selective | top=False, ext=True ❌ | top=True, ext=True ✅ |
| secondary_keys | `[]` ❌ | `['ROUTE_STAGE=P1', '当前阶段：P1']` |
| content | 1065 chars 多主题大条目 | 主体(~900)+响应(~600)+余波(~700) |
| enabled | true（自动触发）❌ | false（手动/事件marker触发）✅ |

---

## 6. 场景公共模板抽离

### 6.1 问题

多个场景条目重复相同结构：安全等级、视觉/听觉/触觉/嗅觉、在场/不在场、伪装恢复。这些应该是一条全局规则，而非每个场景复制一遍。

### 6.2 方案

新增一条常驻低负载条目（`keys=[]`, `constant=true`, `position=after_char`）：

```
场景写作总则·风险等级与空间逻辑
```

内容包含：
- **A/B/S 风险等级定义**（私密/过渡/半公开）
- **感官描写原则**（每处感官至少服务一个叙事目的）
- **空间行为规则**（禁止瞬移、禁止无原因跳结果、转场必须有动作依据）
- **在场与不在场规则**
- **场景余波与伪装恢复**

### 6.3 场景条目瘦身后只保留独有内容

公共部分抽离后，每个场景只写：
- `【空间拓扑】` 门/窗/走廊/楼梯/遮挡关系
- `【进入与离开路径】` 谁可能从哪里出现
- `【固定声音】` 电梯/门铃/脚步/空调/车辆/水声
- `【容易留下的痕迹】` 物品移动/聊天记录/衣物/监控/邻居印象
- `【该阶段的心理意义】` 同一地点在不同阶段意味着什么
- `【场景可供性】` 角色在这里自然能做哪些行动
- `【转场出口】` 能自然转到哪些下一地点

---

## 7. 验证结果分层

验证报告必须分三类（不要把所有问题都叫 Error）：

| 层级 | 含义 | 示例 |
|------|------|------|
| **Schema Error** | 真正结构错误 | JSON/字段缺失/ID重复/spec错误/selective不一致 |
| **Runtime Risk** | 可能影响跑卡 | 泛词触发大条目/多阶段同时命中/事件缺阶段secondary/首轮负载异常 |
| **Quality Gate** | 项目质量标准 | greeting长度/人物厚度/场景厚度/关系厚度/事件包完整性/模板重复 |

**Quality Gate 项 delay 规则**：v1.14 可记录不阻断，但必须分配后续版本号（v1.15/v1.16/v1.17）。

---

## 8. v1.14 清理模式标准流程

从递进式卡执行 v1.14 清理的完整步骤：

### Step 1: 备份与基础解析
- 统计：文件大小、条目数、enabled/disabled/constant/selective、addMemo、spec、顶层同步

### Step 2: Schema/字段回退
- spec/spec_version 双写、顶层←data 同步、addMemo 补齐、selective 一致修复
- match_whole_words=false, use_regex=true, ID 重排 0..N-1
- 配角条目 disabled→enabled+selective+stage secondary

### Step 3: 核心字段去后期泄漏
- description→不变量, personality→人格发动机, scenario→轻剧情+协议

### Step 4: ROUTE_STATE 软胶囊
- 每条 greeting 增加 capsule、OOC 增加冲突裁决、关系/场景 secondary 增加 ROUTE_STAGE

### Step 5: 大条目拆分
- 识别多主题泛key条目 → 拆为主体/响应/余波（专属事件 marker + selective + disabled）

### Step 6: 场景公共模板
- 新增「场景写作总则」常驻条目（keys=[]），场景条目瘦身只留独有内容

### Step 7: greeting 修复
- 低于 1400 字符的 greeting 非灌水补写（原文场景+对白+用户干预点）

### Step 8: 验证 + 报告
- validate_card.py（Schema Error=0）
- audit_worldbook_triggers.py（硬风险=0）
- enrichment_self_check.py（记录延迟项）
- 生成修改报告 + 审计报告

### 验收门槛

| 指标 | v1.14 目标 |
|------|-----------|
| Schema Error | = 0 |
| 硬触发风险 | = 0 |
| 核心字段未来词 | = 0 |
| greeting ≥1400 短缺 | = 0 |
| selective 不一致 | = 0 |
| match_whole_words=true | = 0 |
| ID 不连续 | = 0 |
| 关系/场景薄 | v1.14 记录，v1.15-v1.17 修复 |
| 长对话稳定 | v1.18 验证 |

---

## 9. 关键 Pitfalls

| ID | Pitfall | 触发条件 | 修复 |
|----|---------|---------|------|
| P201 | 核心字段泄漏 | description/personality/scenario 含 P4-P6 词 | 重写为不变量+人格发动机+轻剧情协议 |
| P202 | 泛 key 触发大条目 | "沙发""赤裸"加载 1000+ 字 | 禁用原条目+拆分为事件包+专属 marker |
| P203 | selective 不一致 | top=False 但 ext=True | 双写同步 |
| P204 | 场景模板重复 | 每个场景复制相同安全等级规则 | 抽离为常驻「场景写作总则」(keys=[]) |
| P205 | greeting 无阶段标记 | 首轮无法路由到正确阶段 | 增加 ROUTE_STATE 软胶囊 |
| P206 | Marker 漂移 | 多阶段标记同时出现 | OOC 冲突裁决规则（软方案） |
| P207 | addMemo 缺失 | 世界书在 ST 中不链接 | 补齐顶层 addMemo（双重写入） |
| P208 | ID 不连续 | 拆分/新增导致跳号 | 重排 0..N-1 + display_index 同步 |
| P209 | top.alternate_greetings 为空 | ST 只读取 data 层 | 从 data 同步到顶层 |
| P210 | MSYS path 问题 | `<USER_HOME>` 被译为 `<WINDOWS_PATH>` | 用 execute_code + Windows 绝对路径跑脚本 |
