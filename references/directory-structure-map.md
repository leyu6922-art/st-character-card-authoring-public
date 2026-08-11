# references/ 目录结构（v3.1，2026-07-11重组）

```
references/
├── card-audit-checklist.md        ← 顶层核心（高频访问）
├── game-mechanics-template-library.md ← 顶层核心（游戏机制模板库v3.1）
├── guardian-card-lessons.md       ← 顶层核心（守护卡经验）
├── ntl-transformation-framework.md ← 顶层核心（NTL转换框架）
├── audit/              (7 files) — 审查清单、验证工作流、交叉验证
├── cases/              — 私有案例目录（公开版不随仓库分发）
├── design-patterns/    (5 files) — 设计模式（开放性/玩法型/递归触发链等）
├── discord/            (3 files) — Discord发布规范与违禁词
├── formats/            (8 files) — ST世界书/角色卡JSON格式规范
├── misc/               (5 files) — 杂项工具（对话提取/命名/IP外貌验证等）
├── ntl/                (8 files) — NTL/NTR相关（视角转换/夺回路线/关系矩阵等）
├── st-technical/       (11 files) — ST技术调试（截断/正则/脚本/PNG/编码等）
└── workflows/          (11 files) — 工作流（增强/扩展/并行/计划书/修卡等）
```

## 快速查找指南

| 要做什么？ | 去哪找？ |
|-----------|---------|
| 写角色卡JSON格式 | `formats/worldbook-entry-structure.md` |
| 写世界书条目 | `formats/wb-entry-json-schema.md` |
| NTR/NTL转换 | `ntl/ntl-transformation-framework.md` |
| 审查角色卡 | `audit/card-audit-checklist.md` |
| 发Discord | `<PLATFORM_FORMAT_TEMPLATE>` |
| 游戏机制模板 | `game-mechanics-template-library.md`（顶层） |
| 并行构建大型卡 | `workflows/parallel-large-card-workflow.md` |
| 修卡/修复错误 | `workflows/card-repair-workflow.md` |
| ST截断/正则问题 | `st-technical/` 目录 |
| 看案例怎么做的 | `cases/case-*.md` |

## 注意

- 顶层4个文件是最常访问的核心参考，不进子目录
- `scripts/` 目录在 `references/` 的上级（`st-character-card-authoring/scripts/`）
- validate_card.py 在 `scripts/validate_card.py`，不在 references/
