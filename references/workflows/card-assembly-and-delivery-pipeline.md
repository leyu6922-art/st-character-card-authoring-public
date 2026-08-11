# 角色卡组装 → 交付的可执行管线

> 用于**新建、重组、旧卡加料、阶段卡、配套预设卡**。本文件是 §3.4 的脚本编排入口；不要只从 §7 的脚本清单猜测调用顺序。
>
> **路径约定（必读）：** `<card-skill>` 是 `skill_view(st-character-card-authoring)` 返回的 `skill_dir`；`<preset-skill>` 是 `skill_view(sillytavern-preset-debugging)` 返回的 `skill_dir`。以下命令刻意使用绝对 skill 路径，以便从**项目目录**执行，避免把 `/c/...` 传给 Windows Python 后解析成 `C:\c\...`。当前环境应使用 `skill_dir` 返回的路径或 `<SKILL_ROOT>` 占位符，避免写死用户目录。

## 1. 先分类，再组装

| 情况 | 构建源要求 | 必跑专项门控 |
|---|---|---|
| 新建 / 大改的生产卡 | file-first：`build/all_entries.json` + `assemble_card.py` | `--require-build` |
| 无可靠 build 源的历史手工卡 | 不伪造 build；报告标明 build sync = N/A | 不传 `--require-build`；后续大修先补 canonical build 源 |
| 既有大卡的一轮受控加料 | baseline + manifest | `--enrichment-baseline` + `--enrichment-manifest` |
| 配套预设的 `阶段P#` 简单路由 | 卡和预设必须一并交付 | `--simple-stage-route --preset --preset-policy` |
| 不绑定固定预设的原生标题阶段卡 | 原生标题四包 + `stage-entry-contract.json`；可无 build 源 | `--native-stage-routing --stage-entry-contract <contract.json>` |
| G 型选开 / Greeting 多视角 | 身份底座 + `templates/player-agency-modes.example.json`；双模式默认关闭 | `audit_player_agency_modes.py --require`；按 `identity_toggle` / `feature_toggle` / `system_constant` / `common_content` 分类；普通事件/种子至少3个自然 primary keys，Greeting/route 阶段包例外 |
| 小说 canonical 改编卡 | chapter source manifest + build source | `audit_source_material_coverage.py --source ... --minimum 0.60`；细则见 `source-first-material-and-player-agency-contract.md` |

**禁止混用：** `--simple-stage-route` 与 `--native-stage-routing` 代表两种不同路由架构，交付门控会拒绝同时传入。

## 2. 新建 / 可重建卡：组装顺序

1. 在项目目录建好`build/`内容数据与`assemble_card.py`；组装器必须只读相对路径、从磁盘回读验证，并遵守统一CLI：`python assemble_card.py [output.json]`（可选**第一个位置参数**是输出文件；`check_build_sync.py`会以此形式在临时副本中调用）。
2. 如果项目存在`prepare_build.py → make_contract.py → assemble_card.py`链，必须按该顺序运行；`prepare_build.py`生成`build/greetings.json`后，采用`greeting_mode=prose_plus_director_appendix`时先审源文件：

```bash
python build/prepare_build.py
python "<card-skill>/scripts/audit_greeting_layers.py" build/greetings.json --min-cn 1400 --max-cn 1800 --appendix-standard stage_brief_v1
python build/make_contract.py  # 若项目采用阶段合同
python build/assemble_card.py
python "<card-skill>/scripts/audit_greeting_build_wiring.py" <card.json> --project-dir <project-dir> --appendix-standard stage_brief_v1
```

