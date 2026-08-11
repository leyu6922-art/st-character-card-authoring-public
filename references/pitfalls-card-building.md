# ST角色卡构建 Pitfalls（2026-07-17 道家仙子美母实证）

## 1. delegate_task 大型NSFW内容生成不可靠

**问题**：并行子代理生成30+条目/200KB级别ST角色卡时，子代理产出不可靠。用户反馈"我没有看到子代理在工作"，entries文件始终未生成。

**可靠替代**：主代理直接用 `write_file` 写 content → `execute_code` 组装 JSON → `validate_card.py` 修复结构。

**流程**：
1. 用 `write_file` 写每个条目的 content 到临时 `.txt` 文件
2. 用 `execute_code` 读取所有 `.txt` 文件，组装为完整 JSON entries 数组
3. 分批写入 `entries_system.json` / `entries_characters.json` / `entries_scenes.json`
4. 最终用 `execute_code` 运行 `assemble_card.py` 合并为完整卡 JSON
5. 跑 `validate_card.py` 修复结构问题

## 2. execute_code 中文全角标点 SyntaxError

**问题**：中文全角句号「。」(U+3002)、全角逗号「，」(U+FF0C)等在 execute_code 的 Python 字符串字面量中触发 `SyntaxError: invalid character`。

**解决**：先用 `write_file` 写中文内容到 `.json` 文件，再用 `execute_code` 读取处理。不要在 execute_code 的字符串字面量中放大量中文标点。

## 3. validate_card.py 开场白字数计数方法

**误解**：以为用 `len(re.findall(r'[\u4e00-\u9fff]', text))` 统计中文字符。

**实际**：validate_card.py 用 `len(g)` 计算，即 **总字符数**（含标点、空格、换行），不是仅中文字符。

- 目标：`len(g) >= 1400`
- 中文内容占比约 60-70%，需要约 2000+ 总字符才能达到 1400 "字"
- 用纯中文字符计数会低估 validate 的结果

## 4. G型选开模式 validate trade-off

**现象**：身份条目 `constant=true, enabled=false, keys=[]` 时，共用层角色档案（如寰冲·核心档案）被 validate 标记为「核心角色/威胁档案所有开场白均不触发」ERROR。

**原因**：greeting 是身份中性的（不直接使用角色名"寰冲"），所以不会触发以"寰冲"为 key 的角色档案。

**处理**：这是 **预期行为**，非真实错误。角色名会在 AI 回复中出现，后续轮次会触发。可在 greeting 中自然提及角色名（如「一个名叫寰冲的矮小少年」）来规避，或接受这个 trade-off。

## 5. v3 extensions 字段名混淆

构建时最容易搞错的字段名映射：

| 错误写法 | 正确写法 |
|----------|----------|
| `keysecondary` | `secondary_keys` |
| `order` | `insertion_order` |
| `position: "after_char"` | `position: 4` |
| `extensions: {}` | 必须有完整 31 字段 |

完整 31 字段列表见 `references/v3-extensions-field-list.md`。

## 6. T112：用户自审结果必须用脚本验证（2026-07-18 种孕武道大会实证）

**问题**：用户提交自审结果"0🔴，8🟡（均软门控/建议项）"，但实际跑 enrichment_self_check 脚本输出 `⚠️ 🟡 ≥3 项 → 按 skill 红线必须修复，不能交付`。用户将脚本的交付阻断项误分类为"软门控"。

**根因**：用户可能没有跑脚本，或只看了脚本的🟡标签而忽略了末尾的阈值判定。

**规则**：
1. **用户自审结果仅供参考**——审查时必须重新跑 validate_card + enrichment_self_check，不能信任用户报告的🔴/🟡数量
2. **enrichment_self_check 的 ≥3🟡 阈值是交付阻断**，不是"建议"——即使每条🟡本身是"软门控"，数量累积到3就升级为硬门控
3. **角色条目字数常被自审遗漏**——用户倾向于只看事件种子/场景/NTR关系的字数，忽略角色条目本身。审查时必须用 Step 3 弹性标准逐条检查

**自审 vs 脚本常见偏差模式**：
- 漏报🔴（角色条目低于500字硬底线）
- 误判🟡交付状态（忽略≥3阈值）
- 遗漏结构问题（selective不同步、display_index、use_regex）

## 7. T113：selective 字段顶层 vs extensions 不同步（2026-07-18 实证）

**问题**：条目顶层 `selective: true` 但 `extensions.selective: false`。validate_card 报 warning："顶层selective与extensions.selective不一致（ST按顶层selective触发；建议双字段同步）"。

**影响**：ST 按顶层 selective 触发，所以卡片能正常工作。但不同步是不规范的，可能在未来版本中产生问题。

**修复**：批量同步——遍历所有条目，将 `extensions.selective` 设为与顶层 `selective` 一致。

```python
for e in entries:
    if e.get('selective') != e.get('extensions', {}).get('selective'):
        e['extensions']['selective'] = e.get('selective', False)
```

**预防**：构建卡片时，写入每个条目后立即同步 selective 字段，不要留到最后批量修。
