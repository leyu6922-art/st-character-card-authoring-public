# Manifest 驱动的一次交付门控

> **日常生产唯一入口：** `assemble → run_delivery.py`。
> `run_delivery.py` 只编排并显示策略，真正审计仍由 `final_delivery_gate.py` 完成。
> **重要边界：** `run_delivery.py` 不执行项目自己的 `prepare/generate → make_contract → assemble`；Agent 必须先实际组装，再把最终 JSON 交给 runner。`require_build=true` 只要求并审计 canonical build 链，不是“自动替你构建”。

## 1. 为什么需要 manifest

以前的流程会先无条件执行 validate、trigger、source、enrichment、build-sync 等多个专项脚本，再重复执行 final gate。这样既重复读取大 JSON，也容易发生 source、Greeting 或 build 参数没有进入最终门控的静默漏检。

`build_manifest.json` 把项目事实显式化：原型、路由、Greeting 模式、canonical source、是否可重建、叙事模式和附加合同。Manifest v2 还可显式声明 `event_mode`、`route_policy`、`corpus_mode`；Runner 必须先打印每项 `RUN/SKIP` 与原因；任何 required 项不得静默跳过。

## 2. 最小 manifest

从 `templates/build-manifest.example.json` 复制到项目根目录并按实际填写。该模板是可解析的骨架：默认关闭 source/build 专项，避免虚构路径产生假计划；小说改编新建卡必须在交付前改为真实 source + `source_coverage_required=true`，可重建项目必须改为 `require_build=true`：

```json
{
  "schema_version": 1,
  "prototype": "A",
  "prototype_confidence": "high",
  "prototype_reason": ["玩家身份明确为苦主", "无第二个完整可玩身份"],
  "content_mode": "r18",
  "routing_mode": "flat",
  "greeting_mode": "player_prose",
  "greeting_appendix_standard": "none",
  "require_build": true,
  "canonical_sources": ["sources/chapter-01.txt"],
  "source_coverage_required": true,
  "source_coverage_minimum": 0.6,
  "player_agency_modes_required": false
}
```

### 必填与组合约束

| 字段 | 规则 |
|---|---|
| `schema_version` | 当前必须为 `1` |
| `prototype` | 必填；自动判型结果写入此处，不是让 final gate 猜测 |
| `greeting_mode` | `player_prose` / `prose_plus_director_appendix` / `ai_trigger` |
| `greeting_appendix_standard` | `none` / `stage_brief_v1`; `prose_plus_director_appendix` 默认且必须为 `stage_brief_v1` |
| `routing_mode` | `flat` / `native_greeting_title` / `simple_stage_route` |
| `source_coverage_required=true` | 必须提供非空 `canonical_sources` |
| `routing_mode=native_greeting_title` | 必须提供 `stage_entry_contract` |
| `routing_mode=simple_stage_route` | 必须提供 `preset` 和 `preset_policy` |
| `require_build=true` | 必须保留可重建的 canonical build 链 |

| `semantic_manifest` | 可选；声明时必须是相对 `build_manifest.json` 的语义模块 manifest 路径，Runner 会把它接入统一语义门控；不声明则保持 legacy/non-semantic 路径 |
| `trace.planned_modules` | 可记录本项目计划加载的规范模块，供交接回溯；它**不能**证明 Agent 已读取文档，不能作为 final gate 通过条件。 |

> **执行字段优先级：** 规划书中的 `architecture_mode` 可用于设计说明；真正决定 runner/final gate 分支的是 manifest 的 `routing_mode`。阶段架构必须明确写为 `native_greeting_title` 或 `simple_stage_route`，不能只写泛化的“stage_routing”。

## 3. 自动原型判定，不做形式性打断

默认先自动判断原型，将置信度和理由写入 manifest。仅在选择会显著改变**运行架构、玩家身份或交付物组成**时使用 `clarify`：

1. G 型多视角和单视角均合理；
2. `{{user}}` 是苦主、征服者还是观察者存在实质冲突；
3. 原生标题阶段卡和子系统厚条目会产出不同运行架构；
4. 是否绑定预设无法从请求/规划书确定；
5. 原著事实不足而原创分支会改变玩法核心；
6. 用户明确要求先规划或不立即构建。

事件条目数量、内部模板、ID 排列、少量描写库增补等构建细节不应打断一键生产。

## 4. 命令

