# SillyTavern Reasoning/Thinking 解析器陷阱

## 核心机制（ST 1.18.0 源码实测）

ST 的 reasoning 解析器在 `public/scripts/reasoning.js` 第480行使用 **字面量 `startsWith` 匹配**，不是正则：

```javascript
// reasoning.js 第480行
if (parseTarget.startsWith(power_user.reasoning.prefix) && parseTarget.length > power_user.reasoning.prefix.length) {
    this.#isParsingReasoning = true;
    this.state = ReasoningState.Thinking;
}
// 第498行：suffix 也是字面量匹配
if (this.reasoning.includes(power_user.reasoning.suffix)) {
    this.reasoning = this.reasoning.slice(0, this.reasoning.indexOf(power_user.reasoning.suffix));
}
```

**关键结论：prefix/suffix 只能是纯文本字符串，不支持正则表达式。**

## 配置文件位置

Reasoning 模板存放在：`SillyTavern/data/default-user/reasoning/`

```
Think XML.json     → {"prefix": "<think>", "suffix": "</think>", "separator": "\n"}
DeepSeek.json      → DeepSeek 专用格式
Gemma 4.json       → Gemma 专用格式
OpenAI Harmony.json → OpenAI 格式
Blank.json         → 空模板
```

当前选中的模板在 `power_user.reasoning_select` 中存储。

## Gemini 模型 XML 头问题（2026-07-08 实测）

### 症状
Gemini 模型（通过代理如 gcli.ggchan.dev 或本地代理）有时在 `` 标签前输出 XML 声明：

```
?xml version="1.0" encoding="UTF-8"?>xxxxx
```

这导致 `startsWith(")` 返回 `false`，reasoning 解析器不触发，thinking 内容原样显示为正文。

### 连带症状
- 状态栏可能被 thinking 内容挤掉（模型把状态栏输出在 `` 之后）
- 旁白格式（`*【旁白：...】*`）正常但 thinking 部分可见

### 诊断方法
```javascript
// 在 ST 控制台检查当前 reasoning 配置
JSON.stringify({
  prefix: document.getElementById('reasoning_prefix')?.value,
  suffix: document.getElementById('reasoning_suffix')?.value,
  auto_parse: document.getElementById('reasoning_auto_parse')?.checked,
  select: document.getElementById('reasoning_select')?.value
});
```

### 修复方案（按优先级）

**方案1：修复代理层（根本解决）**
代理（如"第三方扩展"/ThirdPartyExtension 扩展的本地代理 on port 5000）应在转发响应前剥离 XML 头。

**方案2：在代理中配置 Gemini thinking 格式**
Gemini API 原生支持 `thought` 字段（`candidates[i].content.parts[j].thought`），代理应正确传递此字段而非将 thinking 内容拼接到正文。

**方案3：禁用"思维链提取到正文"脚本**
如果 reasoning 解析失败，该脚本会把 thinking 内容提取到正文中显示（适得其反）。在预设脚本面板中禁用它。

## Regex 脚本与 Reasoning 解析的执行顺序

```
1. 模型返回响应（含 thinking 内容）
2. Reasoning 解析器尝试匹配 prefix/suffix（字面量）
3. 解析成功 → thinking 内容存入 reasoning 字段
4. Regex 引擎处理 reasoning 内容（regex_placement.REASONING = 6）
5. Regex 引擎处理正文（regex_placement.AI_OUTPUT = 2）
```

**关键：Regex 脚本在 reasoning 解析之后运行，无法在解析前剥离 XML 头。**

## 相关 UI 元素 ID

| 设置 | 元素 ID | 类型 |
|------|---------|------|
| Prefix | `reasoning_prefix` | textarea |
| Suffix | `reasoning_suffix` | textarea |
| Separator | `reasoning_separator` | textarea |
| Auto Parse | `reasoning_auto_parse` | checkbox |
| Auto Expand | `reasoning_auto_expand` | checkbox |
| Show Hidden | `reasoning_show_hidden` | checkbox |
| Template Select | `reasoning_select` | select-one |
| Reasoning Effort | `openai_reasoning_effort` | select-one |

## 预设脚本面板中的相关脚本

- **"思维链提取到正文"**（预设脚本）— 当 reasoning 解析失败时，会把 thinking 内容显示为正文。如果模型输出格式不标准，应禁用此脚本。
- **"[删除]正文后思考"**（预设正则）— 删除正文后的 thinking 内容
- **"[隐藏]思考正则格式化"**（预设正则）— 格式化 thinking 显示
- **"[隐藏]思考正则隐藏-备用方案"**（预设正则）— 备用隐藏方案
