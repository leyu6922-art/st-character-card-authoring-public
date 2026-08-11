# E/F/G 流程审查发现（2026-07-15）

> 来源：E+F+G 合并窗口对 `st-character-card-authoring` 的审查。用途：修 skill/scripts/templates 时作为专项清单；不是某张卡的审查报告。

## 核心裁决

当前最大风险不是单条规则缺失，而是**默认 G 型选开模式、触发审计、发布/修卡流程**三条下游链路没有完全回灌到审查模板和脚本门控。

> 2026-07-15 本窗口复核状态：P0 1-4 已回灌到 `review-template-system.md`、`validate_card.py`、`SKILL.md`、`世界书触发专项审查模板.md`、`card-repair-workflow.md`；P1 1-8 中除禁词单一来源化（P2级重构）外已做最小修复；P2重复行/标题/路径问题已修或已确认当前索引正确。

## P0 必修项

### 1. G 型审查必须拆成 Common / Greeting / 选开三层

问题：`review-template-system.md` 把“选开模式”写成“在 G1-G7 基础上额外检查”，但 G1-G7 是 greeting-secondary 体系；选开模式不依赖 greeting / selective / secondary。

正确结构：

```text
G-Common（两种模式都必查）
- 共用层角色/场景/事件/语料 content 零 {{user}}
- 系统条目例外需说明
- 人物关系锚点无相对称谓漂移
- 交付含“导入卡片世界书”说明

G-A Greeting 模式专项（备选，发布/不想让玩家操作世界书UI时）
- selective=true + secondary_keys
- greeting首行身份标记
- greeting-secondary 对齐
- <Lore>视角隔离/多轮维持

G-B 选开模式专项（默认）
- 身份条目 constant=true, enabled=false
- comment 必须含“选开”（可同时含“身份”）
- content 明确定义 {{user}}
- greeting 视角中性
- 交付说明：导入世界书 + 每次只启用一个身份
```

### 2. `validate_card.py` 选开模式也必须检查共用层零 `{{user}}`

当前 checks 42-45 的共用层零 `{{user}}` 只在 greeting-mode G 型触发。选开模式只跑 checks 46-47（comment 标注、greeting 身份标记误用），会漏掉共用层视角残留。

建议：抽出 `check_g_common_no_user(entries)`，在 `is_greeting_mode_g or xuankai_entries` 时都运行。排除项仅限 system/OOC/status/system_prompt、身份条目、greeting 视角段。

### 3. 世界书触发专项审查应进入交付门控

`audit_worldbook_triggers.py` 不能只在“交接/修卡”时使用。新卡交付前也应生成触发矩阵报告，用于发现：

- 核心角色/威胁档案只有“档案/设定”key；
- 核心档案所有 opening 不触发；
- 速览低于 250-350 中文字且不自足；
- 泛 key 误触发；
- selective/secondary 被忽略或不自然；
- Prompt Itemization / API usage 与脚本估算不一致。

建议新增 `references/audit/世界书触发专项审查模板.md`，并在 `SKILL.md §3.4` 中作为 `①b` 或独立步骤纳入交付门控。

### 4. 社区反馈修卡必须形成全卡闭环

旧 `card-repair-workflow.md` 偏“外科手术式单点修复”，不够覆盖当前社区反馈风险。标准流程应为：

```text
0. 备份原卡 + 记录反馈截图/原话
1. 分类反馈：内容错误 / 关系称谓 / 触发异常 / 违禁词 / Discord简介 / 结构导入
2. 不只改截图处：按反馈关键词生成全卡 scan list
3. 修改前跑 baseline：validate_card.py + audit_worldbook_triggers.py（必要时 enrichment_self_check.py）
4. 修改：只改目标条目与波及条目；大段中文 file-first
5. 修改后跑：validate_card.py
6. 修改后跑：audit_worldbook_triggers.py -o 修卡触发回归报告.md
7. 若新增/重写内容：跑 enrichment_self_check.py
8. 若涉及 Discord/社区发布或过审：只扫描简介/帖子等平台可见文案；不扫描卡 JSON/世界书/开场白
9. 改动范围 >15条或 >50% 条目 → 升级为完整制卡审查门控
10. 输出修卡报告：原反馈、全卡扫描结果、修复项、验证结果、遗留风险
```

## P1 应修项

1. `multi-perspective-card-design.md` 顶部应标注：**当前默认 G 型是选开模式，本文件仅描述 greeting 模式备选**。默认流程先读 `manual-toggle-identity-pattern.md`。
2. `SKILL.md §1.1` G 型原型表不应只写“selective keys + greeting身份标记”；应改为“默认选开，发布场景可用 greeting+selective 备选”。
3. `validate_card.py` check 46 与文档不一致：建议统一为身份条目 comment **必须含“选开”**，便于 ST UI 识别。
4. `validate_card.py` check 47 的身份标记误用检测太窄，应覆盖 `身份：/身份:/苦主视角/寝取者视角/NTL视角` 等。
5. 选开身份条目结构检查应验证：`constant=true`、`enabled=false`、content 前 300 字明确定义 `{{user}}`，不得混用 `selective=true` 或非空 `secondary_keys`。
6. 平台发布禁词表不属于公开核心流程；公开版只保留脚本化的字段覆盖审计。
7. `SKILL.md §5.2.1` 中“支线角色档案改档案型 key”必须限定为非核心/冷门/后期按需条目；核心主档案不得只有 `角色名档案`。
8. 修卡模板升级条件不能只看改动数量；只要改 `keys/secondary_keys/selective/constant/enabled/prevent_recursion/system_prompt/G型身份条目/greeting身份标记`，即使少于 15 条也要升级为触发专项或全量审查。

## P2 优化项

- `SKILL.md §3.4` 内容层模板表中“所有卡型（3+同场景NPC时）”行重复，可删一处。
- `review-template-system.md` 标题“7模板·含G型”不再适合当前原型数量；建议改成“基础模板 + 原型专项”。
- 审查指令中的 `references/workflows/cross-window-fix-verification.md` 路径应保持指向当前工作流文档。
- Discord 禁词列表建议以公开版不分发平台专用禁词表，避免与脚本常量双份漂移。

## 最小修复顺序

1. 拆 G 型审查体系为 Common / Greeting / 选开。
2. `validate_card.py` 为选开模式增加共用层零 `{{user}}` 检查。
3. 把 `audit_worldbook_triggers.py` 纳入交付门控，新增触发专项审查模板。
4. 重写 `card-repair-workflow.md` 的社区反馈修卡闭环。
5. 更新 Discord 简介/帖子文案敏感词扫描模板（不扫描卡本体）。
