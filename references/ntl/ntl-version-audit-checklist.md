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

## 第四轮：跨卡内容污染检测（2026-07-12 示例角色项目三NTL卡案例新增）

### 背景

级联构建模式下，子代理常拿第一张NTL卡做模板生成后续变体卡。如果批量替换不完整，会导致：
- 爱德卡中出现"黑色巨根""兽人血脉""商人形象"（这些属于黑巨汉，不属于爱德）
- 兽人卡中出现"赌场""VIP""骰子"（这些属于赌场老板，不属于兽人将军）

**核心原则**：不是所有含"赌场"的条目都是污染——需要区分**条目类型**。

### 条目类型分类（污染检测前必做）

| 条目类型 | ID范围示例 | 判断规则 | 处理方式 |
|---------|-----------|---------|---------|
| **{{user}}系统条目** | ID0-9（常驻） | 描述{{user}}自身的规则/系统 | 不应出现其他NTR男性的专属特征词 |
| **{{user}}主角档案** | ID19（{{user}}档案） | 描述{{user}}的身份/外貌/武器 | **绝对不能**出现其他角色的特征词 |
| **{{user}}征服阶段** | ID21-28 | {{user}}如何征服猎物 | 可以提竞争者作为"对手"，但不能把竞争者的手段写成{{user}}的 |
| **猎物档案** | ID10-13（四女档案） | 描述猎物对各NTR男性的反应 | 可以提所有NTR男性（多对多关系），但不应把"对赌场老板的反应"写成"对{{user}}的反应" |
| **竞争者NPC档案** | ID15-18 | 描述其他NTR男性 | **可以**出现该竞争者的专属特征词（如黑巨汉的"赌场""黑色巨根"） |
| **描写库** | ID29-32 | 覆盖所有NTR场景的描写模板 | 可以包含所有NTR类型，但各类型应有明确标注 |

### 检测脚本（按条目类型分级）

```python
import json

# === 配置：当前卡的{{user}}身份 ===
# 修改这两个变量来匹配当前审查的卡
USER_NAME = "爱德"  # {{user}}的角色名
USER_TRAITS = ["长老权杖", "小屁孩巨棒", "法杖", "龙人族", "伪装", "精神力"]  # 属于{{user}}的特征词
USER_FORBIDDEN = {  # 严格禁止出现在{{user}}自身条目中的词（属于其他NTR男性）
    "黑巨汉": ["黑色巨根", "兽人血脉", "赌场", "保镖", "商人形象", "几分钟调教", "VIP"],
    "兽人将军": ["兽人之力", "军营", "战鼓", "烙印", "灌酒", "巡逻"],
    "肥猪领主": ["领主权力", "父子配合", "宠物犬调教"],
}

# === 条目分类 ===
# 从comment推断条目类型
def classify_entry(comment, eid):
    comment_lower = comment.lower()
    if '{{user}}' in comment or '主角档案' in comment:
        return '{{user}}_profile'
    if eid <= 9:
        return '{{user}}_system'
    if '征服阶段' in comment or '寝取阶段' in comment or '反抗' in comment or '当面绿帽' in comment:
        return '{{user}}_conquest'
    if '档案' in comment and ('师傅' in comment or '古兰' in comment or '伊丝娜' in comment or '奥萝拉' in comment or '妮丝' in comment or '伯里' in comment):
        return 'target_profile'
    if '竞争者' in comment or 'NPC' in comment:
        return 'competitor_npc'
    if '描写' in comment or '对话' in comment or '身体' in comment:
        return '描写库'
    return 'unknown'

path = "xxx_NTL版.json"
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

entries = data['data']['character_book']['entries']

# === 分级检测 ===
for e in entries:
    eid = e.get('id', '?')
    comment = e.get('comment', '')
    content = e.get('content', '')
    etype = classify_entry(comment, eid)

    found_issues = []

    # P0：{{user}}自身条目中出现其他NTR男性的专属特征词
    if etype in ('{{user}}_profile', '{{user}}_system', '{{user}}_conquest'):
        for rival_name, forbidden_words in USER_FORBIDDEN.items():
            for word in forbidden_words:
                if word in content:
                    # 取上下文做语义判断
                    idx = content.find(word)
                    ctx = content[max(0,idx-60):min(len(content),idx+80)]
                    found_issues.append(f"🔴 [{rival_name}污染] '{word}': ...{ctx}...")

    # P1：猎物档案中把对竞争者的反应写成对{{user}}的反应（关键词：'你的赌场'→应为'黑巨汉的赌场'等）
    if etype == 'target_profile':
        for rival_name, forbidden_words in USER_FORBIDDEN.items():
            for word in forbidden_words:
                # 只检测"你的{word}"模式——说明AI写的是{{user}}拥有这个
                if f'你的{word}' in content or f'你的{word[0]}' in content[:content.find(word)+len(word)+10] if word in content else False:
                    idx = content.find(word)
                    ctx = content[max(0,idx-40):min(len(content),idx+60)]
                    found_issues.append(f"🟡 [归属歧义] 猎物条目中'{word}'归属不清: ...{ctx}...")

    if found_issues:
        print(f"\n{'='*60}")
        print(f"ID{eid} [{comment}] — 类型: {etype}")
        for issue in found_issues:
            print(f"  {issue}")
```

