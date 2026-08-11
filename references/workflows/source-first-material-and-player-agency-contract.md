# 原文优先素材与玩家代理权合同

## 适用条件

用于小说改编角色卡的重建、加厚或审查：出现人工复合 key、事件/种子不可触发、角色卡资料栏过于标签化、语料对象错位、选开身份使玩家沦为旁观者，或模型可见内容停留在抽象“行为模式”时。

## 一、运行时触发硬约束

| 条目 | 必须满足 | 例外 |
|---|---|---|
| 普通事件/种子 | 严格/引导 profile：`enabled=true`、非 `constant`、自然 primary keys；具体 key 数量由合同声明；开放情境：自然入口/可观察压力/玩家接管点，不把 key 数量当内容质量 | 完整 Greeting 标题或 `ROUTE_STAGE=P#` 精确路由的阶段包 |
| 所有普通 key | 不用“事件库/种子库/语料库/人物档案/阶段：P#”等作者元标签，不用单字泛词，不以事件概括短语充当触发词 | 常驻/手动功能/身份选开 `keys=[]`；阶段精确路由 |
| 语料库 | 每组直接台词以 `【说话人→对象·场景】` 标明对象；叙述素材不混进对话语料 | 无直接台词的纯叙述素材应移入描写库 |
| 描写库 | 独立于语料库，提供环境、物件、动作、感官、关系余波等非角色台词素材；常用全局素材按 `system_constant` 常驻 | 明确阶段专属的描写可放阶段包 |

不可用的 key 必须修复为自然短词；不要为了压低共享 key 或 token 警告改成死 key。运行 `validate_card.py` 和 `audit_worldbook_triggers.py` 后，逐一人工判断警告是“真实误触发”还是“自然 OR 并行加载”。

## 二、原文优先的内容回收

1. 建立 canonical source manifest，先区分原著事实、合理推演和原创分支。
2. 先删掉没有原文依据、只会告诉模型“应该怎样表现”的抽象设计文档句；以连续原文段落、角色对白、动作链、场景物件、感官和余波替换。
3. 对声明 `expanded_reference_corpus` 的小说改编卡，在 canonical 原文已提供时，至少 60% 的**可运行内容条目**应含可追溯的原文摘录或连续改写素材；系统、身份和功能开关不计入分母。`curated_anchor_set` 只要求精选事实/语言锚点可追溯，不把全卡连续摘录比例作为默认硬门槛；如项目需要严格覆盖，在 Manifest/CLI 显式声明 `source_coverage_minimum`。
4. 运行：

```bash
python scripts/audit_source_material_coverage.py <卡.json> \
  --source <chapter-01.txt> --source <chapter-02.txt> --minimum 0.60
```

严格/legacy profile 使用上面的显式 `--minimum 0.60`。框架优先卡使用 `--manifest build_manifest.json`；若 `corpus_mode=curated_anchor_set` 且没有显式 minimum，脚本只报告可用证据，不把全卡覆盖率判为失败。该脚本只验证是否存在最短 24 字的规范化连续摘录，不评判文风，也不替代人工的角色声音审读。

5. `description`、`personality`、`scenario` 不是标签栏：必须交代核心人物、玩家身份/玩法、关系起点、当前冲突与可玩范围。首层资料还必须让模型一眼理解：**简要世界/舞台、`{{user}}` 能决定什么、AI 只能扮演谁及不能代写什么**。`enrichment_self_check.py` 对这三个字段的长度及“世界/玩家/AI 边界”三项首层上下文做黄项提示。

## 三、G 型选开与玩家代理权

- 身份条目必须明确 `{{user}}` 是谁；身份说明叙述层用 `{{user}}` 或固定角色名，不得用裸“你”替代。角色对白中的“你”不受此限制。
- 始终保留最小玩家身份底座：当前选中身份由玩家扮演；AI 只写 NPC、环境和可观察后果。
- `自动推进剧情` 与 `玩家行动边界/场景悬停` 是两个独立的 `feature_toggle`，均默认关闭。前者只允许 NPC/环境造成当前可见场景中的一个可回应变化；后者优先，禁止替 `{{user}}` 说话、思考、判断、使用物件、移动/进出地点、接受/拒绝条件、关键行动、关系决定、结束行为、切阶段或锁定后果。
- 禁止把两条规则压缩成一句空泛的“不要替玩家行动”；必须保留明确禁止项和接管停点。字段与双开优先级由 `audit_player_agency_modes.py --require` 验证。

## 四、范围与安全边界

原文是人物关系、事件事实与叙事声音的最高证据层，但不是跳过范围审查的理由。仅回收和使用明确成年人之间、符合项目范围的素材；不得导入、扩写或以“原文优先”为由移除涉及未成年人的性化内容保护。若旧模型的抽象限制与 canonical 成人素材冲突，可在证据、运行时与安全范围均核对后，用具体原文素材替换抽象表述；不能通过删除未成年人保护或伪造年龄状态来达成。

## 五、交付顺序

```text
canonical manifest / 成人范围核对
→ 原文素材与语料/描写库分层
→ build / assemble
→ validate_card.py
→ audit_source_material_coverage.py（小说卡）
→ audit_worldbook_triggers.py
→ enrichment_self_check.py
→ audit_player_agency_modes.py --require（G 型）
→ check_build_sync.py --require-build
→ `final_delivery_gate.py --source <chapter-01.txt> --source <chapter-02.txt>`（小说 canonical 卡；把覆盖率作为最终门控的一部分）
→ SillyTavern Prompt Itemization 实机验证
```

静态通过不代表 ST 已实机加载。最终报告必须区分：源证据覆盖、结构门控、触发模拟与 ST 实机结果。
