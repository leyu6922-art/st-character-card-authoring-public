# 触发修复测试版 → 正式版发布流程

> 来源：2026-07-15 示例G型卡v2 trigger-fix-test 升 v3 触发修复正式版。适用于：已经做过 key/selective/secondary/泛key 修复的测试版，需要转成可交付正式版。

## 适用场景

- 已有 `*_trigger_fix_test.json` 或类似测试版。
- 测试版的触发审计已证明：secondary 被忽略清零、硬泛key清零、普通句反证清零或有合理解释。
- 用户实测多轮基本稳定，只剩正式化、命名、G型共用层细节、报告归档。

不适用：旧卡仍有大量泛key、secondary失效、validate error、关系错位或内容明显太薄；此时先走 `full-rebuild-after-trigger-audit.md` 或完整修卡流程。

## 标准步骤

1. **保留原版与测试版，不覆盖**
   - 原版继续留作对照。
   - 测试版继续留作触发修复试验记录。
   - 正式版另存：`*_v3_触发修复版.json` 或同类清晰版本名。

2. **最小正式化改动**
   - 修改顶层 `name` 与 `data.name`，去掉 `trigger-fix-test`，标注正式版本。
   - 修改 `data.character_version`，如 `v3_trigger_fix_official`。
   - 不顺手重写大段内容；避免把已验证的触发变量重新打乱。

3. **清理 G型共用层残留**
   - 对 G型卡，正式版前跑 G-Common：角色/场景/事件/语料共用层应零 `{{user}}`。
   - 常见残留：速览里写“若{{user}}=A/若{{user}}=B”。
   - 修法：改为“林白路线/陆天行路线”“苦主路线/征服者路线”等客观路线名；身份差异放进选开身份条目。

4. **保留选开身份条目**
   - `constant=true + enabled=false + comment含「选开」` 的身份条目保留。
   - 不把选开身份条目改成 greeting/secondary 触发。
   - 不把选开条目的 `keys` 清空；enabled=false 时 keys 不参与扫描。

5. **验证**
   ```bash
   python scripts/validate_card.py <正式版.json>
   python scripts/audit_worldbook_triggers.py <正式版.json> -o <正式版_触发审计_Hermes.md>
   ```
   必看结果：
   - `passed=True`
   - `errors=0`
   - G-Common warnings=0（若是G型正式版）
   - secondary被忽略=0
   - 硬风险=0
   - 普通句反证清零或有合理解释

6. **写正式版修改说明**
   最少包含：
   - 源测试版路径、正式版路径、触发审计报告路径。
   - 改动范围（尤其说明“未大改内容，只做正式化/共用层清理”）。
   - validate 结果。
   - 触发审计关键指标。
   - 剩余 warnings 的解释。
   - 后续建议：体验优化 vs 必修问题分开写。

## 报告结论模板

```text
v3正式版可以作为当前正式修复版使用。
它继承 trigger-fix-test 的核心修复：secondary被忽略清零、硬泛key清零、普通句反证清零、自然名速览+深度档案专用key分层。
本次正式化额外清理了 G型共用层速览中的 {{user}} 条件句，使其符合 G-Common 标准。
不建议继续围绕偶发截断大改卡；后续只做常驻瘦身、多主题条目拆分等体验优化。
```

## 常见坑

- **覆盖原版**：会丢失 A/B 对照证据。正式版必须另存。
- **借正式化大改内容**：会破坏 trigger-fix-test 已验证的变量隔离。
- **只跑 validate 不跑触发审计**：无法证明 key/secondary/fallback 仍然稳定。
- **G型共用层残留 `{{user}}`**：validate 可能只是 warning，但正式版前应清理。
- **把偶发截断写成卡失败**：若多轮稳定且触发审计通过，按 `card-vs-runtime-boundary.md` 作为运行环境备注。
