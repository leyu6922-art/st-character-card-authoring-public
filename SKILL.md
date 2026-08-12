---
name: st-character-card-authoring
description: 'Leyu 的 opinionated SillyTavern 角色卡创作工作流。基于小说生成角色卡JSON，内嵌完整世界书，导入即自动链接。覆盖世界观/角色/规则/状态栏/开场白/剧情/文风全流程，并包含构建、审查和交付门控。它是个人实践发行版，不是官方或唯一标准。支持七种原型：恶堕卡(NTR)、守护卡(反NTR)、NTL征服者卡、守护觉醒卡、禁忌后宫征服卡、叙事观察卡(上帝视角)、多视角内置卡(G型)。大型卡用write_file+terminal+并行子代理批量组装。'
version: '0.1.0'
category: 'creative/sillytavern-content-authoring'
triggers:
  - '帮我写卡'
  - '做成角色卡'
  - '做成skill'
  - '角色卡JSON'
  - '世界书'
  - 'SillyTavern角色卡'
  - 'NTL版'
  - 'NTL变体'
  - 'NTL逆寝取'
  - '逆寝取'
  - '寝取别人'
  - '夺回路线'
  - '守护卡'
  - '反杀'
  - '反NTR'
  - '阻止堕落'
  - '剧情节点系统'
  - '决策树'
  - '苦主版'
  - '视角转换'
  - '警花艳母'
  - '堕落度'
  - '开场白'
  - '剧情节点'
  - '世界书条目'
  - '角色卡加厚'
  - '角色卡增强'
  - '示例游戏项目'
  - '舰娘'
  - '催眠'
  - 'NTR'
  - '隐奸'
  - '隐奸NTR'
  - '隐奸NTL'
  - '隐奸黄毛'
  - '隐奸逆寝取'
  - '隐奸征服者'
  - '破局博弈'
  - '只扮演黄毛'
  - '努力破局'
  - '后宫'
  - '后宫征服'
  - '禁忌母子'
  - '禁忌'
  - '人妻'
  - '做卡'
  - '验证角色卡'
  - '审查角色卡'
  - '检查冲突'
  - '卡审查'
  - '角色卡冲突'
  - '角色卡质量'
  - '卡质量评估'
  - '评估角色卡'
  - '卡评估'
  - '条目审查'
  - '条目质量'
  - '世界书审查'
  - '观察者'
  - '随机线索'
  - '语料库'
  - '对话模板'
  - '信息边界'
  - 'NPC行为'
  - 'NPC独立'
  - '全知'
  - '排队'
  - '并行行动'
  - '空闲行为'
dependencies:
  - hermes-agent
---

# Leyu Opinionated SillyTavern 角色卡创作工作流

> **依赖边界**：本仓库的脚本、模板、参考文档和测试构成可独立检查的工作流材料；在 Hermes 中作为 Agent Skill 触发时需要 `hermes-agent` 主机。原生标题阶段路由、预设调试和真实 SillyTavern 运行时属于可选 sibling/宿主能力，不是此基础 Skill 的隐式依赖。

---

## 0. 快速索引

