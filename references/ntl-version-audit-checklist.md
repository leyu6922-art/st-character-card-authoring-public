# NTL版审核检查清单

## 背景

从苦主版转换为NTL版后，大量条目中仍残留苦主视角引用（`{{user}}`指向苦主而非征服者）。示例角色项目案例：33条目中有10个条目、40+处残留。必须系统性审核。

## 三轮审查法

### 第一轮：批量模式匹配

```python
import json

path = "xxx_NTL版.json"
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

entries = data['data']['character_book']['entries']
total_issues = 0

for entry in entries:
    eid = entry.get('id', '?')
    comment = entry.get('comment', '')
    content = entry.get('content', '')

    issues = []
    idx = 0
    while True:
        pos = content.find('{{user}}', idx)
        if pos == -1:
            break
        nearby = content[max(0, pos-60):min(len(content), pos+80)]
        broader = content[max(0, pos-150):min(len(content), pos+200)]

        bad = False
        reason = ""

        # Pattern checks
        checks = [
            ('{{user}}（周密）', '{{user}}（苦主）混用'),
            ('周密（{{user}}）', '苦主（{{user}}）混用'),
            ('{{user}}扮演周密', 'system_prompt错误'),
            ('{{user}}虔诚', '苦主行为'),
            ('保护{{user}}', '保护对象错误'),
            ('推开{{user}}', '动作对象错误'),
            ('抱住{{user}}', '亲密对象错误'),
            ('亲吻{{user}}', '亲密对象错误'),
            ('{{user}}的痛苦', '苦主感受'),
            ('{{user}}的独身母亲', '亲属关系错误'),
            ('{{user}}被霸凌', '苦主遭遇'),
            ('{{user}}失去最后', '苦主遭遇'),
        ]

        for pat, reason_str in checks:
            if pat in broader:
                bad = True
                reason = reason_str
                break

        if bad:
            issues.append((reason, nearby[:120]))
            total_issues += 1
        idx = pos + 1

    status = "✓" if not issues else "❌"
    print(f"  {status} id={eid:2d} [{comment}] ({len(content)}字)")
    for reason, ctx in issues:
        print(f"       ❌ {reason}: ...{ctx}...")

print(f"\n总计: {total_issues} 处问题")
```

### 第二轮：处理JSON转义形式

⚠️ **Pitfall：JSON转义导致模式匹配失败**

JSON文件中的字符串内容使用转义：
- 双引号：`\"` (在raw字符串中是 `\\"`)
- 换行：`\n` (在raw字符串中是 `\\n`)

**错误做法**：直接读raw字符串做匹配
```python
with open(path, 'r') as f:
    raw = f.read()
# 搜索 '不要美化为"成长经历"' → 找不到！
# 因为raw中是 '不要美化为\\"成长经历\\"'
```

**正确做法**：用 `json.load()` 读取后匹配
```python
with open(path, 'r') as f:
    data = json.load(f)
# data中的字符串已经反转义，直接匹配即可
```

**但如果必须在raw字符串上操作**（如批量替换），需要匹配转义形式：
```python
# 搜索转义形式
old = '不要美化为\\\\"成长经历\\\\"'
new = '不要美化为\\\\"成长经历\\\\"'.replace('{{user}}', '周密')
```

### 第三轮：全面验证+误报过滤

修复后重新扫描，过滤以下**正确模式**（不是bug）：

| 模式 | 为什么正确 |
|------|-----------|
| `{{user}}（张强）的霸凌对象` | 描述苦主是征服者的霸凌对象 |
| `十字架被{{user}}夺取` | 征服者夺取十字架 |
| `{{user}}用来威胁妈妈的筹码` | 征服者用苦主威胁 |
| `周密不知道十字架被{{user}}夺取` | {{user}}=征服者，语义正确 |
| `屈服于{{user}}的控制` | 屈服于征服者的控制 |
| `[苦主: 精神xx%]` 在状态栏中 | 苦主作为NPC的状态跟踪 |
| `{{user}}派人绑架周密` | 征服者对苦主做某事 |

**判断原则**：`{{user}}`出现时，如果它在语境中扮演的是征服者角色（对苦主做某事、控制某物、命令某人），则正确。如果它在语境中扮演的是苦主角色（被保护、被推开、痛苦、失去依靠），则为残留。

## system_prompt检查要点

```
✓ 正确: {{user}}扮演[征服者名]——[征服者身份描述]
❌ 错误: {{user}}扮演[苦主名]
```

## 状态栏模板检查要点

```
✓ 正确（征服者视角）:
[{{user}}: 征服者名 | 情绪: xxx]
[目标状态: xxx | 服从度xx%]
[苦主NPC: 精神xx% | 状态: xxx]

❌ 错误（苦主视角）:
[苦主名: 体力xx% 精神xx% | 情绪: xxx]
[妈妈状态: xxx | 灵魂寄宿: xxx]
```

## 防拒绝/禁忌规则检查要点

```
✓ 正确（NTL版）:
- {{user}}（征服者）的贪婪与残忍要贯穿始终
- 苦主作为NPC，永远不会主动参与凌辱
- 妈妈灵魂被控制但内心抗拒（作为NPC底线）

❌ 错误（苦主版残留）:
- {{user}}（苦主）的屈辱感要真实展现
- 苦主作为{{user}}的角色，永远不会主动参与凌辱
```

## 叙事规则检查要点

```
✓ 正确（NTL版）:
- 以{{user}}（征服者）的第一人称为主
- 描写目标时用贪婪的侵略性视角
- 描写苦主时用嘲讽/蔑视的第三人称

❌ 错误（苦主版残留）:
- 以{{user}}（苦主）的第一人称或全知第三人称交替叙事
- {{user}}的选择会影响故事走向（苦主决策模式）
```

## NTL叙事视角设计选择

NTL版的叙事镜头有两种模式：

**模式A：征服者主视角（推荐）**
- 叙事镜头跟随{{user}}（征服者）
- {{user}}内心独白用第一人称"我"
- 苦主反应由AI在第三人称中演绎

**模式B：苦主镜头+征服者内心**
- 叙事镜头跟随苦主NPC（第三人称）
- {{user}}内心独白用第一人称"我"
- 强调苦主的旁观反应和心理折磨

两种都是合法设计，但模式B需要在id=1叙事规则中明确标注为设计选择，否则审核时会被误判为苦主残留。

## 实测案例

### 示例角色项目（33条目，40+处残留）

修复的条目：
- id=0 全局规则: `{{user}}扮演周密` → `{{user}}扮演张强`
- id=2 状态栏: 苦主视角 → 征服者视角
- id=4 防拒绝: `{{user}}（周密）的屈辱感` → `{{user}}（张强）的征服本性`
- id=5 徐玉灵: 7处 `{{user}}` → `周密`
- id=12 叙事规则: 6处苦主视角 → 征服者视角
- id=16 周子龙: `{{user}}的父亲` → `周密的父亲`
- id=25 堕落度: `保护{{user}}` → `保护周密`
- id=27 心理描写: `{{user}}（周密）内心独白` → `周密（苦主NPC）内心独白`
- id=32 禁忌规则: 5处苦主保护规则 → 征服者强化规则

### 美母即堕（29条目，0处残留）

转换时已正确处理：
- system_prompt: `{{user}}扮演陈浩` ✓
- 小秀标记为"苦主NPC，由AI扮演。{{user}}不扮演小秀" ✓
- 所有条目无苦主视角混用 ✓
- 但叙事规则选择了模式B（跟随小秀视角），属于设计选择
