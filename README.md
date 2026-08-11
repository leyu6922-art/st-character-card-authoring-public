# SillyTavern 角色卡创作技能 (st-character-card-authoring)

> **公开版说明**：这是经过脱敏的通用制卡流程。私有角色卡、小说原文、案例文件、个人规划、机器路径和未审查的第三方材料不包含在公开版中。发布边界见 [`PUBLIC_RELEASE.md`](PUBLIC_RELEASE.md)、[`SOURCES.md`](SOURCES.md) 与 [`SECURITY.md`](SECURITY.md)。

基于AI Agent的SillyTavern角色卡自动化创作全流程工具链。从小说文本到可导入的角色卡JSON，覆盖世界观构建、角色建模、世界书编写、验证审查全链路。

部分 NTR/NTL、成人主题和其他敏感虚构场景仅作为 18+ 方法论示例；使用者必须自行确认角色成年、内容合规、来源授权和平台规则。仓库不分发小说原文或私有角色卡。

## 🎯 核心能力

### 七种卡原型支持
| 原型 | 说明 |
|------|------|
| NTR恶堕卡 | 苦主视角，女主渐进堕落 |
| 守护卡(反NTR) | 苦主觉醒，夺回路线 |
| NTL征服者卡 | 寝取者{{user}}主动征服 |
| 守护觉醒卡 | 觉醒后反杀路线 |
| 禁忌后宫征服卡 | 多目标+保密系统 |
| 叙事观察卡 | 上帝视角第三人称 |
| **G型多视角卡** | 同一世界书内多个{{user}}视角，选开模式切换 |

### 自动化工具链
- **validate_card.py** — v5.2 分层验证：`ccv3-core` 格式/类型边界 + `leyu-production`（core + 生产交付门控）
- **atomic_write_json.py** — 无 BOM、回读、备份、`fsync`、原子替换与可选 profile 验证
- **migrate_card.py** — 默认 dry-run、仅写新文件、写入前 CCv3 core 验证的非破坏迁移器
- **check_build_sync.py** — 构建源与成品的语义同步验证（entries + 可用 Lorebook metadata）
- **run_delivery.py** — Manifest 驱动的现代项目唯一完整交付入口：编排 Manifest 对齐、语义模块/文本审计、叙事审计并调用最终门控
- **audit_semantic_modules.py** — 模块合同、运行时元信息、开放路线和跨条目引用审计
- **audit_manifest_alignment.py** — Manifest、模块字段、路径和类型对齐审计
- **audit_worldbook_triggers.py** — 世界书触发可达性审查
- **audit_semantic_text.py** — `semantic_markdown_v1` 一级标题、二级主章节、模块章节顺序、`comment ↔ module_type ↔ content_schema` 一致性与缩进 YAML 依赖审计
- **analyze_token_load.py** — 只读 Token/触发负载分析
- **enrichment_self_check.py** — 内容厚度自检
- **final_delivery_gate.py** — 由 `run_delivery.py` 调用的底层综合交付门控；不代替现代 Manifest 完整入口

`fix_card_format.py` 与 `safe_write_card.py` 仅保留为旧脚本的兼容包装器；新构建流程不得以它们作为主入口。

### 设计模式库
- G型多视角架构（selective keys视角隔离）
- NTL Boss角色设计模式
- 三路径事件种子（成功/失败/半成功）
- 意识清醒型NTR设计模式
- 关系矩阵多对多设计
- 禁忌后宫保密系统

## 📁 目录结构

```
├── SKILL.md                          # 主文档（AI Agent指令）
├── scripts/                          # 自动化脚本
│   ├── lib/                          # CCv3 profile、Issue、World Info matcher 共享逻辑
│   ├── validate_card.py              # 分层验证入口
│   ├── atomic_write_json.py          # 原子 JSON 写入
│   ├── migrate_card.py               # 非破坏迁移
│   ├── check_build_sync.py           # 构建/成品语义同步验证
│   ├── run_delivery.py                # Manifest 现代项目唯一完整交付入口
│   ├── audit_semantic_modules.py      # 语义模块合同审计
│   ├── audit_manifest_alignment.py    # Manifest 对齐审计
│   ├── enrichment_self_check.py      # 内容厚度自检
│   ├── audit_worldbook_triggers.py   # 触发审查
│   ├── audit_semantic_text.py        # Markdown 文本合同审计
│   ├── analyze_token_load.py         # 只读 Token 负载分析
│   ├── final_delivery_gate.py        # Runner 调用的底层综合门控
│   ├── fix_card_format.py            # deprecated compatibility wrapper
│   ├── safe_write_card.py            # deprecated compatibility wrapper
│   └── worldbook-json-converter.py   # 世界书格式转换
├── templates/                        # 文档模板
│   ├── plan-document-template.md     # 规划书模板
│   └── semantic-*-v1.md              # 按模块类型拆分的纯文本模板
├── references/                       # 通用参考资料
│       ├── audit/                        # 审查模板与 fixtures
│       ├── design-patterns/              # 设计模式
│       ├── formats/                      # 格式规范
│       ├── ntl/                          # 18+ NTL 方法论
│       ├── st-technical/                 # ST技术文档
│       └── workflows/                    # 通用工作流文档
```

