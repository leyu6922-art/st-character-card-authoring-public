# GPT 审查/修复闭环：validate 通过 ≠ 可交付

适用场景：一个模型已生成 SillyTavern 角色卡，用户要求新模型参照 skill 流程审查或接手修复。

## 核心教训

1. **不能只看 `validate_card.py`**
   - `validate_card.py` 只代表结构层通过。
   - 必须同时跑：
     - `validate_card.py`
     - `enrichment_self_check.py`
     - `audit_worldbook_triggers.py`
   - `enrichment_self_check.py` 若输出 `🟡 ≥3 项 → 按 skill 红线必须修复，不能交付`，即使 `🔴=0` 也不能声称交付。

2. **构建链路必须可复现**
   - 如果最终 JSON 是手工补丁后的版本，必须把补丁同步回构建源。
   - 常见源文件：
     - `build/all_entries.json`
     - `build/*.txt`
     - `build/assemble_card.py`
   - 修完后必须重跑 `assemble_card.py`，确认不会回滚已修内容。

3. **`data.spec` / `data.spec_version` 必须写入组装脚本**
   - 只在最终 JSON 手工补 `data.spec` 不够。
   - `assemble_card.py` 的 `data` 字典内也要包含：
     ```json
     "spec": "chara_card_v3",
     "spec_version": "3.0"
     ```
   - 否则重跑组装后会再次触发 validate 错误。

4. **secondary_keys 不是自动生效**
   - 有 `secondary_keys` 但顶层 `selective=false` 时，ST 会忽略 secondary。
   - 范围绑定条目必须：
     ```json
     "selective": true,
     "secondary_keys": ["上级范围"]
     ```
   - 或者清空 `secondary_keys`，不要留下假约束。

5. **审查任务先审后改**
   - 用户说“审查之前模型做的卡”时，先输出问题清单和证据，不要直接续写/生成。
   - 用户确认“可以”后再执行 P0 修复包。

## 推荐 P0 修复包

1. 备份当前 JSON、`all_entries.json`、`assemble_card.py`。
2. 跑三脚本并保存关键输出。
3. 修 `enrichment_self_check.py` 阻断项（包括 🟡≥3）。
4. 修 `secondary_keys` / `selective` 不一致。
5. 同步最终 entries 到 `build/all_entries.json`。
6. 修 `assemble_card.py`，确保重跑后保留 `data.spec/spec_version`。
7. 重跑 `assemble_card.py`。
8. 再跑三脚本：
   - `validate_card.py`: errors=0
   - `enrichment_self_check.py`: 🔴=0 且 🟡=0 或脚本明确通过
   - `audit_worldbook_triggers.py`: 硬风险=0，且 `有secondary但顶层selective=false=0`

## 报告口径

- “结构可导入” ≠ “可交付”。
- 只有三脚本门控通过 + 构建链路可复现，才可说“可以交付”。
- 剩余中负载/按需条目不触发可作为 P1 优化，不要和 P0 阻断混淆。
