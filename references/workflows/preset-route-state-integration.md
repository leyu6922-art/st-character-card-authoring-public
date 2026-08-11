> **外部 preset 路线，不是 native 合同**：本页仅用于真实接入 Author’s Note / preset `ROUTE_STAGE` 的项目。native Greeting-title 生产卡不得复制这些 marker 或将其写入 `stage-entry-contract.json`。

# 预设 route_state 集成工作流

> **状态**：2026-07-19 · 艳母的荒唐赌约 v1.17.2 "推荐预设自动路由版"首次实施
> **核心问题**：角色卡依赖 `<route_state>` 标签维持阶段路由，但用户预设可能吞掉状态栏或忽略标签输出要求。需要修改预设本身，让它在每轮回复中自动输出 `<route_state>`。
> **本方案**：对现有 ST 预设做最小改动（新增变量 + 提示词 + Core 插槽 + 显示隐藏 regex），使其与角色卡的 route_state 路由系统协同工作。

---

## 1. 适用场景

当角色卡使用 **推荐预设自动路由版** 的 route_state 阶段路由系统（见 `an-single-authority-stage-routing.md` 的替代方案）时，需要配套预设支持：

1. 推荐预设每轮自动在正文前输出 `<route_state>\nROUTE_MODE=PRESET\nROUTE_STAGE=P#\n</route_state>`
2. 该标签被 ST 扫描，命中世界书阶段条目
3. 该标签在界面上被隐藏，不影响用户阅读

---

## 2. 预设结构预览（三人逆行 v10.0 为例）

```json
{
  "prompts": [...],           // 250+ 提示词
  "extensions": {
    "regex_scripts": [...],    // 41 条 regex — 注意位置！
    "SPreset": {...},
    "tavern_helper": {...}
  }
}
```

### ⚠️ 关键结构发现（2026-07-19 实证）

| 预期位置 | 实际位置 | 影响 |
|---------|---------|------|
| `data["regex_scripts"]` 顶层 | `data["extensions"]["regex_scripts"]` | 顶层 get 返回 None，新 regex 写到错误位置 |
| regex id 为数字自增 | id 为 **UUID 字符串** | 用 int 自增会报 `max() arg is empty`；必须用 `str(uuid.uuid4())` |

---

## 3. 最小修改清单

总共 4 类改动，**不动原始预设的大模块**（文风/NSFW/思维链/aftertalk/summary）：

### 3.1 变量初始化（prompts[3] 变量组）

追加 `{{setvar::route_state_top::}}` 到变量清空行。

```text
原始：{{setvar::status_top::}}{{setvar::user_role::}}...
修改后：{{setvar::route_state_top::}}{{setvar::status_top::}}{{setvar::user_role::}}...
```

**为什么用 route_state_top 而非 status_top**：status_top 已被预设的日期卡片/变量组占用，抢用会破坏其他功能。

### 3.2 新增 route_state 提示词（Core 前）

新增一个 enabled=true, role=system 的提示词：

```
名称：🧭丨艳母 route_state 自动路由
位置：Core（包含 ### 正文 + {{getvar::status_top}}）的前一个索引
内容：{{setvar::route_state_top::\n<route_state_rule>\n10条自动路由规则...\n</route_state_rule>\n}}
```

10 条规则：

1. ROUTE_STAGE 必须是 P0-P6 之一
2. 默认沿用最近一条有效 <route_state> 中的 ROUTE_STAGE
3. 如果是开场，沿用 greeting 中的 <route_state>
4. 只有用户用自然语言明确要求切阶段时，才改变 ROUTE_STAGE
5. 切阶段从下一轮世界书开始稳定生效
6. AI 不得自行跳阶段
7. 不要输出多个 ROUTE_STAGE
8. 不要把 route_state 写成 HTML 注释
9. 不要加入 ROUTE_SCENE/ROUTE_HINT/自然语言
10. route_state 是机器锚点，不让角色朗读

### 3.3 Core 插槽修改

在 `### 正文` 段中，`{{getvar::status_top}}` **前**插入 `{{getvar::route_state_top}}`：

```text
### 正文
{{getvar::route_state_top}}      ← 新增
{{getvar::status_top}}            ← 保留（不要删除）
{{getvar::ui_anti_empty}}
{{getvar::Manual}}
${正文...}
```

注意：route_state_top 必须在 status_top 之前，因为 route_state 需要先输出。

### 3.4 新增显示隐藏 regex

新增一条 regex，作用是：**隐藏界面显示，不影响 outgoing prompt**。

```json
{
  "id": "uuid新生成",
  "scriptName": "route_state-显示隐藏",
  "disabled": false,
  "promptOnly": false,       // 关键：false = 只影响显示，不影响 outgoing prompt
  "findRegex": "/<route_state>[\\s\\S]*?<\\/route_state>/g",
  "replaceString": "",
  "placement": [],
  "runOnEdit": true
}
```

**为什么 promptOnly=false**：这个 regex 的作用是隐藏 `<route_state>` 标签不让用户看到，但标签仍然存在于聊天消息原文中。ST 对 outgoing prompt 的处理流程是：
- promptOnly=false → regex 只影响前端渲染，不影响发往 AI 的消息
- promptOnly=true → regex 影响发往 AI 的消息（会删掉标签，导致阶段路由失效）

