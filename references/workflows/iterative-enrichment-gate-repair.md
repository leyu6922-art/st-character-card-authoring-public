# 迭代式加料门控修复工作流

适用场景：大型 SillyTavern 角色卡已经生成 JSON，但 `enrichment_self_check.py` 或 `final_delivery_gate.py` 仍因内容厚度、素材链条、关系条目不足而不可交付。

## 核心经验

1. **validate 通过不代表可交付**
   - `validate_card.py passed=True` 只说明结构字段、开场白长度、世界书字段等基础格式过关。
   - 交付判断优先看 `enrichment_self_check.py` 与 `final_delivery_gate.py`：legacy/严格 profile 中任何 🔴 或 🟡≥3 都不能交付；开放玩家主导 profile 中 🔴 仍阻断，🟡 是非阻断诊断，除非命中事实、代理、触发、构建或显式合同。

2. **final_delivery_gate exit_code=2 的含义要拆开看**
   - 如果 `enrichment_self_check.py: PASS errors=0 warnings=0`，但 `final_delivery_gate.py` 因 `validate_card.py` / `audit_worldbook_triggers.py` 的诊断型 warning 返回 `exit_code=2`，可报告为“硬门控通过，仅剩人工确认/设计型 warning”。
   - 不要把所有 warning 都机械等同于失败；严格 profile 中用户明确要求的 enrichment 黄项阈值仍需继续修，开放玩家主导 profile 的普通内容建议不因数量自动阻断。

3. **按 Manifest profile 精确补，不要泛泛加厚**
   - 严格/扩展 profile：角色≥1500（核心建议≥2000）、NTR关系≥600、场景≥500、独立语料/描写库建议≥500；适用原型再检查三路径。
   - `curated_anchor_set + open_situation_seed + player_led`：不按字数补齐；补关系/行为框架、精选事实/语言锚点、自然入口、可观察压力、玩家接管点和后果边界。
   - 事件种子只有在 `guided_candidate`/声明严格三路径的原型中才补成功/失败/半成功；开放情境不得补成固定剧本。

4. **黄项清理策略**
   - 当严格/legacy enrichment 黄项仍 ≥3 时，继续修，不能交付；开放玩家主导模式只修复阻断型红项和明确合同错误，保留普通内容建议供人工取舍。
   - 剩余 1-2 个黄项理论上可人工确认，但如果只差几十字，优先顺手清掉，避免用户复审时卡在门控细节。

5. **体积目标与门控目标分离**
   - 计划书设定如“文件 ≥200KB”属于质量目标；`validate_card.py --target-size-kb 200` 低于目标可能只给 warning。
   - 若用户把体积写进质量标准，应继续补到目标以上，不要用“validator没报error”跳过。

## 推荐修复循环

```bash
python scripts/validate_card.py <card.json> --target-size-kb 200
python scripts/enrichment_self_check.py <card.json> --r18 --prototype A --three-path none
python scripts/final_delivery_gate.py <card.json> --project-dir <project_dir> --prototype A --three-path none
```

然后：

1. 从 enrichment 报告提取 🔴 / 🟡 列表。
2. 写独立 repair_card_vN.py，从上一版 JSON 读取并 append 精准补强。
3. 输出新版本 JSON，保留旧版本。
4. 重新跑三层门控。
5. 直到：
   - enrichment：🔴=0 且 🟡<3，最好 🟡=0；
   - final gate：无 FAIL；
   - 文件大小达到计划目标。

## 内容补强模板

### 角色条目补强

必须补具体可用素材，而不是“应当保持人物丰满”：

- 阶段残留：上一阶段的称呼/身体记忆如何影响下一阶段。
- 行为链：靠近 → 试探 → 反应 → 升级 → 事后痕迹。
- 场景差异：在家/对手家/公共空间/协议场景中的不同表现。
- 语言指纹：对不同角色的称呼、句式、情绪变化。
- 弱点与反击口：角色不是静态强/弱。

### NTR关系条目补强

每条关系至少包含：

- 侵犯史/关系演变；
- 双方行为链；
- 触发关键词；
- 场景锚点；
- 成功路径 / 失败路径 / 半成功代价；
- 事后余波。

### 场景条目补强

每个场景至少包含：

- 安全等级；
- 可见物件/声音/气味；
- NPC可能性；
- 事件概率；
- 事后痕迹；
- 与主关系的绑定方式。

## Pitfalls

- 不要只补抽象规则。`enrichment_self_check.py --r18` 会看动作链、语言链、身体反应、场景链、阶段链。
- 不要把 `validate_card.py` 的事件种子 `enabled=false` warning 当成错误；事件库禁用通常是设计如此。
- 不要因 `audit_worldbook_triggers.py` 的高 token 诊断 warning 自动改 keys；先判断是否符合阶段式/按需设计。
- 长中文补强继续用文件脚本 append，不在 `execute_code` 内联大段中文，避免截断和引号问题。
