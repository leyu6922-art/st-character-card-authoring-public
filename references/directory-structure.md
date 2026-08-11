# references/ 目录结构说明

> 更新日期：2026-07-11
> 文件总数：76个 + 4个顶层核心文件
> ⚠️ SKILL.md当前101KB，已超100K patch限制，需执行瘦身方案（方案文档在 build/v3/方案_SKILL瘦身.md）

## 顶层文件（高频访问，每次制卡都用）

| 文件 | 用途 |
|------|------|
| `game-mechanics-template-library.md` | 12个通用游戏机制模板+NTL变体，按需选择 |
| `card-audit-checklist.md` | 自动化+Agent双轨审查流程v4.3 |
| `guardian-card-lessons.md` | 守护卡制作经验（v1→v2→v3迭代教训） |
| `ntl-transformation-framework.md` | NTL转换核心框架（苦主→夺回） |

## 子目录分类

### cases/ (14 files, ~56KB)
案例研究——每张已完成卡的制作记录。
文件命名：`case-{卡名}.md`

### ntl/ (8 files, ~50KB)
NTL/NTR专属设计——视角转换、夺回路线、变体模板、关系矩阵。
核心文件：`ntl-transformation-framework.md`在顶层。

### audit/ (7 files, ~30KB)
审查与验证——检查清单、交叉验证、内容矛盾检测、质量评估、治理报告模式。

### workflows/ (11 files, ~59KB)
工作流——增强/扩充/并行构建/子代理修改/变体卡生产/模板评估/规划就绪评估/多章小说→卡/卡规模判定/多参考卡设计。

### formats/ (8 files, ~37KB)
格式规范——ST原生角色卡/世界书格式、JSON schema、条目结构、清理同步、组装陷阱、双路由架构。

### discord/ (3 files, ~6KB)
Discord发布——简介格式、违禁词表、作品集格式。

### st-technical/ (11 files, ~63KB)
ST技术调试——reasoning parser、regex placement分析、截断诊断、脚本化模式、SP数据库兼容、execute_code字符串转义/临时文件污染、Unicode编码陷阱。

### design-patterns/ (5 files, ~54KB)
设计模式——玩法型卡、守护卡原型、开放性卡、token优化选择性触发、递归触发链。
核心模板库在顶层。

### misc/ (5 files, ~24KB)
杂项工具——中文小说对话提取、greeting文件组装、pitfall库、已知IP外貌验证、子代理JSON构建模式。

## 脚本

`scripts/` 目录（不在references/下）：
- `validate_card.py` — 35项自动审查
- `analyze_token_load.py` — token负载分析
- `fix_card_format.py` — 格式自动修复
- `safe_write_card.py` — 安全写入
- `worldbook-json-converter.py` — 世界书JSON转换（从references/迁入）

## 已知问题

1. SKILL.md 101KB，超100K patch限制，无法通过skill_manage修改 → 需执行瘦身方案
2. 瘦身方案：build/v3/方案_SKILL瘦身.md（目标50KB，19项裁减）
3. 历史本地 references 分类规划（不属于当前仓库，公开导出时不包含）