## 🚀 使用方式

本技能设计为 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的 Skill 使用。

1. 将整个目录复制到 `<HERMES_HOME>/skills/creative/` 下；`<HERMES_HOME>` 由本机 Hermes 安装决定，不要照抄某个用户或盘符路径
2. 在Hermes中说"帮我写卡"或"做成角色卡"即可触发

也可作为独立参考：
- `scripts/` 下的Python脚本可直接对ST角色卡JSON运行
- `references/design-patterns/` 是可复用的设计模式文档
- `references/audit/` 是审查模板体系

## ⚙️ 脚本用法

> **现代 Manifest 项目的唯一完整交付入口是 `run_delivery.py`。**
> 它会编排 Manifest 对齐、语义模块审计、`semantic_markdown_v1` 文本审计、叙事审计，并调用 `final_delivery_gate.py`。
> `final_delivery_gate.py` 是 Runner 调用的底层综合门控；专项 `audit_*.py` 只能用于开发、调试和单项复核，不能代替完整交付。

```bash
# CCv3 core：仅检查规范结构与字段类型
python scripts/validate_card.py path/to/card.json --profile ccv3-core --format json

# Leyu production：默认；先通过 core，再运行内容厚度、关系、触发、选开等生产门控
python scripts/validate_card.py path/to/card.json --profile leyu-production --format json

# 先预览迁移（不写任何文件）
python scripts/migrate_card.py path/to/card.json

# 显式写入新的迁移文件；写入前默认通过 ccv3-core 验证
python scripts/migrate_card.py path/to/card.json --output path/to/card.migrated.json --write

# 将已准备好的 JSON 原子写入目标，并在替换前校验 profile
python scripts/atomic_write_json.py INPUT.json OUTPUT.json --validate-profile ccv3-core

# 内容厚度自检
python scripts/enrichment_self_check.py path/to/card.json

# Manifest 驱动的完整交付（现代 semantic manifest 或兼容 legacy manifest）
python scripts/run_delivery.py path/to/card.json --manifest path/to/build_manifest.json

# 专项审计 / 只读 token 分析 / 构建同步（不能代替上面的完整交付入口）
python scripts/audit_worldbook_triggers.py path/to/card.json
python scripts/audit_semantic_text.py path/to/card.json --manifest build/semantic-module-manifest.json
python scripts/analyze_token_load.py path/to/card.json
python scripts/check_build_sync.py path/to/card.json --project-dir path/to/project --require-build

# 底层综合门控（通常由 run_delivery.py 调用；仅在没有 Manifest 编排需求时单独使用）
python scripts/final_delivery_gate.py path/to/card.json
```

## 📋 审查模板体系

6个通用审查模板覆盖全部卡原型：

| 模板 | 用途 |
|------|------|
| 初始卡审查启动模板 | 新建卡的首次审查 |
| 修卡审查启动模板 | 修改已有卡的审查 |
| 守护卡审查启动模板 | 守护/反NTR卡专用 |
| NTL变体审查启动模板 | NTL征服者卡专用 |
| NTR苦主卡审查启动模板 | NTR苦主视角卡专用 |
| 禁忌后宫征服卡审查启动模板 | 禁忌后宫类型专用 |
| 世界书触发专项审查模板 | 世界书触发机制专项 |

## 📌 技术要点

- **G型多视角架构**：selective keys实现视角隔离，选开模式(constant+enabled=false)支持同会话切换
- **世界书触发机制**：selective条目 = primary key命中 AND secondary key命中
- **Token优化**：常驻条目(keys=[])精简，触发条目按预算分配
- **构建流程**：write_file-first模式避免长内容截断，并行子代理批量生成

## License

本项目原创代码和文档按 [MIT License](LICENSE) 发布。外部小说、角色、预设、教程、图片或其他 IP 不在该授权范围内。
