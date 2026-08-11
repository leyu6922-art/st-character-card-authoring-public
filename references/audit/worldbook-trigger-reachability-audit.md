# 世界书触发可达性审计（Worldbook Trigger Reachability Audit）

> 适用：所有 SillyTavern 角色卡/世界书，尤其是用户质疑“绿灯条目是否真的能触发”时。
> 来源：2026-07-15 校园示例卡守护卡实测 + ST v1.18 `world-info.js` 源码确认 + 大型结构化卡 v4.2 结构分析。
> 配套自动化：`scripts/validate_card.py` v4.8+。

---

## 0. 源码级触发事实（ST v1.18）

来自 `world-info.js`：

```js
// primary key 必须先命中
let primaryKeyMatch = entry.key.find(key => buffer.matchKeys(textToScan, key, entry));
if (!primaryKeyMatch) continue;

const hasSecondaryKeywords = (
    entry.selective &&
    Array.isArray(entry.keysecondary) &&
    entry.keysecondary.length // ignore empties
);

if (!hasSecondaryKeywords) {
    activatedNow.add(entry); // secondary为空时，primary-only触发
    continue;
}
```

**结论**：

1. **真实触发源是 chat history**：当前 greeting、用户消息、AI 回复。不要假设 ST UI 绿点=已进入 `<Lore>`。
2. **顶层 `selective` 才参与触发**：ST 字段映射是 `selective -> selective`；`extensions.selective` 只是我们格式里的兼容副本，单独存在时不会启用副关键词 AND 逻辑。
3. **`secondary_keys` 只有在 `selective=true` 且数组非空时才参与匹配**。
4. **`selective=true` 但 `secondary_keys=[]` 不会死触发**，会退化为 primary-only。这是大型结构化卡大量条目的正常模式；但若用于 G 型身份隔离，则不够安全。
5. **默认 `selectiveLogic=0` = AND_ANY**：任一 primary 命中 + 任一 secondary 命中。
6. ST 支持 `/regex/flags` 形式的 key，正则 key 会绕过普通大小写/整词匹配设置。

---

## 1. 审计目标

世界书触发设计要同时避免三类问题：

| 问题 | 表现 | 后果 |
|---|---|---|
| 漏触发 | 需要的条目没有进入 `<Lore>` | AI缺素材、角色/场景变薄 |
| 误触发 | 不相关条目被泛 key 拉进 `<Lore>` | token膨胀、无关信息污染 |
| 过触发 | 首轮/某个 greeting 触发条目太多 | 截断、回复变短、规则互相覆盖 |

---

## 2. 设计前置：给每个条目声明“触发意图”

写条目时不要先随手填 keys。先在计划书/条目表里声明：

| 触发意图 | 典型条目 | 推荐字段 |
|---|---|---|
| 常驻规则 | OOC、文风、状态栏、反顺从 | `constant=true, keys=[]` |
| 首轮必载 | 当前开场白所需核心角色/场景 | primary key 必须自然出现在对应 greeting |
| 人物按需 | 角色档案、语言指纹 | 角色专名 primary；通常不需要 secondary |
| 场景按需 | 房间/地点/公共场所 | 地点专名 primary；通用子地点用 secondary 限定上级范围 |
| 阶段按需 | 堕落阶段、守护阶段、事件阶段 | 阶段短语 primary，或 selective + 阶段/场景 secondary |
| 手动事件种子 | 可选剧情事件 | `enabled=false`，由玩家/作者手动启用或后续流程激活 |
| G型选开身份 | {{user}}身份定义 | `constant=true, enabled=false`，玩家手动 toggle |
| G型greeting身份 | 视角段 | `selective=true + secondary_keys` 与 greeting 首行身份词精确对齐 |

---

## 3. 大型结构化卡给我们的触发设计启发

大型结构化卡 v4.2 的世界书不是简单“堆关键词”，而是三层触发策略：

### 3.1 唯一专名：primary-only

适合全局唯一概念：

```text
[种族-霜巨人] keys=['霜巨人'], secondary=[]
[诺斯加德联盟-总览] keys=['诺斯加德','白曜城','北境'], secondary=[]
```

这类词本身足够独特，primary-only 可以接受。

### 3.2 范围绑定：primary + secondary

适合容易重名/泛化的地点、区域、组织：