```bash
python "<card-skill>/scripts/run_delivery.py" <card.json> \
  --manifest <project-dir>/build_manifest.json
```

先看策略但不跑 gate：

```bash
python "<card-skill>/scripts/run_delivery.py" <card.json> \
  --manifest <project-dir>/build_manifest.json --dry-run
```

Runner 输出示例：

```text
有效交付计划：
- card validation: RUN — final_delivery_gate baseline
- source coverage: RUN — 12 canonical source(s)
- Greeting appendix audit: SKIP — greeting_mode=player_prose
- native-stage contract: RUN — routing_mode=native_greeting_title
- build sync: RUN — manifest require_build=true
- Greeting build wiring: 仅当 `greeting_mode=prose_plus_director_appendix` 且 `require_build=true` 时 RUN；比较 `build/all_entries.json` 与最终卡的每条 Greeting
```

## 5. Greeting 模式职责

| 模式 | 通用 validator | 专项审计 |
|---|---|---|
| `player_prose` | 保留既有每条 `≥1400` 下限 | 连贯性、重复、工程残留、场景专属收束 |
| `prose_plus_director_appendix` | 只检查结构和非空 | 自动运行 `audit_greeting_layers.py --appendix-standard stage_brief_v1`；正文与附录分开统计，正文仍按 1400 CJK 门槛，并检查八维阶段简报 |
| `ai_trigger` | 只检查结构和非空 | 阶段标题、当前事实、角色行动、玩家接管点、标题绑定；不拿正文长度凑字 |

这不是给正文型 Greeting 降标准。它只阻止 append/trigger 卡为满足不适用的全局长度规则而向模型可见正文灌水。

## 6. 失败后的诊断路径

`run_delivery.py` 失败后，先读 final report 的失败 Gate，再只运行对应专项脚本以定位：

```text
semantic module FAIL → audit_semantic_modules.py（先确认 build_manifest.semantic_manifest 指向当前 semantic manifest）
source coverage FAIL → audit_source_material_coverage.py
build sync FAIL      → check_build_sync.py
Greeting build wiring FAIL → audit_greeting_build_wiring.py；先回到 prepare/generate → make_contract → assemble 链修复 canonical Greeting 源
native contract FAIL → audit_stage_entry_contracts.py
trigger FAIL         → audit_worldbook_triggers.py
content FAIL         → enrichment_self_check.py
```

专项脚本仍是诊断工具，未被删除；日常路径仅取消无条件预跑。

## 7. 运行时负载

`analyze_token_load.py` 是只读诊断器。它按 Greeting/提供文本计算常驻、触发、阶段四包等类别，并给出**粗略字符估算**；不设硬 token cap，也不自动改 key 或删内容。必须与 ST Prompt Itemization / WorldInfoInfo 的实机装载结果对照后，才可提出项目级阈值。

## 8. Manifest v2：四维运行架构

Manifest v2 将以下概念严格分开，禁止用 `routing_mode` 代替叙事或状态合同：

| 维度 | 字段 | 回答的问题 |
|---|---|---|
| 叙事架构 | `narrative_mode` | 故事如何演化：`linear_stage`、`soft_stage`、`open_sandbox` |
| 内容装载 | `routing_mode` | 世界书/阶段条目如何进入上下文：保留 `flat`、`native_greeting_title`、`simple_stage_route` |
| 运行驱动 | `runtime_driver` | 谁驱动运行：`native_st` 或 `external_extension` |
| 运行状态 | `runtime_state` | 谁保存、谁写入、从哪里恢复、可靠性是什么 |
| 事件语义 | `event_mode` | 情境种子、候选事件还是脚本序列 |
| 路线主导 | `route_policy` | 玩家主导、引导路线还是锁定路线 |
| 素材策略 | `corpus_mode` | 精选锚点还是扩展原文语料；不改变运行时事实/状态合同 |

最小 v2 声明：

```json
{
  "schema_version": 2,
  "prototype": "A",
  "narrative_mode": "soft_stage",
  "routing_mode": "native_greeting_title",
  "runtime_driver": "native_st",
  "event_mode": "guided_candidate",
  "route_policy": "guided",
  "corpus_mode": "expanded_reference_corpus",
  "event_policy": "candidate_pool",
  "transition_policy": "outcome_based",
  "narrative_contract": "narrative-contract.json",
  "runtime_state": {
    "authority": "prompt_record",
    "update_mode": "model",
    "contract": "runtime-state-contract.json",
    "recovery_policy": "latest_valid_record",
    "reliability": "best_effort"
  }
}
```

