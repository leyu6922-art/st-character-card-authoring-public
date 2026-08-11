# 原生阶段卡：运行时条目合同门控

> 适用：**原生 Greeting 标题阶段卡**与**分析文档回收后重新编译的阶段卡**。
> 目标：阻止"分析资料直接塞入世界书、P1–P5 首轮不可达、阶段包被普通场景词误触发、人物只靠`角色名档案`死 key加载"的黑丝肥臀类错误。

## 1. 必须先产出 sidecar 合同

在项目 `build/` 或项目根目录创建：

```text
stage-entry-contract.json
```

可复制模板位于 `templates/stage-entry-contract.example.json`，复制到项目目录并按真实阶段集合修改后使用。

合同是**构建元数据**，不嵌入角色卡 JSON，不让模型看见。卡内只放可直接用于叙事的角色、场景、关系与事件素材。

模型可见字段（Greeting、description/personality/scenario、mes_example、group_only_greetings、世界书 `content`）禁止出现：

```text
【源文档：...】
【映射模块：...】
【证据标注：...】
E-001 / E-002 等分析事件编号
```

原文来源、证据等级、合理推演说明应保存到分析文档、build 数据或合同，不得作为世界书正文。

## 2. 合同结构

```json
{
  "schema_version": 2,
  "mode": "leyu_large_native_greeting_stage_v1",
  "architecture_mode": "stage_routing",
  "route_source": "greeting_title",
  "stages": ["P0", "P1", "P2", "P3", "P4", "P5"],
  "required_packs": ["阶段核心", "成人体验", "场景体验", "事件库"],
  "min_units_per_pack": 6,
  "min_unit_chars": 120,
  "phase_memory": {
    "causal_archives": ["白佲·全程因果档案"],
    "memory_gate": "绝对优先级·阶段记忆与叙事可见性协议",
    "system_prompt_anchor_required": true
  },
  "entries": {
    "阶段核心_P0": {"role": "stage_pack", "stage": "P0", "pack": "阶段核心"},
    "成人体验_P0": {"role": "stage_pack", "stage": "P0", "pack": "成人体验"},
    "场景体验_P0": {"role": "stage_pack", "stage": "P0", "pack": "场景体验"},
    "事件库_P0": {"role": "stage_pack", "stage": "P0", "pack": "事件库"},
    "白佲人物速览": {
      "role": "character",
      "natural_keys": ["白佲"],
      "load_examples": ["白佲走进客厅。"]
    },
    "场景·客厅": {
      "role": "scene",
      "natural_keys": ["客厅"],
      "load_examples": ["客厅的灯还亮着。"]
    },
    "白佲·全程因果档案": {"role": "constant"},
    "绝对优先级·阶段记忆与叙事可见性协议": {"role": "constant"},
    "剧情导演与事件推进协议": {"role": "constant"},
    "手动身份选开": {"role": "manual"}
  }
}
```

`schema_version`：新卡一律写 `2`（模板 `templates/stage-entry-contract.example.json` 即 v2）。v1 仅作历史兼容保留；v1 合同携带 `phase_memory` 字段会被解析器直接拒绝，`phase_memory` 的校验与导出仅在 `schema_version=2` 时执行。

`mode` 必须为 `leyu_large_native_greeting_stage_v1`，使用该明确 policy 名以避免普通轻量阶段卡被误套用 6×120 字的大型卡门槛。`route_source` 仅允许 `greeting_title`。

`stages` 必须忠实于原著/规划书。六阶段小说可写 P0–P5；**禁止为迎合旧 P0–P6 审查器凭空编写 P6**。

`required_packs` 的顺序不影响验证（只检查集合一致），但建议按"阶段核心→成人体验→场景体验→事件库"排序以便阅读。

## 3. 条目职责是强制的一对一合同

每个 `character_book.entries[*].comment` 必须唯一，且必须出现在 `entries` 合同中。

| role | 约束 | 用途 |
|---|---|---|
| `stage_pack` | `enabled=true`、`constant=false`、顶层/扩展层 `selective=true`（缺字段报错）、`secondary_keys=[]`（缺字段报错）、`scan_depth=999`、`prevent_recursion=true`、`exclude_recursion=true` | 本阶段四包 |
| `character` | 至少一个 primary key 精确等于 `natural_keys`，且**全部** `load_examples` 能由共享 matcher 触发 | 角色主档案/速览 |
| `scene` | 与 `character` 相同，且不能 `scan_depth=999` | 自然场景补充 |
| `chat_only` | 与 `character` 相同 | 只在自然对话按需加载的规则/资料 |
| `constant` | `enabled=true`、`constant=true`、`keys=[]` | 全阶段稳定规则 |
| `manual` | `enabled=false` | 手动选开或非原生路由模块 |

禁止把 `白佲深度档案`、`人物关系矩阵`、`心理模型`、`阶段行为标志` 当作唯一 primary key。它们是分析分类，不是用户或模型会自然说出的聊天文本。

`constant` 条目禁止 `enabled=false` 冒充常驻规则；`manual` 条目禁止 `enabled=true` 变成自动加载。

