# audit/ 目录文件组织

## 现行体系：6模板审查系统（2026-07-12）

**目录**：7个活跃文件 + `_archived/`（已废弃旧文件）

| 文件 | 用途 |
|------|------|
| `_README.md` | **本文件** — 目录组织说明 |
| `review-template-system.md` | **总索引** — 使用流程、模板清单、设计原则、盲区修复记录 |
| `初始卡审查启动模板.md` | **模板1（结构层）** — 所有卡审查的第一步，7步流程 |
| `NTR苦主卡审查启动模板.md` | 模板2 — A型恶堕卡内容层 |
| `NTL变体审查启动模板.md` | 模板3 — C型NTL逆寝取卡内容层 |
| `守护卡审查启动模板.md` | 模板4 — B/D型守护/觉醒卡内容层 |
| `禁忌后宫征服卡审查启动模板.md` | 模板5 — E型禁忌后宫卡内容层 |
| `修卡审查启动模板.md` | 模板6 — 修卡专用（改动波及范围检查） |

**使用规则**：任何卡审查 = 模板1（结构层）+ 该原型对应的内容层模板。

**两种使用模式**（所有模板支持）：
- **制卡流程内**（agent自审）：直接读取模板内容，按步骤逐项执行
- **交叉验证**（用户手动）：复制模板内容→替换 `[方括号]` → 新Hermes窗口发送

**脚本路径**：所有模板中的 `validate_card.py` 引用使用正斜杠路径 `<HERMES_HOME>/skills/creative/st-character-card-authoring/scripts/validate_card.py`，Windows/Linux 通用，不依赖工作目录。

## 已废弃的旧审查文件

旧文件已移至 `_archived/` 目录（1个已彻底删除）。以下文件是6模板体系之前的产物，**已被上述模板取代**：

- `initial-card-review-template.md` — **已删除**。旧版初始卡审查（3565B，6步简化版），已被 `初始卡审查启动模板.md`（5811B，7步+弹性标准）彻底取代
- `card-audit-checklist.md` / `card-audit-workflow.md` — 旧审查清单/工作流
- `card-cross-verification-workflow.md` — 交叉验证工作流（部分内容已融入模板1）
- `card-governance-report-pattern.md` — 治理报告模板（仍可用于格式参考）
- `card-quality-assessment.md` / `character-card-audit-checklist.md` — 旧版卡质量评估
- `content-contradiction-checks.md` — 内容矛盾检测
- `flexible-review-standards.md` — 弹性审查标准（已融入模板1 Step 3）
- `quality-check-instruction-template.md` — 质检指令模板
- `review-template-blindspots.md` / `review-template-coverage-gaps.md` — 盲区/覆盖度分析（已汇总到 review-template-system.md）
- `skill-maintenance-checklist.md` — Skill维护清单（非审查模板）
- `validate-checklist-detail.md` — 验证清单详情