源Greeting审查失败时不得继续进入`make_contract.py`或`assemble_card.py`。纯`player_prose`/纯`ai_trigger`卡不执行这个专项，但必须在manifest中明确声明模式。
3. 运行组装器产出候选卡；不要在final JSON上继续手工漂移。
4. **如果启用模块化语义 profile**：从 `templates/semantic-module-manifest.example.json` 复制 `build/semantic-module-manifest.json`，完成项目合同、角色/地点模块、投影和可见性字段；在 `build_manifest.json` 填入 `"semantic_manifest": "build/semantic-module-manifest.json"`。统一 Runner 会先调用 `scripts/audit_manifest_alignment.py` 检查 build manifest 与 semantic manifest 的跨合同一致性，再调用 `scripts/audit_semantic_modules.py`；未填该字段时，统一 Runner 会按 legacy/non-semantic 路径跳过新门控。
5. **日常生产路径只运行一次 manifest 驱动的汇总门控，不再无条件预跑全部专项审计：** 从`templates/build-manifest.example.json`复制`<project-dir>/build_manifest.json`，填写真实原型、Greeting模式、路由、build 和 source 要求，再执行：

```bash
python "<card-skill>/scripts/run_delivery.py" <card.json> \
  --manifest <project-dir>/build_manifest.json
```

Runner 必须先打印每项 `RUN/SKIP` 及原因，再调用`final_delivery_gate.py`。若汇总门控 FAIL，才按失败项目运行对应专项脚本诊断；不得把专项预跑 PASS 当成交付结论。完整 schema、自动原型判定和模式分流见`references/workflows/manifest-driven-delivery.md`。
`run_delivery.py` 不会替项目执行 `prepare/generate → make_contract → assemble`；这些步骤必须先由 Agent 按本节第2步实际运行。设置 `require_build=true` 且使用 `prose_plus_director_appendix` 时，final gate 还会自动运行 `audit_greeting_build_wiring.py`，确认 clean build 的 `build/all_entries.json` 仍含完整导演附录并与最终卡逐条一致。
5. 以下专项命令保留为**失败后定向诊断**，或用户明确要求深度审查时使用：

```bash
python "<card-skill>/scripts/validate_card.py" <card.json>
# prose_plus_director_appendix 时才使用；纯正文/纯 ai_trigger 不执行此专项
python "<card-skill>/scripts/audit_greeting_layers.py" <card.json> --min-cn 1400 --max-cn 1800 --appendix-standard stage_brief_v1
python "<card-skill>/scripts/audit_greeting_build_wiring.py" <card.json> --project-dir <project-dir> --appendix-standard stage_brief_v1
python "<card-skill>/scripts/audit_player_agency_modes.py" <card.json> --require
python "<card-skill>/scripts/audit_worldbook_triggers.py" <card.json> -o <trigger-report.md>
python "<card-skill>/scripts/audit_source_material_coverage.py" <card.json> --source <chapter-01.txt> --minimum 0.60
python "<card-skill>/scripts/enrichment_self_check.py" <card.json> --r18 --prototype <A|B|C|D|E|F|G>
python "<card-skill>/scripts/check_build_sync.py" <card.json> --project-dir <project-dir> --require-build
```

6. 需要手动复核 CLI 参数或排查 runner 时，才选择下方的 final gate 原始命令。单脚本 PASS 不能代替汇总门控。

## 3. 汇总门控命令

### 普通新建 / 可重建卡

```bash
python "<card-skill>/scripts/final_delivery_gate.py" <card.json> \
  --project-dir <project-dir> --prototype <type> --require-build
# greeting_mode=prose_plus_director_appendix 时在上面命令追加：--greeting-layer-audit --greeting-appendix-standard stage_brief_v1 --greeting-mode prose_plus_director_appendix
# 且 `--require-build` 时，final gate 自动追加 source/artifact Greeting 接线审查：`audit_greeting_build_wiring.py`（Runner 计划名称：`Greeting build wiring`）
# ai_trigger 时追加：--greeting-mode ai_trigger
# player_prose 使用默认模式，不追加 Greeting-layer 专项
```

`final_delivery_gate.py` 在 `--prototype G` 时自动要求双选开合同；其他新卡在上述命令中追加 `--require-player-agency-modes`。**小说 canonical 改编卡还必须在同一条 final gate 命令中重复传入每个 `--source <chapter.txt>`，可选传 `--source-coverage-minimum 0.60`（默认也是 0.60）；传入 source 后，最终门控会实际运行原文覆盖审计，而非只依赖前面的单脚本报告。**只有旧卡明确维持历史构造时，才可额外传入 `--legacy-player-agency-modes`；新卡不得使用该豁免。

