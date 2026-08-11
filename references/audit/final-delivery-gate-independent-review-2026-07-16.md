# Final Delivery Gate 独立审查补充（2026-07-16）

适用：审查 `final_delivery_gate.py` / `validate_card.py` / `enrichment_self_check.py` / `check_build_sync.py` 与 SKILL 文档是否一致。

## 结论口径

- 脚本链路通过不等于文档完全通过；交付结论要拆成：脚本行为 / 文档一致性 / 真实卡回归。
- `exit=2` 必须写成“仅 warning，可人工确认”，不能写成“完全通过”，也不能当失败。
- 真实旧卡 `exit=1` 时必须读分项归因：真实卡问题 / gate 误杀 / gate 漏检 / 归因不准。

## 独立审查最低命令集

```bash
python -m py_compile scripts/validate_card.py scripts/audit_worldbook_triggers.py scripts/enrichment_self_check.py scripts/check_build_sync.py scripts/final_delivery_gate.py
python scripts/validate_card.py references/audit/fixtures/bad_greeting_truncated.json
python scripts/validate_card.py references/audit/fixtures/bad_xuankai_keys_nonempty.json
python scripts/enrichment_self_check.py references/audit/fixtures/bad_r18_empty_shell.json --r18
python scripts/enrichment_self_check.py references/audit/fixtures/good_r18_rich_terms.json --r18
python scripts/enrichment_self_check.py references/audit/fixtures/good_g_normal_event_no_threepath.json --prototype G --r18
python scripts/check_build_sync.py references/audit/fixtures/good_build_nested/good_build_nested.json --project-dir references/audit/fixtures/good_build_nested
python scripts/check_build_sync.py references/audit/fixtures/bad_build_unsynced/bad_build_unsynced.json --project-dir references/audit/fixtures/bad_build_unsynced
python scripts/final_delivery_gate.py references/audit/fixtures/bad_code_residue.json --project-dir references/audit/fixtures
```

## Strict 模式验证方法

构造一张 otherwise-good 临时卡，在卡 JSON 注入 `高一/初中/萝莉/未成年`，并另造发布简介 fixture：

- 默认：不应因为这些词导致 `localization/residue scan` fail。
- `--strict-age`：只在提供 `--publish-text` 时扫描发布文案中的未成年/儿童化词汇并输出 warning；不扫描卡 JSON。
- `--strict-platform`：只在提供 `--publish-text` 时扫描发布文案中的社区平台词并作为 error；不扫描卡 JSON。

注意：临时卡必须基于结构干净的 fixture，否则 validate 结构错误会干扰 strict scan 判断。

## 文档一致性红线

这些表述会误导低阶模型，必须收窄：

- 把“平台专项敏感词扫描”写成普通本地 ST 成品卡默认阻塞项。
- 把“发布文案未成年词汇专项扫描/替换”写成普通返修默认步骤，或要求成人化卡本体。
- “--r18 才启用 final gate R18”——当前 final gate 默认启用 R18；只有普通/非 NSFW 世界书才 `--no-r18`。
- “G 型默认 none / 阻止/攻防 触发三路径”与当前实现不一致。当前应写：G 型 `auto`，只对明确 `守护/破局/救援/反杀/争夺/保护/营救/拯救` 类事件 soft。

## 真实卡回归期望

- 黑绿足球 G 型：`exit=2`，`enrichment_self_check.py PASS`，不应出现 R18 空壳误杀或 G 型普通事件三路径误杀。
- 周雨晴 E 型：`exit=2`，R18 PASS，build sync PASS，residue PASS。
- 绿冠星空 A-N：若仍含代码残留，`exit=1` 应归因到 `localization/residue scan`，不是 R18 黄项误杀。

## 最小修复原则

优先 patch 文档口径，不大改脚本。脚本层若已通过 fixture + 真实卡回归，只做命名/噪音级优化。
