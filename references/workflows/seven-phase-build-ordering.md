# 7-Phase 构建顺序（大型卡标准流程）

> 来源：示例游戏项目卡、示例角色项目卡、天仙配卡(2026-07-12)。适用于30+条目的大型NTR/媚黑卡。

## Phase 总览

```
Phase 1: 系统条目（constant=true, 6-8条）    ← 主代理 execute_code
Phase 2: 世界观+场景（6-8条）                ← 主代理 write_file + execute_code
Phase 3: 核心女主（6-8条）                   ← 并行子代理 ×2-3
Phase 4: 重要女主+黑人男性（8-12条）          ← 并行子代理 ×2-3
Phase 5: 事件种子+辅助（4-8条）              ← 主代理 execute_code
Phase 6: 卡壳组装                            ← 主代理 write_file + execute_code
Phase 7: 合并JSON + validate_card + 修复     ← 主代理 execute_code
```

## 各Phase详解

### Phase 1: 系统条目（constant=true）

全部 constant=true, keys=[], position=before_char（OOC/状态栏）或 after_char。

典型条目：
- ID 0: OOC防护+禁词列表（before_char）
- ID 1: 文风叙事控制（before_char）
- ID 2: 文风与氛围锚点·模板16（before_char）
- ID 3: 反顺从规则·模板17（before_char）
- ID 4: 叙事节奏控制·模板14（before_char）
- ID 5: 状态栏系统·模板1（before_char）
- ID 6: 旁白解说规则·模板9（before_char）
- ID 7: NPC自主行动表·模板5（after_char）

**构建方式**：execute_code 内联写 make_entry()，内容 < 600字可内联。
**输出**：`/tmp/<project>_phase1.json`

### Phase 2: 世界观+场景

constant=false, 有关键词触发。

典型条目：
- 世界观核心设定（1000-1500字）
- APP/系统规则（800字）
- 社会制度（1000字）
- 场景条目 ×3-4（每个500-800字）

**构建方式**：write_file 写 .txt → execute_code 组装 JSON。
**输出**：`/tmp/<project>_phase2.json`

### Phase 3+4: 角色条目（并行子代理）

每个角色 1-3 条（基础档案 + 堕落轨迹 + 行为库）。
每条 1200-2500字。

**子代理分配策略**：
- 子代理A：核心女主 3人 × 2条 = 6条
- 子代理B：重要女主 3-5人 × 1-2条 = 6条
- 子代理C：黑人男性 2-3人 + 事件种子 3-4条 = 6条

**每个子代理的 goal 必须包含**：
1. 小说文件路径
2. 完整的 make_entry 模板（含31字段extensions）
3. 每条的 ID、keys、comment
4. 最低字数要求
5. 输出路径：`/tmp/<project>_content/char_{id}.json`

**输出**：`/tmp/<project>_content/char_*.json`（由子代理直接写入）

### Phase 5: 事件种子+辅助

enabled=false 的事件种子条目 + 堕落规则 + 自由创作总则。

典型条目：
- 关键剧情事件（800-1500字/条，enabled=false）
- 堕落阶段跃迁规则（1000字）
- 自由创作总则（600字）

**构建方式**：execute_code 内联或 write_file。
**输出**：`/tmp/<project>_phase5.json`

### Phase 6: 卡壳组装

description / personality / scenario / system_prompt / first_mes / alternate_greetings。

**构建方式**：全部 write_file 写 .txt → execute_code 读取组装。
**greeting 每条 ≥ 1400字**（validate_card.py 硬性要求）。

**两轮生成模式**：
1. 第一轮：写基础版（800-1200字）
2. 第二轮：append 扩展段落到 ≥ 1400字

### Phase 7: 合并 + 验证

```python
# 1. 读取所有phase JSON文件
# 2. 读取子代理产出的 char_*.json
# 3. 读取卡壳 .txt 文件
# 4. 合并所有条目 → 按ID排序 → 检查ID连续性
# 5. 组装完整的 chara_card_v3 JSON
# 6. 输出到目标目录
# 7. 运行 validate_card.py
# 8. 修复所有error → 重跑验证
```

## ID分配规范

| 范围 | 类型 | constant |
|------|------|----------|
| 0-7 | 系统条目 | true |
| 8-15 | 世界观+场景 | false |
| 16-25 | 核心女主 | false |
| 26-35 | 重要女主+黑人 | false |
| 36-45 | 事件+辅助 | false |

## 子代理并行规则

- 最多3个并行子代理（delegation.max_concurrent_children=3）
- 每个子代理写不同ID范围的条目
- 子代理之间无依赖，各自写独立文件
- 主代理最后合并，不并行写同一文件

## 与 content-file-first-build-pattern 的配合

- Phase 1: 短内容，execute_code 内联
- Phase 2: 中等内容，write_file + execute_code
- Phase 3+4: 长内容，子代理直接写 JSON
- Phase 5: 中等内容，execute_code 或 write_file
- Phase 6: 卡壳字段，write_file + execute_code
- Phase 7: 纯组装，execute_code
