# SillyTavern v3 角色卡 Extensions 字段参考

> 来源：validate_card.py lines 190-197（2026-07-17 验证）

## 条目级 extensions 必须包含的 31 个字段

```json
{
  "position": 4,
  "exclude_recursion": false,
  "display_index": 0,
  "probability": 100,
  "useProbability": true,
  "depth": 4,
  "selective": false,
  "selectiveLogic": 0,
  "case_sensitive": false,
  "match_whole_words": false,   // 🚨 中文卡必须false，见T93（Python \\W不匹配CJK字符）
  "use_group_scoring": false,
  "automation_id": "",
  "role": 0,
  "vectorized": false,
  "sticky": 0,
  "cooldown": 0,
  "delay": 0,
  "scan_depth": 100,
  "match_persona_description": true,
  "match_character_description": true,
  "match_character_personality": true,
  "match_character_depth_prompt": false,
  "match_scenario": true,
  "match_creator_notes": true,
  "triggered": false,
  "group": "",
  "group_override": false,
  "group_weight": 100,
  "prevent_recursion": true,
  "delay_until_recursion": false,
  "addMemo": true
}
```

## 条目级必须字段（required_entry_fields）

```
id, keys, secondary_keys, comment, content, constant, selective,
addMemo, insertion_order, enabled, position, use_regex, extensions
```

## 常见错误映射

| 错误写法 | 正确写法 |
|----------|----------|
| `keysecondary` | `secondary_keys` |
| `order` | `insertion_order` |
| `position: "after_char"` | `position: 4`（top-level 用数字，0=before_char, 4=after_char） |
| `extensions: {}` | 必须有完整 31 字段 |
| 缺少 `addMemo` | 条目顶层 + extensions 内都要有 `addMemo: true` |
| 常驻条目 `keys: ["规则","兼容"]` | constant=true 时必须 `keys: []` |
| 中文卡 `match_whole_words: true` | 必须 `false`，否则Python `\W` 不匹配CJK字符导致所有中文key失效（T93） |

## position 语义

| 值 | 含义 |
|----|------|
| 0 | before_char（角色定义前，用于身份条目） |
| 4 | after_char（角色定义后，用于大部分内容条目） |

## validate_card.py 开场白字数计数方法

validate_card.py 使用 `len(g)` 计算开场白长度，即 **总字符数**（含标点、空格、换行），**不是**仅中文字符。

- 目标：`len(g) >= 1400`
- 中文内容占比约 60-70%，所以需要约 2000+ 总字符才能达到 1400 "字"
- 用 `len(re.findall(r'[\u4e00-\u9fff]', text))` 统计中文字符会低估 validate 的计数

## T93: 中文卡 match_whole_words 必须为 False（2026-07-17）

**根因**：Python 3 默认 Unicode 模式下，`\w` 匹配所有 Unicode word characters（含CJK中文字符），因此 `\W` **不匹配中文字符**。当 `match_whole_words=True` 时，`_matches_key` 函数走 regex word boundary 分支：
```python
re.search(r'(?:^|\W)(' + re.escape(needle) + r')(?:$|\W)', haystack)
```
中文关键词（如"寰冲"）后接中文字符（如"和"），"和"是 `\w` 不是 `\W`→regex 不匹配→所有中文 key 返回 False→触发全面断裂。

**修复**：对中文语言卡，所有条目 `extensions.match_whole_words` 设为 False。英文卡不受影响。

## T94: data.extensions 世界书绑定（2026-07-17）

v3 卡的 `data.extensions` 必须包含以下字段：
```json
{
  "world": "",
  "depth_prompt": {"prompt": "", "depth": 4, "role": "system"},
  "position": 0,
  "fav": false,
  "talkativeness": "0.5",
  "creator_notes": "..."
}
```

**致命**：`world` 字段为空=世界书未绑定到角色卡。ST 无法加载内嵌世界书，所有条目形同虚设。**validate_card.py 不检查此项**——必须手动验证。

## T95: execute_code 中文长文本静默截断（2026-07-17）

execute_code 工具对中文长字符串字面量（>500中文字）会静默截断，不报错不警告。

**症状**：在 execute_code 中直接写中文长文本（如角色卡条目 content），实际写入的只有前500中文字左右，后续内容丢失。

**解决方案**：
1. 先用 `write_file` 工具写入中文内容到 .json/.md 文件
2. 再用 `terminal` 跑 Python 脚本读取文件并合并到目标 JSON
3. 禁止在 execute_code 中直接写超过500中文字的字符串字面量

## G型选开模式·角色档案触发 trade-off（2026-07-17）

当 G型选开模式的 greeting 保持身份中性（不写角色名如"寰冲""韩琪"）时：
- 共用层角色档案条目（如 ID 8 寰冲·核心档案）会被 validate_card 报 ERROR「核心角色/威胁档案所有开场白均不触发」
- 这是 **设计预期**——greeting 中性=身份不预设

**解决方案**：在 greeting 中自然地提到角色名（如「寰冲和寰宇两兄弟从后院走来」），既触发角色档案又不绑定 {{user}} 身份。不要为了触发而硬塞名字——如果确实需要身份中性，接受这个 trade-off，它不影响实际使用（AI 回复中会出现角色名，后续轮次会触发）。