## 4. 原生标题阶段四包

每个阶段必须有且仅有：

```text
阶段核心_P#
成人体验_P#
场景体验_P#
事件库_P#
```

每个阶段的 Greeting 的**首个可见内容**必须是唯一的完整标题（允许前置 `<initvar>...</initvar>` 技术块），例如：

```text
【开场：引狼入室·公园初见｜P0】
```

对应四包的 primary keys 必须**精确等于**该阶段所有完整 Greeting 标题；不能用`健身房`、`象棋摊`、`魔镜旅馆`或`P3`短标签代替。

每包至少有 `min_units_per_pack` 个带标签的实质素材单元，且**每个标签后的正文**至少达到 `min_unit_chars` 个非空白字符；两项都必须通过。系统硬下限分别是 **6** 和 **120**，合同只能提高，不能降低。例如：

```text
【事件库_P3_01_场景进入】
【事件库_P3_02_人物反应】
...
【事件库_P3_06_关系余波】
```

素材标签格式为 `【包名_阶段_编号_描述】`（如 `【阶段核心_P0_01_素材】`）。禁止跨包/跨阶段的标签混入，禁止编号重复。

事件库是候选池，不是既成历史。每个候选须包含进入前提、自然引入方式、人物反应和关系/剧情余波。

## 5. Sibling architecture auditor 接线

合同验证通过后，门控自动将合同转换为 manifest 并传入兄弟脚本 `audit_native_stage_architecture.py`，恢复完整的阶段结构审计。合同不可解析时（schema 错误、mode 不匹配等）不会向 architecture auditor 传入 manifest，避免旧 P0–P6 默认审计制造噪声。代码已强制此承诺：此时 sibling 架构/脚本两项审计显式标记为未运行，报告中给出明确 FAIL 行，不回退 legacy P0-P6 默认审计。

## 6. 构建与交付命令

先在项目目录组装卡，再运行：

```bash
python "<card-skill>/scripts/audit_stage_entry_contracts.py" <card.json> \
  --contract <project-dir>/stage-entry-contract.json \
  -o <project-dir>/stage-entry-contract-report.md
```

原生标题阶段卡的最终交付命令必须携带合同：

```bash
python "<card-skill>/scripts/final_delivery_gate.py" <card.json> \
  --project-dir <project-dir> --prototype <type> \
  --native-stage-routing \
  --stage-entry-contract <project-dir>/stage-entry-contract.json
```

项目有 canonical build 源时再额外追加 `--require-build`；历史手工卡不得伪造 build 源，口径与《角色卡组装 → 交付的可执行管线》一致。

遗漏合同、合同未声明条目、任何阶段四包缺失、跨阶段误触发、自然 key 不可触发、分析层残留，均为 `FAIL`，不得交付。

## 7. 边界

此门控证明的是**构建合同与静态触发逻辑**。仍需在 SillyTavern 中通过 Prompt Itemization / WorldInfoInfo 验证真实激活条目、多轮聊天与模型输出质量。它不替代实机测试，也不改变现有 CCv3 core、迁移、build 同步或 R18 内容密度检查。

> 本文件是该合同门控规范的**权威副本**；`standalone-card-stage-routing` skill 中的对应文档（`runtime-entry-contract-gate.md`）为镜像，两者不一致时以本文件为准。

## 8. 与 Manifest v2 叙事/状态合同的边界

`stage-entry-contract.json` 继续保持 schema v2，不升级成所谓“Stage Contract v3”，也不承载运行时状态。它只负责：

- 技术路由来源和阶段标题绑定；
- 阶段列表与现有四包构建厚度；
- 世界书条目职责、触发和阶段记忆锚点。

Manifest v2 的其他职责由独立文件承担：

```text
stage-entry-contract.json  → 如何装载阶段内容
narrative-contract.json     → 故事如何演化、事件如何成为候选、结果如何转移
runtime-state-contract.json → 状态如何读、写、冲突处理和恢复
```

`linear_stage` 可以继续使用现有原生标题阶段合同，但必须另外声明 ordered-step 与 runtime-state 合同。`soft_stage` 仍可使用原生标题路由，却把阶段解释为记忆/信息边界，把阶段内剧情写成可跳过、可拒绝、可失效的候选事件。`open_sandbox + event_mode=open_situation_seed` 不需要阶段四包或阶段转移合同：只审开放入口、事实边界、玩家代理和情境种子语义；`open_sandbox` 的 `transition_policy` 必须为 `none`。未声明 `event_mode` 的旧 v2 `event_policy=none/candidate_pool` 保持原有兼容分支：`event_policy=none` 不需要事件合同，`candidate_pool` 虽需候选事件合同但允许省略 `stages` 和 `event.stage`，不得携带非空 `transitions` 或 `transition_conditions`，同时接受人物/地点/行为多入口审计。

因此，阶段包四包门控不会因 Manifest v2 被删除或改义；新叙事专项由 `run_delivery.py` 按 `narrative_mode` 条件调用。旧 v1 项目和现有 schema v2 阶段合同不需要补写新字段。
