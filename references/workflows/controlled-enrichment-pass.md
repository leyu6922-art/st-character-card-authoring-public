# 受控加料轮次：责任分层 + 基线差分门控

适用：一张大型角色卡已有合格基线，后续要做多轮内容补强，但不能再“全卡无差别加厚”。

## 核心原则

**每轮只承担一种内容责任，并只触碰预先列出的条目。** 加料不是版本号递增；它必须能回答：本轮补什么、为什么是这些条目、哪些既有内容明确不碰、怎样证明没有扩散改动。

推荐顺序（可按题材裁剪，不要求机械四轮）：

| 轮次 | 唯一职责 | 典型目标 |
|---|---|---|
| R1 关系矩阵 | 让对象差异真正进入关系与阶段条目 | 对象状态、筹码、误判、称呼边界、升级条件 |
| R2 因果链 | 让协议/赌约/决定有可追踪原因 | 前置、表面理由、隐性动机、关键误判、接受理由、关系锁定、下一推力 |
| R3 事件—空间—配角矩阵 | 让事件能跑、场景有功能、配角不抢戏 | 事件内对象状态、空间反应差异、配角功能/边界、余波 |
| R4 主体形象收束 | 防止主角被关系表和事件表淹没 | 外观/仪态、心理防御、第一反应、事后余波、阶段形象递进 |

R4 不是“再加一层剧情”；它是对主角可辨识性的定向收束。完成某轮后先跑门控，除非有新的实机证据，否则进入实机测试，不继续离线堆料。

### 条件模式：协议/交易/赌约/规则驱动的因果链

仅当故事的关键转折由契约、交易、赌约、游戏规则或强制协议驱动时，R2 必须在**全局索引 + 对应阶段 + 对应事件**三层同步写齐以下八项：

`前置状态 → 表面理由 → 隐性动机 → 关键误判 → 各方接受理由 → 关系锁定 → 下一阶段推力 → 禁止误写`

否则模型容易把不可逆转折写成无缘由的服从、随机玩法或前置事实。普通开放卡不要为了套这八项而凭空制造协议。

### R4 主体性收束的人工验收

关系/事件矩阵加厚后，不以“条目更多”作为收尾条件。抽读主角相关条目，确认仍有：外观或仪态锚点、身份防御、微反应、主动计算/选择、对象差异、事件后余波、阶段变化和禁止误写。若主角只剩被其他角色或事件调用的反应容器，R4 不合格；补主角条目与关键阶段/事件中的角色中心性，不再扩写关系矩阵。

## 每轮开工前必须写 manifest

把 manifest 放在项目 `build/` 或 `reports/`，例如：

```json
{
  "pass_name": "R4-protagonist-consolidation",
  "allowed_entry_ids": [5, 10, 11, 12],
  "allowed_card_field_paths": ["data.character_version"],
  "allowed_entry_fields": ["content"],
  "required_headings": {
    "5": ["【主体形象总锚点】"],
    "10": ["【本阶段主角形象锚点】"]
  },
  "min_total_content_delta": 1000,
  "max_total_content_delta": 25000
}
```

规则：

- 默认禁止新增/删除条目、改 keys、改 `selective`、改 `secondary_keys`、改常驻配置；这些属于另一个结构修复轮。
- 已在前一轮验收过的条目不加入本轮 `allowed_entry_ids`，除非能说明真实漏洞。
- `required_headings` 是职责验收，不是凑字标题；内容必须是可运行素材。
- `max_total_content_delta` 是防止后期“最后抛光”重新变成全卡膨胀，不是压缩内容的通用硬上限。

## 自动化门控

```bash
python scripts/verify_enrichment_pass.py BASELINE.json CANDIDATE.json build/enrichment_manifest.json
python scripts/validate_card.py CANDIDATE.json
python scripts/enrichment_self_check.py CANDIDATE.json --r18 --prototype A
python scripts/audit_worldbook_triggers.py CANDIDATE.json
```

若采用配套预设的简化 `阶段P#` 路由，再追加：

```bash
python scripts/verify_simple_stage_route.py CANDIDATE.json \
  --forbid ROUTE_STAGE --forbid ROUTE_MODE --forbid '当前阶段：'
```

任何以下情况都必须停止交付：

- 基线差分发现未授权条目或结构字段变动；
- 本轮缺失 manifest 指定的职责标题；
- 增量超过本轮预算但没有更新并重新确认 manifest；
- 结构/加料/触发门控出现硬错误。

## 交付报告最小字段

每轮报告必须列出：基线文件、候选文件、manifest、实际变更 ID、每条字符增量、总增量、未触碰的前轮条目、四个门控结果，以及“下一步是实机测试还是下一职责轮”的明确结论。

## 快照卫生

备份不得把整个项目复制到项目自身的 `backups/` 子目录；下一次复制会把旧备份再次纳入，形成备份递归和几千个冗余文件。只备份目标 JSON/预设文件，或把完整快照放到项目目录外的同级归档根目录。