```text
[诺斯加德联盟-城镇-凛风渡-下城区]
keys=['下城区']
secondary_keys=['凛风渡']
selective=true
```

意思是：只在“凛风渡 + 下城区”同时出现时触发，而不是任何城市的“下城区”都触发。

迁移到我们的卡：

```text
❌ keys=['家']
✅ keys=['客厅','卧室','浴室'], secondary_keys=['比企谷家'], selective=true

❌ keys=['学校']
✅ keys=['五楼空教室','体育馆更衣室','值班室'], secondary_keys=['校园示例卡'], selective=true
```

### 3.3 模块开关：enabled=false

DLC事件/扩展默认禁用，不让它们靠泛词乱进 prompt。我们的事件种子库也应如此：

```text
enabled=false
comment='事件种子：某场景'
content='触发条件 + 分段事件模板'
```

### 3.4 分段标记：组织结构，不参与触发

大型结构化卡用 `➡️系统开始/结束`、`➡️种族开始/结束` 等空条目作为世界书书签。大型卡可借鉴，但这些条目必须低内容/低token，且不承担剧情触发。

---

## 4. 审计流程

### Step 1：结构概览

统计：

- 总条目数
- `constant=true` 常驻条目数
- `enabled=true/false` 数量
- `selective=true` 数量
- 有 `secondary_keys` 但顶层 `selective!=true` 的条目
- 顶层 `selective` 与 `extensions.selective` 不一致的条目
- 单字/泛词 primary key 条目
- 多主题大条目

### Step 2：逐个 greeting 模拟真实初始触发

每个 `first_mes` / `alternate_greetings[i]` 都是独立会话入口，必须分别模拟。

源码对齐伪代码：

```python
def match_entry(entry, text):
    if entry.constant or not entry.enabled:
        return False

    primary_hits = [k for k in entry.keys if match_key(k, text)]
    if not primary_hits:
        return False

    # ST只看顶层selective；secondary为空时退化为primary-only
    secondary_keys = [k for k in entry.secondary_keys if k]
    if entry.selective is True and secondary_keys:
        secondary_hits = [k for k in secondary_keys if match_key(k, text)]
        if entry.selectiveLogic == 0:  # AND_ANY
            return bool(secondary_hits)
        if entry.selectiveLogic == 3:  # AND_ALL
            return len(secondary_hits) == len(secondary_keys)
        if entry.selectiveLogic == 2:  # NOT_ANY
            return not secondary_hits
        if entry.selectiveLogic == 1:  # NOT_ALL
            return len(secondary_hits) < len(secondary_keys)

    return True
```

输出每个 greeting：

- 触发条目列表
- 命中的 primary key
- 命中的 secondary key
- 常驻+触发总 token 估算
- 是否仅由泛 key 命中

### Step 3：反证测试

额外用“普通聊天句”测试泛 key：

```text
我要回家。
学校今天很安静。
老师让我去教室。
有人在房间里唱歌。
你看见那个人了吗？
```

任何条目只靠 `家/学校/老师/人/你/唱歌/房间` 这类词触发，都要视为高风险。

### Step 4：按问题类型修复

| 类型 | 判定 | 处理 |
|---|---|---|
| 正常触发 | 专名/目标场景词在目标 greeting 中出现 | 保留 |
| 泛 key 误触发 | 仅靠 `家/人/你/学校/老师` 等命中 | 删除泛 key，改专名/复合短语 |
| 副关键词无效 | 有 `secondary_keys` 但顶层 `selective=false` | 清空副词或开启顶层 selective |
| extensions-only selective | 只有 `extensions.selective=true` | 补顶层 `selective=true` |
| 首轮死触发 | 期望首轮可用但所有 greeting 均不触发 | 把 key 写入对应 greeting 或改 key |
| 中后期触发 | 后续聊天自然会出现，不要求首轮加载 | 保留并备注设计意图 |
| 整包误加载 | 一个条目多个主题，任一 key 加载全部 | 拆条目或 selective 限定 |
| 过触发 | 某 greeting 触发负载 > 8000 tokens | 精简常驻、拆分、调整 key |

---

## 5. 关键词设计规则

### 5.1 primary key 只放“能独立代表条目”的词

可以：

```text
雪之下雪乃 / 由比滨结衣 / 校园示例卡更衣室 / KTV包间 / 比企谷家
```

谨慎：

```text
体育馆 / 唱歌 / 教室 / 老师 / 学校
```