### 合理残留 vs 必须清理

| 场景 | 示例 | 判断 |
|------|------|------|
| 竞争者NPC条目描述该竞争者的特征 | ID15 黑巨汉档案: "黑色巨根是他的核心武器" | ✅ 合理 |
| {{user}}征服条目提到竞争者作为对手 | ID22: "爱德的法杖也在暗中控制师傅——你可以利用这点" | ✅ 合理（不是"你的法杖"） |
| {{user}}征服条目中描述{{user}}的手段时出现竞争者特征词 | ID22: "你用黑色巨根贯入" 但{{user}}=爱德 | 🔴 污染——爱德没有黑色巨根 |
| {{user}}阶段规则中出现竞争者专属领域 | ID21: "保持友善商人形象" 但{{user}}=爱德 | 🔴 污染——爱德不是商人 |
| 描写库/对话库覆盖所有NTR类型 | ID29: "模板2·黑巨汉暴力型：黑色巨根……" | ✅ 合理——描写库本应覆盖所有类型 |

## 第五轮：Find-replace残留检测（2026-07-12 爱德卡案例）

### 背景

批量替换不完整会导致**结构性残留**——替换脚本留下占位符。这些不在任何关键词黑名单里，脚本扫描无法发现，只有人工阅读才能识别。

### 检测模式

```python
import re

# 模式1：括号内的人为标记 — "(爱德独自行动)" "(已移除)" "(已替换)"
artifacts = re.findall(r'（[^）]*(?:行动|移除|替换|已删)[^）]*）', content)
if artifacts:
    print(f"  ID{eid}: find-replace残留: {artifacts}")

# 模式2：语法断裂 — "没有（X）、没有Y" 这种不通的句式
broken = re.findall(r'没有（[^）]+）、', content)
if broken:
    print(f"  ID{eid}: 语法断裂: {broken}")
```

### 实测案例

爱德卡从NTL赌场卡批量替换时：
- "被保镖摸臀" → 替换脚本把"保镖"→"(爱德独自行动)" → "被（爱德独自行动）摸臀"
- "爱德没有保镖、没有旅馆" → "爱德没有（爱德独自行动）、没有旅馆"
- 句子完全不通，但"(爱德独自行动)"不在任何污染词列表里

### 已知占位符

| 占位符 | 来源 | 应修复为 |
|--------|------|---------|
| （爱德独自行动） | 替换"保镖"→爱德式行动 | 改写为人称视角转换，或删除 |
| （已移除） | 替换"保镖"→删除 | 直接删除，不需要标记 |
| （已替换） | 替换角色名 | 直接替换，不需要标记 |



## 实测案例

### 示例角色项目三NTL卡（2026-07-12 级联污染案例）

**污染链**：子代理用NTL赌场卡做模板 → 级联生成兽人卡和爱德卡 → 批量替换不完整

- **爱德卡**：85-99%条目与赌场卡相似。ID21含"保持友善商人形象"、ID22含"黑色巨根""兽人血脉"、ID28标题与内容不符
- **兽人卡**：11个条目含"赌场""VIP""骰子"等残留（作为{{user}}系统条目不应该有）
- **赌场卡**：作为第一张卡，本身没有跨卡污染问题，但核心系统条目过薄（ID21:276字, ID30:318字）

**修复量**：爱德卡重写5条目+清理8条目残留，兽人卡清理5条目残留，赌场卡扩充4条目

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
