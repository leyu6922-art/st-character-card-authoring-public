# Token优化：常驻→触发+selective改造

## 适用场景

当已有角色卡的token负载过高（首轮>15K token或常驻条目>10个），需要将always-on条目改造为按需触发。

## 诊断流程

1. 统计常驻条目（constant=True）的总字符数和条目数
2. 统计触发条目（constant=False）的关键词，检查是否有过于宽泛的词
3. 模拟first_mes触发：遍历所有触发条目，检查keys是否出现在first_mes+description+system_prompt中
4. 计算总注入量 = 常驻字符 + 触发字符，估算token

## 宽泛关键词检测

以下关键词几乎必然在对话中出现，导致对应条目每轮都被触发：

| 过于宽泛的key | 应改为 |
|--------------|--------|
| 单字key（"家"、"人"） | 具体词（"凡间住宅"、"新人物"） |
| 通用概念（"阶段"、"状态"、"剧情"、"事件"） | 加限定词（"堕落阶段"、"状态管理"、"剧情推进"、"新事件"） |
| 角色名简称（"白然"、"妈妈"） | 保留角色名本身（合理），但移除同义词 |
| "NPC"、"生成"、"配角" | "新NPC"、"人物生成" |
| "幻想"、"内心"、"沉沦" | "绿帽幻想"、"内心独白"、"沉沦结局" |

## 改造步骤

### Step 1: 合并重复扩展条目

两种重复模式都需要处理：

**模式A：条目间重复**（多个条目覆盖同一主题）

常见模式：同一内容被复制多份，后缀"扩展2/扩展3/扩展4/扩展5"。

检测方法：
```python
import re
base_groups = {}
for e in entries:
    comment = e.get('comment', '')
    base = re.sub(r'扩展\\d*', '', comment).strip()
    if base not in base_groups:
        base_groups[base] = []
    base_groups[base].append(e['id'])

# 2+条目的组就是重复候选
for base, ids in base_groups.items():
    if len(ids) >= 2:
        print(f"  {base}: IDs {ids}")
```

合并策略：保留第一个，将后续条目的独特内容追加到第一个的content末尾（用分隔线标注来源），然后删除后续条目。

**模式B：条目内重复**（单个条目内部包含多份自己的副本）

**2026-07-07 示例角色项目案例实测**：条目content内部被复制了3-4遍，后缀从"扩展"变为"扩展2""扩展3""扩展4"，但内容几乎完全相同。每个这样的条目浪费75%的token。

检测方法：
```python
for entry in entries:
    c = entry.get('content', '')
    separators = re.findall(r'━━━.*?扩展\d+.*?━━━', c)
    if len(separators) >= 2:
        print(f"  ID={entry['id']}: {entry['comment']} | {len(c)} chars | {len(separators)+1}份副本")
```

修复方法：只保留第一份内容（从开头到第一个"扩展2"分隔符之前），删除后续副本：
```python
for entry in entries:
    c = entry['content']
    match = re.search(r'\n━━━ .*?扩展2.*?━━━', c)
    if match:
        entry['content'] = c[:match.start()].rstrip()
```

**实测效果（示例角色项目）**：9个条目从平均5500字缩减到平均1400字，节省33,596字符（~45KB文件大小）。

### Step 2: 精简常驻条目

**必须常驻的条目（4-6条）：**
- 全局规则/OOC防护
- 文风与叙事控制
- {{user}}角色设定
- 状态栏模板
- 格式增强规则

**应该转为触发的条目：**
- 世界观/时代规则 → keys: 相关地名/概念
- 性爱规则/淫语库 → keys: 性爱相关词
- 好感度系统 → keys: "好感度"、"好感阶段"
- 剧情推进 → keys: "剧情推进"、"时间线"
- 对话示例库 → keys: 角色名+"对话"
- 文风示例库 → keys: "文风"、"描写风格"

### Step 3: 收窄触发条目的关键词

对每个触发条目检查keys：
1. 移除单字key（len<=1）
2. 移除过于宽泛的通用词
3. 确保每个key至少2个字符且有明确指向

### Step 4: 设置prevent_recursion=True

所有条目的 `extensions.prevent_recursion` 必须为True。False会导致条目A的内容触发条目B，B触发C，链式膨胀3-5倍。

### Step 5: 重新编号ID

合并删除后必须重编号：
```python
for i, e in enumerate(entries):
    e['id'] = i
    e['extensions']['display_index'] = i
```

## 实测数据（示例角色项目案例）

| 指标 | 改造前 | 改造后 | 降幅 |
|------|--------|--------|------|
| 条目总数 | 136 | 107 | -21% |
| 常驻条目 | 14 | 6 | -57% |
| 首轮token | ~29,500 | ~13,300 | -55% |
| 中期负载 | ~30,000+ | ~10,400 | -65% |
| 文件大小 | 717KB | 654KB | -9% |

## 注意事项

- 角色名作为key是合理的（"二娘"、"三娘"），不需要收窄
- 合并扩展条目时先比较内容，确认是真正重复而非独立内容
- 常驻条目keys必须为空列表，避免触发额外条目
- 改造后必须模拟first_mes验证触发数