v1 项目保持原行为：不要求新合同、不根据旧 `routing_mode` 猜测模式，报告内部只标记 `narrative_mode=legacy_unspecified`，并跳过新增叙事专项。v2 才运行按模式分流的合同审计。

合同职责也必须分离：

```text
stage-entry-contract.json  → 技术路由、阶段包、触发、条目职责
narrative-contract.json     → 事实、信息边界、候选事件、阶段结果转移
runtime-state-contract.json → 状态字段、事件状态、写入者、冲突、恢复
```

模式与专项审计：

| 模式 | 必跑 | 明确跳过 |
|---|---|---|
| `linear_stage` | ordered-step、runtime-state | candidate-event、soft transition、open-sandbox |
| `soft_stage` | candidate-event、outcome transition、确定性路径模拟、runtime-state | ordered-step、open-sandbox |
| `open_sandbox` + `event_mode=open_situation_seed` | open-sandbox入口、开放情境事实/代理审计 | 固定候选结果、阶段 transition、ordered-step、三路径模拟 |
| `open_sandbox` + `event_policy=none`（legacy v2） | 结构化人物/场景/行为入口、NPC自主性 | candidate-event、阶段 transition、ordered-step |
| `open_sandbox` + `event_policy=candidate_pool`（legacy v2） | open-sandbox入口、candidate-event（stages/event.stage可选） | 阶段 transition、ordered-step |

open-sandbox 构建元数据统一放在世界书条目的 `extensions` 中，不写入模型可见正文；`entry_role` 只允许 `character_entry`、`scene_entry`、`behavior_entry`、`system_constant`、`event_candidate`。只有同时满足 `sandbox_entry=true`、根字段 `enabled=true`、`constant=false`、`selective=true`、非空自然 `keys` 以及唯一 `extensions.sandbox_entry_id` 的交互条目才参与开放入口计数；同类入口不能复用完全相同的 key 集合。`event_policy=candidate_pool` 可以只用 scopes/context 分组而不伪造 stages 或 event.stage；`transition_policy=none` 时 transitions 必须省略或为空，任何 stage.transition_conditions 也必须为空。

`simulate_freeplay_paths.py` 仅在 `soft_stage` 的 candidate-event 与 transition 专项审计均通过后运行，遍历合同中的每个候选事件和每个阶段转移，模拟 normal、skip、reject、invalidate、transition 五类路径，不代表模型自然语言行为验收。候选事件合同必须显式 `auto_fact=false`，因此“进入候选池”不等于“事实已经发生”；阶段转移还必须声明 `irreversible=true`，并尊重 `blocked_by`。未来阶段事件必须保持 locked，不得在初始状态全部 available。坏合同由 Runner 转换为受控 `NARRATIVE ERROR`，不得泄漏 traceback。

`runtime_driver=external_extension` 不会加入 `routing_mode`。能力状态保留三态：`CAPABILITY_MISSING`（合同/资产/fixture 缺失或不可解析）、`DECLARED_UNVERIFIED`（结构存在但 fixture 未验证）、`VERIFIED`（为未来隔离 fixture 协议保留）。本版本不会把“读取一份声称通过的 JSON 报告”升级为 `VERIFIED`；external extension 当前最多为前两态，dry-run 遇到前两种返回非零。`reliability=authoritative` 还必须提供真正可复现的 `runtime_state_verification` 证据，不能只靠 Manifest 声明。

Runner 先调用统一的 `validate_contract_bundle(manifest, narrative_contract, runtime_state_contract)`，检查三项模式/策略一致性和恢复策略映射；专项审计器接收到不适用模式时必须报 `CONTRACT_MODE_MISMATCH`，不能静默返回成功。独立 CLI 传入 `--manifest` 时也走同一 bundle 校验。

普通框架优先卡可直接参考 `templates/build-manifest.open-sandbox.example.json` 与 `templates/narrative-contract.open-situation-seed.example.json`。严格/引导卡使用 `templates/build-manifest.v2.example.json`。旧 v1 模板仍保持 legacy 行为。所有模式都必须区分“build source 存在”“Prompt 已装载”“AI 采用候选”“事实已确认”；静态门控 PASS 不等于 SillyTavern 实机 PASS。