禁止：

```text
家 / 人 / 你 / 我 / 他 / 她
```

以及**场景类泛词**（即使单独看像"自然词"，但几乎所有 greeting/聊天都会出现）：

```text
卧室 / 客厅 / 浴室 / 洗手间 / 天台 / 顶楼 / 走廊 / 门口
商场 / 广场 / 酒店 / 餐厅 / 教室 / 办公室 / 学校
墓地 / 墓碑 / 公园 / 花园 / 阳台
```

修复方案：用**复合地点名**替代单字泛词：
- ❌ `keys=['卧室','客厅','浴室']`
- ✅ `keys=['南山别墅卧室','南山别墅客厅','齐家浴室']`
- 或 `range-bind`：`keys=['卧室','客厅'], secondary_keys=['南山别墅'], selective=true`

> 2026-07-16 绿帽快餐卡实证：场景条目用了 `keys=['卧室','客厅','浴室','洗手间']` → 所有greated都含这些词 → 首轮全部误触发。修复后所有场景key改用专名复合短语（`南山别墅卧室` / `酒店天台` / `齐天家`）。

### 5.2 secondary key 用来做“范围绑定”，不是备注

正确：

```text
keys=['客厅','卧室']
secondary_keys=['比企谷家']
selective=true
```

错误：

```text
keys=['雪乃']
secondary_keys=['黑发','过膝袜']
selective=false  # 副词被忽略
```

### 5.3 多主题条目不要共享一组 keys

错误：

```text
配角+NTR角色威胁档案
keys=[优美子, 姬菜, 户部, 叶山, 黑人, 老师]
```

建议：

```text
优美子+姬菜档案
户部翔威胁档案
叶山隼人威胁档案
黑人群体威胁档案
平冢老师风险档案
```

---

## 6. 自动化门控

### 6.1 快速阻断：validate_card.py

`validate_card.py` v4.8+ 已覆盖：

- 源码对齐触发模拟：顶层 selective、selectiveLogic、secondary 空数组退化 primary-only、regex key、大小写/整词近似。
- 泛 key error。
- 每个 first_mes/alternate 的触发负载报告。
- `secondary_keys` + 顶层 `selective=false` warning。
- `extensions.selective=true` 但顶层 `selective!=true` error。
- 普通 selective 卡不会被误判为 G 型；只有 greeting 首行含身份/视角标记时才跑 G 型专项。
- 多主题大条目 warning。
- 仅靠泛 key 命中的误触发 error。

交付前必须查看这些输出，不能只看 `passed=True/False`。

### 6.2 交接/修卡报告：audit_worldbook_triggers.py

当需要给用户或另一个窗口交接世界书触发问题，或准备正式修卡前，运行：

```bash
python scripts/audit_worldbook_triggers.py <卡.json> -o <世界书触发审计报告.md>
```

输出内容：
- 总览：条目数、常驻数、selective/secondary风险数。
- 每个 `first_mes/alternate` 的触发条目和 token 估算。
- 风险条目清单：硬泛key、secondary被忽略、extensions.selective单独生效误判、多主题大条目。
- 逐条触发矩阵：每个 greeting 命中了哪些 primary/secondary。
- 普通句反证测试：如“我要回家”“有人在房间里唱歌”会不会误触发。
- 下一步修复建议。

`validate_card.py` 用于阻断结构/硬错误；`audit_worldbook_triggers.py` 用于生成可阅读的 Markdown 审计报告。两者互补。


---

## 7. 报告格式

```markdown
## 世界书触发审计

| ID | 条目 | 触发意图 | keys | secondary | selective | first_mes | alt1 | alt2 | 判定 | 建议 |
|---:|---|---|---|---|:--:|---|---|---|---|---|
| 10 | 场景·比企谷家 | 场景按需 | 家/比企谷家 | 客房 | false | 误触发(家) | 误触发(家) | - | 🔴 | 删除“家”，改范围绑定 |
```

最后给出：

- 能正常触发的条目
- 误触发条目
- 副关键词无效条目
- extensions/top-level selective 不一致条目
- 死触发/中后期触发条目
- token 负载是否过高

---

## 铁律

**绿灯≠触发；启用≠加载；secondary_keys≠自动生效；extensions.selective≠顶层selective。**

每张卡交付前都必须做触发可达性/误触发审计。
