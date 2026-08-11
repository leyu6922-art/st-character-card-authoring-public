# references/ Directory Map (v3.1, 2026-07-11)

> 9 subdirectories + 4 top-level core files. 77 files total, ~310KB.
> 私有案例和角色卡文件不随公开版分发；公开文档只引用通用方法与脚本。

## Top-Level (high-frequency, every session)

| File | Size | Purpose |
|------|------|---------|
| `game-mechanics-template-library.md` | 37KB | 🔥 12通用模板 + 5 NTL子节 + 3 NTL独立 = 20设计模式 |
| `card-audit-checklist.md` | 7KB | 每次制卡必用的审查清单 |
| `guardian-card-lessons.md` | 9KB | 守护卡核心经验（状态栏/选择系统/构建流程） |
| `ntl-transformation-framework.md` | 13KB | NTR→NTL转换核心框架 |

## Subdirectories

### `audit/` (7 files, ~24KB)
审查与验证：双轨审查流程、内容矛盾检测、质量评估、治理报告模式。

### `cases/` (14 files, ~57KB)
案例方法：公开版只保留可迁移的检查方法，不分发具体角色卡复盘。

### `design-patterns/` (5 files, ~24KB)
设计模式：开放性卡片、玩法型卡片、守护卡原型、递归触发链、token优化。

### `discord/` (3 files, ~6KB)
Discord发布：格式规范、违禁词表、作品集展示模板。

### `formats/` (8 files, ~36KB)
格式规范：ST原生角色卡/世界书格式、JSON Schema、条目结构、双路线架构。

### `misc/` (5 files, ~23KB)
杂项工具：对话提取、开场白组装、陷阱库、IP外貌验证、子代理JSON构建。

### `ntl/` (8 files, ~43KB)
NTL/NTR专有：视角转换、夺回路线、变体卡工作流、关系矩阵、权重分配。

### `st-technical/` (11 files, ~61KB)
ST技术调试：Reasoning Parser、正则placement、截断诊断、脚本化模式、编码陷阱。

### `workflows/` (11 files, ~57KB)
工作流：扩充/增强/并行构建/多章小说/规划书评估/模板评估/修卡流程。

## Also in scripts/

| File | Purpose |
|------|---------|
| `scripts/validate_card.py` | 35项结构自动检查（每次制卡必跑） |
| `scripts/worldbook-json-converter.py` | 世界书JSON转换器（从references/迁入） |
