# SillyTavern Regex Placement 与世界书内容篡改分析

> 2026-07-09 实测确认：ST源码验证，预设正则脚本会在prompt组装时修改世界书内容。

## 关键源码证据

### regex_placement 枚举（engine.js:281）

```javascript
export const regex_placement = {
    MD_DISPLAY: 0,    // @deprecated
    USER_INPUT: 1,    // 用户输入
    AI_OUTPUT: 2,     // AI输出（显示层）
    SLASH_COMMAND: 3, // 斜杠命令
    // 4 - sendAs (legacy)
    WORLD_INFO: 5,    // ← 世界书内容！
    REASONING: 6,     // 推理链
};
```

### 世界书内容经过正则引擎（world-info.js:5086）

```javascript
const content = getRegexedString(entry.content, regex_placement.WORLD_INFO,
    { depth: regexDepth, isMarkdown: false, isPrompt: true });
```

关键参数：
- `isPrompt: true` → `promptOnly` 脚本会生效
- `isMarkdown: false` → 但 `markdownOnly` 的过滤逻辑被 `promptOnly` 覆盖

### promptOnly 与 markdownOnly 的交互逻辑（engine.js:352-354）

```javascript
if (
    (script.placement.includes(placement)) &&  // placement 匹配
    (
        (script.promptOnly && isPrompt) ||                    // 条件A: promptOnly+isPrompt → 总是运行
        (!script.markdownOnly && !script.promptOnly && !isMarkdown && !isPrompt)  // 条件B
    )
)
```

**结论**：当 `promptOnly=true` 且 `isPrompt=true` 时，无论 `markdownOnly` 是否为 true，脚本都会运行。

## 实际影响（示例玄幻项目·参考预设预设）

| 正则 | 规则 | placement | promptOnly | markdownOnly | 世界书匹配数 |
|------|------|-----------|------------|--------------|-------------|
| [14] | 杀"不是X是Y"句式 | [1,2,3,5] | True | True | 52处 |
| [16] | `——` → `…` | [1,2,3,5] | True | True | 699处 |
| [17] | 杀含"语气/气音"的句子 | [2,3,5] | True | True | 43处 |

**总计：794处世界书内容被正则篡改**，AI模型看到的世界书已经不是用户写的原文。

## 正则脚本关键字段

| 字段 | 含义 | 对世界书的影响 |
|------|------|---------------|
| `disabled` | 是否禁用（True=关闭） | True时不影响任何内容 |
| `placement` | 在哪些上下文执行 | 包含5则影响世界书 |
| `promptOnly` | 是否只在prompt组装时运行 | True时修改模型输入 |
| `markdownOnly` | 是否只在markdown模式运行 | 被promptOnly覆盖 |
| `runOnEdit` | 编辑消息时是否重新执行 | 不影响世界书 |

## 诊断方法

检查预设的正则脚本是否影响世界书：

```python
import json
preset_path = "预设文件.json"
with open(preset_path, 'r', encoding='utf-8') as f:
    preset = json.load(f)

regex = preset.get('extensions', {}).get('regex_scripts', [])

for i, r in enumerate(regex):
    disabled = r.get('disabled', False)
    placement = r.get('placement', [])
    prompt_only = r.get('promptOnly', False)

    if not disabled and 5 in placement and prompt_only:
        name = r.get('scriptName', f'regex_{i}')
        find = r.get('findRegex', '')[:60]
        print(f"⚠️ [{i}] {name} 会影响世界书内容!")
        print(f"    find: {find}")
```

## 修复方案

### 方案1：关闭有问题的正则（简单但影响AI输出质量）

在预设中将 placement 包含 [5] 的正则设为 OFF。

### 方案2：修改正则的 placement（推荐）

将 placement 从 `[1,2,3,5]` 改为 `[1,2,3]`（去掉5），只杀AI输出中的八股，不碰世界书。

**注意**：ST预设JSON中的正则 placement 是数组，直接编辑即可：
```json
"placement": [1, 2, 3]  // 去掉5
```

### 方案3：调整世界书内容避开正则匹配

- 破折号 `——` → 改用 `—` 或 `：`
- "不是X，是Y"句式 → 改写为"与其说是X，不如说是Y"
- 含"语气"的句子 → 改用"语调""声调""口吻"

## 验证修复效果

修复后扫描世界书确认无残留：

```python
import re
r14 = re.compile(r'(不是|并非)[\s\S]{0,40}?(?<!不)是')
r16 = re.compile(r'——')
r17 = re.compile(r'[。，]?[^。，]*(?:语气|气音|尾音|音调)[^。，]*[。，]?')

# 读取世界书，统计匹配数
# 修复后匹配数应为0（如果用方案2+3）
```

---

*来源：示例玄幻项目 × 参考预设预设冲突分析*
*ST版本：SillyTavern 1.12.x*
*验证日期：2026-07-09*
