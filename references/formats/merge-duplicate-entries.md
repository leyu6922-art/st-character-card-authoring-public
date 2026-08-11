# 合并重复条目（扩充后的必要步骤）

当卡片经过多轮扩充后，会出现大量"原始+扩充"配对条目（如id=3恶魔相机 + id=132恶魔相机·扩充）。这些重复条目浪费token且增加维护成本。**每次大规模扩充后，必须做一次合并去重。**

## ⚠️ 条目内重复（2026-07-07 示例角色项目案例）

除了条目间的重复，还有一种更隐蔽的浪费：**单个条目content内部包含自己的多份副本**。

表现：条目content中有 `━━━ XXX扩展2 ━━━`、`━━━ XXX扩展3 ━━━`、`━━━ XXX扩展4 ━━━` 等分隔符，每个分隔符后面的内容与第一份几乎完全相同。这种条目的75%内容是重复的。

检测：`re.findall(r'━━━.*?扩展\d+.*?━━━', content)` 返回2+个匹配时，说明有内部重复。

修复：只保留第一个分隔符之前的内容。详见 `references/design-patterns/token-optimization-selective-triggers.md` Step 1 模式B。

## 检测方法

```python
# 找出所有带"扩充"标注的条目
expand_entries = [e for e in entries if '扩充' in e.get('comment', '')]
print(f"发现 {len(expand_entries)} 个'扩充'条目待合并")

# 按关键词分组找出配对
keyword_groups = {}
for e in entries:
    for kw in e.get('keys', []):
        if kw not in keyword_groups:
            keyword_groups[kw] = []
        keyword_groups[kw].append(e['id'])
# 多条目共享的关键词 = 潜在重复
for kw, ids in keyword_groups.items():
    if len(ids) > 1:
        print(f"  关键词'{kw}'出现于: {ids}")
```

## ⚠️ Pitfall: 扩展N条目比较时必须去掉标题行（2026-07-07 示例角色项目案例）

批量生成的"扩展N"条目，标题行（第一行）包含编号差异（如`扩展2` vs `扩展3`），但正文内容可能完全相同。**直接比较整段content会因标题行不同而误判为"不同内容"**。

**错误比较**：
```python
if entry_a['content'] == entry_b['content']:  # ← 标题行不同，永远False
```

**正确比较**：
```python
# 去掉第一行（标题行），只比较正文
body_a = '\n'.join(entry_a['content'].split('\n')[1:])
body_b = '\n'.join(entry_b['content'].split('\n')[1:])
if body_a == body_b:
    print(f"  ✅ 完全相同，可删除其一")
```

**实测案例（示例角色项目NTL版）**：
- "扩展·仙母对话示例库扩展2" vs "扩展·仙母对话示例库扩展3"：整段比较=不同，去标题行比较=100%相同
- 19个"扩展N"条目被确认为完全相同副本，删除后文件从699KB瘦身到586KB（-16.2%）

**检测脚本**：
```python
# 自动检测所有"扩展N"条目组内的重复
import re
groups = {}
for e in entries:
    comment = e['comment']
    m = re.match(r'(.+?)(?:扩展(\d+))?$', comment)
    if m and '扩展' in comment:
        base = m.group(1)
        num = m.group(2) or 'base'
        if base not in groups:
            groups[base] = []
        groups[base].append((num, e['id'], e['content']))

for base, items in groups.items():
    numbered = [(n, eid, c) for n, eid, c in items if n != 'base']
    if len(numbered) < 2:
        continue
    # 去标题行两两比较
    for i in range(len(numbered)):
        for j in range(i+1, len(numbered)):
            n1, eid1, c1 = numbered[i]
            n2, eid2, c2 = numbered[j]
            body1 = '\n'.join(c1.split('\n')[1:])
            body2 = '\n'.join(c2.split('\n')[1:])
            if body1 == body2:
                print(f"  ⚠️ id={eid1}(扩展{n1}) = id={eid2}(扩展{n2}): 完全相同，删除id={eid2}")
```

## 合并策略

```python
# 定义配对：(原始id, 扩充id)
merge_pairs = [(3, 132), (19, 106), (50, 125), ...]

# 执行合并
for orig_id, exp_id in merge_pairs:
    orig = by_id[orig_id]
    exp = by_id[exp_id]
    # 追加扩充内容到原始条目
    orig['content'] += f"\n\n━━━ {exp.get('comment','')} ━━━\n\n"
    orig['content'] += exp['content']

# 删除扩充条目
all_expanded = set(exp for _, exp in merge_pairs)
entries = [e for e in entries if e['id'] not in all_expanded]
```

## 实测数据

示例玄幻项目：132→88条目（-44），601.7KB→550.9KB（-51KB），0残留"扩充"条目。

## 注意事项

- 合并前确认扩充条目确实与原始条目配对（不是独立新内容）
- 链式合并：A→B→C 三个条目时，全部合并到A
- 合并后验证无残留"扩充"条目
- 合并后检查条目大小，超过5000字的条目考虑是否需要拆分
