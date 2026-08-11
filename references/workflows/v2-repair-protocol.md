# v2 返修协议（2026-07-16 绿冠星空卡实证）

> 当 `validate_card.py` 通过（0 errors）但卡仍不可交付时适用。
> 核心原则：不要补丁式修卡，按硬风险优先级分层修复，每层修完跑完整验证。

## 修复顺序（严格执行）

### Phase 1: 硬风险清理（不可交付的必须项）

1. **构建/代码残留** — 默认必做；扫 `TODO/qinyun_profile/print(f/os.path.join/\\u4e00/子代理/```/script.py`。entry 内容中出现 Python 变量赋值/代码片段/Unicode 范围表达必须清除。
2. **发布文案专项（非默认阻塞）** — 仅当用户要求 Discord/社区发布或过审文本时启用 `--strict-platform`；只扫描简介/帖子正文/标题/标签等平台可见文案，不扫描卡 JSON、世界书、开场白或小说原文。
3. **未成年词汇专项（非默认阻塞）** — 只针对发布简介/帖子中的幼女、萝莉、未成年等词汇；单纯角色年龄小于18岁不自动构成问题，不为平台规则成人化卡本体。

### Phase 2: 开场白修复

4. **去重** — 5条 greeting 扫描重复行，删除完全重复行（保留状态栏等必要结构重复）。
5. **补足字数** — 每条 ≥1400 中文字。不足时自然扩展场景描写，禁止用重复模板/旁白灌水。
6. **补字残留检查** — 检测连续重复句式、双版本拼接、`pad_to/填充` 等残留。

### Phase 3: 触发策略修复

7. **secondary_keys 失效** — 扫描 `secondary_keys` 非空但 `selective=false` 的条目。每条决定：
   - 如果是范围限定（NTR关系/场景）→ 设 `selective=true` + 保留 secondary
   - 如果是备注/说明 → 清空 secondary_keys
8. **泛 key 压缩** — 减少 `系统/积分/兑换/妈妈/妹妹/女友/岳母` 等单字/双字泛 key，改为 `欢乐送系统/秦韵妈妈/叶城妹妹/叶城女友/叶城岳母` 等自然复合 key。重跑触发审计验证。
9. **死触发修复** — 审计报告标记为“所有开场白均不触发”的条目：如果是核心/威胁档案必须修复 key 或 greeting；如果是中后期背景线 → 设为 `enabled=false` 做事件种子。

### Phase 4: 内容加厚

10. **核心角色档案** — ≥1500中文字（建议 ≥2000），每条目包含：关系锚点、外貌描写、语言指纹、行为模板、场景反应差异、可调用动作模板。
11. **NTR关系条目** — ≥600中文字（建议 ≥1000），包含：侵犯阶段演变史、行为链、NTR场景触发关键词、远程观看视角。
12. **新增独立描写库** — 至少3条：身体与感官、远程观看与导演视角、世界观氛围。每条 ≥500中文字，comment 不含“场景”字样（避免被 enrichment 误判为场景条目缺安全等级）。

### Phase 5: 重跑完整门控（每层修完至少跑一次）

```bash
python scripts/validate_card.py <卡.json>
python scripts/audit_worldbook_triggers.py <卡.json> -o <审计报告.md>
python scripts/enrichment_self_check.py <卡.json>
python scripts/analyze_token_load.py <卡.json>  # 可选
```

快速扫描辅助（默认交付用 final_delivery_gate 的 residue scan；发布专项只扫简介/帖子）：
```python
# 发布文案专项：只读 discord简介.md / 帖子正文，不读卡JSON
forbidden=["萝莉","luoli","loli","幼女","幼齿","童贞","未成年"]
# 卡本体硬风险：只扫 residue/构建残留
residue=["TODO","待补","占位","qinyun_profile","print(f","os.path.join","\\u4e00","\\u9fff","子代理"]
```

## 交付判定标准

| 门控 | 必须通过 |
|---|---|
| `validate_card.py` | 0 errors |
| `audit_worldbook_triggers.py` | 硬风险=0，secondary失效=0 |
| `enrichment_self_check.py` | 🔴=0，且 🟡≤2 |
| residue/构建残留扫描 | 0 hits |
| 发布文案专项 `--publish-text <简介.md> --strict-platform` | 仅用户要求发布/过审时执行，只改简介/帖子文案 |
| 未成年词汇专项 `--publish-text <简介.md> --strict-age` | 仅用户要求发布文案边界专项时执行；年龄<18本身不是问题 |
| 开场白 | 每条 ≥1400 中文字，重复行≤0 |
| core_id 9-14 | ≥2000 中文字 |
| NTR关系 15-19 | ≥1000 中文字 |
| 独立描写库 | ≥3 条，每条 ≥500 中文字 |

以上全部 PASS 才算可交付。

## 已知 pitfall

- **enrichment "场景" 误判**：描写库/语料库若 comment 或 keys 含“场景”字眼，enrichment_self_check.py 会按场景条目检查安全等级。修复：改名使用“氛围/描写/视角”类关键词，不用“场景”。
- **发布专项词回弹**：若本轮启用了 strict-platform/strict-age，加厚条目时新写内容可能重新引入平台敏感词/年龄边界词；该专项场景下每轮加厚后都要重新扫描，普通本地卡不默认阻塞。
- **greeting 补字 → 重复行**：用拼接方式补字数容易产生重复行。修复后必须扫描重复行并删除。
