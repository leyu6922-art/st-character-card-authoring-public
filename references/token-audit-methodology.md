# ST角色卡Token审计方法

## 用途
对已完成的角色卡JSON做token消耗审计，识别token爆炸风险。

## 审计步骤

### 1. 分类条目
用execute_code读取JSON，将世界书条目分为三类：
- **常驻条目** (constant=true): 每次对话必注入
- **非常驻启用** (constant=false, enabled=true): selective触发
- **已禁用** (constant=false, enabled=false): 不注入

### 2. 估算每个条目token
```python
def est_tokens(text):
    return int(len(text) / 1.5)  # 混合CJK+ASCII粗估
```

### 3. 检查条目内重复段落
这是最常见的token浪费源。逐条检查：
- `■ 详细外貌描写` 出现次数（应=1）
- `■ 语言风格详析` 出现次数（应=1）
- `■ 性爱细节库` 出现次数（应=1）
- `■ 语言风格详析` 出现次数（应=1）
- 任何 `■ xxx详细` 出现>1次的都是重复

每多一次浪费约200-500 tok。

### 4. 检查条目间内容重叠
- 对话精华库(id=27/28) vs 各角色条目中的台词 → 高度重叠应二选一
- NPC行动表(id=5) vs 角色条目的对话示例 → 台词重叠应清理

### 5. 检查开场白内部重复
用paragraph切分(按`\n\n`)，检查是否有相同前80字的段落。

### 6. 常驻条目合理性审查
常驻条目(token)应该只保留：
- ✓ 全局规则/OOC防护 (id=0)
- ✓ 状态栏系统 (id=3)
- ⚠ 世界观/文风/旁白/防拒绝 → 考虑改selective(keys触发)

### 7. Token预算估算
```
常驻合计 + 非常驻合计(全触发) = 最坏情况
常驻合计 + 非常驻×40% + 1个开场白 = 保守估计
```

### 8. 风险评估
| 场景 | 约消耗 | 风险 |
|------|--------|------|
| 开局(常驻+1st_mes) | ~6K | ✓ |
| 1角色+2-3条目 | ~10K | ✓ |
| 2角色+5-6条目 | ~18K | ⚠ |
| 多角色同屏+全触发 | ~32K+ | ❌ |

## 典型问题模式

### A. 角色条目膨胀(>1000 tok)
原因：内容是AI生成时逐段累加，没有去重。
修复：删除重复段落，保留最详细的那一版。

### B. 对话库与角色条目重复
原因：先写了角色条目(含台词)，后来又建了专门的对话库条目。
修复：角色条目保留3-5句核心台词，对话库保留完整版。

### C. 常驻条目过多
原因：想确保AI每次都看到规则。
修复：改为selective(keys触发)，如文风条目用keys=["文风","叙事","描写"]。

## execute_code审计模板

```python
import json

with open('card.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

entries = data['data']['character_book']['entries']

def est_tokens(text):
    return int(len(text) / 1.5)

# 分类
const = [e for e in entries if e.get('constant')]
enabled = [e for e in entries if not e.get('constant') and e.get('enabled', True)]
disabled = [e for e in entries if not e.get('constant') and not e.get('enabled', True)]

# 统计常驻token
const_total = sum(est_tokens(e['content']) for e in const)
nc_total = sum(est_tokens(e['content']) for e in enabled)

# 检查重复段落
for e in entries:
    content = e.get('content', '')
    for pat in ['■ 详细外貌描写', '■ 语言风格详析', '■ 性爱细节库']:
        c = content.count(pat)
        if c > 1:
            print(f"⚠ id={e['id']} {e['comment']}: '{pat}' 重复{c}次")

# 检查开场白重复
first_mes = data['data'].get('first_mes', '')
paras = [p.strip() for p in first_mes.split('\n\n') if len(p.strip()) > 50]
seen = {}
for j, p in enumerate(paras):
    ps = p[:80]
    if ps in seen:
        print(f"⚠ first_mes 段落{j}与{seen[ps]}重复")
    seen[ps] = j

print(f"\n常驻: {const_total} tok | 非常驻: {nc_total} tok")
print(f"最坏情况: {const_total + nc_total} tok")
```