### 受控加料候选卡

```bash
python "<card-skill>/scripts/final_delivery_gate.py" <candidate.json> \
  --project-dir <project-dir> --prototype <type> \
  --enrichment-baseline <baseline.json> \
  --enrichment-manifest <manifest.json>
```

只有 source-of-truth 已齐备时才再加 `--require-build`。历史手工卡不能用缺失 build 的假绿来冒充可重建项目。

### 配套预设 `阶段P#` 路由卡

先从 `<preset-skill>/templates/preset-audit-policy.example.json` 复制 policy 到项目目录，填入真实 route/Core identifiers；再运行：

```bash
python "<card-skill>/scripts/final_delivery_gate.py" <card.json> \
  --project-dir <project-dir> --prototype <type> \
  --simple-stage-route \
  --preset <recommended-preset.json> \
  --preset-policy <preset-audit-policy.json>
```

如果项目规定 prompt 与 `prompt_order` 的 enabled 状态必须一致，policy 设 `enabled_authority: "must_match"`；否则差异仅作为 WARN，不得误报成卡侧路由已坏。

### 独立原生标题阶段卡

**REQUIRED SUB-SKILL：** 先加载 `standalone-card-stage-routing`，按其原生标题四包、Greeting 标题、EJS 禁用/实测边界和 ST 实机验收要求构建；本汇总门控只负责调用其中的两项静态审计，不能替代该专项设计规范。

当前生产协议只支持 `route_source: "greeting_title"`。`ROUTE_STAGE=P#` 属于配套预设/Author's Note 运行时路线，不得伪装成 native standalone stage contract；该外部运行时路线尚未接入本门控。final gate 检测到该类标记（条目 key 以 `ROUTE_STAGE=` 开头，或任一 Greeting 文本含 `ROUTE_STAGE=P#`）会硬拒绝（错误锚点 `STAGE_EXTERNAL_ROUTE_UNSUPPORTED`），本门控结论不得作为该类卡的交付证据。

先把 `templates/stage-entry-contract.example.json` 复制到项目目录并命名为 `stage-entry-contract.json`，按真实阶段和条目 comment 填写，再运行：

```bash
python "<card-skill>/scripts/final_delivery_gate.py" <card.json> \
  --project-dir <project-dir> --prototype <type> \
  --native-stage-routing \
  --stage-entry-contract <project-dir>/stage-entry-contract.json
```

如果项目有 canonical build 源，再额外追加 `--require-build`；历史手工卡不应伪造 build 源。

该 flag 会顺序运行 `audit_native_stage_architecture.py` 与 `audit_stage_card_scripts.py`，覆盖合同声明的全部真实阶段四包、标题 key、`scan_depth=999`、EJS 残留、initvar/MVU/Regex 链。

## 4. 交付判定与人工边界

- `exit 0`：所有已选静态门控通过。
- `exit 1`：存在结构、内容红项、路由、build 同步或指定专项门控失败，不能交付。
- `exit 2`：仅 warning，可在人工确认后交付；该结果必伴随报告文件生成，且必须在报告中逐项说明为什么可接受，不能写成“全绿”。
- `exit 3`：门控自身内部错误，结论无效，修复门控后重跑。
- `exit 4`：CLI 用法错误（含互斥 flag、缺成对参数等 argparse 用法错误）；此时未运行任何门控、不写报告，不得当作审计结论。
- 任何静态结果都**不替代** SillyTavern 导入、Prompt Itemization / WorldInfoInfo、Regex 实际链路、多轮聊天和模型行为测试。

## 5. 新增/改动脚本后的元审查

每次在 `scripts/` 新增、删除或改变交付门控参数后，运行：

```bash
python "<card-skill>/scripts/audit_skill_pipeline.py"
```

它会检查：关键脚本与工作流入口是否存在、可编译、`--help` 可执行、`final_delivery_gate.py` 是否仍暴露管线必需 flag、以及 SKILL.md 是否仍链接本文件。它只验证**流程接线**，不替代各领域脚本的正反例测试，也不声称 ST 实机已通过。