所以我们的 route_state 标签必须：
1. 在 outgoing prompt 中保留 → ST 能扫描到 → 触发世界书
2. 在界面显示中隐藏 → 用户阅读体验不变

### 3.5 保留原模块（重要）

| 原模块 | 做法 | 原因 |
|--------|------|------|
| `HTML注释-去除` regex | **不动** | 预设依赖它清理思维链/Prism 注释，关闭会改变原体验。我们的 route_state 已不用 HTML 注释，不冲突 |
| 文风系统 | 不动 | 不改变预设的写作风格 |
| NSFW 模块 | 不动 | 不改变预设的成人内容处理 |
| 思维链主体 | 不动 | 不改变预设的思考方式 |
| aftertalk/summary | 不动 | 不改变预设的后处理 |

---

## 4. 实施步骤

### 4.1 文件操作

```bash
# 1. 复制原预设
cp "原预设.json" "原预设_艳母推荐预设自动路由版.json"

# 2. Python 修改
python modify_preset.py    # 见下文
```

### 4.2 Python 修改脚本关键逻辑

```python
import json, shutil, uuid

# 复制
shutil.copy2(SRC, DST)
with open(DST, encoding="utf-8") as f:
    data = json.load(f)

prompts = data["prompts"]

# 1. 变量组添加 route_state_top（prompts[3]）
prompts[3]["content"] = prompts[3]["content"].replace(
    "{{setvar::status_top::}}",
    "{{setvar::route_state_top::}}{{setvar::status_top::}}"
)

# 2. 插入 route_state 提示词（Core 前）
core_idx = 234  # 找到 Core 的实际索引
route_state_prompt = {
    "name": "🧭丨艳母 route_state 自动路由",
    "enabled": True,
    "role": "system",
    "content": "{{setvar::route_state_top::\n<route_state_rule>\n...\n</route_state_rule>\n}}"
}
prompts.insert(core_idx, route_state_prompt)

# 3. Core 插槽修改
core = prompts[core_idx + 1]  # 因为插入后 Core 索引 +1
core["content"] = core["content"].replace(
    "{{getvar::status_top}}",
    "{{getvar::route_state_top}}\n    {{getvar::status_top}}"
)

# 4. 新增 regex（注意：在 extensions.regex_scripts 下，非顶层）
regex_list = data["extensions"]["regex_scripts"]
regex_list.append({
    "id": str(uuid.uuid4()),
    "scriptName": "route_state-显示隐藏",
    "disabled": False,
    "promptOnly": False,
    "findRegex": "/<route_state>[\\s\\S]*?<\\/route_state>/g",
    "replaceString": "",
    "placement": [],
    "runOnEdit": True,
    # ... 其他字段从现有 regex 复制
})
data["extensions"]["regex_scripts"] = regex_list

with open(DST, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

### 4.3 验证清单

修改后检查 JSON 内：

```text
[✅] prompts 总数 = 原数 + 1
[✅] prompts[3] content 含 {{setvar::route_state_top::}}
[✅] route_state 提示词存在且 enabled=true
[✅] Core prompt 中 {{getvar::route_state_top}} 在 {{getvar::status_top}} 之前
[✅] regex_scripts 总数 = 原数 + 1
[✅] 新增 regex 的 promptOnly=false
[✅] HTML注释-去除 保持原状（未修改）
```

---

## 5. 实机测试清单

导入修改版推荐预设后测试：

| 测试 | 操作 | 预期 |
|------|------|------|
| T1 普通发送 | 发普通消息 | AI 回复 raw 中有 `<route_state>\nROUTE_MODE=PRESET\nROUTE_STAGE=P#\n</route_state>` |
| T2 第二轮续航 | 发"继续" | route_state 保留同阶段 |
| T3 未来词 | P1 中讨论 P6 词 | route_state 仍 P1，P4/P6 不触发 |
| T4 切阶段 | "切到 P2" | 本轮输出 ROUTE_STAGE=P2，下一轮 P2 触发 |
| T5 Swipe/Regen/Cont | 摩擦操作 | 均输出 route_state |
| T6 界面检查 | 查看聊天 | `<route_state>` 标签在界面上不可见 |

---

## 6. 已知限制

| 限制 | 说明 |
|------|------|
| 只保证推荐预设下自动续航 | 换其他预设后 route_state 可能不输出，需改用 AN 权威版 |
| 切阶段需一轮延迟 | 本轮输出新 ROUTE_STAGE，ST 下一轮才扫描到，世界书才切换 |
| 依赖 Core 插槽位置 | 如果预设的 Core 结构大幅改动，插槽位置需重新适配 |
| 不兼容 AN 混用 | 推荐预设版和 AN 权威版不能在同一个聊天中同时使用 |

---

## 7. 发布说明模板

```text
推荐搭配本预设使用。本预设会自动输出 <route_state> 机器状态块，
用于维持世界书阶段触发。

请将 World Info → Minimum Activations 设置为 0。
不要在同一聊天里同时使用 Author's Note ROUTE_STAGE。

如果使用其他预设，请改用 v1.17.1a AN 权威版（附链接）。
```
