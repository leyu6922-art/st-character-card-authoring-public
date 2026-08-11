# 交付门控报告 — bad_code_residue.json

- card: `<HERMES_HOME>\skills\creative\st-character-card-authoring\references\audit\fixtures\bad_code_residue.json`
- project_dir: `<HERMES_HOME>\skills\creative\st-character-card-authoring\references\audit\fixtures`
- prototype: `未指定`
- r18: `True`
- strict_age: `False`
- strict_platform: `False`
- three_path: `auto`
- final verdict: **不可交付**
- exit_code: `1`

## Summary

| Check | Status | Errors | Warnings |
|---|---:|---:|---:|
| validate_card.py | WARN | 0 | 4 |
| audit_worldbook_triggers.py | WARN | 0 | 3 |
| enrichment_self_check.py | WARN | 0 | 1 |
| check_build_sync.py | N/A | 0 | 0 |
| localization/residue scan | FAIL | 9 | 0 |

## validate_card.py: WARN

### Warnings
- 条目[4] 被禁用 (enabled=false)——事件种子库，设计如此
- 条目[2] '林梦瑶语料库': 所有开场白均不触发。若这是中后期/按需条目可接受；若期望首轮可用，需要把关键词写入对应greeting/chat。
- 条目[5] '身体与环境描写库': 所有开场白均不触发。若这是中后期/按需条目可接受；若期望首轮可用，需要把关键词写入对应greeting/chat。
- 条目[6] 'NTR关系：林梦瑶×对手': 所有开场白均不触发。若这是中后期/按需条目可接受；若期望首轮可用，需要把关键词写入对应greeting/chat。

## audit_worldbook_triggers.py: WARN

- report: `<HERMES_HOME>\skills\creative\st-character-card-authoring\references\audit\fixtures\bad_code_residue_worldbook_trigger_audit.md`
### Warnings
- [2] 林梦瑶语料库: 所有开场白均不触发
- [5] 身体与环境描写库: 所有开场白均不触发
- [6] NTR关系：林梦瑶×对手: 所有开场白均不触发

### Notes
- 完整报告: <HERMES_HOME>\skills\creative\st-character-card-authoring\references\audit\fixtures\bad_code_residue_worldbook_trigger_audit.md

## enrichment_self_check.py: WARN

### Warnings
- 事件种子[4] '事件种子：文件袋攻防' 119中文字 (建议≥150)

### Notes
- 角色[1] '核心角色档案：林梦瑶' 4996中文字/6097总字符 ✔
- 语料库[2] 1472中文字 ✔
- 场景[3] 1368中文字 [有安全等级]
- 行为模板[1] '核心角色档案：林梦瑶' 189个信号/链 ✔
- 描写库[5] 1512中文字 ✔
- NTR关系[6] 'NTR关系：林梦瑶×对手' 3810中文字 ✔
- R18素材[1] '核心角色档案：林梦瑶' 覆盖4类链条: 动作链/语言链/身体反应/场景链
- R18素材[6] 'NTR关系：林梦瑶×对手' 覆盖4类链条: 动作链/语言链/场景链/阶段链

## check_build_sync.py: N/A

### Notes
- 未检测到 build/all_entries.json、assemble_card.py 或 build/assemble_card.py；build sync: N/A

## localization/residue scan: FAIL

### Errors
- python编码声明残留 命中 1 次
- import json代码残留 命中 1 次
- make_entry函数残留 命中 1 次
- event变量赋值残留 命中 1 次
- 三引号代码残留 命中 2 次
- pad_to构建残留 命中 1 次
- PLACEHOLDER/TODO占位残留 命中 2 次
- Unicode标签残留 命中 1 次
- print调试残留 命中 1 次
