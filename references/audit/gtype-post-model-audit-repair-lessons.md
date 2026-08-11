# G型卡后审与修复经验：黑绿足球案例

适用场景：接手另一模型已制作/扩写的 SillyTavern G型多视角卡，用户要求“参照 skill 流程审查/修复”。

## 关键教训

1. **不要把 validate_card PASSED 等同于可交付**
   - 必须同时跑：`validate_card.py`、`audit_worldbook_triggers.py`、`enrichment_self_check.py`。
   - `enrichment_self_check.py` 若 exit_code=1，即使“🔴 需修复: 0”，只要软门控达到脚本红线（例如 `🟡 ≥3 项`），也不能宣称交付完成。

2. **脚本命令空输出不代表通过**
   - 有些脚本正常通过时 stdout 很少或为空。
   - 审查时要捕获 exit_code，并在必要时以 Python 导入方式调用验证函数，取得 errors/warnings 明细。

3. **触发审计重点：顶层 selective 才决定 secondary_keys 是否生效**
   - `extensions.selective=true` 不等于顶层 `selective=true`。
   - 有 `secondary_keys` 但顶层 `selective=false` 时，ST 实际会忽略 secondary，范围绑定失效。
   - 场景条目若依赖“绿茵大学/某角色”等范围绑定，必须顶层 `selective=true`。

4. **G型共用层与身份层的 `{{user}}` 处理要分开**
   - 共用层（角色/场景/事件/语料/普通规则）不得残留 `{{user}}`。
   - 但 G型选开身份条目必须在前 300–500 字自足定义 `{{user}}` 身份，例如“当本条目启用时，{{user}}=秦天”。
   - 不要全局替换 `{{user}}`，否则会破坏选开身份条目的 validate 检查。

5. **首轮触发负载要实测，不只看关键词是否“合理”**
   - 对 `first_mes + alternate_greetings` 扫描 enabled 条目的 primary keys，统计首轮命中数。
   - 泛 key（如“事件/语料/对话/一起/学伴/训练/学习”）会造成大量误触发，优先改为复合 key。
   - 事件种子 disabled 命中可视为设计行为，但 enabled 条目的首轮命中过高需要修。

6. **文件大小口径要说明清楚**
   - Python `len(json.dumps(...))/1024` 近似的是字符数，不是实际磁盘 UTF-8 文件体积。
   - 同时报告：磁盘文件大小、compact JSON UTF-8 大小、entry content UTF-8 大小、content 汉字数，避免“40KB/200KB/400KB”口径混乱。

7. **计划书必须随最终架构同步**
   - 若扩写从 17 条变为 73 条，旧规划书不能继续作为最终交付依据。
   - 修复完成后写 `规划书_v2_最终同步版.md`，记录最终条目矩阵、触发策略、脚本结果与剩余注意事项。

## 推荐修复顺序

1. 备份原 JSON。
2. 修违禁词与顶层/data 同步。
3. 修 G型 `{{user}}`：共用层清理，身份条目保留并前置身份定义。
4. 修 `secondary_keys` 被忽略：按设计设置顶层 `selective=true` 或清空 secondary。
5. 降低首轮触发负载与泛 key 重叠。
6. 补厚 enrichment 软门控，尤其 NTR关系条目 ≥1000 中文字。
7. 同步最终规划书。
8. 重跑三脚本，确认：validate errors=0、audit 无硬风险、enrichment exit=0。

## 可复用审查输出

最终报告应区分：
- 结构验证：validate_card 结果；
- 触发验证：audit_worldbook_triggers 结果；
- 内容厚度：enrichment_self_check 结果；
- 专项扫描：违禁词、G型共用层 `{{user}}`、secondary 被忽略、首轮 enabled 命中数；
- 文件大小：实际 KiB 与内容汉字数。
