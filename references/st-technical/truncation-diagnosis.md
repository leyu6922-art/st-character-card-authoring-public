# 截断/空回诊断与优化

## 触发条件

社区反馈"截断空回"、"回复为空"、"输出被截断"时使用此流程。

## 快速诊断（推荐，2026-07-05 新增）

```bash
# 在 skill 根目录运行（推荐生成 Markdown 报告，ST v1.18 触发逻辑对齐）
python scripts/audit_worldbook_triggers.py <卡文件.json> -o <触发审计报告.md>

# 旧版负载脚本仍可作为补充：常驻/触发条目明细、关键词负载等
python scripts/analyze_token_load.py <卡文件.json>
```

输出：逐 greeting 触发矩阵、普通句反证、selective/secondary 风险、常驻/触发条目明细、token负载汇总、高频关键词、优化建议。
下方手动步骤仅在脚本无法覆盖的场景下使用。

## 手动诊断步骤

### Step 1: 基础数据采集

```python
import json
from collections import defaultdict

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

entries = data['data']['character_book']['entries']

# 基础统计
print(f"文件大小: {os.path.getsize(path)} bytes")
print(f"条目数: {len(entries)}")
print(f"总content: {sum(len(e.get('content','')) for e in entries)} chars")

# 常驻条目
const_entries = [e for e in entries if e.get('constant', False)]
print(f"常驻条目: {len(const_entries)}条, {sum(len(e['content']) for e in const_entries)} chars")
```

### Step 2: 关键词重叠分析

关键词重叠是截断的第一大原因。当用户输入触发一个常见词时，可能同时拉起5-6条条目。

```python
key_to_entries = defaultdict(list)
for i, e in enumerate(entries):
    for k in e.get('keys', []):
        key_to_entries[k].append(i)

overlapping = {k: v for k, v in key_to_entries.items() if len(v) > 1}
for k, v in sorted(overlapping.items(), key=lambda x: -len(x[1])):
    print(f"  '{k}' -> {len(v)}条: {[entries[i]['comment'][:20] for i in v]}")
```

**判断标准**:
- 单词出现在3+条目 → 高风险（应去重）
- 单词出现在4+条目 → 必须修复

### Step 3: 重复条目检测

```python
key_sets = {}
for i, e in enumerate(entries):
    keys = tuple(sorted(e.get('keys', [])))
    if keys and len(keys) >= 2:
        key_sets.setdefault(keys, []).append(i)

for keys, indices in key_sets.items():
    if len(indices) >= 2:
        print(f"重复: {keys} -> {[entries[i]['comment'][:25] for i in indices]}")
```

### Step 4: Token负载估算

```python
const_chars = sum(len(e['content']) for e in entries if e.get('constant', False))
avg_triggered = sum(len(e['content']) for e in entries if not e.get('constant', False)) / max(1, len([e for e in entries if not e.get('constant', False)]))

print(f"常驻基线: {const_chars} chars (~{const_chars/1.5:.0f} tokens)")
print(f"平均条目: {avg_triggered:.0f} chars")
print(f"触发5条: {const_chars + avg_triggered*5:.0f} chars (~{(const_chars + avg_triggered*5)/1.5:.0f} tokens)")
print(f"全部触发: {sum(len(e['content']) for e in entries)} chars")
```

**负载参考（诊断信号，不是绝对红线）**：
- < 5000 tokens：通常安全
- 5000-8000 tokens：中等风险，取决于模型 context、lore budget、输出长度
- 8000-12000 tokens：高风险，需要检查是否都是相关条目
- > 12000 tokens：优先审计触发质量；若全部是结构化协议且模型上下文足够，仍可能流畅（大型结构化卡首轮约 7.2 万字符常驻仍可玩）

**不要只看裸 token/字符数。** 必须同时看：①触发条目是否相关；②是否泛 key/secondary 无效；③输入内容是结构化协议还是高密度叙事素材；④每轮要求模型输出多少内容（状态栏、旁白、多 NPC、反顺从、阶段推进会显著增加输出截断风险）。

### Step 5: first_mes 触发模拟（精确负载估算）

Step 4 只是粗估。真正精确的方法是模拟开场白实际触发了多少条目：

```python
fm = data['data']['first_mes']

# 找出被 first_mes 关键词触发的条目
triggered = []
for e in entries:
    if e.get('constant'):
        continue
    for k in e.get('keys', []):
        if k in fm:
            triggered.append(e['id'])
            break

const_content = sum(len(entries[e]['content']) for e in range(len(entries)) if entries[e].get('constant'))
triggered_content = sum(len(entries[eid]['content']) for eid in triggered)
total = const_content + triggered_content

print(f"常驻: {const_content} chars")
print(f"触发: {len(triggered)}条, {triggered_content} chars")
print(f"总负载: {total} chars (~{total//2} tokens)")

# 列出每个触发条目的触发关键词
for eid in triggered:
    e = entries[eid]
    for k in e.get('keys', []):
        if k in fm:
            print(f"  [{eid}] '{k}' → {e['comment'][:35]} ({len(e['content'])}c)")
            break
```

**判断标准**:
- first_mes触发条目 > 20 → 极高风险
- 常驻+触发总token > 8000 → 必须优化

