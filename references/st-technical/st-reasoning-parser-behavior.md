# SillyTavern Reasoning Parser 行为分析（ST 1.18.0 实测）

## 核心发现

### 1. 字面量匹配，不是正则

ST的reasoning解析器使用JavaScript的 `startsWith()` 和 `indexOf()` 做字面量匹配，**不支持正则表达式**。

```javascript
// reasoning.js 第480行
if (parseTarget.startsWith(power_user.reasoning.prefix) && parseTarget.length > power_user.reasoning.prefix.length) {
    // 进入thinking解析模式
}
// 第498行
if (this.reasoning.includes(power_user.reasoning.suffix)) {
    // 找到结束标签
}
```

**实测结论**：prefix/suffix只能是纯文本，改成 `(?:<\?xml[^>]*\?>\s*)?</think>` 这样的正则模式**无效**。

### 2. 处理顺序：Reasoning Parser → Regex Engine

```
流式接收 → ReasoningHandler.process() 处理message.mes（字面匹配）
                ↓
流式结束 → getRegexedString(message.mes, AI_OUTPUT) 应用正则脚本
```

**关键**：AI_OUTPUT正则脚本在reasoning parser之后执行。如果 `` 标签被XML头等干扰导致parser失败，正则脚本无法修复。

### 3. Reasoning设置文件位置

```
<SILLYTAVERN_ROOT>/data/default-user/reasoning/Think XML.json
```

内容：
```json
{
    "name": "Think XML",
    "prefix": "
```

---

## 已知问题

### Gemini代理XML头干扰（gcli.ggchan.dev）

**症状**：AI回复以原始文本 `?xml version="1.0"...` 开头，thinking内容未被折叠。

**根因**：Gemini模型或gcli.ggchan.dev代理在返回thinking内容时，有时在 `</think>`
```

格式：`*【旁白：内容】*`（星号包裹，ST渲染为斜体灰色）

**用途**（5种）：
- 机制解释（道具/系统/规则）
- 风险提示（危险/后果）
- 进度提示（数值变化/阶段跃迁）
- 行动引导（列出可选方案）
- 角色心理（NPC内心想法）

**频率**：每轮回复1-2段，穿插在叙事段落之间，不集中在末尾。

### 关键Pitfall

**旁白规则必须在system_prompt中显式声明**：
- first_mes中的旁白示例**不够**——模型看到示例但不知道要继续使用
- system_prompt必须有明确的规则说明格式、用途、频率
- 没有规则时，模型会生成纯叙事，不带旁白段落

**system_prompt插入位置**：
- 放在状态栏铁律之后、核心规则之前
- 与状态栏铁律并列，作为"第二铁律"

### 状态栏铁律模板

```
【铁律】每次回复的【第一行】必须是状态栏。格式参见世界书"状态栏系统"条目。不可省略，不可模糊，不可用"同上"代替。例外：开场白（first_mes/alternate_greetings）中可以省略状态栏，从第二轮开始必须显示。

【旁白规则】在叙事关键节点使用旁白解说，格式为 *【旁白：解说内容】*（星号包裹方括号，酒馆中显示为斜体灰色文字）。旁白用于：
- 机制解释：恶魔相机的使用流程、指令效果、灵魂损耗等
- 风险提示：龙傲天在附近、使用相机的危险性
- 进度提示：角色堕落值变化、阶段跃迁条件
- 行动引导：列出当前可选的行动方案
- 角色心理：NPC的内心想法和潜意识变化
每轮回复至少包含1-2段旁白，穿插在叙事段落之间，不要集中在末尾。
```

### 验证方法

导入卡后，发送一条消息检查AI回复：
1. 第一行是否是状态栏（`<action_info>` 格式）
2. 正文中是否有 `*【旁白：...】*` 格式的斜体段落
3. 旁白是否穿插在叙事中（不是集中在末尾）

如果状态栏存在但旁白缺失 → system_prompt缺少旁白规则
如果两者都缺失 → 检查reasoning parser是否正常工作（thinking标签是否被正确解析）

### ST配置文件位置

| 配置项 | 文件路径 |
|--------|----------|
| Reasoning设置 | `<SILLYTAVERN_ROOT>/data/default-user/reasoning/*.json` |
| 全局设置 | `<SILLYTAVERN_ROOT>/data/default-user/settings.json` |
| OpenAI预设 | `<SILLYTAVERN_ROOT>/data/default-user/OpenAI Settings/*.json` |
| 正则脚本 | settings.json → `extension_settings.regex` (list) |
| 扩展 | `<SILLYTAVERN_ROOT>/data/default-user/extensions/` |

### API连接配置（settings.json关键字段）

```json
{
    "main_api": "openai",
    "openai_settings": {
        "api_server": "http://127.0.0.1:5000/api",  // ST自身的API服务器（不是连接目标）
        "custom_url": "https://gcli.ggchan.dev/v1",   // 实际API端点
        "reverse_proxy": "https://gcli.ggchan.dev"     // 反向代理
    }
}
```

**注意**：`api_server` 是ST对外提供的API端口，不是ST连接的后端。实际连接目标是 `custom_url` / `reverse_proxy`。

### "酒馆助手"与"第三方扩展"的关系

- "酒馆助手"是"第三方扩展"（ThirdPartyExtension）扩展的子模块
- 安装路径：`<SILLYTAVERN_ROOT>/data/default-user/extensions/ThirdPartyExtension/`
- 两者是同一个扩展，不是独立的扩展
- "第三方扩展"的渲染开关和"酒馆助手"的API代理是同一扩展的不同功能模块
