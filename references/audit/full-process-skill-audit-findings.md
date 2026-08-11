# 制卡全流程 skill 审查发现（v6.33 实测）

用途：当维护 `st-character-card-authoring` 或其审查脚本时，先看本文件，避免回归已发现的流程断点。

## 本次实测发现

1. **G 型选开模式 validate 崩溃**
   - 根因：`all_greetings` 只在 `selective_entries` 分支内定义；选开模式没有 selective 条目，但 check 47 仍使用 `all_greetings`。
   - 修复：在 G 型/选开两类检查前统一定义 `all_greetings = [first_mes] + alternate_greetings`。

2. **31 字段 extensions 没有真实校验**
   - 根因：旧 validate 只检查 `len(ext) < 10`，只有 10 个字段的条目也能通过。
   - 修复：用 `required_ext_fields` 白名单逐项检查，缺字段报 error。

3. **发布文案敏感词扫描范围误写成全卡**
   - 旧模板误把 description/system_prompt/first_mes/entry keys/content 等卡内字段纳入 Discord 审查。
   - 当前规则：Discord/社区只审简介/帖子文案；卡 JSON、世界书、开场白和小说原文不参与平台审查，除非人工复制到帖子里。

4. **check 26 文档与代码不一致**
   - 实际脚本已豁免 `constant=true + enabled=false + keys` 的选开身份条目。
   - 文档不得再写“check 26 会误报 error”，应写“已内置豁免；若报错说明脚本版本旧”。

5. **10 步交付门控与 §4.0 四步审查容易混淆**
   - §4.0 的 4 步只是 §3.4 交付前 10 步中的结构/内容审查部分。
   - 交付前仍必须继续跑加料自检、Discord、违禁词、pitfalls、角色名验证、多 NPC 验证。

6. **G 型选开身份条目被 enabled=false 检查误杀**
   - 根因：check 14 曾把所有 `enabled=false` 且非事件种子的条目视为 error；但选开身份条目本来就必须 `constant=true + enabled=false`，由玩家在 ST 世界书 UI 手动启用。
   - 修复：`validate_card.py` 对 `constant + enabled=false + content含{{user}} + comment含选开/身份` 的条目豁免，不再阻断默认 G 型选开模式。

## 维护原则

- 发现脚本与文档冲突时，优先修脚本，再同步 SKILL.md 与 review-template-system.md。
- “规则写在 skill 里”不够；能自动检查的必须进入 `validate_card.py` 或独立脚本。
- 修改校验脚本后，用最小 JSON fixture 覆盖：普通卡、G greeting 卡、G 选开卡、extensions 缺字段卡。

## 2026-07-15 结构治理修复

- §1 决策树补齐：A-Hidden.隐奸恶堕、C+.隐奸NTL、非NTR/普通世界书/玩法型卡出口。
- §1 原型表命名去冲突：A+.纯恶堕 与 A-Hidden.隐奸恶堕 分离。
- §2 重排为 2.1→2.7，合并重复 §2.5 模板匹配，保留 G greeting / G 选开两模式。
- §3.3b 补 G 型选开模式硬性检查清单，明确 check14/26 不应误杀选开身份。
- review-template-system.md 补 F型叙事观察卡显式审查行。
- §7 参考索引用当前目录实际文件自动重建，分 active / archived / deleted。



## 2026-07-15 补充发现：T73 绿灯误判/泛key误触发

校园示例卡守护卡实测发现：ST UI 中绿色条目并不代表“已触发”。卡中 6 条含 `secondary_keys` 的触发条目均为 `selective=false`，副关键词实际被忽略；`场景·比企谷家` 使用单字 key `家`，在 first_mes 的“回家”中误触发。

已修复流程：
- `validate_card.py` 升级 v4.7，新增每个 first_mes/alternate 的触发审计、泛key error、多主题大条目 warning、secondary_keys/selective 说明。
- `SKILL.md §3.3` 新增触发审计铁律。
- `references/misc/pitfall-library.md` 新增 T73。


## 2026-07-15 补充发现：T74 selective 源码对齐与 G型误判

大型结构化卡 v4.2 与 ST v1.18 源码确认：
- ST 读取顶层 `selective`，不是 `extensions.selective`。只有 extensions 副本为 true 时，secondary_keys 不会参与触发。
- `selective=true` 且 `secondary_keys=[]` 会退化为 primary-only，不是死触发。
- 普通世界书也会大量使用 selective 做地点/范围绑定，不能看到 selective=true 就判定为 G 型多视角卡。

已修复：
- `validate_card.py` 升级 v4.8：源码对齐触发模拟（顶层selective、selectiveLogic、secondary空退化primary-only、regex key）。
- G型 checks 42-45 仅在 greeting 首行含身份/视角标记时运行，避免误伤大型结构化卡类普通 selective 卡。
- `worldbook-trigger-reachability-audit.md` 重写为源码对齐版，并加入大型结构化卡“范围绑定”模式。


## 2026-07-15 补充发现：T75 触发审计需要可交接报告

`validate_card.py` 能阻断 hard error/warning，但输出不适合作为跨窗口交接件；校园示例卡触发治理需要一份“逐 greeting 触发矩阵 + 普通句反证 + 风险建议”的 Markdown 报告。

已修复：
- 新增 `scripts/audit_worldbook_triggers.py`：生成世界书触发审计 Markdown 报告。
- `worldbook-trigger-reachability-audit.md` 增加脚本调用方式和职责分工。
- `SKILL.md §3.3` 增加交接/修卡前运行报告脚本的要求。