### Step 6: 检查标签

```python
print(f"Tags: {data['data'].get('tags', [])}")
```

标签混用不影响截断但影响社区体验（如纯爱卡带NTR标签）。

## 修复策略

### 修复1: 关键词去重（最大收益）

对每个重叠关键词，只保留在最语义相关的条目中：

```python
# 对每个重叠词，指定保留条目的index
dedup_rules = {
    '第一次': [17],       # 保留"场景-插入姐姐的里面"
    '发现': [12],         # 保留"场景-发现自慰"
    '口交': [20],         # 保留"场景-姐姐用嘴巴叫我起床"
    # ... 对每个重叠词做判断
}

for keyword, keep_indices in dedup_rules.items():
    for idx in key_map[keyword]:
        if idx not in keep_indices:
            entries[idx]['keys'].remove(keyword)
```

**选择保留条目的原则**:
1. 条目标题最直接包含该关键词的
2. 条目内容最核心围绕该关键词的
3. 如果两条都相关，保留constant=True的那条

### 修复2: 合并重复条目

```python
# 合并两个keys相同的条目
e1, e2 = entries[idx1], entries[idx2]
# 取较长内容为基础，补入另一条独有的段落
merged_content = merge_unique_sections(e1['content'], e2['content'])
merged_keys = list(dict.fromkeys(e1['keys'] + e2['keys']))
e1['content'] = merged_content
e1['keys'] = merged_keys
entries.pop(idx2)
```

### 修复3: 关键词精简（通用→复合）

将通用关键词改为复合关键词，避免被 first_mes 中的常见字触发：

```python
# ❌ 通用关键词 — 会被"姐姐""妈妈"等常见词触发
28: {'keys': ['姐姐', '催眠', '胁迫']}   # "姐姐"在first_mes中→触发
29: {'keys': ['甜蜜', '书萱', '日常']}   # "书萱"在first_mes中→触发
31: {'keys': ['妈妈', '旗袍', '调教']}   # "妈妈"在first_mes中→触发

# ✅ 复合关键词 — 只在明确提到时才触发
28: {'keys': ['姐姐催眠详解']}
29: {'keys': ['书萱甜蜜日常']}
31: {'keys': ['妈妈旗袍详解']}
```

**适用条目类型**：身体描写库、场景描写库、详解条目、扩展条目。
**不适用**：角色档案（需要被角色名触发）、场景条目（需要被地名触发）。

### 修复4: 常驻→触发转换

将非核心常驻条目改为按需触发：

```python
# 必须常驻（每轮都需要的规则）：
#   全局规则/OOC防护、文风控制、状态栏、防拒绝

# 可以转触发（按需加载）：
#   催眠体系、性爱规则、好感度系统、剧情推进、创作总则、世界观
make_triggered = {
    2: {'constant': False, 'keys': ['催眠', '学伴', 'Dave']},
    3: {'constant': False, 'keys': ['性爱', '淫语', '肉棒', '蜜穴']},
    7: {'constant': False, 'keys': ['剧情推进', '事件生成']},
}
```

### 修复5: 常驻条目keys清空

常驻条目的keys必须为空——否则加载时会触发额外条目（叶无云堕落版实测：10个常驻条目带关键词→一加载就触发额外22条）：

```python
for e in entries:
    if e.get('constant'):
        e['keys'] = []
        e['selective'] = True
```

## 修复原则

1. **只改结构，不删内容** — 所有剧情/描写/台词完整保留
2. **最小改动** — 只修复会导致截断的问题，不做"顺便优化"
3. **备份优先** — 修改前 `cp xxx.json xxx.backup.json`
4. **验证JSON** — 修改后 `json.loads()` 确认格式正确

## 实测案例

### 叶无云堕落版（2026-07-05）

82条目，first_mes触发32条（22135字/~11067 tokens）→截断。

| 阶段 | 条目数 | 字数 | tokens | 降幅 | 方法 |
|------|--------|------|--------|------|------|
| 原始 | 32条 | 22135 | ~11067 | — | — |
| 第一轮 | 23条 | 14984 | ~7492 | 32% | 关键词精简（身体描写/场景描写改复合关键词） |
| 第二轮 | 20条 | 12840 | ~6420 | 42% | 5个常驻条目转触发 |
| 第三轮 | 14条 | 8543 | ~4271 | 61% | 常驻keys清空 + 性爱规则转触发 |

最终：4常驻 + 10触发，开场白不再截断。

### 周雨晴角色卡

- 68条目/227KB/37868 chars content
- 问题：NTR标签混用 + 车震play重复条目 + 48组关键词重叠
- 修复：删NTR标签 + 合并1条重复 + 去重48→20组
- 结果：67条目/223KB，内容零删除

## 用户侧排查

如果制卡侧优化后仍然截断，提示用户检查：

1. **lore token_budget**: 酒馆设置中世界书token预算，建议 ≥ 6000
2. **SP-数据库 tableFill**: 默认20条，50+条目卡需调到50-80
3. **模型context**: 8K context的模型处理大卡吃力，建议16K+
4. **max_context**: 酒馆主设置中的最大上下文长度