| 你要做什么 | 去哪 |
|-----------|------|
| 确定做什么类型的卡 | [1. 卡片原型选择](#1-卡片原型选择) |
| 分析参考卡 | [2. 分析阶段](#2-分析阶段) |
| 写开场白 | [3.2 开场白规范](#32-开场白规范) |
| **导演附录最高标准** | `references/design-patterns/greeting-director-appendix-standard.md`（`stage_brief_v1`，正文+附录模式默认启用） |
| 构建条目录入 | [3.3 条目录入](#33-条目录入) |
| 组装JSON | [3.4 JSON组装](#34-json组装) |
| 🆕 日常组装→交付（唯一入口） | 项目 `build_manifest.json` → `scripts/run_delivery.py` → `final_delivery_gate.py`；先读 `references/workflows/manifest-driven-delivery.md` |
| 🚨 做完卡→交付（必做） | **不得只生成JSON就交付**：必须通过 `run_delivery.py`/`final_delivery_gate.py`，回读最终卡、核对构建源一致性，并报告 PASS/FAIL/WARNING；详见 [4. 验证阶段](#4-验证阶段) |
| 🆕 Manifest v2 叙事/状态合同 | [Manifest v2 叙事模式与运行状态](#manifest-v2-叙事模式与运行状态)；四维分离、v1兼容、按模式专项审计 |
| 🧪 **v5.2 规范边界、迁移与回归命令** | `references/workflows/v5.2-validation-and-migration.md`（profiles / atomic writer / non-destructive migrator / fixture / CI） |
| 🆕 **不绑定预设的原生标题阶段卡** | **REQUIRED SUB-SKILL：** `standalone-card-stage-routing`（标题四包、EJS 边界、阶段实机验收）＋ 合同模板 `templates/stage-entry-contract.example.json`（复制到项目目录改名 `stage-entry-contract.json`，schema v2） |
| 验证卡质量 | [4. 验证阶段](#4-验证阶段) |
| 审查卡 | §4.0 审查模板体系 → 选择对应原型模板 |

| 🆕 **Netorase主动送妻（A-N型）** | [§1.0 A型子变体](#a型子变体netorase主动送妻a-n型2026-07-12新增) → {{user}}=主动策划者，非被动苦主 |
| 🆕 **A-N×E 混合型** | §1.0 A-N×E混合型 → {{user}}=参与者+导演，自己操遍全派又主动分享 |
| 🆕 **多视角内置卡（G型·✅POC+生产级双验证·🆕决策树第一优先级）** | §1.4 多视角内置设计 → 小说有苦主+NTL双线 → **强制G型**。greeting模式（发布）or 选开模式（自用/中途切换）。完整设计规范: `multi-perspective-card-design.md` + `manual-toggle-identity-pattern.md` |
| 🆕 **Discord 发布文案审查** | §5.3 / §5.3.1 → 仅发布简介/帖子需要扫描平台违禁词；不扫描角色卡 JSON 正文。 |
| 🆕 **交付前加料自检** | §3.5 加料自检 → 按 Manifest `event_mode`/`corpus_mode`/`route_policy` 条件化；legacy/严格卡保留旧红线，普通开放卡改查信息增量与玩家代理 |
| Token超了/截断 | [5.2 Token管理](#52-token管理) + `references/st-technical/trigger-quality-vs-token-load.md`（触发质量 vs 裸 token）+ `references/st-technical/card-vs-runtime-boundary.md`（卡质量 vs 运行环境边界） |
| 发Discord | [5.3 Discord发布](#53-discord发布) |
| 🆕 **发合集（一图流）** | `references/<PLATFORM_FORMAT_TEMPLATE>` → 类脑IAIAS合集频道，3行/卡，标签-一句话，不用📋🎮分段 |
| 🆕 **多NPC信息边界** | `references/design-patterns/npc-information-boundary.md` — NPC间知道什么/感知到什么，所有多角色卡必读 |
| 🆕 **NPC行为独立性** | `references/design-patterns/npc-behavioral-independence.md` — 解决排队式表演，NPC并行行动+空闲行为 |
| 🆕 **跨窗口管道（100+章超大规模小说）** | `references/workflows/multi-chapter-novel-to-card.md` §超大规模处理 + `references/workflows/analysis-document-template.md` — Window1读+分析→Window2构建 |
| 🆕🆕 **ST触发机制（重要！）** | `references/design-patterns/st-worldbook-triggering-behavior.md` — ST不二次扫描已插入条目，触发关键词必须在greeting/chat中。含POC验证实录。|
| 🆕🆕 **世界书触发可达性审计** | `references/audit/worldbook-trigger-reachability-audit.md` + `references/audit/世界书触发专项审查模板.md` — 交付前检查绿灯≠触发、顶层selective/secondary、泛key误触发、逐greeting触发矩阵；运行 `scripts/audit_worldbook_triggers.py <卡.json> -o <审计报告.md>` 生成Markdown报告。|
| 🆕🆕 **触发审计失败后全新重做** | `references/workflows/full-rebuild-after-trigger-audit.md` — 当旧卡结构/触发/条目厚度整体不合格时，停止补丁式修卡，重新跑原型判定→源文件统计→新版规划书→触发设计矩阵→v2构建。|
| 🆕 **架构选型与阶段记忆模型** | 阶段路由卡必读：`st-card-architecture-patterns` §一（架构分流）+ §八（三层装载含全程因果常驻层）+ `references/phase-memory-gate-architecture.md`（全程因果档案+记忆闸门+Greeting前史） |
| 🆕🆕 **人物关系矩阵预检** | §2.4.8 — 写角色条目前先做关系锚点表：血缘/婚姻/归属/NTR/NTL归属/视角限定/原文证据 |
| 🆕🆕 **主档案触发铁律** | §3.3 条目录入 — 核心角色档案 key 必须含自然角色名，禁止只用 `角色名档案`；secondary 必须用自然场景词 |
| 🆕 **G型身份、双选开与自然触发契约** | `references/design-patterns/g-type-toggle-and-natural-trigger-contract.md` + `templates/player-agency-modes.example.json` — 身份/功能职责、导演与玩家边界默认关闭、边界优先级、自动门控。新身份卡交付必须跑 `scripts/audit_player_agency_modes.py <卡.json> --require` 与 `final_delivery_gate.py`。 |
| **原文优先、事件 key、语料对象与玩家代理权流程** | `references/workflows/source-first-material-and-player-agency-contract.md` — 事实锚点、自然 key、语料“说话人→对象”和玩家代理权；固定 key 数量/原文覆盖率/语料字数只对声明了相应严格 profile 的卡生效。 |
| **开放兼容模块化档案** | `references/design-patterns/semantic-modular-open-card-architecture.md` + `templates/semantic-module-manifest.example.json`；`build_manifest.semantic_manifest` 启用后由 `run_delivery.py` 调用语义门控 |
| **纯文本语义 Markdown 层** | `references/formats/semantic-module-text-style.md` + `templates/semantic-*-v1.md`；`text_profile=semantic_markdown_v1` 启用后运行 `scripts/audit_semantic_text.py`，只审正文格式和模块章节，不审变量或运行时合同 |
| 查模板 | `references/game-mechanics-template-library.md` |
| 查格式规范 | `references/formats/worldbook-entry-structure.md` |
| 查所有参考文件 | [7. 参考文件索引](#7-参考文件索引) |

---

## 1. 卡片原型选择

创作角色卡前，**先确定原型**。不同原型的设计理念、系统提示词、世界书结构完全不同。

### 1.0 原型判定决策树（🚨 强制判定门控 — 默认自动，不做形式性打断）

**不要看到NTR素材就默认做A型。** 先用以下决策树判断。

做完小说分析后，**第一个动作必须是跑本节决策树**。禁止跳过此步直接开始构建。

**流程**：
1. 按决策树逐分支判断，引用小说具体证据说明为什么走到这个分支。
2. 默认自动选择高置信原型，并把`prototype`、`prototype_confidence`和`prototype_reason`写入项目`build_manifest.json`；高置信结论可直接进入 §2/§3，不得为了形式确认中断一键构建。
3. 只有满足任一条件才用 `clarify`：G型与单视角均合理；`{{user}}`身份存在实质冲突；原生标题阶段/子系统厚条目会改变运行架构；是否绑定预设无法判断；原著事实不足而原创扩展会改变玩法；或用户明确要求先规划/不立即构建。
4. 事件数、条目ID、内部模板、少量素材加厚等普通构建细节不得触发 `clarify`。

```
🆕 小说同时有苦主+NTR男性角色，双方都有完整可玩线？
├─ 是 → G型·多视角内置（第一优先级）
│      玩家自选身份。视角段触发：选开模式（默认/推荐）or greeting模式（发布）
└─ 否 → 继续：

        小说有传统NTR三角关系（苦主+被NTR女性+第三方男性）？
        ├─ 否 → 继续判断非传统NTR出口：
        │   ├─ 只有施暴者+受害者，无苦主/男友/丈夫 → F型·叙事观察卡（{{user}}=无形观察者，详见 §1.3）
        │   ├─ 禁忌关系+多女性，{{user}}是主导征服者 → E型·禁忌后宫（详见 §1.2）
        │   └─ 非NTR/普通题材（纯爱/悬疑/冒险/世界观资料/玩法设定）
        │       → 普通世界书 / 玩法型卡 / 开放性卡（见 §3.8）。先用 clarify 确认玩法目标，不套NTR原型。
        └─ 是 → 继续：

        {{user}}有能力阻止NTR吗？
        ├─ 有，且有机会/时间窗口 → 检查NTR是否"不可避免"
        │   ├─ NTR不可避免 → A型·恶堕卡
        │   │   └─ 子变体检查：
        │   │      ① {{user}}是主动策划者/导演？ → A-N.Netorase
        │   │      ② 用户要求"复仇一定失败/女性彻底恶堕"？ → A+.纯恶堕
        │   │      ③ 核心体验是隐奸/碎片证据/确信度追踪？ → A-Hidden.隐奸恶堕
        │   │      ④ 都不是 → 传统A型（被动苦主）
        │   └─ NTR可避免 → B型·守护卡
        ├─ 有，但原著中觉醒了反杀 → D型·守护觉醒
        ├─ 无，{{user}}是征服者 → C型·NTL
        │   └─ 若核心是隐奸信息战/AI苦主努力破局/幕后操控 → C+.隐奸NTL
        └─ 禁忌关系+多女性 → E型·禁忌后宫
            └─ 子变体检查：{{user}}同时深度参与性爱+主动分享？ → A-N×E混合型
```

**判断标准**：如果一个玩家拿到这张卡，"不需要费很大劲就能做到守护" → 这不是纯NTR卡，应该做守护卡。纯NTR卡的核心是"你怎么挣扎都没用"——男主再强也改变不了结局。

**⚠️ 用户主动要求特定卡型时的处理**（2026-07-13·示例角色项目/G型实证 → 2026-07-15泛化）：即使决策树没有自然走到某分支，用户仍可能主动询问「X型可以做吗」。此时不要机械拒绝——而是评估该卡型可行性（素材是否支撑、是否需要推演扩展、用户是否接受设计差异），确认后跳转到对应设计章节。**决策树是引导工具，不是硬性限制。**

### A型子变体：纯恶堕（不可避免型，2026-07-14新增）

当用户明确要求"无论苦主怎么布局/复仇，最终都一定失败"时，归入A型·纯恶堕子变体。核心特征：

| | 传统A型（被动苦主） | 纯恶堕（不可避免型） |
|---|---|---|
| 苦主行动 | 无力阻止但可以尝试 | **尝试一定失败，且失败会加速堕落** |
| 女性结局 | 堕落但可能留有余地 | **彻底恶堕→对苦主产生羞辱/失望/鄙视** |
| 复仇 | 可能部分成功 | **复仇一定反噬**（如：打残NTR→证据被发现→女性为保护苦主更加臣服NTR） |
| 最终关系 | 苦主可能得到原谅 | **女性主动切断与苦主的关系** |
| 典型代表 | 校园媚黑 | 沉欲之小西的美母教师 |

**判定标准**：用户说"不管怎么布局都失败""最终一定沉沦""恶堕""对苦主有羞辱/失望"→ 纯恶堕。

**设计要点**：
- 反顺从规则/系统条目必须明确写"无论玩家做什么，NTR终将发生"
- 事件种子必须包含"复仇失败"和"恶堕终局"——苦主每步行动都有反噬后果
- 女性堕落轨迹必须包含"对苦主态度转变"段：保护→厌烦→羞辱→鄙视→断绝关系
- NTR角色可被肉体伤害但心理控制不受影响——"控制不依赖肉棒"
- 审查额外检查：苦主的阻止/复仇是否有"反噬后果"设计？是否有"加速堕落"机制？

### A型子变体：Netorase主动送妻（A-N型，2026-07-12新增）

当{{user}}是NTR的**主动策划者/导演**而非被动苦主时，归入A型·Netorase子变体。核心区别：

| | 传统A型（被动苦主） | A-N型（Netorase主动送妻） |
|---|---|---|
| {{user}}身份 | 受害者/观察者，无力阻止 | 策划者/导演，主动安排 |
| 核心体验 | 屈辱+矛盾快感+自欺 | 掌控全局+背德刺激+导演快感 |
| 关键系统 | 堕落度追踪、苦主体验规则 | **淫妻兴奋度追踪、送妻选择系统、魔力监视/远程观看** |
| {{user}}性行为 | 通常无或极少 | {{user}}通常有独立的性伴侣/玩物 |
| 妻子态度 | 被动的、不知情的、被迫的 | 主动配合、知情挑逗、享受游戏 |
| 典型代表 | 校园媚黑 | 示例关系卡（24章/21万字→42条目/307KB） |

**判定标准**：小说中{{user}}是否主动策划/安排NTR？是否有"送妻"的明确动机和行为？→ 是 → A-N型。

**设计要点**：
- system_prompt必须定义{{user}}=主动策划者身份，强调"你不是受害者，你是导演"
- 必须包含**淫妻兴奋度系统**条目（核心！替代传统堕落度追踪）
- 必须包含**送妻选择系统**条目（决定送谁给谁/什么方式）
- 必须包含**魔力监视/远程观看**机制（{{user}}观看NTR场景的方式）
- 系统常驻条目增加"妻子共性规则"——妻子们知情配合，不是被动受害
- 叙事节奏循环改为：日常调情→送妻铺垫→NTR场景→兴奋回味→新目标谋划
- 审查时NTR苦主卡模板的"苦主体验"检查替换为"导演体验"检查

**示例关系卡案例（2026-07-12）**：魔王主动送四位妻子+妹妹给勇者，享受观看快感。42条目/307KB/5开场白。完整Netorase系统设计参考。

### A-N型 × E型 禁忌后宫混合型（2026-07-13识别）

当{{user}}同时满足以下两个条件时，归入A-N×E混合型：
1. **自己深度参与性爱**（像E型：和所有女性都有直接性关系，是后宫核心）— **而非**纯A-N型中{{user}}仅作为"导演/观众"
2. **主动分享/鼓励女性被他人操**（像A-N型：享受绿帽快感，安排分享）— **而非**纯E型中{{user}}独占后宫女性

**典型场景**：门派/家族内部的共享生态——{{user}}是全派的性核心，同时也是推动分享的Netorase导演。

| 维度 | 纯A-N型（示例关系卡） | 纯E型（禁忌后宫） | **A-N×E混合型** |
|------|------------------|-----------------|----------------|
| {{user}}性角色 | 观众/导演 | **参与者**（独占后宫） | **参与者+导演** |
| 后宫女性归属 | 名义上属于{{user}}但实际共享 | **独占** | **既占有又共享** |
| 绿帽体验 | 纯观看 | 无 | 自己操完→分享→观看→再自己操 |
| 核心机制 | 送妻选择系统 | 保密系统+关系阶段 | **淫妻兴奋度+分享选择系统+后宫协调** |
| 典型代表 | 示例关系卡（24章→42条目） | 乖妈妈的小骚屄（3.6万字→23条目） | 示例武侠项目（20章40万字→预50条） |

**判定标准**：小说中{{user}}是否同时有"和后宫女性直接性关系"和"主动安排/享受她们被他人操"两条线？→ 是 → A-N×E混合型。

**设计要点**（混合型的特殊挑战）：
- **送妻选择系统 + 后宫协调并存**：{{user}}既要决定"今天送谁给谁玩"，也要维持和每位女性的直接关系——两个系统必须并行，不能只做一个
- **叙事节奏更复杂**：纯A-N是"日常→送妻→观赏→回味"；A-N×E需要"日常双线(和A做/安排B被C做)→群交融汇→回味双线"
- **男性共享对象也是{{user}}戏友**：{{user}}会和共享对象互操对方的女人——这不是单向送妻，是双向共享生态
- **{{user}}的兴奋双源**：来自看见自己女人被操，也来自自己操别人的女人
- **状态栏需要双维度**：每个女主同时显示"和{{user}}的亲密度"和"被分享的兴奋度"
- **保密需求低**：纯E型有保密铁律，但A-N×E混合型中门派内是公开的共享生态（外部江湖可保持秘密）
- **群交是日常而非事件**：和纯A-N的"送妻是事件"不同，混合型中群交/换妻是日常状态

**典型特征检测**：小说中所有主要女性都和{{user}}有性关系，但{{user}}也主动让她们和其他男人做——不是被动承受也不是纯送妻。共享对象通常是同组织内的成员（同门/兄弟/室友）。**与纯A-N的关键区别**：{{user}}不是旁观者，是参与者；群交不是偶尔的"安排"，是日常。

**设计陷阱**（2026-07-13 session实证）：
- ❌ 只用A-N型的淫妻兴奋度系统，忽视{{user}}和女性之间的独立关系线
- ❌ 只用E型的保密系统——混合型中门内公开，保密对象是外部世界
- ❌ 叙事节奏只按A-N循环走——{{user}}自己操人时不需要"铺垫→送妻→观赏"

### 1.1 原型总表与双版本制作

**双版本制作规则**（用户要求“保留原版”时）：
- **不要覆盖原文件**
- 创建新文件：`{卡名}_守护版.json` / `{卡名}_NTL版.json`
- 原版完全不动
- 新版基于原版增加/修改条目，保留原有内容

| 原型 | 核心体验 | {{user}}角色 | 关键机制 | 典型代表 |
|------|---------|-------------|---------|---------|
| **A. 恶堕卡** | 目睹堕落的矛盾快感 | 苦主（被动承受） | 堕落度追踪、NTR场景渐进 | 校园媚黑 v2 |
| **A+.纯恶堕** 🆕 | 复仇反噬+女性彻底堕落+断绝关系 | 苦主（行动一定失败） | **恶堕铁律**：复仇加速堕落/女性态度转变/苦主被抛弃 | 沉欲之小西的美母教师 |
| **A-N. Netorase主动送妻** | 掌控+背德刺激+导演快感 | 策划者/导演（主动安排） | 淫妻兴奋度追踪、送妻选择系统、远程观看 | 示例关系卡（42条目/307KB） |
| **A-N×E. 混合型** 🆕 | 自己操遍全派+主动分享观看 | 参与者+导演（双重身份） | 淫妻兴奋度+后宫协调并存、双向共享生态、群交日常化 | 示例武侠项目（预50条目） |
| **B. 守护卡** | 阻止堕落的紧张博弈 | 守护者/觉醒者（主动阻止） | 剧情节点、决策树、多结局、唤醒系统 | 校园示例卡、示例角色项目守护版 |
| **C. NTL逆寝取** | 寝取别人爱人的快感 | 新角色（征服者/抢夺者） | 征服线、目标抗力、苦主NPC | 示例角色项目·赌场老板NTL版（225KB/43条） |
| **C+.隐奸NTL** 🆕 | 隐奸迷雾中的信息博弈+征服 | 幕后操控者（全知/布局/破局博弈） | 三层信息差（操控版）+苦主「努力破局」AI+博弈循环+全知监控 | 示例隐奸项目·NTL版（设计阶段） |
| **D. 守护觉醒** | 夺回的热血+唤醒的感动 | 原苦主觉醒（反杀） | 唤醒系统、三层阻力、反转道具 | 示例角色项目守护版 |
| **E. 禁忌后宫征服卡** | 禁忌关系+多女性后宫 | 征服者（儿子/外甥等） | 保密系统、权力反差、关系阶段、多女主协调 | 乖妈妈的小骚屄 |
| **F. 叙事观察卡** | 旁观暴行的沉浸体验 | 上帝视角·无形观察者 | 观察/介入/回避选择系统、旁白引导、NPC自主推进 | 38G巨奶警花被迫献乳 |
| **G. 多视角内置卡** 🆕 | 一卡多身份/视角切换/零残留 | 玩家自选（苦主or征服者） | 默认选开模式（constant+enabled=false手动toggle）；发布/免操作场景可用greeting+selective备选。✅POC+生产级双验证 | 天仙配 G 型卡（45条目/362KB，替代三卡960KB） |

### 1.2 禁忌后宫征服卡（新增 E 型，2026-07-12）

**⚠️ E型不属于NTR体系。** 核心是禁忌感（母子/姨甥/师生等）+ 权力反差（公开身份vs私下关系）+ 多女性协调。

| 特征 | 说明 |
|------|------|
| {{user}}角色 | 征服者——主动方，享受禁忌关系 |
| 核心体验 | 权力反差（高高在上的女人私下是你的）+禁忌快感+多线关系管理 |
| 关键机制 | 保密系统（核心！）、关系阶段（每位女主独立追踪）、公开/私下模式切换、多女主协调 |
| 设计重点 | system_prompt定义{{user}}=征服者身份；保密铁律必须常驻；每位女主有独立的关系阶段和对话库 |
| 与NTL区别 | NTL的{{user}}是寝取者（抢别人女人），E型无\"抢劫\"动态——女主本就属于{{user}}（母子/姨甥）或自愿加入 |

**典型特征检测**：小说中{{user}}与多位女性有禁忌关系（非NTR），且{{user}}是主导方、女性是自愿者 → E型。

**设计要点**：
- 保密是第一原则 — 常驻OOC条目必须强调
- 状态栏显示每位女主当前模式（公开/私下）+ 关系阶段
- 系统条目：OOC防护+保密铁律+文风锚点+叙事节奏+反顺从+行为标志+旁白+剧情导演协议+语料库+人物关系矩阵（10条常驻）。⚠️ 实测：状态栏模板在ST中几乎无效——AI不会按模板格式输出，已从必须常驻中移除。语料库和人物关系矩阵经测试确认为必须常驻——AI首轮需要对话参考素材和关系锚点，否则首轮对话质量和角色关系一致性下降明显。
- 场景条目必须有安全等级（秘窝=S→办公室=B→宴会厅=B）
- 事件用enabled=false种子库模式
- **审查用禁忌后宫征服卡模板**：`references/audit/review-template-system.md` 模板5 — 保密闭环/公开私下双模式/权力反差/场景安全等级

**不同NTR类型需要完全不同的架构设计**，不能套用同一模板。

| NTR类型 | 控制手段 | 卡的核心系统 | 代表案例 |
|---------|---------|-------------|---------|
| 肉体征服型 | 性能力/暴力/权力 | 好感度/堕落度系统 | 道家仙子美母、示例游戏项目 |
| 灵魂操控型 | 超自然道具/催眠 | 道具使用系统+副作用+觉醒线 | 示例玄幻项目（恶魔相机） |
| 认知扭曲型 | 洗脑/常识置换 | 阶段性认知变化系统 | 人妻妈妈娼馆 |
| 经济胁迫型 | 金钱/债务/权力 | 交易系统+债务追踪 | — |
| 身份便利型 | 职务/关系/环境 | 场景触发+身份利用 | — |
| **隐奸型** 🆕 | **信息不对称/碎片化证据** | **三层信息差+确信度追踪+碎片化暗示** | 示例隐奸项目 |
| **隐奸NTL型** 🆕🆕 | **信息战+破局博弈** | **隐奸信息差（NTL操控版）+AI苦主「努力破局」+博弈循环+全知监控** | 绿妹妹隐奸NTR·NTL版（设计阶段） |
| **意识清醒型（植物人NTR）** 🆕 | **身体瘫痪·意识清醒·无法反抗** | **双重视角系统（{{user}}看到的 vs 妈妈感受到的）+「全程知晓」反转锚点+被动式身体反应描写规则** | 昏迷冷艳教师妈妈（134KB/30条/5开场白） |

**隐奸型NTR特殊架构**：详见 `references/design-patterns/hidden-ntr-design.md`。

---

#### 意识清醒型·植物人NTR特殊架构（2026-07-13新增）

**核心设定**：受害者（母亲/妻子等）因昏迷/瘫痪/植物人状态无法动弹，但**听觉和身体感觉完全清醒**。她能听到每一个侵犯者的对话，能感觉到每一次插入和射精，但连闭上嘴巴、皱一下眉头都做不到。最大的虐点是醒来后说「我其实什么都知道」——之前所有的NTR描写都因此获得更残酷的双重意义。

**与普通昏迷NTR的本质区别**：普通昏迷NTR的受害者只是「无意识的肉体」，而意识清醒型NTR的受害者是**全程有意识的精神受害者**。这要求：
- 所有被动式身体反应描写都承载双重含义——{{user}}看到的是生理反射，受害者感受到的是精神折磨
- 必须有一条专门条目描写「昏迷中的意识清醒状态」——她在想什么、她怎么计数度过那几百个小时
- 醒来后的对峙必须是全卡最高潮——平静地陈述事实比愤怒更有杀伤力
- 身体的不可逆改变(子宫脱垂/乳钉/菊穴扩张)不仅是道具——是她意识中真实承受过的创伤痕迹

**特殊系统条目需求**：
1. **被动式身体反应规则**（常驻）：定义昏迷状态下非自愿的神经反射（阴道收缩/乳头挺立/高潮痉挛）——强调「这不是配合，这只是肉体在受刺激时的自然反应」
2. **感官描写锚点**：听觉（每个侵犯者的声音特征/脚步声/对话内容）+ 触觉（体液的温度/插入的深度/疼痛的位置）+ 口腔味觉（精液的咸腥/口水的腥臭）
3. **醒来后对峙锚点**：必含原文对话「我其实……什么都知道……」「你为什么不阻止他们……」，以及平静的绝望和自嘲
4. **身体不可逆改变条目**：所有永久性创伤（子宫脱垂/乳钉/菊穴扩张/阴唇打孔）详细描述——因为这些不是性趣道具，而是她意识中真实承受过的创伤

**核心反转设计**：整个故事中{{user}}以为妈妈只是「无意识的肉体」，在自慰/清理时不会太有罪恶感（反正她不知道）。但妈妈醒来后一句「我什么都知道」瞬间瓦解所有自我安慰——她从头到尾知道每一件事。这个反转必须在所有条目中隐伏暗示（「她的眼角划过一滴泪」「她的眉头在侵犯中微微皱起」），让醒来后的反转有前文支撑。

**典型特征检测**：小说中受害者因外力（车祸/疾病/袭击）陷入无意识状态+作者暗示受害者可能「有感觉」+醒来后与{{user}}的对峙情节 → 意识清醒型NTR。核心不同于肉体征服型——紧张感来自受害者苏醒后的对峙揭示「我什么都知道」，而非肉体抵抗。
- 必须包含「全程知晓」反转设计：在前期昏迷阶段的描写中埋下伏笔（如「她的眼角划过一滴泪」「无意识地皱了一下眉头」），让醒来后的反转有迹可循
- 必须有一条专门的条目描写被动身体反应规则（非自愿神经反射：阴道收缩/乳头挺立/高潮痉挛——强调这些是生理反射不是主观配合）
- 必须有一条条目专门描写醒来后的对峙锚点：平静地陈述事实比愤怒更有杀伤力——「我其实什么都知道」「你为什么不阻止他们」
- 身体的不可逆改变（子宫脱垂/乳钉/菊穴扩张）不仅是性趣道具——是她在意识清醒状态下真实承受过的创伤证据

**灵魂操控型NTR特殊架构**：必须包含道具使用系统(2-3条)+副作用系统(1-2条)+觉醒线(1-2条)+道具进化路线(1条)。与肉体征服型不同——紧张感来自副作用失控+苦主察觉，不是被发现的风险。

---

### 1.3 叙事观察卡

**⚠️ F型不属于NTR体系。** 核心是{{user}}作为无形观察者存在，观看NPC之间的故事展开，可选择介入/回避。

| 特征 | 说明 |
|------|------|
| {{user}}角色 | 无形观察者——不被NPC感知，可观看/介入/回避 |
| 核心体验 | 沉浸式旁观+选择介入时机的博弈 |
| 关键机制 | 观察者规则（system_prompt定义）、NPC自主推进、介入风险评估、旁白引导 |
| 设计重点 | system_prompt必须定义{{user}}=无形观察者身份和三种行为模式（观看/介入/回避）；NPC有自己的行动节奏，不等{{user}}输入；旁白用于引导和机制解释 |
| 与NTR区别 | 无苦主、无征服者——{{user}}是第三方。适合：(1)小说无传统NTR三角关系 (2){{user}}想体验"观看者"视角 (3)施暴者和受害者之间的单线故事 |

**典型特征检测**：小说只有施暴者+受害者两个核心角色，无苦主/男友/丈夫 → F型。

**设计要点**：
- system_prompt必须定义观察者三种行为模式及其后果
- 状态栏增加"观察者"维度（视角/介入度）
- NPC自主行动：施暴者有自己的"计划表"，不因观察者沉默而停止
- 反顺从规则适配：观察者不是万能的，介入有风险
- 旁白大量使用：解释机制、引导行动、展示NPC心理
- 审查用NTR苦主卡模板（最接近的现有模板），但去掉苦主相关检查

**⚠️ NTL≠守护版（关键区分）**：
- **NTL（逆寝取）**：{{user}}是**寝取者**——主动追求/征服别人的爱人。原作苦主变成NPC。核心是"我要抢走你的女人"。
- **守护版/觉醒版**：{{user}}仍然是**原作苦主**——觉醒后夺回自己的未婚妻。核心是"我要把属于我的夺回来"。
- 两者{{user}}身份完全不同，不能混用。

**详细设计**：
- 守护卡/觉醒版 → `references/design-patterns/guardian-card-archetype.md` + `references/guardian-card-lessons.md` + `references/ntl/guardian-transformation-framework.md`
- NTL逆寝取 → `references/ntl/ntl-netori-framework.md`

### 1.4 多视角内置设计（G型，2026-07-13·✅ POC已验证通过）

**问题**：NTR→NTL的"修改后转换"模式存在结构性缺陷——做完整张NTR卡（200KB+）后再翻转视角，AI的注意力已分散到数百KB内容中，隐式视角残留（行为模板假设、触发条件角度、关系描述立场）无论如何审查都会遗漏。这不是模型问题，是**任务结构问题**。6张NTL卡的实证确认。

**方案**：对于同时有NTR和NTL可玩性的小说（苦主+黄毛双方都有完整角色线），**不要分两次生成两张卡**——而是在一次构建中生成**共享世界书+多套视角层**：

- **共用层**：系统条目 + 女性角色档案 + 男性角色档案（中性） + 场景描述 + 事件·事实段（谁做了什么，用角色名不用{{user}}）
- **视角层**：苦主视角段（NTR体验） + 寝取者A视角段（NTL征服） + 寝取者B视角段（NTL掠夺），用selective keys按身份选择性加载
- **身份声明**：每个Greeting首段用 `【▎身份：XXX】` 标记，玩家切换到对应greeting即声明身份。**首行必须包含对应视角段的全套触发关键词**
- **世界书铁律**：事件/角色/场景条目的content中**零{{user}}引用**。全部用具体角色名（李明、麦克、约翰）。系统条目（OOC、状态栏）引用{{user}}是例外——它们是描述"当前玩家"而非描述世界事件

**✅ 已验证的架构事实（天仙配POC，2026-07-13）**：

1. **Selective keys 视角隔离精准** ✅：3种身份greeting各自只加载对应视角段，无关视角零污染。共用层全部身份加载。
2. **多轮维持稳定** ✅：4轮连续对话，每轮API请求中视角段持续存在。Greeting始终在chat history中→ST每轮重新扫描。
3. **触发依赖Greeting，不依赖before_char递归** ✅：ST不二次扫描已插入条目内容。`prevent_recursion: true` 意味着OOC条目内容不会触发视角段。视角段加载**完全依赖Greeting内嵌关键词**。
4. **Secondary key必须与Greeting文本严格对齐** ✅：`苦主视角`≠`苦主体感`，一字之差就全断。POC实测：3个视角中2个因巧合正常，1个因"差一个字"断裂——**不是设计，是巧合**。构建时必须Python验证字符串重叠。
5. **世界书必须导入绑定到角色** ✅：`data.extensions.world`为空不代表世界书不存在——嵌入世界书存储在`data.character_book`中，需在ST中手动"导入卡片世界书"。未导入时`<Lore>`只有角色基础字段。
6. **Token Budget=0不是问题** ✅（Codex源码确认）：`Budget Cap=0`含义是"取消上限"，不是"禁用世界书"。真正预算是`Context% × maxContext`。
7. **prevent_recursion全局true不影响Greeting触发** ✅：prevent_recursion只阻止已插入条目内容递归触发其他条目，不影响chat history正常扫描。

**适用边界**：
| 场景 | 用G型 | 用旧方法 |
|------|--------|---------|
| 小说有明确苦主+NTL角色，双方都可玩 | ✅ | ❌ |
| 小说只有NTL视角（{{user}}天生征服者） | ❌ 过度设计 | 直接用C型 |
| 已有NTR卡，只要NTL版 | ❌ 推倒重来浪费 | 用§3.7转换 |

**Token效率**：一张多视角卡（~45条目/320KB）替代三张独立卡（~120条目/960KB），节省67%。随着可扮演角色增加（≥4人），效率优势更明显。

**构建规则（生产环境）**：
- 视角段条目 `prevent_recursion: true`（防跨视角污染），但**不依赖递归触发**
- 视角段 secondary keys **必须**包含Greeting中出现的全部关键词变体（如`['苦主体感', '苦主视角']`）
- Greeting首行格式：`【▎身份：XXX｜视角描述】 key1 key2 key3`
- OOC条目中指示AI在回复中自然使用身份关键词（长期会话后备维持）
- **🚨 构建后必做验证**：Python确认 `greeting_keywords ∩ entry_secondary_keys ≠ ∅`（每条视角段）
- 交付给用户时必须附带导入说明（ST中"导入卡片世界书"步骤不可跳过）

**POC 验证过程中的四个关键修复**（详见 §5.1 pitfalls T50-T52）：
| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 1 | AI返回元分析模式 | POC卡description/system_prompt为空 | 补角色定义字段 |
| 2 | 世界书完全不加载 | 未执行ST"导入卡片世界书" | 用户手动导入绑定 |
| 3 | 苦主视角段不加载 | secondary key `苦主视角` ≠ greeting中`苦主体感` | 扩大secondary_keys |
| 4 | 误以为Token Budget=0是根因 | 两个设置的混淆 | Codex源码审查修正 |

完整文档和POC验证实录：
- `references/design-patterns/multi-perspective-card-design.md` — G型完整设计规范
- `references/design-patterns/st-worldbook-triggering-behavior.md` — ST触发机制实测
- 天仙配目录下 `多视角卡_动机到验证_完整报告.md` — 完整POC实验报告
- 天仙配目录下 `多视角卡POC实验报告_给Codex.md` — 给Codex的前置信息差报告

#### G型扩展：NTR角色独立化 + 3×3关系矩阵（2026-07-13·示例角色项目实证）

当小说中的NTR男性角色是"同一人多形态"（如富公子/肥猪/小鬼实为一人三形态）时，用户可能要求将其拆分为**完全独立的角色**。此时G型从"苦主+1个NTR"扩展为"苦主+多个独立NTR"，形成**N×M关系矩阵**。

**设计模式**：每个NTR角色对所有女性都有攻略线，但权重不同：
- ★★★主线：详细堕落阶段+专属事件种子+深度行为模板（从原著提取）
- ★★支线：简化堕落描述+1-2个事件种子+基本态度
- ★支线：仅基础互动描述

**3×3矩阵示例（示例角色项目）**：

| NTR角色 | 主线★★★ | 支线★★ | 支线★ |
|---------|---------|--------|-------|
| 富公子·计谋型 | 二娘 | 三娘 | 大娘 |
| 肥猪·蛮力型 | 三娘 | 二娘 | 大娘 |
| 小鬼·伪装型 | 大娘 | 二娘 | 三娘 |

**关键设计决策**：

1. **苦主视角完全开放**：不绑定原著时间线。身份条目只定义行为倾向（绿母癖/出卖冲动），不指定"先出卖谁/什么时候出卖"。玩家完全自主决定出卖哪个妈妈、什么方式、什么顺序。
2. **NTR角色视角半开放**：玩家选择NTR角色后，可以攻略任意一位女性（不只是主线目标），但主线目标有更详细的内容支撑。
3. **身份条目只定义身份和行为规则，不锁定目标**：`content="{{user}}是巨棒征服者·计谋型，擅长用金钱/权势胁迫..."` — 不写"你的目标是二娘"。
4. **NTR矩阵条目拆分为独立条目**：每个NTR角色×每位女性一条关系条目（如"富公子×二娘""富公子×三娘"），不合并。
5. **支线内容差异化**：同一NTR角色对不同女性的攻略方式完全不同（富公子对二娘用胁迫，对三娘用金钱诱惑，对大娘需特殊条件）。

**3×3矩阵的条目规划**：
- 共用层：每位女性1条角色档案 + 每位NTR角色1条角色档案 + 每对关系1条NTR矩阵条目 = N+M+(N×M)条
- 身份层：每位可扮演角色1条身份条目 = N+M条
- 事件种子：按主线/支线权重分配内容量
- 示例角色项目预期：7角色档案+9关系矩阵+4身份+6事件+5系统+5语料 = ~36条

**适用边界**：
| 场景 | 用3×3矩阵 | 用标准G型 |
|------|-----------|----------|
| NTR角色是"同一人多形态"且用户要求拆分 | ✅ | ❌ |
| NTR角色本身就是独立人物 | ❌ 直接用标准G型 | ✅ |
| 苦主视角需要完全自由（不绑定原著时间线） | ✅ | 可选 |
| NTR角色各自只攻一个目标（无交叉） | ❌ 过度设计 | ✅ |

完整设计规范和计划书模板：`示例角色项目_G型计划书.md`（存放于小说目录/世界书创作/）。

#### 选开模式（手动切换，2026-07-13新增）

**G型有两种视角段触发方式。** greeting 模式（默认）适合"发布给社区的卡"，选开模式适合"自己做自己玩、需中途切换身份"。

**原理**：身份条目 `constant=true, enabled=false`，默认不加载。玩家在ST世界书UI中手动启用一条 → {{user}} 立即切换。禁用A启用B → 下一轮 {{user}} 变化。零关键词依赖，不依赖 greeting。

**构建差异**（vs greeting 模式）：
- 身份条目：`constant=true, enabled=false`（非 `selective=true`）
- 不需要 `secondary_keys`、不需要 selective AND 逻辑
- `keys` 可以非空（角色名 + `{{user}}`）——`enabled=false` 时 keys 不参与扫描，无害
- comment 标注「选开」方便玩家识别

**交付说明**：告知用户"导入后打开ST世界书UI → 找到标注「选开」的条目 → 启用一个身份 → 开始"

完整设计规范见 `references/design-patterns/manual-toggle-identity-pattern.md`。

## 2. 分析阶段

> 🚨 **前置条件：必须先完成 §1.0 原型判定。** 高置信结论写入 `build_manifest.json` 后可直接进入本节；只有 §1.0 列出的真实架构/身份歧义才等待用户确认。禁止跳过 §1.0 直接进入本节。

### 2.1 预设优先原则（最高优先级）

**预设是最高优先级。** 所有设计决策遵循 P0-P3 兼容性：

| 等级 | 含义 | 风险 |
|------|------|------|
| **P0** 🟢 | 纯文本通用 | 无 |
| **P1** 🟡 | 格式依赖 | 低 |
| **P2** 🟠 | 功能依赖 | 中 |
| **P3** 🔴 | 脚本依赖（MVU等） | 高 |

**设计决策树**：变量/脚本机制与预设冲突？→ 不支持 → 删除，改为纯文本。

详见 `references/game-mechanics-template-library.md` 兼容性标注。

### 2.2 参考卡分析门控

分析参考卡前做两件事：
1. **卡类型匹配**：参考卡是TRPG冒险卡？→ 对NSFW/NTR卡大部分设计不适用
2. **预设依赖检测**：system_prompt为空+含regex_scripts+大量getvar/setvar → P3依赖，只提取纯文本模式

**铁律**：不盲目崇拜大型卡。469条目的TRPG卡对NSFW卡可移植的设计模式可能只有2-3个。

**提取流程**：解析结构 → 读条目 → 分类 → 提取P0/P1模式 → 标注依赖。

**大型结构化卡案例（2026-07-11）**：从469条目TRPG卡提取7个纯文本模式 → 入库模板13-19。详见 `references/design-patterns/structured-card-run-validation.md`。

### 2.3 计划书策略

- 用户要求时：先写计划书（.md），确认后再继续。**计划书模板**：`templates/plan-document-template.md`
- 用户没要求：直接构建，但结构性决策时暂停确认
- 条目>30或新类型 → 框架先行法：Phase1框架→Phase2核心→Phase3深度
- **🆕 架构选型字段（2026-07-26）**：阶段路由卡的计划书必须填写 `architecture_mode=stage_routing`、`route_source=greeting_title`、阶段列表、全程因果档案覆盖角色表、未来泄漏清单。`author_note`/`ROUTE_STAGE=P#` 当前只属于配套预设外部路线，不进入 native 独立阶段合同；final_delivery_gate 已对 `ROUTE_STAGE=P#` 标记硬拒绝（条目 key 以 `ROUTE_STAGE=` 开头或 greeting 文本含该标记均直接 FAIL，错误锚点 `STAGE_EXTERNAL_ROUTE_UNSUPPORTED`）。缺任意项 → 禁止进入组装。
- **触发审计失败后的旧卡重做**：如果旧卡同时存在 validate 未通过、硬泛key/误触发、secondary被忽略、条目数远低于计划、无事件种子、多主题大条目等问题，不要补丁式修卡。先按 `references/workflows/full-rebuild-after-trigger-audit.md` 重新跑原型确认、源文件统计和新版规划书。
- **世界书触发设计矩阵必填**：计划书阶段先声明每条世界书的触发意图、触发模式、primary/secondary职责、首轮需求与误触发风险；禁止写完内容后随手填keys。详见模板 §5.0 与 `references/audit/worldbook-trigger-reachability-audit.md`。

计划书门控：角色数据≥80% / 对话场景≥3个/角色 / 系统条目≥3 / 世界观≤30% / 触发设计矩阵已填写 / 🆕 阶段路由卡额外：架构选型字段已填写

### 2.4 小说预处理（做卡前必做）

1. **合集拆分**：如果是一个大txt含多个故事（尚香书苑等来源常见）：
   - 先读索引部分（通常前几行），提取各故事标题列表
   - 在正文中搜索各标题的起始行号
   - 按边界提取每个故事为独立文件，存到各自文件夹
   - 删除行号前缀（原始文件行如 `34|内容` → `内容`）
2. **章节拆分**：对每个故事的大txt按章节标记拆分（参考脚本 `references/workflows/novel-collection-split-pattern.py`）：
   - 支持格式：`第一章`/`第1章`/`第0章`/`第一章 标题名`
   - Strip BOM字符（U+FEFF）避免第一章漏检
   - 检测末尾假阳性（文件末尾的`第一章`往往是下个故事预告而非本章节）
   - 第一个章节标记前的内容自动归入第一章
   - 参考脚本模板：`references/workflows/novel-collection-split-pattern.py`
3. **目录去重**：MD5+diff首20行检测重复文件
4. **章节完整性**：对比在线章节目录，补全缺章
5. **角色名混淆检测**：列出共享同字的角色→grep原文交叉验证
6. **已知IP外貌验证**：游戏/动漫角色必须查官方设定，AI生成的外貌大概率有幻觉错误
7. **角色名混淆预检（2026-07-13新增·乖妈妈卡实证）**：列出小说中共享同一字/读音相近的角色名（如「小雪」vs「小雨」），在正文中grep确认各角色真实称呼。特别注意：
   - 姐姐/妹妹名含「小」字 vs 男主昵称也含「小」字
   - 系统条目#0定义的{{user}}名是**唯一正确的称呼来源**
   - 如果同一角色在不同章节有不同称呼（昵称/全名/绰号），用**最常用+最不易混淆**的那个

8. **人物关系矩阵预检（2026-07-15新增·天仙配G型反馈）**：在写任何角色条目之前，先做一张「人物关系锚点表」，写进计划书/分析文档，后续条目录入逐条对照。至少包含：
   - 角色本人身份：真实姓名/昵称/年龄/所属阵营/可扮演身份
   - 血缘/婚姻/从属：谁的母亲、谁的妹妹、谁的父亲、谁的侍妾/丫鬟/奴婢/公公/婆婆/儿媳
   - NTR/NTL归属：被谁征服、名义归属谁、实际侍奉谁、是否后来转归属
   - 视角限定：这条关系是「对林子睿而言」还是「对麦克/詹姆而言」；禁止写无主语的「妹妹/母亲/父亲」
   - 原文证据：每条关键关系至少标注章节或原文关键词，不能凭记忆补。

9. **开放兼容语义建模**：普通开放/改写路线/软阶段卡先读`references/design-patterns/semantic-modular-open-card-architecture.md`，创建`build/semantic-module-manifest.json`，声明`contract_level=lite|standard|full`、`architecture_mode`和唯一`authoritative_route`，再为关键设定标注`evidence_status`与`mutability`。工程标签留在manifest；角色/地点按职责模块写，阶段/事件只做运行时投影。

10. **超大规模小说战略采样（2026-07-15新增）**：当小说超过100章时，逐章读取不可行。使用`references/workflows/multi-chapter-novel-to-card.md`中的采样策略：读前5-10章+后3-5章+用grep关键词定位中间关键章节。总阅读量目标40-80章即可覆盖全部故事阶段。跨窗口管道工作流见`references/workflows/analysis-document-template.md`。

### 2.5 模板匹配（🚨 计划书确认后、构建前强制门控 — 未完成本节禁止进入 §3）

**从分析到构建的桥——选择这个卡需要哪些模板。** 不是“看一眼模板库”，而是逐个过一遍决定“用/不用/改造”。模板选择结果必须写入计划书“系统设计”部分，构建阶段逐条对照实现。

**流程**：
1. 打开 `references/game-mechanics-template-library.md`
2. 对照小说特征逐个模板判断适用性，输出表格：

```
| 模板 | 适用？ | 理由 | 改造？ |
|------|--------|------|--------|
| 1 状态栏 | ✅ | 任何卡都需要 | 标准版 |
| 13 人物描写结构化 | ✅ | 提升角色深度 | 每角色+场景反应差异 |
| 14 叙事节奏控制 | ✅ | NTR/剧情卡必须 | 标准NTR循环 |
| 17 反AI顺从 | ✅ | NTR/对抗卡必须 | +拒绝策略层次 |
| ... | ... | ... | ... |
```

**快速勾选规则**：
- 任何卡：16(文风锚点) + 18(状态行为标志)
- NTR/剧情卡：+14(叙事节奏) + 17(反AI顺从)
- 多场景卡：+19(场景环境锚定)
- 多NPC卡（3+同场景NPC）：+`references/design-patterns/npc-information-boundary.md` + `references/design-patterns/npc-behavioral-independence.md`
- 有超自然道具：+8(道具进化) + `references/design-patterns/structured-item-system.md`
- 30+条目大型卡：+15(事件分段标记) + `references/workflows/section-markers-organization.md`
- 多视角卡套装：+情感滤镜（`references/workflows/variant-card-production-workflow.md`）
- **G型 greeting 模式**：+selective keys设计（`references/design-patterns/multi-perspective-card-design.md`）+ greeting身份标记 + 零{{user}}规则 + ST触发机制（`references/design-patterns/st-worldbook-triggering-behavior.md`）
- **G型选开模式（默认）**：+手动条目开关（`references/design-patterns/manual-toggle-identity-pattern.md`）— `constant=true + enabled=false` 替代 selective keys
- 非NTR/普通世界书/玩法型卡：+`references/design-patterns/open-ended-card-design.md` 或 `references/design-patterns/gameplay-type-card-design.md`，按用户玩法目标裁剪，不套NTR堕落/守护模板。

- **开放兼容内容层**：若`narrative_mode=open_sandbox`、`route_policy=player_led`，或用户明确说“可自由改写/不完全按原著走”，追加读取`references/design-patterns/semantic-modular-open-card-architecture.md`，先建立来源状态×可变性双轴和角色/地点模块清单，再写正文；不能只把线性事件改成“AI自由发挥”。

**铁律**：没有模板匹配 = agent 自由发挥 = 模板库形同虚设。

详见 `references/workflows/template-evaluation-workflow.md`。

### 2.6 系统权重评估（2026-07-13新增）

当原著小说中有"系统"设定时，做卡前必须先判断系统是**核心机制**还是**一次性催化剂**，这决定卡中系统的条目深度和机制复杂度。

**评估方法**（用search_files做统计）：
```python
# 1. 搜索"系统名"在全文中的出现次数和分布
# 用search_files(file_glob='*.txt', path=小说目录, pattern='系统全名', output_mode='count')
# 2. 检查系统名是否在多个章节中出现
# 3. 看后半部分章节是否还提系统
```

**判定标准**：

| 指标 | 核心机制 | 一次性催化剂 |
|------|---------|------------|
| 系统名出现次数 | 50+次，贯穿全篇 | ≤20次，集中在1-2章 |
| 系统名分布 | 所有章节都有 | 仅前1/3出现，后文完全消失 |
| 系统功能是否关键 | 无系统无法推进剧情 | 系统激活后角色自行延续，系统不再被需要 |
| {{user}}依赖度 | 经常提到系统/使用系统 | 前期等系统激活，激活后就不再提 |

**设计决策**：
- 核心机制 → 独立1-2条系统条目（含完整机制说明）+ 可考虑模板八（道具进化）
- 一次性催化剂 → 仅1条背景条目（"系统激活过程"），**不做独立机制模块**
- 中间态（偶尔提及但非核心）→ 1条触发条目，enabled=false种子库模式

**案例**：《示例武侠项目》（2026-07-13）
- "美汁汁儿系统"仅在第6章出现6次，第15章1次 → **一次性催化剂**
- 本质作用：解释"为什么大家接受淫乱"
- 设计决策：仅1条背景条目，不引入任何玩法机制

### 2.7 角色范围优先于内容加厚（2026-07-13新增）

**经验教训**：在投入精力做内容加厚（扩充语料库/加厚阶段特征库/加场景描写）之前，先确认角色范围。否则可能白白投入大量工作，然后被要求裁剪。

**流程**：
1. **规划书阶段**：列出所有角色，标注核心/重要/配角
2. **和用户确认**：哪些角色要，哪些可以砍
3. **只有确认了范围之后**，才进入条目加厚阶段
4. **裁剪发生时**：按照T49流程清理所有残留引用

**适用场景**：任何包含多个角色的卡。用户多次在扩充后又要求精简（天仙配卡、武林卡），说明「先确认范围再加厚」是通用需求。

## 3. 构建阶段

> 🚨 **前置条件：必须先完成 §1.0 原型判定（高置信结果已写入 `build_manifest.json`，或真实歧义已获确认），且完成 §2.5 模板匹配并写入计划书。** 不同原型的构建流程完全不同（A型用并行子代理、G型用双层世界书、B型用决策树等）。跳过原型判定/模板匹配 → 构建必然出错。
>
> 🚨 **构建≠完成。** 本节只覆盖JSON的生成。JSON生成完毕后，先按 §3.4 生成 manifest 并运行 runner；只有用户明确要求深度审查、修旧卡、运行时异常排障或 final report 指向内容/语义问题时，再跳到 §4.0 执行专项复核。

### 3.1 核心产出物

**角色卡JSON**（内嵌世界书 `character_book`），不是独立世界书JSON。

### 3.2 开场白规范

**先按 `build_manifest.json.greeting_mode` 选择结构，禁止混用旧的默认规则**：
- `greeting_mode=player_prose`：自然正文，不带导演附录；每条保留既有≥1400总字符门槛，并人工检查连贯性、重复和场景专属收束。
`greeting_mode=prose_plus_director_appendix`：构建源将 `prose_body` 与 `director_appendix` 分开保存，组装时以独立 `---` 拼接；正文禁止工程语言，附录用特殊 Markdown 排版。正文纯汉字目标约1500、硬下限≥1400，附录不计入；**默认采用 `stage_brief_v1` 最高标准**：每条附录必须有当前节点、人物状态、情报边界、推演方向、关键冲突、角色预计动向、场景氛围、潜在分歧点八个维度，并以具体玩家接管点收束。必须运行 `python scripts/audit_greeting_layers.py` 自动审计；可重建项目在 assemble 后还必须运行 `audit_greeting_build_wiring.py`，确认 canonical build Greeting 与最终卡逐条一致，再完成人工阶段事实/关系/分歧复核。
  - 最高标准的完整格式、内容合同和人工专项见 `references/design-patterns/greeting-director-appendix-standard.md`。
  - 这八维是**阶段/开场专属简报**，不是全局剧情导演协议的复制品；每个 Greeting 必须根据当前正文、规划书、阶段素材和信息边界单独编写。
  - 自动审计只检查层级、最低密度和八维存在；必须另做人工复核：阶段专属性、原文/阶段一致性、未来泄漏、候选语言、分歧后果和玩家代理权。
- `greeting_mode=ai_trigger`：只写标题、当前事实、角色行动与玩家接管点；不套正文型字数门槛，也不跑正文/附录专项。
- 纯`player_prose`/纯`ai_trigger`卡不执行这个专项；`audit_greeting_layers.py`只审 `prose_plus_director_appendix`。
- 视角与玩家称呼：以项目规划书/build manifest确认的`player_anchor`和视角为准，禁止套用固定的“第二人称你”或擅自改用源材料人名；G型选开遵循中性叙事规则，固定玩家角色卡使用已确认的角色名/称呼。
- `greeting_appendix_standard`：`player_prose`/`ai_trigger` 使用 `none`；`prose_plus_director_appendix` 默认且必须使用 `stage_brief_v1`。`run_delivery.py` 会把该声明转为 `final_delivery_gate.py --greeting-appendix-standard stage_brief_v1`，防止只做层级检查而漏掉八维内容合同。
- Greeting数量：以规划书/build manifest声明的`first_mes`、`alternate_greetings`数量和阶段绑定为准；“4固定场景+1随机”只是旧卡案例，不是所有卡的默认硬规则。
- 正文/附录分工：`prose_body`内不嵌状态栏、导演规则或工程字段；采用`prose_plus_director_appendix`时，阶段事实、NPC行动、信息边界和玩家接管点必须放在正文后的`director_appendix`，不能因“纯叙事”旧规则被删掉。

**存放入口**：
- `data.first_mes` — 主开场白（卡片加载默认显示）
- `data.alternate_greetings` — 备选开场白（🔄切换）
- ⚠️ `alternate_greetings` 必须在 `data` 层，**不能在 `data.extensions` 里**
- ⚠️ **不放世界书条目里** — enabled=false的条目不会自动显示

**first_mes 与 alternate_greetings 关系**：两者独立字段，修改一个不会自动同步另一个。first_mes是最有冲击力的场景，alternate_greetings覆盖不同时间线阶段。

**{{user}}视角（仅 `greeting_mode=player_prose` 且规划书确认第二人称时）**：可用"你"描写{{user}}感官体验。`❌ 第三人称：王启坐在桌前` → `✅ 你从一阵剧烈的咳嗽中醒来`。固定玩家角色、G型选开和 `ai_trigger` 必须服从本节开头的 `player_anchor` / 中性叙事规则，不得套用本示例。

**旁白解说**：格式为 `【旁白：解释内容】`（方括号，不带星号——星号会被预设正则隐藏）。在system_prompt中显式声明旁白规则，世界书常驻条目中重复。用于机制解释/风险提示/进度提示/行动引导。每轮1-2段。

**Emoji处理**：BMP字符(U+0000-U+FFFF)可直接用。补充平面字符(U+1F000+)替换为文字描述（`📍`→`[地点]`）。⚠️ `[U+XXXX]`文字标签AI会原样输出，不要用！

**连续开场白链**（仅正文型长篇）：可按原著时间线准备 8-12 个 greeting，并以悬念/过渡句收束；`player_prose` 与 `prose_plus_director_appendix` 的正文遵循本节开头的 ≥1400 门槛，`ai_trigger` 不适用该字数规则。

**扩写策略**：
- 差距<50字：末尾追加感官描写
- 差距50-200字：中间插入心理/环境描写
- 差距200-500字：写扩展段落→读卡→拼接
- 差距>500字：写完整场景段落→批量应用
- ⚠️ 多轮扩写用不同锚点，避免替换错位
- ⚠️ execute_code内联中文每轮只增加70-100字符 → 大段扩写用write_file

### 3.2.1 内容模式决策：框架优先与严格复播分流

Manifest v2 可以显式声明四个互不替代的维度：

```yaml
narrative_mode: open_sandbox | soft_stage | linear_stage
event_mode: open_situation_seed | guided_candidate | scripted_sequence
route_policy: player_led | guided | locked
corpus_mode: curated_anchor_set | expanded_reference_corpus
```

职责必须保持分离：

- `narrative_mode` 是运行架构：是否有阶段入口、状态图和阶段隔离。
- `event_mode` 是事件语义：开放情境提示、候选事件，还是脚本序列。
- `route_policy` 是未来路线的主导权：玩家主导、引导路线或锁定路线。
- `corpus_mode` 只控制素材生产与内容自检，不得改变 Runner、状态写入或事实边界。

普通小说衍生卡默认建议：

```yaml
narrative_mode: open_sandbox
event_mode: open_situation_seed
route_policy: player_led
corpus_mode: curated_anchor_set
```

只有确实需要阶段连续性、固定信息顺序或严格复现原著流程时，才声明：

```yaml
narrative_mode: linear_stage
event_mode: scripted_sequence
route_policy: locked
corpus_mode: expanded_reference_corpus
```

兼容规则：旧 Manifest 没有这些字段时归入 `legacy_unspecified`，继续执行原有门禁，不自动推断为开放卡；新字段只有显式声明后才改变自检与事件审计。

**开放情境种子不是随机事件，也不是隐形剧本。** 每个种子只需提供情境核心、关联人物、当前可观察压力、原著事实锚点、角色倾向、自然入口、玩家接管点和开放方向；不得写死固定动机、发展顺序、成功/失败/半成功路径、状态写入、阶段推进或唯一结局。`auto_fact` 必须为 `false`，玩家可以忽略、拒绝、中断、调查、保护、谈判、反制、逃离或改写方向。

**玩家主导不等于 AI 静止。** NPC、环境和已有矛盾可以产生可观察变化，但不能因为连续几轮平淡就强制调用某个事件种子，也不能把候选情境直接改写成已发生事实。导演协议只在 Manifest/选开明确启用时提供软推进，并始终服从玩家代理权和事实可见性。

### 3.3 条目录入

**make_entry() 函数**：参数名是 `entry_id`（不是 `id`！）。函数定义在 `references/formats/worldbook-entry-structure.md`。

**条目录入必须包含**：
- 31字段 `extensions`（空对象会导致截断！）
- `secondary_keys`（不是 `keysecondary`）
- `insertion_order`（不是 `order`）
- `addMemo: True`、`use_regex: True`
- `enabled` 在条目**顶层**（ST读这个，不读extensions里的）
- `prevent_recursion: True`（全部！False导致递归触发链→截断）

**position映射**：before_char=0, after_char=4。OOC防护和状态栏用before_char。

**常驻条目**：`constant=True` 时 `keys=[]`（必为空，否则触发额外条目→截断）。

**触发条目**：`constant=False` 时必须有 `keys`（缺keys=永远不触发=白写）。关键词用精准短语而非单字。

**主档案触发铁律（2026-07-15·校园示例卡实证+T70教训）**：核心角色/威胁档案的 primary key 必须包含自然角色名或常用称呼（如 `雪乃`、`雪之下`、`雪之下雪乃`），**不能**只有 `角色名档案` 这类人工复合词。`雪乃档案` 这种词永远不会在正常对话中出现 → 深度档案变成死代码。若因 token 考虑需要分层，用「中厚速览（自然名触发→250-350中文字，自足可用）+ 深度档案（复合词触发→按需加载）」模式，但速览本身必须自足，不能依赖「需要时触发档案」。详见 `references/workflows/lightweight-summary-deep-profile-trigger-pattern.md`。

**secondary key 自然词规则**：secondary key 必须是自然场景/阶段词（如 `KTV`、`侍奉部`、`五楼空教室`），不能是备注标签（如 `黑发`、`过膝袜`）或人工档案词。详见 `references/audit/worldbook-trigger-reachability-audit.md` §5.2。

**触发审计铁律（2026-07-15·校园示例卡守护卡实证）**：
- ST 世界书编辑器里的蓝/绿圆点只说明条目类型/启用状态，**不是“已触发”证明**。真实触发只看 chat history（当前 greeting + 用户/AI消息）中的关键词。
- `secondary_keys` 只有在**顶层** `selective=true` 且副词数组非空时才参与 selectiveLogic 判断；`selective=false` 时副关键词会被 ST 忽略。`selective=true` 但 `secondary_keys=[]` 会退化为 primary-only，不是死触发。
- 禁止单字/泛词 primary key（如`家`、`人`、`你`、`学校`、`老师`）——会导致无关场景误触发。场景条目用复合短语/专名：`比企谷家`、`家中派对`、`五楼空教室`。
- 多主题大条目不要多个角色名共用一包内容；任一 key 命中都会加载整包，导致无关NPC/威胁进入 prompt。按角色/威胁对象拆分，或用 selective 精确限定。
- 交付前必须查看 `validate_card.py` v4.8+ 的触发审计输出：每个 first_mes/alternate 分别触发哪些条目、总 token、是否存在泛 key 误触发、顶层/extension selective 是否不一致。
- 需要交接/修卡前，运行独立报告脚本生成完整 Markdown 矩阵：`python scripts/audit_worldbook_triggers.py <卡.json> -o <世界书触发审计报告.md>`。该脚本会输出逐 greeting 触发表、普通句反证、风险条目和修复建议。
- 详细审计流程与报告模板见 `references/audit/worldbook-trigger-reachability-audit.md`。

**角色条目关系锚点（写content前先填）**：每个角色档案开头必须先写3-6行「关系锚点」，再展开性格/经历/行为模板。格式建议：
```
【关系锚点】
- 血缘/现实身份：A是B的妹妹 / C是D的父亲（必须写清参照对象）
- 当前归属：被X征服，名义为X的侍妾/丫鬟/妻/奴；若转归属，写明阶段
- 与{{user}}关系：当{{user}}=某身份时，此人是{{user}}的谁；G型多视角需分别写
- 容易混淆点：不是谁的亲妹妹/亲生母亲/父亲；避免「自己的妹妹」这种无主语写法
```
铁律：**禁止在角色档案中裸写「自己的妹妹」「亲生母亲」「父亲」「妹妹」而不标注参照对象**。统一写「林子睿的妹妹」「麦克的父亲」「林子睿的母亲」。

**条目深度标准（按内容模式执行）**：
- `expanded_reference_corpus` 或 `scripted_sequence`：保留角色≥1500字（核心≥2000字）、场景/系统≥500字等严格建议；启用对应 gate 时，硬失败语义不变。
- `curated_anchor_set` + `open_situation_seed`：不以统一字数或条目拆分数量判断质量；最低要求是每个核心角色有可运行的关系/行为框架，关键角色有少量可追溯原文锚点，情境有自然入口和玩家接管点。
- 所有模式都必须避免抽象空话、死key、重复注水、未标注对白、事实混淆和玩家代理越权。具体信息增量优先于字数增长。

**大型卡并行构建**（条目>30或>100KB）：子代理分批生成 → merge.py合并 → validate_card审查。

**⚠️ 长内容write_file-first模式（T58教训）**：execute_code中内联的长中文字符串（>500中文字）会被静默截断30-63%。严格/扩展语料 profile 构建长角色条目（目标≥1500字/条）时，必须；开放 profile 也应使用同一写入/回读方式，但不为满足字数目标重复注水：
1. 用 `write_file` 把每条内容写到独立的 `.txt` 文件
2. `execute_code` 中用 `open(path).read()` 加载
3. 短内容（<300字，如事件种子/系统条目）可内联
4. **每次写入后回读验证实际中文字数**

### 3.3.1 模块化语义条目合同（开放兼容卡必读）

启用`semantic_profile=modular_semantic_v1`时，角色按`角色/<角色名>/<职责模块>`拆分；地点按`世界观/地点/<地点名>`拆分。事件等模块使用正式命名空间。模块覆盖`条目作用→核心锚点→触发→表现→不应误写→开放变化`；地点需时间、规则、边界和入口。候选事件不得写成已发生或固定路线，否定示例不锁死。Projection 的`semantic_ref`必须指向卡模块或稳定模块 ID。日常只运行`run_delivery.py`：先执行`audit_manifest_alignment.py`，再执行语义门控。

### 3.3b G型多视角卡构建（🆕 2026-07-13·POC+生产级双验证）

**触发条件**：§1.0 决策树判定为 G 型时，用此节替代 §3.7 的分别生成+转换模式。

**🆕 Step 0: 选择触发模式**（构建前先决定）：
- **选开模式**（默认，推荐）：身份条目 `constant + enabled=false`，玩家在 ST 世界书 UI 手动 toggle。同会话内自由切换身份，不依赖 greeting 关键词。
- **Greeting 模式**（备选，适合发布给社区/不希望玩家操作世界书 UI 的场景）：选不同 greeting = 不同身份，通过 selective keys 自动匹配。每次切换身份需新开会话。
- 判断标准：默认走选开。仅在"玩家完全不懂 ST、需要选 greeting 即选身份"时用 greeting 模式。

**G型卡构建不完全遵循常规流程。** 构建前必须先读取 `references/design-patterns/manual-toggle-identity-pattern.md`（选开模式，默认）或 `references/design-patterns/multi-perspective-card-design.md`（greeting 模式，备选）。

**🆕 选开模式构建流程（4步，默认）**：

```
Step 0: 共用层{{user}}清理（从已有卡重构时必须）
  读取所有共用层文件 → content.count('{{user}}')统计
  → 替换为具体角色名 → 验证零残留
  ⚠️ 系统条目可保留{{user}}（描述"当前玩家"），只清理角色/场景/事件/语料
  典型规模：19文件71处替换

Step 1: 共用层构建
  角色/场景/事件条目 → content 零{{user}}
  系统条目 → 多视角版本

Step 2: 身份条目构建
  每个可扮演身份一条：
    constant=true, enabled=false
    keys=[]
    secondary_keys=[]
    selective=false
    position=before_char（角色定义放前面）
    comment="XXX{{user}}（选开）"  ← 标注方便玩家在ST中识别
    content="{{user}}是XXX...（角色定义+行为规则+叙事视角）"

Step 3: Greeting + 交付
  greeting 视角中性（不预设 {{user}} 身份，只写场景/NPC。见 manual-toggle-identity-pattern.md §4.3）
  必须附加"选开模式使用说明"给用户
```

**选开模式验证**：
- Leyu-production contract：`constant=true + enabled=false + keys=[] + secondary_keys=[] + selective=false`；身份靠 ST 世界书 UI 手动启用，绝不靠关键词路由
- validate_card.py 会输出稳定 rule_id：`MANUAL_TOGGLE_KEYS_NONEMPTY`、`MANUAL_TOGGLE_CONSTANT_FALSE`、`MANUAL_TOGGLE_ENABLED_TRUE`
- 手动验证：导入ST → 启用一个身份条目 → 确认 {{user}} 正确 → 禁用 → 启用另一个 → 确认切换

**选开模式硬性检查清单（默认模式必跑）**：

1. 身份条目必须 `constant=true, enabled=false, keys=[], secondary_keys=[], selective=false`，`comment` 含「选开」或「身份」，`content` 明确定义 `{{user}}` 当前身份
2. 普通常驻条目和选开身份条目都必须 `keys=[]`；选开身份的身份说明在 `comment` 与 `content`，不放入 trigger keys
3. 角色/场景/事件/语料等共用层 content 零 `{{user}}`；系统条目和身份条目是例外
4. greeting 必须视角中性：不写身份标记首行，不预设 `{{user}}` 是苦主/征服者，不写绑定某身份的内心或动作
5. `validate_card.py --profile leyu-production` 必须通过；checks 46-47 覆盖「选开」标注与 greeting 身份标记误用
6. 交付说明必须包含两步：① ST 中「导入卡片世界书」；② 打开世界书 UI，每次只启用一个标注「选开」的身份条目


**Greeting 模式构建流程（5步，备选）**：

```
Step 1: 条目分类
  读小说 → 列出所有角色和场景
  → 标记"共用事实"（角色档案/场景描写/事件种子）vs"视角相关"（行为规则/体感描写/身份假设）

Step 2: 共用层构建
  角色/场景/事件条目 → content 零{{user}}，用具体角色名
  系统条目 → 多视角版本（含"如果{{user}}=XXX → 规则A；如果{{user}}=YYY → 规则B"）

Step 3: 视角层构建
  每个可扮演身份 2-3 条 selective 条目：
    1条身份体验规则 + 1条感官/行为模板 + 可选1条典型场景
  → selective=true, secondary_keys 包含 greeting 中全部关键词变体

Step 4: Greeting 组装
  每身份 2-3 条 greeting → 首行：【▎身份：XXX｜视角描述】 key1 key2 key3
  → 确认首行关键词 ∩ 视角段 secondary_keys ≠ ∅

Step 5: 验证
  validate_card.py checks 42-45 → 导入ST → 每身份各测一轮 → 查<Lore>确认视角隔离
```

**硬性检查清单**（按 `multi-perspective-card-design.md` §4.2）：

1. 事件/角色/场景条目 content 零 `{{user}}`（grep 全卡验证 → `validate_card.py` check 43）
2. 每个 greeting 首行含全部身份 key，格式：`【▎身份：XXX｜视角描述】 key1 key2 key3`
3. 视角段 secondary_keys 与 greeting 关键词有交集（Python 验证 → `validate_card.py` check 42）
4. 共用层系统条目 constant=true, keys=[]
5. 视角段 constant=false, selective=true, keys 非空
6. 每个身份至少 2 条视角段（感官+心理 → `validate_card.py` check 44）
7. 全部条目 prevent_recursion=true

**从已有卡重构（天仙配模式）**：
- 读取所有现有卡 → 逐条对比 content hash → 相同条目直接进共用层
- 差异条目拆分：事实段→共用层 + 视角段→各自 selective 条目
- 预期共用率 70-92%（严格遵循 skill 规范的卡共用率高）
- 系统条目（反顺从/状态栏/NPC行动）改为多视角版本

**关键规则**：
- 依赖 greeting 触发，不依赖 before_char 递归（ST 不二次扫描已插入条目）
- 交付时必须附带导入说明（ST "导入卡片世界书"步骤不可跳过，见 `multi-perspective-card-design.md` §4.3）
- 最终验证：`validate_card.py` checks 42-45 全部通过

### 3.4 JSON组装

**CCv3 core 格式**：顶层必须有 `spec="chara_card_v3"`、`spec_version="3.0"`、`data`；所有标准角色字段位于 `data`（含 `name/description/tags/creator/character_version/mes_example/extensions/system_prompt/post_history_instructions/first_mes/alternate_greetings/personality/scenario/creator_notes/group_only_greetings`）。不要把顶层镜像、`data.spec` 或 `data.spec_version` 误称为 CCv3 必填。

**Leyu-production 兼容策略**：若导出器同时保存顶层与 `data` 的镜像（如 `first_mes`、`alternate_greetings`），两份必须一致；`data.spec/data.spec_version` 是允许保留的兼容额外字段，但当前没有 ST 实测依据时不得强制要求。使用 `validate_card.py --profile ccv3-core` 检查规范边界，使用默认 `leyu-production` 执行内容/触发/生产门控。

**character_book**：CCv3 Lorebook 可合法包含 `name`、`description`、`scan_depth`、`token_budget`、`recursive_scanning`、`extensions` 与 `entries`。构建/迁移不得因为“精简”删除这些字段；未知或导出器字段默认保留。

**参考卡格式检测**：`chara_card_v3` 的 entries是list有id → `character_book.entries`。独立世界书的 entries是dict(key为字符串编号)。

**大型既有卡的后续加料（强制）**：不得无差别重写全卡。每一轮补强先写 `baseline + manifest`，再运行 `scripts/verify_enrichment_pass.py`；配套预设使用简化 `阶段P#` 路由的卡，额外运行 `scripts/verify_simple_stage_route.py`。完整责任分层、manifest 字段和命令见 `references/workflows/controlled-enrichment-pass.md`。

**组装后的脚本编排（强制）**：新建/重组卡、历史手工卡、受控加料、配套预设路由、原生标题阶段卡需要的构建源与 gate 不同，禁止只看 `scripts/` 清单自行猜顺序。先读取 `references/workflows/card-assembly-and-delivery-pipeline.md` 和 `references/workflows/manifest-driven-delivery.md`，新建生产卡默认用`先实际 prepare/generate → make_contract → assemble，再 build_manifest.json → scripts/run_delivery.py → final_delivery_gate.py`；新建可重建项目必须 `require_build=true`，历史手工卡不能伪造 build 绿灯；配套预设路由必须同时审计 card 与 preset。

---

### 🚨 交付前强制门控 — 不完成本节不能输出卡给用户

**标准生产交付：** JSON组装完成后，必须生成`build_manifest.json`并运行`run_delivery.py`；`run_delivery.py`不会替代项目自己的 builder。可重建且使用导演附录的项目还会在 final gate 中执行 `audit_greeting_build_wiring.py`；`exit 0`前禁止说“卡做好了”。Runner 会把正确条件传给`final_delivery_gate.py`，并显示每项`RUN/SKIP`原因，不能静默漏跑。

**Agent/CI 输入错误处理：** 自动化在需要机器解析 Manifest 或 semantic manifest 配置读取错误时使用 `--format json`。当前 `--format json` 只保证以下配置错误采用结构化 JSON 输出：`DELIVERY_MANIFEST_NOT_FOUND`、`DELIVERY_MANIFEST_JSON_INVALID`、`DELIVERY_MANIFEST_SCHEMA_INVALID`、`SEMANTIC_MANIFEST_NOT_FOUND`、`SEMANTIC_MANIFEST_JSON_INVALID`。完整交付计划、semantic audit、semantic migration coverage 和 `final_delivery_gate.py` 结果目前仍以文本输出；不得把 `--format json` 描述成完整 Runner JSON 报告。coverage 四项统计仅用于迁移可观测性，不替代正式 semantic audit，也不改变 Legacy 正式 namespace 的既有审计策略。

**下列 15 步是“用户明确要求深度审查 / 修旧卡 / 运行时异常排障”的完整专项复核路径，不再在每次正常生产前无条件重复预跑。** 任何被选中的专项未通过前，只输出进度，不输出“完成”。

```
做完卡后立即 →
  ① 跑 validate_card.py（自动抓 enabled=false / 缺addMemo / keys=[] / position不一致等结构性问题）→ 修复全部error → 确认passed=True；若采用“正文+后置导演附录”，同一阶段必须另跑 `python scripts/audit_greeting_layers.py <卡.json> --min-cn 1400 --max-cn 1800 --appendix-standard stage_brief_v1`，并在第⑭步 `final_delivery_gate.py` 追加 `--greeting-layer-audit --greeting-appendix-standard stage_brief_v1`；正文污染/分层缺失/正文不足/八维附录缺失均不得继续交付
  ② 读 references/audit/初始卡审查启动模板.md → 按7步逐项执行
  ③ 根据卡原型选内容层模板（见下表），读取并逐项执行
  ④ 修复所有发现 → 重跑validate_card确认通过
  ⑤ 🔴 世界书触发审计（必做）→ 读 `references/audit/世界书触发专项审查模板.md`，运行 `python scripts/audit_worldbook_triggers.py <卡.json> -o <触发审计报告.md>` → 修硬泛key、普通句误触发、secondary被忽略、extensions-only selective、first_mes无关深度档案误触发；高负载本身不是错误，先看触发质量
  ⑥ 🔴 卡内输出复杂度审查（必做）→ **只审角色卡/世界书自身**写死的每轮强制输出项：旁白/状态栏/多NPC并行/阶段推进/反顺从判定/信息边界/随机线索。若卡内同时≥5项每轮必写，必须合并常驻或改按需触发；状态栏默认简版，完整版按需。**用户预设/API/模型安全/破限制力度属于运行环境，不作为角色卡质量不通过项**
  ⑦ 🆕 加料自检（见 §3.5）→ 逐项对表 → 不足的立即补 → 再重跑 validate_card
  ⑧ 🆕 Discord发布文案（仅用户要求发布时）→ 生成discord简介.md + 纯文字版
  ⑨ 🆕 发布文案违禁词扫描（仅用户要求发布时）→ 只扫描将要发出的简介/帖子，不扫描角色卡 JSON 正文；见 §5.3.1
  ⑩ 🆕 Pitfalls自检 → **先读 SKILL.md §5.1 陷阱汇总逐条对照**；再读 `references/misc/pitfall-library.md` 获取最新补充陷阱的详细症状/根因/修复
  **⑪ 🔴 角色名一致性验证（2026-07-13新增·乖妈妈卡213处命名错误教训）** → 用Python搜全卡所有条目content中的主角称呼，与系统条目#0定义的{{user}}名逐条比对。不同条目对同一角色必须使用完全一致的称呼。特别注意子代理产出（薛明/金晓玲等"后来加入的"条目最容易用错名）。**🆕 角色名幻觉验证（T60）**：AI可能为NPC自行发明名字（如把"艾尔诺"写成"亚伦"）→必须`grep`小说全文确认每个角色名。见`references/audit/hero-name-verification-pattern.md`。
  **⑫ 🔴 人物关系一致性验证（2026-07-15新增·天仙配G型反馈）** → 对照§2.4的人物关系锚点表，扫描全卡所有角色条目/身份条目/事件条目中的血缘、婚姻、归属、称谓。重点查：`自己的妹妹`、`亲妹妹`、`亲生母亲`、`父亲`、`母亲`、`公公`、`婆婆`、`儿媳`、`侍妾`、`丫鬟`、`主人`等无参照称谓。凡是可被理解成当前条目主语的关系词，必须改成「X的妹妹/母亲/父亲」。G型多视角额外检查：同一角色在不同{{user}}身份下的关系是否随视角变化。
  **⑬ 🔴 多NPC协调验证（2026-07-13新增·双卡交叉验证）** → 如果卡中有3+同场景NPC角色，检查是否存在信息边界+行为独立性常驻条目。缺失则回退构建阶段补写。
  **⑭ 🔴 汇总交付门控（必做）** → 标准生产使用 `python <card-skill>/scripts/run_delivery.py <卡.json> --manifest <project-dir>/build_manifest.json`；它先打印有效交付计划，再以正确参数调用`final_delivery_gate.py`。只有排查 runner/CLI 时才手工运行`references/workflows/card-assembly-and-delivery-pipeline.md`中的原始 final-gate 命令。退出码契约：`exit 0` 才能写静态门控通过；`exit 1` 有错误不可交付；`exit 2` 仅 warning——判定前提是报告文件已生成，只能带逐项人工解释交付，不能宣称全绿；`exit 3` 是门控内部错误，排障后重跑；`exit 4` 是 CLI 用法错误（含 argparse 互斥/缺成对参数，未运行任何门控、不写报告），修正命令后重跑。⑭ `exit 0` 之后，`architecture_mode=stage_routing` 的卡还必须完成第⑮步人工专项（合同审计确认/阶段隔离模拟/未来泄漏人工复核/事件候选语义）才可交付。
  **⑮ 🔴 阶段路由卡专项（🆕 2026-07-26）** → 仅 `architecture_mode=stage_routing` 时执行。① 合同审计：`stage-entry-contract.json` schema v2 字段齐全（`architecture_mode`/`route_source`/`phase_memory`）。② 组件存在：全程因果档案、阶段记忆闸门、`system_prompt` 压缩锚点。③ 隔离模拟：逐 greeting 验证标题触发对应阶段四包且不触发其他阶段包。④ 未来泄漏：人工复核常驻条目/P0-P1 阶段包是否含后期专属称呼/秘密/习惯（脚本只做锚点标记，判定需人工）。⑤ 事件候选语义：每条事件种子有前提/切入/反应/分歧标记。```

**踩坑实录（2026-07-13·示例关系卡卡）**：发布卡时 agent 漏了 Discord简介、发布文案违禁词扫描和 pitfalls 自检。原因是门控只列了5步。现保留 15 步专项复核：其中 Discord 两步只在发布时启用；正常生产以 runner 结果为交付依据。

**踩坑实录（2026-07-15·大型结构化卡/示例G型卡型触发对照）**：大型结构化卡首轮可达7w+字符但不卡，因为大部分是结构化协议且非常驻触发精准；示例G型卡型首轮仅2w+字符却容易卡，因为secondary_keys在selective=false下被忽略，`家/学校/妈妈/妹妹`等泛key把深度档案和场景同时拉入。现在交付门控新增⑤触发审计+⑥卡内输出复杂度审查；高负载只是诊断信号，不是绝对红线。**外部预设/API/模型安全导致的截断/回空，不计为卡质量失败。**

**踩坑实录（2026-07-15·天仙配G型关系反馈）**：完整跑完的大卡仍可能出现人物关系错位（如把「林子睿的妹妹」写成「詹姆的亲妹妹」、把「林子睿的母亲」写成「麦克的亲生母亲」）。根因是角色档案写作时使用了无主语亲属词。现在新增§2.4人物关系矩阵预检 + §3.3关系锚点 + 交付门控⑫人物关系一致性验证。

| 卡原型 | 内容层模板 |
|--------|-----------|
| A.恶堕(NTR) | `references/audit/NTR苦主卡审查启动模板.md` |
| **A-Hidden.隐奸恶堕** 🆕 | NTR苦主卡模板 + `references/design-patterns/hidden-ntr-design.md` | **三层信息差/确信度/碎片化证据**——审查时额外检查隐奸核心规则是否常驻、确信度是否可追踪 |
| **A-N.Netorase主动送妻** 🆕 | NTR苦主卡模板 + §1.0 A-N 子节检查项（淫妻兴奋度/送妻选择/魔力监视/导演体验） | **导演体验/送妻闭环/远程观看机制**——审查时额外检查淫妻兴奋度系统是否独立、送妻选择是否覆盖全部目标女性+男性 |
| **A-N×E混合型** 🆕 | 禁忌后宫模板 + NTR苦主卡模板（叠加审查） | **双系统并存/双向共享生态/群交日常化**——审查时额外检查后宫协调是否与淫妻兴奋度并行、保密范围（门内公开≠门外保密）、{{user}}双源兴奋是否均有描述 |
| C.NTL逆寝取 | `references/audit/NTL变体审查启动模板.md` |
| **C+.隐奸NTL** 🆕 | NTL变体审查模板 + `references/design-patterns/hidden-ntl-composite.md` | **隐奸信息差操控/苦主破局行为/博弈循环/全知视角一致性**——审查时额外检查AI苦主是否有「努力破局」指令、信息差是否为{{user}}操控工具而非迷雾 |
| B/D.守护/觉醒 | `references/audit/守护卡审查启动模板.md` |
| E.禁忌后宫 | `references/audit/禁忌后宫征服卡审查启动模板.md` |
| ⚠️ **所有卡型**（3+同场景NPC时） | +`npc-information-boundary.md` + `npc-behavioral-independence.md` | 审查时额外检查：信息边界全局规则是否存在、各角色条目是否有信息子段、NPC并行规则是否定义、空闲NPC是否有行为模板 |
| **G.多视角内置** 🆕 | 初始卡审查模板 + G-Common + 触发模式专项（默认选开/Greeting备选，见 `review-template-system.md`） | 共用层零{{user}}/身份选开结构/greeting-secondary对齐/视角隔离/交付说明 |

**踩坑实录（2026-07-12）**：agent做完NTR卡后直接输出"卡做好了，可直接导入ST使用"，用户追问"审查模板使用了吗"→agent才补跑审查。该门控就是为了防止这个。

**踩坑实录（2026-07-12 · 四卡实证）**：天仙配/芭蕾舞美母/38G警花/示例G型卡世家四张卡——每次 agent 宣布"完成"后，用户都发现内容不足（缺语料库、角色偏薄、场景缺安全等级、NTR应改守护）。**现在 §3.5 加料自检在交付前自动拦截这些问题。**

### 3.5 🆕 加料自检 — 交付前自动检查内容是否够"厚"

**背景（2026-07-12 · 四卡实证）**：天仙配、芭蕾舞美母、38G警花、示例G型卡世家四张卡——每次 agent 宣布"完成"后，用户都指出内容不足。模式固定：「初版交付 → 用户要求加料（扩充语料库/场景/事件种子/角色条目）→ 加料完成 → 用户要求审查 → 审查修复 → 才真正完成」。**本节把「加料」步骤提前到交付前，省去用户手动提醒。**

**在步骤④（修复完→重跑validate_card通过）之后，立即执行以下自检。先读取 Manifest 的四个内容模式字段，再决定适用门槛；不能把严格卡规则自动套到普通开放卡。**

| Manifest profile | 适用自检 | 不得误套用的旧硬门槛 |
|---|---|---|
| 字段未声明（`legacy_unspecified`） | 保持旧卡兼容：执行原有自检并在报告标注 legacy | 不得自动改成开放卡 |
| `expanded_reference_corpus` + `guided_candidate`/`scripted_sequence` | 角色/场景/系统厚度、完整候选事件结构、三路径（仅原型合同要求）、原文覆盖等严格 gate | 仍需检查重复、抽象空话、死key和玩家越权 |
| `curated_anchor_set` + `open_situation_seed` + `player_led` | 查角色框架是否可运行、精选事实/语言锚点、自然入口、可观察压力、接管点、重复率、事实/代理/可见性 | 不强制 20+ 对白、60%覆盖、500字语料、3个 primary key、成功/失败/半成功固定分支、固定体积或独立语料库拆分 |

生产入口必须使用：

```bash
python scripts/enrichment_self_check.py <卡.json> --manifest <build-manifest.json>
```

下面的内嵌伪代码保留作为旧项目结构参考，默认语义对应 `legacy_unspecified`/严格 profile；它不是普通开放卡的新门槛。可执行事实以同目录 `enrichment_self_check.py` 当前实现和 Manifest policy 为准。

```python
# 加料自检脚本 — 每做完一张卡就运行这个
def enrichment_self_check(card_path):
    import json, re
    with open(card_path, 'r', encoding='utf-8') as f:
        card = json.load(f)
    entries = card['data']['character_book']['entries']

    issues = []

    # === A. 角色条目深度 ===
    char_entries = [e for e in entries
                    if not e.get('constant') and e.get('enabled')
                    and any(kw in e.get('comment','') for kw in
                           ['档案','设定','性格','描写库'])]
    for e in char_entries:
        cn = sum(1 for c in e.get('content','') if '\u4e00' <= c <= '\u9fff')
        if cn < 1500:
            issues.append(f"🔴 角色条目[{e['id']}] '{e['comment'][:20]}' 仅{cn}字 (需≥1500)")
        elif cn < 2000 and '核心' in e.get('comment',''):
            issues.append(f"🟡 核心角色[{e['id']}] '{e['comment'][:20]}' 仅{cn}字 (建议≥2000)")

    # === B. 语料库检查 ===
    corpus_entries = [e for e in entries
                      if '语料库' in e.get('comment','') or '语料' in e.get('comment','')
                      or '对话库' in e.get('comment','') or '台词' in e.get('comment','')]
    if not corpus_entries:
        issues.append("🔴 缺少语料库条目（对话模板/台词集/描写库）—— AI没有参考素材")
    else:
        for e in corpus_entries:
            cn = sum(1 for c in e.get('content','') if '\u4e00' <= c <= '\u9fff')
            if cn < 500:
                issues.append(f"🟡 语料库[{e['id']}] '{e['comment'][:20]}' 仅{cn}字 (建议≥500)")

    # === C. 场景条目深度 ===
    scene_entries = [e for e in entries
                     if '场景' in e.get('comment','') and e.get('enabled')]
    for e in scene_entries:
        cn = sum(1 for c in e.get('content','') if '\u4e00' <= c <= '\u9fff')
        if cn < 500:
            issues.append(f"🔴 场景[{e['id']}] '{e['comment'][:20]}' 仅{cn}字 (需≥500)")
        # 检查安全等级定义
        safety_keywords = ['安全等级','S级','A级','B级','C级','D级','隐私']
        if not any(kw in e.get('content','') for kw in safety_keywords):
            issues.append(f"🟡 场景[{e['id']}] '{e['comment'][:20]}' 缺少安全等级定义 (S/A/B/C/D)")

    # === D. 事件种子深度 ===
    seed_entries = [e for e in entries if not e.get('enabled', True)]
    for e in seed_entries:
        cn = sum(1 for c in e.get('content','') if '\u4e00' <= c <= '\u9fff')
        if cn < 80:
            issues.append(f"🔴 事件种子[{e['id']}] '{e['comment'][:20]}' 仅{cn}字 (需≥80)")
        elif cn < 150:
            issues.append(f"🟡 事件种子[{e['id']}] '{e['comment'][:20]}' 仅{cn}字 (建议≥150)")

    # === E. 行为模板检查（角色条目的内容质量） ===
    # 角色条目不能只有静态描述（"X是Y"），需要有具体的行为链（"X场景→做A→结果B"）
    for e in char_entries:
        # 行为链的典型模式：→、当...时、如果...就
        behavior_signals = ['→', '当', '如果', '触发', '场景', '行为举例', '行为链']
        content = e.get('content', '')
        signal_count = sum(1 for s in behavior_signals if s in content)
        # 行为模板段通常以列表形式出现：- X场景：做A→结果B
        template_lines = [l for l in content.split('\n') if l.strip().startswith('-') and '→' in l]
        total_behaviors = signal_count // 2 + len(template_lines)  # 粗略估计
        if total_behaviors < 3:
            issues.append(f"🟡 角色条目[{e['id']}] '{e['comment'][:20]}' 行为模板不足（检测到{total_behaviors}个，建议≥3）")

    # === F. 描写库独立检查 ===
    # 语料库=对话台词。描写库=身体/感官/氛围描写。两者不能混成一条
    desc_entries = [e for e in entries
                    if '描写库' in e.get('comment','') or '描写' in e.get('comment','')]
    # 检查描写库是否独立于语料库
    pure_desc = [e for e in desc_entries if '语料' not in e.get('comment','') and '对话' not in e.get('comment','')]
    if not pure_desc:
        issues.append("🟡 缺少独立描写库条目（身体/感官/氛围描写不应和对话语料混在同一条）")
    else:
        for e in pure_desc:
            cn = sum(1 for c in e.get('content','') if '\u4e00' <= c <= '\u9fff')
            if cn < 500:
                issues.append(f"🟡 描写库[{e['id']}] '{e['comment'][:20]}' 仅{cn}字 (建议≥500)")

    # === G. 阶段跃迁行为标志检查 ===
    # 堕落/守护/征服阶段条目的跃迁条件必须是具体行为，不能是抽象数值
    stage_entries = [e for e in entries
                     if any(kw in e.get('comment','') for kw in
                           ['阶段','堕落','守护','征服','沉沦','臣服','屈服'])
                     and e.get('enabled')]
    for e in stage_entries:
        content = e.get('content', '')
        # 检测是否有具体行为触发条件（非纯数值）
        has_behavior_triggers = any(kw in content for kw in
            ['触发条件','跃迁','标志','行为','具体表现','门','阈值行为'])
        # 检测是否有纯数值陷阱
        has_pure_numbers = bool(re.search(r'[>≥]\s*\d+', content))
        if not has_behavior_triggers:
            issues.append(f"🟡 阶段条目[{e['id']}] '{e['comment'][:20]}' 缺少行为触发条件（跃迁不能只靠数值）")
        if has_pure_numbers and not has_behavior_triggers:
            issues.append(f"🔴 阶段条目[{e['id']}] '{e['comment'][:20]}' 只用数值定义跃迁，需补充具体行为标志")

    # === H. NTR关系条目深度检查（2026-07-13新增·昏迷教师卡实证） ===
    # NTR关系条目（赵高×白若雯/李明×白若雯/群体NTR等）容易被当成"轻量关系备注"写得太薄
    # 但它们是AI生成NTR场景的核心素材，必须足够厚
    ntr_rel_entries = [e for e in entries
                       if any(kw in e.get('comment','') for kw in ['×','NTR线','NTR','矩阵'])]
    for e in ntr_rel_entries:
        cn = sum(1 for c in e.get('content','') if '\\u4e00' <= c <= '\\u9fff')
        comment = e.get('comment','')[:25]
        if '矩阵' in comment:
            if cn < 300:
                issues.append(f"🟡 NTR矩阵[{e['id']}] '{comment}' 仅{cn}字 (建议≥300)")
        else:
            if cn < 600:
                issues.append(f"🔴 NTR关系[{e['id']}] '{comment}' 仅{cn}字 (需≥600，含侵犯史/行为链/触发关键词)")
            elif cn < 1000:
                issues.append(f"🟡 NTR关系[{e['id']}] '{comment}' 仅{cn}字 (建议≥1000)")

    # === I. 双版本一致性（如果有多版本） ===
    # （手动检查：同目录下是否有多个JSON文件）

    return issues
```

**加料自检清单（人类可读版）**：

| 维度 | legacy/严格 profile | 普通开放 profile | 不通过怎么修 |
|------|---------|---------|------------|
| 角色条目字数 | ≥1500字/条，核心建议≥2000 | 不设统一字数；必须有关系锚点、行为框架和可复用事实 | 补信息增量，不用重复句扩字 |
| 角色行为模板 | 每角色≥3个行为链 | 至少覆盖关键触发/反应/接管点；按角色复杂度判断 | 补具体触发物、可观察反应和分支窗口 |
| 语料库 | 可要求独立语料库和≥500字 | 可合并进角色档案/精选锚点，不要求拆库或500字 | 检查是否有独特语言锚点，不为数字堆语料 |
| 描写库 | 独立于语料库，严格卡可设≥500字 | 可按职责合并，仍须有具体感官/动作素材 | 删除抽象规则和重复段，补真实信息 |
| 场景安全等级 | 阶段/严格场景按合同要求 | 只在确实有隐私/风险机制时要求 | 不能用安全等级替代可观察事实 |
| 事件种子字数/路径 | 严格候选按合同；适用原型才查三路径 | 不固定字数、顺序、结果或三路径 | 保留自然入口、事实锚点、开放方向和玩家接管点 |
| 阶段跃迁条件 | 用具体行为定义 | 避免纯数值（堕落值≥50） | 改为「当她不再叫你全名→跃迁到阶段2」的行为标志 |
| NTR关系条目字数 | ≥600字/条（含侵犯史） | ≥1000字/条（含行为链+触发关键词） | 添加：分阶段演变史、行为链、NTR场景触发关键词 |
| 阶段跃迁条件 | 用具体行为定义 | 避免纯数值（堕落值≥50） | 改为「当她不再叫你全名→跃迁到阶段2」的行为标志 |
| NTR关系条目字数 | ≥600字/条（含侵犯史） | ≥1000字/条（含行为链+触发关键词） | 添加：分阶段演变史、行为链、NTR场景触发关键词 |
| NTR矩阵 | ≥300字 | — | 确保覆盖所有女×NTR男的关系对照 |
| 开场白字数 | ≥1400字/条 | — | validate_card 已检查，此处不重复 |
| addMemo双重写入 | 全部True | — | `for e in entries: e['addMemo']=True; e['extensions']['addMemo']=True` |

**🚨 红线规则（按 Manifest）**：legacy/严格 profile 仍执行“🔴 必修；🟡≥3阻断”。`curated_anchor_set + open_situation_seed + player_led` 中，🔴 仍必须修复；🟡 是报告中的非阻断诊断，除非它指向事实边界、玩家代理、触发安全、构建同步或明确声明的项目合同。静态 PASS 不等于已完成 ST 实机行为验收。

**🆕 G型卡额外自检**：G型卡在加料自检之外，必须额外确认：
- `validate_card.py` checks 42-45 全部 PASS（secondary key 对齐/零{{user}}/视角段数量/greeting 关键词）
- 每个视角段的 secondary_keys 在对应 greeting 首行中实际出现（check 42 自动覆盖）
- 共用层角色/场景/事件条目零 `{{user}}`（check 43 自动覆盖）
- 导入 ST 后每个身份各测一轮 → `<Lore>` 中确认视角隔离（手动）

**执行方式**：做成卡流程的最后一步。在步骤④（修复完→重跑validate_card）之后，立即运行此脚本，修完所有🔴🟡后再输出「完成」。也可通过独立脚本快速执行：

```bash
python scripts/enrichment_self_check.py <卡文件路径.json>
```

内联代码（当 scripts/ 路径不可达时）：

### 3.6 系统条目清单

大型卡（30+条目）必须包含以下系统条目。**⚠️ system_prompt 也必须包含状态栏铁律和旁白规则**（不能只靠世界书条目）。

**必须常驻（constant=true）**：
- 全局OOC防护 / 文风叙事控制 / 防拒绝规则 / 剧情导演协议 / 语料库（对话参考素材）/ 人物关系矩阵
- ⚠️ 状态栏模板已从必须常驻移除——实测在ST中几乎无效，AI不会按模板格式输出状态栏

**推荐常驻（根据卡的复杂度决定）**：
- 格式增强 / 叙事节奏控制（模板14）/ 反AI顺从（模板17）/ 文风锚点（模板16）

**建议触发（constant=false，用关键词触发）**：
- 性爱规则与姿势库 / 好感度系统 / 剧情推进 / 自由创作总则 / 状态管理

**⚠️ NTR/剧情卡必须包含模板14（叙事节奏控制）+ 模板17（反AI顺从）**。validate_card.py 会检查并输出 warning。

### 3.7 NTL视角转换

**⚠️ 优先判断：如果小说同时有苦主+NTL双线且还没做卡 → 不要走本节，直接用 §3.3b G型（多视角内置）。本节仅用于"已有成品NTR卡，只要快速出NTL版"的场景。**

保留原文角色设定不变，只改视角和关系结构：
1. 备份原版
2. 改system_prompt（{{user}}身份）
3. 重写first_mes + alternate_greetings
4. 改关键世界书条目
5. **四轮审查法**（详见`references/ntl/ntl-version-audit-checklist.md`）：批量{{user}}视角匹配 → JSON转义处理 → 误报过滤 → **跨卡内容污染检测**（按条目类型分级：{{user}}条目中出现其他角色特征词=污染，竞争者NPC条目中出现=合理）

**增量构建（已有2+版本时）**：读取所有现有版本的条目，逐条分类为复用/微调/重写/新增。规划书必含复用分析表。详见 `references/workflows/variant-card-production-workflow.md`。

**多视角NTL（同一小说→多张独立NTL卡）**：每个NTR男性角色→一张独立NTL卡，{{user}}=该NTR男性，原苦主变NPC，其他NTR男性变竞争者。先做一张确认后再做其余。第二张起基于第一张NTL卡改造（非原版NTR卡），只改~10条{{user}}相关条目，效率提升60%。详见 `references/workflows/variant-card-production-workflow.md` 的"级联构建模式"。

详见 `references/ntl/ntl-perspective-conversion.md`。

**⚠️ 多视角世界观着色（2026-07-13新增）**：同一世界观从苦主→NTL视角转换时，事实不变但感情色彩必须整体转换——"奴役工具"→"特权保障"、"恐惧之地"→"自由猎场"。详见 `references/workflows/variant-card-production-workflow.md` 的「多视角世界观情感滤镜」章节。**这是NTL转换中常见的遗漏项**——只改了{{user}}身份，没改世界观描述的情感滤镜。

### 隐奸NTL特殊转换（C+型，2026-07-13新增）

当原卡是隐奸型（A-Hidden型，三层信息差+确信度追踪）且用户要求NTL版时，需要额外注意：

**核心差异**：普通NTL是「正面对抗/征服」，隐奸NTL是「**信息战+破局博弈**」。{{user}}不是公开的征服者，而是幕后的信息操控者。

**转换要点**：
1. **信息差反转**：原隐奸的三层信息差（写真/语音/日常线索）从「折磨{{user}}的工具」变成「{{user}}操控的工具」——{{user}}全知，主动向AI苦主投喂碎片
2. **AI苦主获得「努力破局」指令**：原版苦主是NPC被动观察者，NTL版中AI苦主是**主动的破局者**——会调查/反抗/寻找真相
3. **新增苦主行为库**：世界书必须有专门条目定义AI苦主的调查手段（翻手机/跟踪/质问等）
4. **{{user}}的约束变化**：从「无法确认真相」变为「不能让苦主找到确凿证据」
5. **叙事节奏**：原隐奸的「怀疑→确认→再怀疑」循环保留，但由{{user}}主动操控节奏

**woniyu玩法模式**（来源于Discord玩家讨论）：
- 不扮演user（苦主）→ AI扮演苦主，获得「努力破局」指令
- 选黄毛角色扮演{{user}}→ 幕后操控者/集团首脑
- {{user}}全知→ 能监控苦主的一切行动和反应
- 核心乐趣：看AI在隐奸迷雾中挣扎→破坏其努力→让他绝望→征服
- AI不会口胡→ 规则内破局，挣扎有真实感

详见 `references/design-patterns/hidden-ntl-composite.md`。

### 3.8 开放性/玩法型卡片

- **开放性卡**：事件条目=enabled=false种子库，阶段阈值=必要条件非充分条件。
- **玩法型卡**：核心是"引导玩家体验一个系统"，含随机匹配/收集进度/事件触发/场景模板。

详见 `references/design-patterns/open-ended-card-design.md` 和 `references/design-patterns/gameplay-type-card-design.md`。

### 3.9 关键代码片段（复制即用）

**validate_card.py 调用**（首选 CLI）：
```bash
python scripts/validate_card.py <卡.json>
```
若确需进程内拿到 `passed/errors/warnings` 变量，用 importlib 加载（不要用 `exec(open(...).read())`）：
```python
import sys, importlib.util
sys.path.insert(0, r'<skill_dir>/scripts')  # 写死本 skill 的 scripts 绝对路径
spec = importlib.util.spec_from_file_location('validate_card', r'<skill_dir>/scripts/validate_card.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
passed, errors, warnings = mod.validate_card('/path/to/card.json')
if not passed:
    for e in errors: print(f"❌ {e}")
for w in warnings: print(f"⚠️ {w}")
```

**make_entry() 函数**：参数名是 `entry_id` 不是 `id`！完整函数定义见 `references/formats/worldbook-entry-structure.md`。

**v3 JSON 必填值**：`"spec": "chara_card_v3"`, `"spec_version": "3.0"`。

**迁移/递归设置**：不再调用原地 `fix_card_format.py`。先预览：`python scripts/migrate_card.py INPUT.json`；确认后：`python scripts/migrate_card.py INPUT.json --output OUTPUT.migrated.json --set-prevent-recursion true --write`。任何 ID 重排或 Unicode 替换也必须显式传 `--renumber-ids` / `--normalize-unicode`。

---

## 4. 验证阶段

### 4.0 审查模板体系（7模板·含G型）— 做卡完成后强制执行

**日常生产只以 §3.4 的 `build_manifest.json → run_delivery.py` 为交付入口。** 本节两轮审查用于用户明确要求深度审查、修旧卡、运行时异常排障，或 final report 指向内容/语义问题时，不是每张正常新卡的无条件前置。

> ⚠️ 本节 4 步是深度复核的结构/内容路径，不能替代汇总交付门控。深审完成后仍必须回到 §3.4 运行 runner；`architecture_mode=stage_routing` 的卡还需完成第⑮步人工阶段专项。

```
做完卡 →
  ① 跑 validate_card.py（自动门控，先修全部error）
  ② 模板1 初始卡审查（结构层：计划对照/字数/一致性/addMemo）
  ③ 根据卡原型选择内容层模板（见下表）
  ④ 修复所有发现 → 重跑validate_card确认通过
  → 回到 §3.4 继续执行 ⑤-⑮，完成后才可交付
```

完整体系见 `references/audit/review-template-system.md`。各模板位于 `references/audit/`：

| 原型 | 内容层模板文件 | 核心关注点 |
|------|--------------|-----------|
| A.恶堕(NTR) | `NTR苦主卡审查启动模板.md` | 堕落闭环/苦主体验/男性行为独立性 |
| **A-N.Netorase主动送妻** 🆕 | NTR苦主卡模板 + A-N子节检查项 | 导演体验/送妻闭环/远程观看（淫妻兴奋度系统是否独立、送妻选择是否覆盖全部目标） |
| **A-N×E混合型** 🆕 | 禁忌后宫模板 + NTR苦主卡模板 | 双系统并存/双向共享生态/群交日常化（后宫协调与兴奋度并行、保密范围、{{user}}双源兴奋） |
| B/D.守护/觉醒 | `守护卡审查启动模板.md` | 唤醒闭环/反转道具/多结局 |
| C.NTL逆寝取 | `NTL变体审查启动模板.md` | 跨卡污染/{{user}}纯度/NTR矩阵覆盖 |
| **C+.隐奸NTL** 🆕 | NTL变体审查模板 + `references/design-patterns/hidden-ntl-composite.md` | 隐奸信息差操控/苦主破局博弈/全知视角一致性 |
| E.禁忌后宫 | `禁忌后宫征服卡审查启动模板.md` | 保密闭环/公开私下双模式/权力反差/安全等级 |
| F.叙事观察 | NTR苦主卡模板（去掉苦主检查） | 观察者规则/NPC自主推进/介入风险 |
| **G.多视角内置** 🆕 | 初始卡审查模板 + G型专项（见下方） | greeting-secondary key对齐/共用层零{{user}}/视角隔离/多轮维持 |
| **G.选开模式** 🆕 | G型审查 + 手动验证（Leyu-production：`constant=true + enabled=false + keys=[] + secondary_keys=[] + selective=false`；checks 46-47 覆盖「选开」标注与 greeting 身份标记误用） | 身份条目 comment含「选开」/交付含使用说明 |
| 修卡 | `修卡审查启动模板.md` | 改动波及范围（>15条自动升级全量） |

**使用方式**：

- **制卡流程内（agent自己审查）**：直接读取 `references/audit/` 下的模板内容，逐步骤执行。不要复制到新窗口——agent自己按模板步骤审查。
- **独立审查（用户手动交叉验证）**：复制模板内容→替换 `[方括号]` → 在新Hermes窗口发送。这是双窗口交叉验证工作流的一部分。
- 模板全部通用版，零硬编码。

⚠️ **执行模板里的 validate_card 步骤时，首选 CLI：`python scripts/validate_card.py <卡.json>`**（不在 skill 根目录运行时把脚本路径写成绝对路径）。历史模板内嵌的 `exec(open(...).read())` 片段已废弃，不要照抄；若确需进程内调用，用 importlib 加载：
```python
import sys, importlib.util
sys.path.insert(0, r'<skill_dir>/scripts')  # 写死本 skill 的 scripts 绝对路径
spec = importlib.util.spec_from_file_location('validate_card', r'<skill_dir>/scripts/validate_card.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
passed, errors, warnings = mod.validate_card('<卡.json>')
```

### 4.0.1 导演附录最高标准专项

当 `greeting_mode=prose_plus_director_appendix` 时，导演附录按 `stage_brief_v1` 处理，不再把“有标题、有分隔线”视为内容合格。每条 Greeting 必须完成：

1. 自动运行 `audit_greeting_layers.py --appendix-standard stage_brief_v1`；
2. 对照 `greeting-director-appendix-standard.md` 检查八维和玩家接管点；
3. 逐条确认附录与当前阶段正文、阶段素材、人物关系和信息边界一致；
4. 检查“角色预计动向/潜在分歧点”仍是候选推演，不是事实化剧情；
5. 确认附录没有复制全局导演协议，也没有替代场景悬停/玩家行动边界选开条目。

自动门控通过只能记为“结构与最低内容密度通过”；未完成人工专项，不得报告为导演附录质量通过。

### 4.1 验证流程

**铁律：修卡/审查的第一步永远是跑validate_card.py，不要肉眼扫JSON。**

```
① 跑 validate_card.py（自动抓 enabled:false / 缺addMemo / keys=[] / position不一致等结构性问题）
  → 修复脚本报的全部错误
② 内容审查（Agent逐条：对话准确性、行为模板、视角一致性）
  → 交叉验证（两个窗口独立审查→合并发现）
  → 修复 → 重跑validate_card确认通过
```

**踩坑实录（2026-07-12）**：用户让"看看有没有问题"→agent肉眼扫230KB JSON→发现"10个constant条目keys=[]"并手动改为有值→但validate_card.py check 26明确要求常驻条目必须keys=[]→修复方向反了。教训：先跑脚本。

**踩坑实录（2026-07-12 NTL赌场老板卡）**：子代理构建NTL卡时extensions用了驼峰命名（`automationId`/`groupOverride`）+漏掉十几个字段→ST导入后世界书不链接→agent肉眼扫发现→手动修→又给constant条目加了keys→validate_card报错→二次修复。教训：①子代理不受skill约束，防字段名错误靠validate_card不靠skill文档 ②validate_card.py check13已升级为31字段逐个校验，能自动抓字段名错误和缺失字段 ③本session agent误删10条enabled=false事件种子条目（T18）+误给constant条目加keys（违反check26），两处都是"先改后验证"的反面教材。

### 4.2 validate_card.py

**红线**：任何角色卡完成前必须跑。validate_card.py v5.2 提供两个明确边界：

- `--profile ccv3-core`：CCv3 根结构、完整 `data` 必填字段、Lorebook 类型/合法元字段、字符串或数字 ID；不要求顶层镜像或 `data.spec`。
- 默认 `--profile leyu-production`：在 core 之外继续执行 greeting ≥1400、31 字段扩展兼容、生产级内容/触发/关系门控与 G 型检查。
- `--format json`：输出稳定 `rule_id/severity/path/message/profile`，供 pytest、CI 与交付门控使用。
- **Runner 的 `--format json` 边界**：自动化在需要机器解析 Manifest 或 semantic manifest 配置读取错误时使用它；当前只保证上述五类配置错误采用结构化 JSON 输出。完整交付计划、semantic audit、semantic migration coverage 和 `final_delivery_gate.py` 结果仍以文本输出，不得把它描述成完整 Runner JSON 报告。启用 semantic manifest 的 Card 若 JSON 根节点不是对象，正式语义审计仍应以 `exit 1` + `SEMANTIC_AUDIT_INPUT_ERROR` 结束且不输出 traceback；coverage 统计不得遮蔽该正式错误。
- **迁移覆盖统计不是审计替代品**：`modern_text_modules_audited`、`legacy_semantic_modules_audited`、`non_semantic_entries_ignored`、`unregistered_formal_namespace_modules` 是文本报告中的 coverage 四项统计，只记录迁移覆盖范围；统计失败不能遮蔽正式审计，也不能借此放宽 Legacy namespace 规则。
- 配置错误的稳定错误码和 coverage 四项统计应分别按各自输出格式进入 CI/交付报告；不要用字符串猜测、宽泛异常捕获或“统计成功”代替正式 gate 结果。
- 匹配模拟由 `scripts/lib/worldbook_matcher.py` 单一实现共享；同时覆盖 primary、top-level selective、secondary logic、regex、大小写和 whole-word。

**修复工作流**：分类问题（规范/生产策略/内容/触发）→ 规范迁移使用 `migrate_card.py` 输出新文件 → 内容逐条 patch → 触发问题先跑 `audit_worldbook_triggers.py` → 每次改源后跑 canonical `check_build_sync.py`。

### 4.3 多子代理审查（30+条目卡）

3个并行子代理：结构格式(13项) / 内容原文(8项) / Skill规范(14项)。context必须传递完整路径和关键信息。修复后必须重跑。

⚠️ **子代理报告路径**：子代理写入 `/tmp/` 的文件在父session中不可读。关键发现只通过delegation response的summary文本传递。如需详细报告，让子代理写入用户目录（如桌面）。

⚠️ **NSFW安全过滤**：NSFW角色卡的卡壳(card_shell.json)子代理经常被模型安全过滤拒绝。卡壳部分（description/first_mes/alternate_greetings）由主代理在execute_code中直接生成，不委托子代理。

### 4.4 批量旧卡验证

`validate_card_report()`汇总 → `migrate_card.py` 预览并输出新文件 → 手动确认 position/display_index → `audit_worldbook_triggers.py` 审计 → canonical build-sync → 开场白/内容补强。不得原地批量改卡。

---

## 5. 发布与维护

### 5.1 常见陷阱（Pitfalls汇总）

| 陷阱 | 说明 | 修复 |
|------|------|------|
| first_mes顶层截断 | 顶层和data层不一致 | 统一为data层完整版 |
| 视角矛盾 | 条目禁止"你"但开场白全用"你" | 统一为第二人称 |
| 常驻keys非空 | constant=true带关键词→额外触发→截断 | keys=[] |
| alternates误放extensions | ST显示0个备选 | 移到data层 |
| 触发条目无keys | 永远不被触发=白写 | 补关键词 |
| 绿灯误判/泛key误触发(T73) | ST绿点/启用不等于真实触发；secondary_keys在顶层selective=false时被忽略；extensions.selective单独为true无效；selective=true+secondary空会primary-only；单字key如`家`会让无关场景常驻触发 | 跑validate_card触发审计；泛key改复合短语；需要副key约束时开启selective；多主题条目拆分 |
| Discord含违禁词 | 萝莉/幼女/童贞触发数删 | 全文扫描替换 |
| 开场白嵌入状态栏 | AI机械复制→叙事割裂 | first_mes纯叙事 |
| extensions空对象 | 搭配世界书时开场白无法生成 | 填满31字段 |
| extensions字段名错 | 子代理用驼峰(automationId/groupOverride)代替下划线(automation_id/group_override)，ST不认→世界书不链接。validate_card.py check13已升级为31字段逐个校验（2026-07-12实测） | 跑validate_card自动抓 |
| 新增条目复制extensions不完整(T79) | 优化/裁剪条目后新增速览条目时，若从分区标记或空扩展条目复制extensions，只会得到display_index等少数字段，validate_card报缺31字段；尤其在“轻量速览+深度档案”模式中常见 | 从现有条目中寻找`len(extensions)>=31`的完整模板再复制；复制后设置`display_index/id/addMemo`，并立即跑validate_card |
| 子代理extensions字段不全(T27) | 子代理产出的条目extensions只有~12/31字段，缺失exclude_recursion/outlet_name/group_override/group_weight/prevent_recursion等19个字段。天仙配案例：子代理设置30字段但缺19个，需主代理补全 | **合并后必须验证extensions完整性。** 修复代码：`default_ext={31字段默认值}; for k,v in default_ext.items(): entry['extensions'].setdefault(k,v)` |
| 锚点替换错位 | 多轮扩写用同一锚点 | 每轮换不同锚点 |
| 全局替换误伤外貌 | 不同角色共享颜色词 | 按角色关键词精确定位 |
| greeting/entry同脚本修改 | 中途报错→所有修改丢失 | greeting和entry分开不同execute_code调用 |
| validate_card误报(常驻→触发) | 条目从常驻转触发后，check18(开场白误入)和check23(状态栏字符)的豁免条件(constant+comment关键词)失效 | 误报是正常的，忽略即可 |
| `{{user}}`占位符泄漏 | 多视角NTL卡级联构建时，条目content中的"原{{user}}"渲染为新卡的{{user}}名（如"原兽人将军"） | 合并后全文扫描`原{{user}}`→替换为实际角色名（如"原赌场老板"） |
| 子代理greeting长度不足 | 子代理产出的alternate_greetings普遍<800字符（应≥1400），倾向于写"精炼"片段而非完整叙事 | 合并后逐条检查len()，不足的用execute_code扩写（追加场景细节/旁白/心理描写） |
| 子代理NSFW安全过滤 | 子代理写描写库/事件种子/场景模板等NSFW内容时被模型拒绝 | NSFW内容由主代理execute_code直接写，不委托子代理 |
| 开场白字节vs字符 | write_file报告字节数，validate_card.py检查字符数。中文UTF-8每字符≈3字节 | 用len()验证≥1400字符，≥1400字符需要≥4200字节 |
| execute_code三引号嵌套 | 长中文对话含引号→SyntaxError | 内容写到.txt文件再读取 |
| **构建脚本eid未自增(T45)** | mk()依赖外部eid，批量调用忘记自增→全部id=0。衍生产物：part2读取part1后`max(e.id)`=0→从eid=1而非正确值开始→合并后大量重复条目 | 加eid+=1，构建后检查`len(set(e.id))==len(entries)`。多阶段构建时用固定文件路径加载，不要假设ID正确 |
| **开场白一轮扩写不足(T46)** | 首次写350-750字，三路扩写才到1400 | 直接写1200+起步，差距>500时写完整文本文件再读 |
| **中文字vs总字符(T47)** | 加料自检只统计汉字，中文字1100但总字符1500+ | 接受中文字1200+且内容质量达标的条目 |
| **开场白用pad_to类占位符填充(T48)** 🆕 | 开场白字数不够1400时用通用填充函数塞重复旁白→ST中显示为连续重复的垃圾文本 | 差距<50：追加感官描写；差距>500：重写完整场景。不要用带重复因子的字符串填充函数 |
| **first_mes泛词连锁触发(T76)** 🆕🆕 | first_mes场景描写自然包含"客厅""身体""堕落""日常""沐浴""味道"等泛词→命中大量条目首轮全部加载。周雨晴卡实测：12条/4960字被first_mes触发→修后3条/1161字 | keys不能用first_mes场景中的常见词。改用场景专属短语（"沙发上偷摸"替代"客厅"、"敏感点"替代"身体"、"堕落进度"替代"堕落"）。验证：`[k for k in entry.keys if k in first_mes]`为空=安全。详见`references/misc/pitfall-t76-t79-token-repair.md` |
| **greeting双版本拼接+重复填充(T77)** 🆕🆕 | 每个alternate_greetings内含同一场景两个版本拼接，或末尾有重复氛围句（同句重复7-11次）。T48变体。周雨晴卡实测：ALT3重复11次，ALT5重复9次 | 诊断：line_counts检查行重复。修复：①双版本拼接→识别重复场景起始行→删第二版本 ②重复氛围句→smart_dedup保留首次。清理后必须≥1400字→用新内容补写。详见`references/misc/pitfall-t76-t79-token-repair.md` |
| **跨窗口审查报告修正模式(T78)** 🆕🆕 | 用户从另一窗口独立审查给出修正报告。典型修正：token影响表述夸大/复合关键词违反T70/常驻条目数偏高/修复顺序错（先加厚再修结构） | 逐条核验不盲从。**修复顺序铁律：结构字段→greeting去重→常驻瘦身→触发key分层→validate→再考虑加厚。**"先加厚再修结构"会适得其反。详见`references/misc/pitfall-t76-t79-token-repair.md` |
| **trigger key分层设计(T79)** 🆕🆕 | 18组关键词重叠（如"胸部"命中3条、"体位"命中3条）→一个关键词连锁触发多条无关条目 | 分层：轻量场景用自然具体词（"乳交""后背位"）；深度档案用专属标签（"体位描写库"）。目标：关键词重叠归零。详见`references/misc/pitfall-t76-t79-token-repair.md` |
| **裁剪角色后系统条目残留引用(T49)** 🆕 | 裁剪角色后只删了对应条目，但系统条目中的示例和引用未同步更新。另一窗口交叉验证发现22处残留。**实证：最常漏扫的系统条目**：`[3]反顺从规则`的NPC举例（吕玲珑）、`[8]淫妻兴奋度`的角色对比（吕玲珑最慢）、`[0]OOC防护`的背景引用（美汁汁儿系统）、`状态栏[1]`的阶段枚举 | 裁剪角色后必须扫所有系统条目/场景/开场白中对已删角色的引用。铁律：**每删一个角色，做一次全卡scan**。重点检查：`content`全文（不仅comment）含已删角色名、系统条目举例句、开场白背景描写 |
| **make_entry()参数混淆** | `make_entry(eid, keys, comment, content, ...)` 第三/四参数是`comment`和`content`。构建时若遗漏comment直接用多行字符串作第三参数，Python会将内容字符串当作comment、然后报`missing 1 required positional argument: 'content'` | 使用`add(**kw)`包装：`def add(**kw): global eid; e = mk(eid, **kw); entries.append(e); eid += 1`。调用时显式传`comment=xxx, content=yyy` |
| 首轮触发过载 | 角色名("师傅""伯里")作关键词→first_mes触发全部条目→token>15K | 用复合关键词("古兰""主母")或不常见的名字 |
| 首轮触发过载 | 角色名("师傅""伯里")作关键词→first_mes触发全部角色条目→token>15K | 用复合关键词("古兰""主母")或不常见的名字 |
| **架构漂移(T122·2026-07-26)** 🆕 | 开始用阶段路由构建，中途变成厚条目；或用户提供厚条目映射模板，仍拆成P#薄条目 | 计划书必须记录 `architecture_mode`，build manifest同步；验证器检查是否存在两套冲突路由 |
| **阶段未来泄漏(T123·2026-07-26)** 🆕 | 常驻条目/早期阶段包写了后期专属称呼、秘密、身体变化、习惯 | 常驻只保留底层人格+因果方向+协议；后期专属内容只进入对应阶段包 |
| **事件事实化(T124·2026-07-26)** 🆕 | 事件库写成"已经发生""此后固定会""角色已经接受" | 每个事件单元需具备前提、自然切入、人物反应和分歧/代价 |
| **AI自动跳阶段(T125·2026-07-26)** 🆕 | 导演协议看到事件就默认升级P#，或模型自行改路由标记 | 记忆闸门明确"只能从当前阶段事件库选候选；转阶需玩家明确切换" |
| **P#死键(T126·2026-07-26)** 🆕 | `阶段：P#`/`事件库`/`语料库`为唯一key，聊天永不出现 | 阶段包换Greeting标题；普通条目换自然词 |
| 关键词优化降负载(T24) | 条目扩充后content变长→first_mes触发的条目总token从5K飙到15K+→validate_card报error | **扩充条目后必须重新检查first_mes触发负载。** 修复：把高频关键词（"妈妈""妹妹""老师""黑人""别墅"等）改为复合短语（"林美娟设定""菲儿外貌""黑人街场景"）。天仙配案例：15150字→3626字，降低76%。铁律：扩充条目后→重跑关键词触发分析→优化→重验validate_card | | 即使关键词不同但first_mes中含所有关键词（如"倪楠""妈妈""倪珠"同时出现）→一个角色4条目全部触发→3个角色=12条+8常驻=20K+ tokens | **每个条目的关键词必须足够独特，不与first_mes中的常见词重叠。** 方案：①用"角色名+条目类型"复合关键词（"倪楠设定"/"倪楠性格"）替代纯角色名 ②减少每角色条目数（4条→3条）③将部分条目改为常驻(keys=[])——但常驻本身占token，需权衡 |
| 子代理误设constant=true(T21) | 子代理产出的角色条目（薛明/金晓玲基础档案等）被设为constant=true→常驻条目数暴增→token激增+check26报错 | **合并后必须逐条检查constant字段。** 批量修复：`for e in entries: if e['id'] in character_id_range: e['constant'] = False` |
| 主代理也误设constant=true(T25) | 主代理写核心女主基础档案时设constant=True——角色条目应该是keyword-triggered(constant=False)。天仙配案例：ID11/13/15被误设，需后续修复 | **铁律：只有系统规则条目(OOC/文风/状态栏/旁白/叙事节奏/反顺从/NPC行动)才是constant=true。角色/世界观/场景/事件/辅助全部constant=false+keys** |
| 堕落轨迹条目误禁用(T26) | 主代理把"堕落轨迹"条目(enabled=false)当作辅助条目禁用→validate_card报错"非事件种子不应禁用" | **只有事件种子库(enabled=false)可以禁用。堕落轨迹/阶段特征/规则条目必须enabled=true+有keys** |
| 子代理extensions字段不全(T27) | 子代理产出的条目extensions只有~12/31字段，缺失exclude_recursion/outlet_name/group_override/group_weight/prevent_recursion等19个字段。子代理用了camelCase(automationId)而非snake_case(automation_id) | **合并后必须验证每个条目extensions有全部31字段。** 修复：`default_ext = {31个字段默认值}; for k,v in default_ext.items(): entry['extensions'].setdefault(k,v)` |
| 审查关键词映射假阳性(T28) | 计划书vs实际映射检查只搜comment+content[:200]，漏搜keys字段→"唐幂恋情"在keys中但搜索报缺失 | **Step2映射检查必须搜comment+content[:200]+keys三个字段** |
| NSFW子代理过滤扩展(T29) | memory记录"卡壳由主代理直接写"，但实际角色条目（描写库/行为模板/堕落轨迹）也被安全过滤拒绝。天仙配案例：3个子代理中2个被拒（核心女主+黑人角色+事件种子），仅"重要女主"(唐幂/冷清雪等较含蓄)通过 | **NSFW内容不委托子代理的范围应扩展到：角色描写库、堕落轨迹、事件种子、行为模板——不仅是卡壳** |
| 合并后ID不连续(T22) | 各子代理独立分配ID(10-17/18-25/30-32/40-45)→合并后ID跳跃→validate_card check15报错 | **合并后全量重编号。** `for i, e in enumerate(sorted(entries, key=lambda x: x['id'])): e['id'] = i; e['extensions']['display_index'] = i` |
| execute_code中文引号SyntaxError | execute_code中内联中文文本含中文引号（\u201c\u201d）时触发Python SyntaxError | **大段中文内容不走execute_code。** 改用：write_file写内容到/tmp/→write_file写Python脚本到/tmp/→terminal执行 |
| validate_card非连续ID IndexError(T23) | validate_card.py check27/31用`entries[eid]`直接索引list→ID不连续时(如ID=10但list中index不是10)→IndexError | **已修复：** validate_card.py现在用`entry_map = {e['id']: e for e in entries}`做dict查找。但仍建议合并后重编号ID |

### 5.2 Token管理

**目标**：触发负载是诊断指标，不是硬红线。高 token/高字符数本身不等于坏卡；只要 ST/模型上下文足够、没有截断、触发内容都相关，1w-10w 级请求规模也可以接受（大型结构化卡实测）。注意：ST请求查看器里的“10万”常常是字符数/JSON体规模，不等于API实际input tokens；真实占用优先看 Prompt Itemization、API usage 或官方 countTokens。真正需要优化的是：泛 key 噪声、无关条目污染、递归触发链、重复内容、累计计费失控和模型实际质量下降。

**先读专项参考**：`references/st-technical/trigger-quality-vs-token-load.md`。该文件总结大型结构化卡/参考助手预设/校园示例卡/示例G型卡/示例G型卡/示例关系卡的对比：卡顿不只由裸 token 决定，还取决于触发条目是否相关、内容是结构化协议还是高密度叙事素材，以及每轮输出义务（状态栏/旁白/多NPC/反顺从/阶段推进）是否过重。若问题来自社区某预设/某模型截断，还要读 `references/st-technical/card-vs-runtime-boundary.md`，先区分卡内缺陷与运行环境问题。

**五大优化策略**：
1. 常驻keys=[] — 不带关键词避免额外触发
2. 复合关键词 — `"{角色}身体描写"` 而非 `"{角色名}"`。**⚠️ 复合关键词仅用于降低深度档案/冷门条目的误触发，核心角色主档案必须保留自然角色名作为 primary key。** `角色名档案` 这类人工复合词不能作为主档案的唯一 key（死代码）。详见 §3.3 主档案触发铁律。
3. 常驻转触发 — 只保留4-8条真正每轮都需要的内容
4. 性爱规则按需加载 — 不放常驻
5. **关闭递归触发** — 所有触发条目 `prevent_recursion=True`（False导致链式触发→token膨胀3-5倍）

**负载参考（诊断信号，不是硬红线）**：<2000轻 / 2000-4000正常 / 4000-6000偏高 / >6000需审计。大型结构化卡实测证明高请求体不必然卡；若触发内容相关且模型上下文足够，可接受高负载。真正必须修的是：无关触发、泛key、secondary失效、递归链、重复greeting、常驻输出义务过重、或实际已出现截断/回空。

**🆕 Token修复顺序铁律（T78·2026-07-15·周雨晴卡实证）**：当token负载过高需要修复时，**必须按以下顺序执行，不能跳步或倒序**：
1. 规范字段与镜像一致性（完整 `data` 必填字段；仅在镜像同时存在时统一 `first_mes` 等；不强制 `data.spec/spec_version`）
2. greeting去重（删除重复场景+重复氛围句）
3. 常驻瘦身（13条→5-7条，移除不必要的常驻）
4. 触发key分层（解决关键词重叠，建立自然key+档案key双层）
5. validate验证
6. **最后才考虑加厚内容**

"先加厚再修结构"会适得其反——加厚增加条目字数→触发更多token→截断更严重。必须先让token空间充裕，再投入内容加厚。

**⚠️ T70教训：降token不能牺牲触发**。复合关键词（`雪乃设定`）能降负载但条目永远不触发=死代码。正确策略：①接受简单关键词的token代价②通过精简常驻条目数(7→4)③合并系统条目/移入system_prompt④精简角色条目内容来控制总token。**关键词必须是AI对话中会自然出现的词。**

**T78：中厚速览 + 深度档案（2026-07-15 校园示例卡v2实证）**：当加料自检要求角色/威胁档案≥1500-2000字，导致opening一提角色名就触发整条深度档案、token负载超标时，不要削薄内容，也不要把自然角色名改成完全不会触发的死key。正确做法：新增**250-350中文字的中厚“角色速览/威胁速览”**条目，用自然角色名触发；原2000字深度档案改用专用key（如`雪乃档案`、`户部档案`）按需触发。速览不能只是90-130字标签，必须自带：角色定位、危险信号、当前回合写法、玩家可介入窗口、深度档案key提示。**重要：速览与深度档案不会自动一起触发**——ST不会递归扫描已插入世界书条目，且`prevent_recursion=true`会阻止“速览内容里写了档案key”触发深度档案。若首轮需要可用素材，速览本身必须够厚；深度档案只是二层按需素材。详见 `references/workflows/lightweight-summary-deep-profile-trigger-pattern.md`。

### 5.2.1 社区反馈修卡专项：关系称谓与触发回归（T76/T77）

**T76：多视角/G型角色关系相对称谓漂移。** 从苦主版、NTL版或G型共用层迁移内容时，`妹妹`、`妈妈`、`自己的`、`亲生`、`父亲`这类相对称谓会随 {{user}} 身份改变而失真。社区反馈通常先指出一处（如詹姆条目把「林菲儿=林子睿的妹妹」写成「自己的妹妹/亲妹妹」），但同类错误往往分布在 Mike/James/支线角色条目中。

**修复流程**：不要只改截图处。先脚本全卡扫描高危短语：`自己的妹妹|亲妹妹|亲生母亲|自己的母亲|麦克的母亲|詹姆的妹妹|姐姐侍妾`，再改成**绝对关系锚点**：`林子睿的妹妹`、`林美娟的女儿`、`麦克的侍妾/林子睿的母亲`、`先入门侍妾`。G型共用层禁止使用依赖当前 {{user}} 的相对亲属称谓，除非明确写「对林子睿而言」。

**T77：关系修复后触发负载回归。** 小修人物关系后，新版 `validate_card.py` 可能暴露旧卡既存触发错误：单字泛key（如 `家`）误触发、`性格/阶段/征服/语料/对话` 等共享泛key导致首轮加载整套深度条目，token从6K飙到10K+。这不是关系修复引入，但交付前必须处理到0 error。

**修复流程**：关系修复后必须跑 `validate_card.py`。若报触发负载/泛key：①删除单字key（`家`→`南山别墅/林家别墅/逍遥岛别墅`）；②深度条目改复合key（`林美娟性格/林美娟阶段/林美娟语料`）；③仅对**非核心/冷门/后期按需**支线角色档案改档案型key（`唐幂档案/冷清雪档案`），避免开场白一提人名就触发全档案。核心主档案仍必须有自然角色名或中厚速览承接，不能只剩`角色名档案`死key。目标：`validate passed=True, errors=0`；剩余「开场白不触发」warning可接受，因为深度条目是按需触发。

### 5.2.2 扩卡触发审计工作流（T35教训）

当向已有卡新增条目时，必须执行此流程防止token负载暴涨：

```python
# 1. 列出所有新条目的关键词
new_keywords = []
for e in new_entries:
    new_keywords.extend(e['keys'])

# 2. 逐个检查是否出现在first_mes中
fm = card['data']['first_mes']
for kw in new_keywords:
    if kw in fm:
        print(f"⚠️ '{kw}' 出现在first_mes中 → 会触发该条目")

# 3. 匹配的关键词改为复合短语
# 常见需要替换的词：
#   "院子" → "枣树下"/"院墙边"/"鸡笼旁"
#   "山上" → "花生地"/"老槐树"/"山顶旱田"
#   "村民" → "村口榕树"/"田埂邻居"
#   "猪圈" → "猪圈旁"/"猪圈栅栏"
#   "妈妈" → "母亲"（如果"妈妈"在first_mes中但"母亲"不在）

# 4. 重跑validate_card确认负载<8000
```

### 5.3 Discord发布

**三种格式按场景选用**：

| 场景 | 格式文件 | 说明 |
|------|---------|------|
| **合集频道发卡**（最常用） | `<PLATFORM_FORMAT_TEMPLATE>` 🆕 | 3行/卡，`标签/标签 - 一句话`，不用分段标题 |
| 单卡展示帖 | `<PLATFORM_FORMAT_TEMPLATE>` | 分段展示（📋/🎮/👥/🎭），≤20行 |
| 完整介绍帖 | `<PLATFORM_FORMAT_TEMPLATE>` | 50+行，含完整系统说明 |

**🚨 用户说"合集"/发来平台截图 → 必须用 collection-listing 格式，不要用分段模板。** 分段模板（📋🎮👥🎭）对合集频道太啰嗦，用户会拒绝。2026-07-12实测：agent用showcase格式→用户发截图纠正→改用3行一图流格式。

**红线**：所有格式（含展示格式）必须满足 ≤2000 Unicode codepoints。展示格式目标1200-1800字（留余量给emoji和markdown标记），合集格式无下限。每次制卡完成后生成简介文档，用 `sum(1 for c in content if ord(c) <= 0xFFFF)` 验证长度。
审查流程：硬性禁词→高风险语境→中风险近似词→逐字精读。

### 5.3.1 🆕 Discord 发布文案违禁词扫描

**边界（优先于历史案例）**：平台只审核将要发布的简介/帖子，不审核角色卡 JSON、世界书、开场白或卡内内容。**不要为了社区发布扫描、删改或降尺度角色卡正文。** 未要求发布时本节不运行，也不进入 `run_delivery.py` 的日常 gate。


```python
# 仅扫描即将发布的文本文件；card.json 不在扫描范围内。
from pathlib import Path
publish_text = Path('discord简介.md').read_text(encoding='utf-8')
forbidden = ['萝莉', 'luoli', 'loli', '幼女', '童贞']
for word in forbidden:
    if word.lower() in publish_text.lower():
        print(f"❌ 发布文案含禁词：{word}")
```

**常见漏扫位置**：标题、摘要、玩法标签、合集的一句话介绍和纯文字版。卡内 description 只有被逐字复制进发布帖时，才以复制后的发布文本为对象审查。

### 5.4 截断/空回诊断

先读 `references/st-technical/card-vs-runtime-boundary.md`：制卡流程只判定卡内问题（泛key、secondary失效、first_mes误触发、常驻/每轮强制项、人物关系、内容厚度）。单次偶发截断、用户预设、模型安全策略、API网关/流式断流属于运行环境排查，不能直接判卡失败。

| 症状 | 根因 | 修复 |
|------|------|------|
| 完全空回 | 旧格式或损坏 JSON 未被 ST 解析 | 先 `migrate_card.py` dry-run，再输出新 CCv3 文件并用 `validate_card.py --profile ccv3-core` 验证 |
| 第一次截断/第二次正常 | API预设膨胀 | 调max_context |
| 每次都截断 | 递归触发链/世界书过载 | 修复prevent_recursion |
| 正文开头后几百字直接断、缺少闭合标签/状态栏/abstract/note，且重复多次 | **输出侧问题**：实际 response cap/网关安全断流/预设输出义务过重。若日志中正文只生成几百中文字，却要求2000-4000字+面板+摘要，先不要继续修世界书 | 做A/B：同预设安全短剧情是否也断；若安全也断=API/response cap；若只有敏感剧情断=网关安全。临时降输出：字数600-1200、关闭INDRS/abstract/note/草稿/思维链/强制状态栏，或换模型/端点 |
| 回复变短 | 世界书条目总token过高 | 优化关键词 |
| 🆕 首轮截断后续正常 | first_mes触发过多条目+常驻过多 | T76修复：优化keys+瘦身常驻 |
| 🆕 greeting选择后空回 | greeting重复填充导致token暴涨 | T77修复：去重greeting |

**🆕 截断修复后的加厚原则**：截断/空回修复完成后，不要立即加厚内容。先确认token负载稳定在安全范围（<6000 tokens），再开始P2内容加厚。加厚过程中每轮都要检查token变化——如果加厚导致token重新超标，立即停止并优化触发结构。

### 5.5 SP-数据库兼容

条目>50时，用户需调大 `maxEntriesPerChannel.tableFill` 到50-80。制卡侧目标40-60条以内。

---

## 6. 模板库（模板13-19 🆕 源自大型结构化卡）

**全部P0纯文本通用。** 完整模板库见 `references/game-mechanics-template-library.md`。

| 模板 | 一句话 | 何时用 |
|------|--------|--------|
| 13 人物描写结构化 | 每个特质=体现+行为举例+触发条件 | 写任何角色条目时 |
| 14 叙事节奏循环 | 铺垫→紧张→NTR→余韵→日常 | NTR/剧情卡必须 |
| 15 事件分段标记 | `[场景开场]→[互动]→[选择点]→[分支]` | 写事件条目时 |
| 16 文风锚点 | 核心基调+感官锚点+禁止文风 | 任何卡必须 |
| 17 反AI顺从 | 玩家输入=尝试，非既定事实 | NTR/对抗卡必须 |
| 18 状态行为标志 | "乳头挺立"替代"堕落值+5" | 任何有状态追踪的卡 |
| 19 场景环境锚定 | 安全等级+NPC分布+事件概率 | 多场景卡必须 |

**配套参考文件**：
- `logical-firewall.md` — 四层校验体系
- `personality-encoding.md` — 六维性格编码
- `structured-item-system.md` — 道具结构化描述
- `section-markers-organization.md` — 分段标记工作流
- `structured-card-run-validation.md` — 大型结构化卡跑卡验证

---

## 7. 参考文件索引

> **自动重建说明（2026-07-15）**：本索引按当前目录实际文件生成，分为 active / archived / deleted。以后不要手工维护百行索引；新增/删除文件后用脚本扫描 `references/`、`scripts/`、`templates/` 重新生成。
> 默认只读 active；`_archived/` 仅用于追溯旧审查体系，不参与新卡流程。

### 审查模板（active）（21）

| 文件 | 摘要 |
|------|------|
| `references/audit/NTL变体审查启动模板.md` | NTL变体卡审查启动模板（通用版） |
| `references/audit/NTR苦主卡审查启动模板.md` | NTR苦主卡审查启动模板（通用版） |
| `references/audit/_README.md` | audit/ 目录文件组织 |
| `references/audit/card-audit-checklist.md` | 角色卡审查工作流（Card Audit） |
| `references/audit/card-audit-workflow.md` | 卡审查流程（自动化脚本+Agent双审） |
| `references/audit/card-cross-verification-workflow.md` | 角色卡交叉验证工作流（Card Cross-Verification Workflow） |
| `references/audit/card-governance-report-pattern.md` | 治理报告委派模式（Governance Report Delegation） |
| `references/audit/card-quality-assessment.md` | 已有卡质量评估流程（2026-07-11 校园媚黑守护卡v2评估验证） |
| `references/audit/character-card-audit-checklist.md` | 角色卡条目质量审查清单 |
| `references/audit/content-contradiction-checks.md` | 卡内容矛盾检测（脚本审查Phase 2） |
| `references/audit/full-process-skill-audit-findings.md` | 制卡全流程 skill 审查发现（v6.33 实测） |
| `references/audit/hero-name-verification-pattern.md` | 角色名幻觉验证模式（T60 · 2026-07-14） |
| `references/audit/quality-check-instruction-template.md` | 角色卡规划书质检指令模板 |
| `references/audit/review-template-system.md` | 审查模板体系（基础模板 + 原型专项） |
| `references/audit/世界书触发专项审查模板.md` | 世界书触发专项审查模板：触发意图、泛key、secondary、普通句反证、速览自足性 |
| `references/audit/skill-maintenance-checklist.md` | Skill 维护检查清单（2026-07-12 交叉验证总结） |
| `references/audit/validate-checklist-detail.md` | 完成前强制验证（红线步骤，不可跳过！） |
| `references/audit/修卡审查启动模板.md` | 修卡审查启动模板（通用版） |
| `references/audit/初始卡审查启动模板.md` | 初始卡审查启动模板（通用版） |
| `references/audit/守护卡审查启动模板.md` | 守护卡/觉醒卡审查启动模板（通用版） |
| `references/audit/禁忌后宫征服卡审查启动模板.md` | 禁忌后宫征服卡审查启动模板（通用版） |

### 案例（active）（23）

| 文件 | 摘要 |
|------|------|

### 设计模式（active）（35）

| 文件 | 摘要 |
|------|------|
| `references/design-patterns/structured-card-run-validation.md` | 大型结构化卡 v4.2 — 实际跑卡验证报告 |
| `references/design-patterns/greeting-director-appendix-standard.md` | Greeting 导演附录最高标准：stage_brief_v1 八维阶段简报 + 玩家接管点 + 人工专项 |
| `references/design-patterns/gameplay-type-card-design.md` | 玩法型卡片设计参考 |
| `references/design-patterns/guardian-card-archetype.md` | 守护卡原型设计参考 |
| `references/design-patterns/hidden-ntl-composite.md` | 隐奸NTL复合设计模式（Hidden NTL Composite Pattern） |
| `references/design-patterns/hidden-ntr-design.md` | 隐奸NTR设计模式（Hidden NTR Design Pattern） |
| `references/design-patterns/logical-firewall.md` | 分层逻辑防火墙设计模式 |
| `references/design-patterns/manual-toggle-identity-pattern.md` | 手动选开身份模式（G型子选择） |
| `references/design-patterns/material-pack-entry-pattern.md` | 素材包条目设计模式（Material-Pack Entry）——成人素材条目与行为/规则条目职责分离，keys=阶段P#跟随阶段触发 |
| `references/design-patterns/multi-perspective-card-design.md` | 多视角内置角色卡设计模式（G型·✅ POC已验证） |
| `references/design-patterns/native-stage-trigger-card-architecture.md` | 阶段型小说原生开场标题触发架构（不绑定预设的单文件阶段卡·Greeting 标题路由） |
| `references/design-patterns/npc-behavioral-independence.md` | NPC行为独立性设计 |
| `references/design-patterns/npc-information-boundary.md` | 多NPC信息边界设计 |
| `references/design-patterns/open-ended-card-design.md` | 开放性卡片设计案例（示例玄幻项目改造） |
| `references/design-patterns/semantic-modular-open-card-architecture.md` | 开放兼容型模块化语义档案：角色×职责、来源/真值/时间/可见性、行为响应、地点合同、开放路线与运行时投影；配套审计脚本和 manifest 模板 |
| `templates/semantic-module-manifest.example.json` | Lite/Standard/Full 兼容的项目与运行时合同示例，复制后按项目删改 |
| `references/formats/semantic-module-text-style.md` | 纯文本层规范：Markdown 层级、模块 schema、作者版/运行时版分离和 YAML 缩进边界 |
| `templates/semantic-*-v1.md` | 角色心理、身份、语言、地点、互动机制、关系六类模块正文模板 |
| `references/design-patterns/persona-contradiction-modeling.md` | 人设反刻板方法论：核心矛盾建模+离散对白流+反复读自查清单（🆕 2026-07-26，内容质量层） |
| `references/design-patterns/personality-encoding.md` | 六维性格编码模型 |
| `references/design-patterns/recursive-trigger-chain.md` | 递归触发链 - 完整诊断与修复 |
| `references/design-patterns/st-worldbook-triggering-behavior.md` | ST 世界书触发机制实测文档 |
| `references/design-patterns/stage-adult-material-enrichment-packs.md` | 阶段成人素材包加厚模式——给已能稳定路由的阶段卡补调情语料/身体反应链/性事件示例 |
| `references/design-patterns/structured-item-system.md` | 道具/机制的结构化描述模板 |
| `references/design-patterns/token-optimization-selective-triggers.md` | Token优化：常驻→触发+selective改造 |
| `references/design-patterns/user-perspective-narration.md` | {{user}}视角与旁白解说机制 |

### Discord 发布（active）（4）

| 文件 | 摘要 |
|------|------|
| `references/<PLATFORM_FORMAT_TEMPLATE>` | Discord合集/平台列表格式（类脑IAIAS·一图流） |
| `references/<PLATFORM_FORMAT_TEMPLATE>` | Discord 简介文档规范（每次必生成） |
| `references/<PLATFORM_FORMAT_TEMPLATE>` | Discord作品集展示格式 |

### 格式规范（active）（9）

| 文件 | 摘要 |
|------|------|
| `references/formats/dual-route-architecture.md` | 双路线架构：守护 vs NTR 分支系统 |
| `references/formats/json-assembly-pitfalls.md` | JSON组装坑点清单（2026-07-11 实测验证） |
| `references/formats/md-to-json-assembly.md` | MD → JSON 组装参考 |
| `references/formats/merge-duplicate-entries.md` | 合并重复条目（扩充后的必要步骤） |
| `references/formats/st-native-charcard-format.md` | SillyTavern 角色卡内嵌世界书格式（2026-07-04 修正版） |
| `references/formats/st-native-worldbook-format.md` | SillyTavern 原生世界书导出格式 |
| `references/formats/wb-entry-json-schema.md` | 世界书条目JSON Schema + 节点/结局内容格式 |
| `references/formats/worldbook-cleanup-and-sync.md` | 世界书清理与同步工作流 |
| `references/formats/worldbook-entry-structure.md` | 世界书条目结构参考 |

### 杂项/Pitfalls（active）（7）

| 文件 | 摘要 |
|------|------|
| `references/misc/greetings-from-file-assembly.md` | 开场白文件化组装模式 |
| `references/misc/pitfall-library.md` | T70: 开场白扩写的迭代模式（2026-07-14·校园示例卡守护卡实证） |
| `references/misc/pitfall-t58-execute-code-thinning.md` | T58: execute_code写入条目内容实际字数远低于预期（2026-07-13·示例G型卡世家G型卡实证） |
| `references/misc/pitfall-t61-t64.md` | T61: 小说预处理·文件名含标题后缀（2026-07-14·医生妈妈叶明熙卡实证） |
| `references/misc/sub-agent-json-build-patterns.md` | 子代理并行构建JSON的模式与陷阱 |

### NTL/NTR（active）（11）

| 文件 | 摘要 |
|------|------|
| `references/ntl/guardian-transformation-framework.md` | NTR→守护版 视角转换框架（夺回/觉醒线） |
| `references/ntl/ntl-conquest-card-workflow.md` | NTL逆寝取卡创建工作流（2026-07-12·赌场老板案例） |
| `references/ntl/ntl-netori-framework.md` | NTL逆寝取框架（{{user}}=寝取者） |
| `references/ntl/ntl-perspective-conversion.md` | NTL视角转换指南 |
| `references/ntl/ntl-recovery-route-workflow.md` | NTL夺回路线卡·创建工作流 |
| `references/ntl/ntl-variant-audit-extras.md` | NTL变体卡审查追加项 + 新验证坑（2026-07-11·示例角色项目NTL案例） |
| `references/ntl/ntl-variant-card-workflow.md` | NTL变体卡创建工作流（2026-07-11·示例角色项目案例） |
| `references/ntl/ntl-variant-templates.md` | NTL/变体卡模板（合并到通用模板库的补充） |
| `references/ntl/ntl-version-audit-checklist.md` | NTL版审核检查清单 |
| `references/ntl/ntr-multi-target-weight-distribution.md` | NTR多目标权重分配指南 |
| `references/ntl/ntr-relationship-matrix.md` | NTR关系矩阵设计模式 |

### ST 技术（active）（14）

| 文件 | 摘要 |
|------|------|
| `references/st-technical/execute_code-string-escaping.md` | 中文字符的字节/字符比（2026-07-04 叶无云案例） |
| `references/st-technical/execute_code-tmp-contamination.md` | /tmp/ 文件污染问题（2026-07-04 闷骚健身美母案例） |
| `references/st-technical/sillytavern-scripting-patterns.md` | SillyTavern 脚本化模式参考 |
| `references/st-technical/sp-database-plugin-compatibility.md` | SP-数据库插件兼容性指南 |
| `references/st-technical/st-reasoning-parser-and-png-format.md` | SillyTavern Reasoning Parser 与 PNG 角色卡格式（2026-07-08 实测） |
| `references/st-technical/st-reasoning-parser-behavior.md` | SillyTavern Reasoning Parser 行为分析（ST 1.18.0 实测） |
| `references/st-technical/st-reasoning-parser-pitfalls.md` | SillyTavern Reasoning/Thinking 解析器陷阱 |
| `references/st-technical/st-regex-placement-analysis.md` | SillyTavern Regex Placement 与世界书内容篡改分析 |
| `references/st-technical/st-truncation-diagnosis.md` | ST 截断诊断完整流程 |
| `references/st-technical/card-vs-runtime-boundary.md` | 角色卡质量 vs 运行环境问题边界：预设/API/模型安全导致的截断不计为卡质量失败 |
| `references/st-technical/trigger-quality-vs-token-load.md` | 触发质量 vs 裸 token 负载：大型结构化卡/参考助手预设/我方剧情卡对比，解释为什么高请求量未必卡、低触发量也可能截断 |
| `references/st-technical/truncation-diagnosis.md` | 截断/空回诊断与优化 |
| `references/st-technical/unicode-encoding-pitfalls.md` | Unicode Encoding Pitfalls for Character Cards |
| `references/st-technical/worldbook-position-depth-guide.md` | 世界书插入位置与深度取舍指南：桶型结构/U型注意力/三分层放置/D0-D4 风险（🆕 2026-07-26） |

### 工作流（active）（39）

| 文件 | 摘要 |
|------|------|
| `references/workflows/analysis-document-template.md` | 小说分析文档模板 — 跨窗口交接件 |
| `references/workflows/card-assembly-and-delivery-pipeline.md` | 角色卡组装→交付分支矩阵：build、加料、原生阶段、配套预设与最终门控命令 |
| `references/workflows/manifest-driven-delivery.md` | 日常生产的 build_manifest → run_delivery → final gate 单次门控；RUN/SKIP 报告、自动判型、Greeting 模式和失败诊断分流 |
| `references/workflows/card-repair-workflow.md` | 修卡工作流（社区反馈/逻辑修复） |
| `references/workflows/controlled-enrichment-pass.md` | 大型既有卡的受控加料：四类责任分层、baseline+manifest 差分门控与快照卫生 |
| `references/workflows/content-file-first-build-pattern.md` | Content-File-First 构建模式（通用版） |
| `references/workflows/cross-window-fix-verification.md` | 交叉验证·修复核验清单 |
| `references/workflows/enhancement-workflow.md` | 角色卡对比增强工作流参考 |
| `references/workflows/expansion-workflow.md` | 首次生成太薄的根因分析与扩充工作流 |
| `references/workflows/full-rebuild-after-trigger-audit.md` | 触发审计失败后的全新重做流程：何时停止补丁式修卡，重新跑原型判定/源文件统计/新版规划书/触发设计矩阵 |
| `references/workflows/multi-chapter-novel-to-card.md` | 多章小说→角色卡 完整工作流（2026-07-03 圣馨医院案例） |
| `references/workflows/multi-reference-card-design.md` | 多参考卡设计模式（Multi-Reference-Card Design） |
| `references/workflows/novel-collection-split-pattern.py` | !/usr/bin/env python |
| `references/workflows/novel-to-card-sizing.md` | 小说→角色卡 预估分析流程 |
| `references/workflows/parallel-large-card-workflow.md` | 大型卡并行生成+合并工作流 |
| `references/workflows/parallel-subagent-card-modification.md` | 大型角色卡JSON修改·并行子代理工作流 |
| `references/workflows/planning-readiness-evaluation.md` | 计划书达标评估方法论 |
| `references/workflows/section-markers-organization.md` | 分段标记：大型卡组织工作流 |
| `references/workflows/seven-phase-build-ordering.md` | 7-Phase 构建顺序（大型卡标准流程） |
| `references/workflows/stage-entry-contract-gate.md` | 原生阶段卡运行时条目合同门控——`stage-entry-contract.json`（schema v2）sidecar 的产出与审计要求 |
| `references/workflows/template-evaluation-workflow.md` | 模板库评估工作流（2026-07-10 交配学校案例） |
| `references/workflows/variant-card-production-lessons.md` | 变体卡生产经验（异世界系列+校园女友验证，2026-07-11） |
| `references/workflows/variant-card-production-workflow.md` | 变体卡生产流程（2026-07-11异世界卡验证） |

### 根目录旧兼容参考（active，但优先用子目录新版）（63）

| 文件 | 摘要 |
|------|------|
| `references/card-audit-checklist.md` | 角色卡审查清单（自动化+Agent双轨）v4.3 |
| `references/card-audit-workflow.md` | 角色卡审查工作流（脚本审查 + Agent审查） |
| `references/card-cross-verification-workflow.md` | 角色卡交叉验证工作流（Card Cross-Verification Workflow） |
| `references/card-governance-report-pattern.md` | 治理报告委派模式（Governance Report Delegation） |
| `references/directory-map.md` | references/ Directory Map (v3.1, 2026-07-11) |
| `references/directory-structure-map.md` | references/ 目录结构（v3.1，2026-07-11重组） |
| `references/directory-structure.md` | references/ 目录结构说明 |
| `references/dual-route-architecture.md` | 双路线架构：守护 vs NTR 分支系统 |
| `references/enhancement-workflow.md` | 角色卡对比增强工作流参考 |
| `references/execute_code-string-escaping.md` | 中文字符的字节/字符比（2026-07-04 叶无云案例） |
| `references/execute_code-tmp-contamination.md` | /tmp/ 文件污染问题（2026-07-04 闷骚健身美母案例） |
| `references/expansion-workflow.md` | 首次生成太薄的根因分析与扩充工作流 |
| `references/game-mechanics-template-library.md` | 游戏机制模板库（Game Mechanics Template Library） |
| `references/gameplay-type-card-design.md` | 玩法型卡片设计参考 |
| `references/greetings-from-file-assembly.md` | 开场白文件化组装模式 |
| `references/guardian-card-lessons.md` | 守护卡设计教训（2026-07-11 用户反馈 + 实践验证） |
| `references/md-to-json-assembly.md` | MD → JSON 组装参考 |
| `references/multi-chapter-novel-to-card.md` | 多章小说→角色卡 完整工作流（2026-07-03 圣馨医院案例） |
| `references/multi-reference-card-design.md` | 多参考卡设计模式（Multi-Reference-Card Design） |
| `references/novel-archetype-patterns.md` | 小说原型→模板组合指南（Novel Archetype → Template Combination） |
| `references/novel-to-card-sizing.md` | 小说→角色卡 预估分析流程 |
| `references/ntl-perspective-conversion.md` | NTL视角转换指南 |
| `references/ntl-transformation-framework.md` | NTR→NTL 视角转换框架 |
| `references/ntl-version-audit-checklist.md` | NTL版审核检查清单 |
| `references/ntr-multi-target-weight-distribution.md` | NTR多目标权重分配指南 |
| `references/open-ended-card-design.md` | 开放性卡片设计案例（示例玄幻项目改造） |
| `references/pitfall-library.md` | 角色卡创作陷阱库（完成前必读） |
| `references/planning-readiness-evaluation.md` | 计划书达标评估方法论 |
| `references/quality-check-instruction-template.md` | 角色卡规划书质检指令模板 |
| `references/recursive-trigger-chain.md` | 递归触发链 - 完整诊断与修复 |
| `references/sillytavern-scripting-patterns.md` | SillyTavern 脚本化模式参考 |
| `references/sp-database-plugin-compatibility.md` | SP-数据库插件兼容性指南 |
| `references/st-native-charcard-format.md` | SillyTavern 角色卡内嵌世界书格式（2026-07-04 修正版） |
| `references/st-native-worldbook-format.md` | SillyTavern 原生世界书导出格式 |
| `references/st-reasoning-parser-and-png-format.md` | SillyTavern Reasoning Parser 与 PNG 角色卡格式（2026-07-08 实测） |
| `references/st-reasoning-parser-behavior.md` | SillyTavern Reasoning Parser 行为分析（ST 1.18.0 实测） |
| `references/st-reasoning-parser-pitfalls.md` | SillyTavern Reasoning/Thinking 解析器陷阱 |
| `references/st-regex-placement-analysis.md` | SillyTavern Regex Placement 与世界书内容篡改分析 |
| `references/st-truncation-diagnosis.md` | ST 截断诊断完整流程 |
| `references/template-evaluation-workflow.md` | 模板库评估工作流（2026-07-10 交配学校案例） |
| `references/token-audit-methodology.md` | ST角色卡Token审计方法 |
| `references/token-optimization-selective-triggers.md` | Token优化：常驻→触发+selective改造 |
| `references/truncation-diagnosis.md` | 截断/空回诊断与优化 |
| `references/unicode-encoding-pitfalls.md` | Unicode Encoding Pitfalls for Character Cards |
| `references/worldbook-cleanup-and-sync.md` | 世界书清理与同步工作流 |
| `references/worldbook-entry-structure.md` | 世界书条目结构参考 |
| `references/worldbook-json-converter.py` | !/usr/bin/env python3 |

### 脚本（active + compatibility）

| 文件 | 摘要 |
|------|------|
| `scripts/atomic_write_json.py` | 无 BOM、回读验证、备份、SHA 与原子替换的 JSON 写入器 |
| `scripts/analyze_token_load.py` | 只读 Token 负载分析（共享 matcher；不自动改 key/卡） |
| `scripts/audit_skill_pipeline.py` | 组装→交付流程接线元审查：模板真实解析、标题 matcher、文档命令、脚本/文档存在性、编译、CLI help、汇总 flag |
| `scripts/audit_stage_entry_contracts.py` | 阶段合同 schema v1/v2 审计与 native manifest 转换 |
| `scripts/lib/stage_routing.py` | 阶段标题语法唯一事实源（与 standalone sibling byte-identical） |
| `scripts/audit_worldbook_triggers.py` | 世界书触发审计报告：逐greeting触发矩阵、普通句反证、selective/secondary风险 |
| `scripts/audit_manifest_alignment.py` | build manifest 与 semantic manifest 的 narrative/architecture/route/state/source 跨合同一致性门控 |
| `scripts/audit_semantic_modules.py` | 模块化语义门控：正式命名空间、职责模块、必需字段、开放锁死词、projection 引用、跨条目引用和工程元数据泄漏 |
| `scripts/audit_semantic_text.py` | `semantic_markdown_v1` 文本门控：一级标题、二级主章节、章节顺序、`comment ↔ module_type ↔ content_schema` 一致性、重复章节和缩进 YAML 依赖 |
| `scripts/audit_source_material_coverage.py` | novel-card 原文素材证据审计：legacy/严格默认按 canonical 连续摘录检查≥60%；`curated_anchor_set` 无统一最低比例，除非 Manifest/CLI 显式声明 `source_coverage_minimum` |
| `scripts/check_build_sync.py` | canonical 语义构建同步：keys/路由/extensions/regex 漂移均拦截 |
| `scripts/enrichment_self_check.py` | 加料厚度与可运行素材门控 |
| `scripts/audit_greeting_layers.py` | Greeting正文/导演附录分层、正文污染和正文纯汉字长度门控 |
| `scripts/audit_greeting_build_wiring.py` | clean build Greeting 源与最终卡的逐条同步、stage_brief_v1 源接线门控 |
| `scripts/run_delivery.py` | 日常唯一入口：读取 `build_manifest.json`、打印 RUN/SKIP、调用 final gate |
| `scripts/final_delivery_gate.py` | 汇总交付门控；可选 sibling 缺失时返回 `CAPABILITY_MISSING` |
| `scripts/lib/stage_memory.py` | 阶段记忆锚点的共享规则 ID 与判定，供 validator/contract/enrichment 统一使用 |
| `scripts/migrate_card.py` | 非破坏性 CCv3 迁移；默认 dry-run，显式 output/语义 flags |
| `scripts/validate_card.py` | `ccv3-core` / `leyu-production` profiles + JSON Issue 报告 |
| `scripts/lib/worldbook_matcher.py` | 唯一 World Info 匹配实现，供验证/触发审计/Token 分析共享 |
| `scripts/fix_card_format.py` | **deprecated**：安全兼容入口，默认写 sibling `.migrated.json` |
| `scripts/safe_write_card.py` | **deprecated**：兼容入口，委托 atomic writer |
| `scripts/verify_enrichment_pass.py` | 受控加料差分：未授权条目/字段、职责标题、增量预算 |
| `scripts/verify_simple_stage_route.py` | 配套预设 `阶段P#` 路由的卡侧契约检查 |
| `scripts/worldbook-json-converter.py` | legacy 独立世界书 JSON 格式转换（缺 section 必须人工复核） |

### v5.2 回归与 CI

- `tests/`：pytest fixtures 与 profile/build-sync/migration/capability/matcher 回归。
- `.github/workflows/test.yml`：私有备份仓库同步后执行 pytest 与 `audit_skill_pipeline.py`。注意：单 skill checkout 下元审计对 sibling（`standalone-card-stage-routing`）检查降级为 WARN、6 个依赖 sibling 的 pytest 自动 skip；整树目录布局中该 workflow 不会被 GitHub 触发，需本地执行 pytest 与元审计。
- `references/workflows/v5.2-validation-and-migration.md`：v5.2 的权威命令与边界。

### 模板（active）（2）

| 文件 | 摘要 |
|------|------|
| `templates/plan-document-template.md` | 角色卡规划书模板（Plan Document Template v1.0） |
| `templates/build-manifest.example.json` | 日常交付策略模板：原型、Greeting、路由、source/build 与专项门控条件 |
| `templates/player-agency-modes.example.json` | G 型/身份卡玩家代理权与选开合同模板 |
| `templates/stage-entry-contract.example.json` | 阶段入口合同模板（schema v2）——native 阶段卡必须复制到项目目录改名 `stage-entry-contract.json` 后填写 |

### 归档审查旧文件（archived，默认不读）（13）

| 文件 | 摘要 |
|------|------|
| `card-audit-checklist.md`（旧归档，仅内部） | 角色卡审查工作流（Card Audit） |
| `card-audit-workflow.md`（旧归档，仅内部） | 卡审查流程（自动化脚本+Agent双审） |
| `card-cross-verification-workflow.md`（旧归档，仅内部） | 角色卡交叉验证工作流（Card Cross-Verification Workflow） |
| `card-governance-report-pattern.md`（旧归档，仅内部） | 治理报告委派模式（Governance Report Delegation） |
| `card-quality-assessment.md`（旧归档，仅内部） | 已有卡质量评估流程（2026-07-11 校园媚黑守护卡v2评估验证） |
| `character-card-audit-checklist.md`（旧归档，仅内部） | 角色卡条目质量审查清单 |
| `content-contradiction-checks.md`（旧归档，仅内部） | 卡内容矛盾检测（脚本审查Phase 2） |
| `flexible-review-standards.md`（旧归档，仅内部） | 审查弹性标准 — 硬门槛 vs 软判断 |
| `quality-check-instruction-template.md`（旧归档，仅内部） | 角色卡规划书质检指令模板 |
| `review-template-blindspots.md`（旧归档，仅内部） | 审查模板盲区：6项实测发现的覆盖缺口（2026-07-12） |
| `review-template-coverage-gaps.md`（旧归档，仅内部） | 审查模板覆盖盲区分析 |
| `skill-maintenance-checklist.md`（旧归档，仅内部） | Skill 维护检查清单（2026-07-12 交叉验证总结） |
| `validate-checklist-detail.md`（旧归档，仅内部） | 完成前强制验证（红线步骤，不可跳过！） |

### 已删除/旧引用（deleted，禁止新流程引用）（5）

| 旧引用 | 处理 |
|------|------|
| `audit/initial-card-review-template.md` | 当前目录不存在；如需内容，先确认是否已迁移到 active/archived 文件 |
| `audit/review-template-blindspots.md` | 当前目录不存在；如需内容，先确认是否已迁移到 active/archived 文件 |
| `初始卡审查启动模板.md` | 当前目录不存在；如需内容，先确认是否已迁移到 active/archived 文件 |


## Manifest v2 叙事模式与运行状态

新项目在判型和路由选择后，必须把四个维度分别写入 Manifest：

```text
narrative_mode  → linear_stage / soft_stage / open_sandbox
routing_mode    → flat / native_greeting_title / simple_stage_route
runtime_driver  → native_st / external_extension
runtime_state   → authority + update_mode + contract + recovery_policy + reliability
```

不要根据旧 `routing_mode` 自动猜测叙事模式。Manifest v1 保持原行为，内部只标记 `legacy_unspecified`，跳过新增专项；只有 v2 才要求显式 `narrative_mode`、`narrative_contract` 和适用的 `runtime_state.contract`。

合同职责：

- `stage-entry-contract.json`：技术路由、阶段标题、现有阶段四包、触发和条目职责；继续使用 schema v2，不改名为 Stage Contract v3。
- `narrative-contract.json`：当前阶段事实、各角色知识边界、未解决线程、候选事件、失效条件和结果驱动转移。
- `runtime-state-contract.json`：`revision`、`current_stage`、`facts_in_force`、`knowledge_boundaries`、`unresolved_threads`、`event_status`、`transition_flags`、`last_major_event`、`last_update_source`，以及 writer、冲突和恢复规则。

模式专项由 `scripts/run_delivery.py` 条件调用：

| `narrative_mode` | 必跑专项 | 跳过专项 |
|---|---|---|
| `linear_stage` | `audit_ordered_step_contract.py`、`audit_runtime_state_contract.py` | soft/open 专项 |
| `soft_stage` | `audit_candidate_event_semantics.py`、`audit_stage_transition_policy.py`、`simulate_freeplay_paths.py`、runtime-state | ordered/open 专项 |
| `open_sandbox` | `audit_open_sandbox_entries.py`、候选事件语义 | 阶段 transition、ordered-step |

`soft_stage` 中阶段是记忆和信息边界，阶段内剧情是可跳过、可拒绝、可失效的候选事件；候选事件必须显式 `auto_fact=false`，不能自动事实化。`linear_stage` 允许有序节点；`open_sandbox` 不要求阶段转移条件，但必须有多人物/地点/行为入口、NPC主动性以及无候选事件时世界仍可继续的证据。`simulate_freeplay_paths.py` 只验证确定性状态图，不替代 ST 实机模型行为验收。

外部扩展只能声明为 `runtime_driver=external_extension`，不能伪装成新的 `routing_mode`。如果没有扩展合同、脚本资产和测试 fixture，交付计划必须显示 `CAPABILITY_MISSING` 或 warning，不得全绿；即使使用 `--dry-run`，也返回非零能力缺失状态。

## 8. 技能维护原则 — 什么值得入库

**本文档记录的是「创作模式/设计解法」，不是「做过什么卡」。** 不是每张卡做完都需要写一个新的设计模式。

### 入库过滤准则

只有当**四个条件全部满足**时，才将某个创作经验/设计模式沉淀入库：

| # | 条件 | 说明 | 自查问题 |
|---|------|------|---------|
| 1 | **沟通量大** | 该卡经历了多轮沟通、修正、用户反馈 | 是不是一句话就产出的？如果是→不进 |
| 2 | **有明确约束** | 用户对设计/风格/结构有具体限制，且这些约束推动了设计改进 | 有没有用户多次强调的要求？如果没有→不进 |
| 3 | **有实质阻力** | 遇到了非琐碎困难（安全过滤/AI行为失常/结构矛盾），且找到了通用解法 | 这次创作有没有遇到真困难？如果没有→不进 |
| 4 | **跨题材可复用** | 解法不依赖特定角色名/世界观/词条/题材，能直接用到下一张不同类型的卡 | 抽象到最底层仍然成立吗？只对这张卡成立→不进 |

### 典型不录案例

| 卡类型 | 为什么不录 |
|--------|-----------|
| 一句话产出、无沟通过的卡 | 没有可复用的经验——Hermes直接从小说原文产出，过程没有发掘出新解法 |
| 某张卡独有的角色名/情节词条 | 写进skill只会增加噪声，不能指导其他卡的创作 |
| 某张卡中特定场景的描写模板 | 虽然好用但绑定该世界观，不能通用 |
| 环境错误/安装问题 | 临时性的，不是创作经验 |

### 典型入库案例

| 模式 | 来源 | 为什么入 |
|------|------|---------|
| 多NPC信息边界 | 天仙+冷艳教师双卡交叉验证 | ①两张卡都经历了多轮修正 ②用户明确强调NPC行为问题 ③AI默认全知是实质阻力 ④适用所有多角色卡 |
| NPC行为独立性 | 同上 | 同上 |
| 意识清醒型植物人NTR | 冷艳教师妈妈 | ①用户多次强调"醒来对峙"设计 ②昏迷但意识清醒的特殊设定无法套用现有模式 ③适用同类昏迷题材 |
| 隐奸NTL玩法设计 | 绿妹妹隐奸NTL | ①来自Discord讨论+用户选择 ②AI苦主破局是全新玩法 ③信息差反转机制可复用 |

### 跨窗口治理复核 — 审查报告过期时必做

当另一个窗口反馈“审查报告已过时 / 部分 P0 已修 / 又发现二阶断点”时，先按 `references/audit/cross-window-skill-governance-pattern.md` 复核当前真实文件和最小 fixture。旧报告只能作为维护清单，不可按原 P0 顺序机械执行。

**触发信号**：
- 另一个窗口指出当前文件已不同步
- validate 脚本刚修过一个检查，可能产生相邻检查误杀
- 多窗口对同一 skill 的修复优先级不一致
- §7 索引、决策树、审查体系出现系统性腐烂

**铁律**：当前文件 + 可执行验证结果优先于旧报告文本。脚本修复必须用“合法最小 fixture + 非法最小 fixture”回归验证。

**2026-07-15 E/F/G流程审查补充**：审查模板、G型选开、发布/修卡流程的专项发现已沉淀到 `references/audit/full-process-skill-audit-2026-07-15-efg.md`。修 skill/scripts/templates 时优先处理其中的最小修复顺序：G型审查拆成 Common/Greeting/选开三层 → validate 选开模式也查共用层零`{{user}}` → `audit_worldbook_triggers.py`纳入交付门控 → 社区反馈修卡闭环 → Discord全字段违禁词扫描。

### 上下游衔接验证 — 新增内容后必做

每当你向skill添加新的设计模式、参考文件、交付门控或 runner 参数后，**必须逐点验证以下7个衔接点**——不是"看一眼"，而是打开对应章节、运行对应 fixture 或静态审查确认接线。

```
新增一个设计模式/参考文件 →
  ① 上游决策：§1.0 决策树是否有分支能走到新模式？§1.1 原型表是否有该行？
  ② 模板匹配：§2.5 是否列出了该模式需要的模板/参考文件？
  ③ 构建指导：§3 是否有该模式的构建子节（或跳转到参考文件的明确指令）？
  ④ 运行编排：`build_manifest.json` 是否声明真实 `routing_mode`/Greeting/source/build 条件？`run_delivery.py --dry-run` 是否打印正确 RUN/SKIP 与 final gate argv？
  ⑤ 中游门控：§3.4 交付门控表是否有该模式 → 审查模板的映射？
  ⑥ 下游审查：§4.0 审查表是否有该模式的行（带审查维度）？
  ⑦ 索引可查：§7 参考文件索引是否添加？§0 快速索引是否加跳转行（重要模式）？
```

**实战教训（G型多视角内置·v6.16→v6.17）**：v6.16新增了§1.4和两个高质量参考文件，但7个衔接点全部断裂——agent无法通过标准决策流自然抵达G型，必须"提前知道它存在"。这是"只写文件不更新上下游"的教科书级反面案例。

| 衔接点 | v6.16 状态 | v6.17 修复 |
|--------|:--:|------|
| §1.0 决策树 | ❌ | ✅ 新增G型第一分支 |
| §1.1 原型表 | ❌ | ✅ 新增G型行 |
| §2.5 模板匹配 | ❌ | ✅ 新增G型推荐行（含两个参考文件） |
| §3 构建阶段 | ❌ | ✅ 新增 §3.3b（5步+7项检查清单） |
| §3.4 门控表 | ❌ | ✅ 新增G型映射（标注checks 42-45覆盖） |
| §4.0 审查表 | ❌ | ✅ 新增G型行（含4个审查维度） |
| §3.5 加料自检 | ❌ | ✅ 新增G型额外自检段落 |

**缺任何一环 = 新增的模式不会被实际用上。** 只写文件不更新触发/门控/审查 = 形同虚设。

**Patch 工具注意事项**：用 `patch` 工具修改 SKILL.md 时，如果原文件中有内嵌的 `\n` 字面量（两行被错误合并到一行的情况），`patch` 的模糊匹配可能无法定位。此时改用 Python `readlines()` + 逐行替换来处理。

### 「顺藤摸瓜」修复原则

修复数字/引用/路径等**需要在全文件保持一致的项**时，不要只改发现的那一处：

1. 先搜全文件所有出现该模式的位置
2. 在同一个patch中全部修正
3. 确认零残留

**案例（2026-07-13门控数字修复）**：另一窗口发现门控步骤数一处不匹配，搜索全SKILL.md后共修复5处（§0/§3.4标题/§3.4踩坑/T33/T42/版本行）。

> **原则**: 入库的最终目标是**让下一张不同类型的卡也能受益**。如果做不到这一点，就不值写入skill，记在memory里供参考就够了。

> **版本**: v6.49（2026-08-06：收紧 Runner `--format json` 能力边界，区分配置错误 JSON 与完整交付文本，并同步 coverage 四项统计用途）
> **核心原则**: 预设优先，纯文本为王
> **模板库**: v3.3（19个模板）
> **上次更新**: 新增 manifest-driven delivery：`build_manifest.json → run_delivery.py → final_delivery_gate.py`；修复原型确认与 Greeting 审计旧文档冲突；新增 pipeline 级真实 dry-run、临时 assemble/build-sync 烟雾验证、simple/native/appendix 分支回归测试，以及稳定 manifest 错误码、semantic migration coverage、非对象 Card 根节点结构化错误处理和 Runner `--format json`/完整交付文本边界。
