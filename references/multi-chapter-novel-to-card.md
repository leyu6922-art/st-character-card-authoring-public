# 多章小说→角色卡 完整工作流（2026-07-03 圣馨医院案例）

## 概述
将10章中篇小说（约9万字）转化为150KB+角色卡（含40条世界书条目）的完整流程。

## 工作流

### Phase 0: 模板库审查 + 原型选择（写规划书前必做！）
```
1. skill_view("st-character-card-authoring", "references/game-mechanics-template-library.md")
2. skill_view("st-character-card-authoring", "references/novel-archetype-patterns.md")
3. 根据小说类型选择原型（系统流/纯NTR/征服者后宫/禁忌乱伦）
4. 逐个模板对照小说特点，输出"采用/不采用"表格
5. 确定{{user}}视角（原型表中有决策框架）
6. 将采用的模板融入后续条目设计
7. 按 templates/plan-document-template.md 写规划书
```
⚠️ 不要跳过这步直接写规划书——模板选择会改变条目架构设计。
原型选择和{{user}}视角决策在Phase 0完成，避免规划书写完后返工。

### Phase 1: 原料采集
```
1. search_files 找到小说目录下所有 .txt 文件
2. read_file 逐章读取（注意 limit 参数，大文件可能需要分页）
3. 同时读取参考卡（如有）了解JSON结构
4. 统计总字数、章节数、角色数量
```

### Phase 2: 角色提取
从原文中提取：
- 所有女性角色：姓名、年龄、外貌、性格、穿着、语言风格
- 男性主角：姓名、年龄、外貌、性器特征、性格演变
- 角色关系矩阵
- 关键剧情节点

### Phase 3: 世界书条目设计
按优先级分层：

| 层级 | 条目 | constant | order | 说明 |
|------|------|----------|-------|------|
| 系统层 | 全局规则、世界观 | true | 199-200 | 仅2-3条最核心的系统规则 |
| 核心规则 | 沦陷值、性爱规则、状态栏 | true | 186-189 | 纯文本规则，不涉及具体角色 |
| 风险检测 | 被发现风险 | true | 197 | 通用规则 |
| 主角 | 详细档案 | **false** | 195 | 触发式！keys=[主角名] |
| 核心角色 | 行为模板+档案 | **false** | 190 | 触发式！按出场时加载 |
| 其他角色 | 档案 | **false** | 180-185 | 触发式 |
| 事件/场景 | 种子库 | false, enabled=false | 150-175 | 手动或AI判断触发 |
| 备选开场白 | 不同切入点 | false, enabled=false | 118-121 | enabled=false |
| 文风样本 | 原著摘录 | false, enabled=false | 50-59 | enabled=false |

⚠️ **常驻条目数量铁律：≤10个**（建议6-8个）
超过10个常驻条目会导致首轮token负载过高。角色档案（包括主角）应全部设为触发式。
2026-07-10 万恶后宫系统案例：初始24个常驻→token 8796超限→修正为6个常驻→token降至5032。

⚠️ **常驻条目keys铁律：必须keys=[]**
constant=True的条目始终加载，keys无意义且会导致截断。构建时必须清空。

### Phase 4: execute_code 构建
由于 execute_code 每次调用都是独立沙箱，大型卡需要**分批构建、中间保存、最终合并**：

```python
# === 第1个 execute_code：读取小说 + 构建系统条目 ===
import json, os

# 1. 用 Python open() 读取小说（不要用 read_file，会去重）
base = "/path/to/novel/"
all_text = ""
for i in range(1, N+1):
    with open(f"{base}/第{i}章*.txt", 'r', encoding='utf-8') as f:
        all_text += f.read()

# 2. 定义 make_entry() + 构建系统条目（entries 0-N）
entries = []
entries.append(make_entry(0, [], [], "全局规则", """...""", constant=True))
# ... 更多系统条目

# 3. 中间保存！
with open("/tmp/entries_part1.json", "w", encoding="utf-8") as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)
```

```python
# === 第2个 execute_code：构建角色条目 ===
import json

def make_entry(uid, keys, secondary_keys, comment, content, ...): ...

entries = []
entries.append(make_entry(0, ["光辉"], [], "光辉", """...""", constant=True))
# ... 更多角色条目

with open("/tmp/entries_part2.json", "w", encoding="utf-8") as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)
```

```python
# === 第3个 execute_code：合并 + 组装最终JSON ===
import json

# 读取所有 part
parts = []
for i in range(1, N+1):
    with open(f"/tmp/entries_part{i}.json", "r", encoding="utf-8") as f:
        parts.extend(json.load(f))

# 重新编号
for i, entry in enumerate(parts):
    entry["id"] = i

# 读取 first_mes
with open("/tmp/novel_full.txt", "r", encoding="utf-8") as f:
    text = f.read()
first_mes = text[:2500]

# 组装卡片
card = {
    "spec": "chara_card_v2", "spec_version": "2.0",
    "data": {
        "name": "...", "description": "...",
        "first_mes": first_mes,
        "extensions": {
            "world": {"entries": parts},
            "additional": {"character_book": {"entries": parts}}
        }
    }
}
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(card, f, ensure_ascii=False, indent=2)
```

**关键规则**：
- ⚠️ 不要用 `read_file` 读小说文件（同session去重会失败），用 Python `open()`
- ⚠️ 每个 execute_code 末尾必须保存中间结果到 `/tmp/xxx_partN.json`
- ⚠️ 字符串含中文双引号时，用单引号包裹（`'他说"你好"'`）
- 最终合并时用 `parts.extend()` 而非 `parts.append()` 避免嵌套列表

### Phase 5: 部署与验证（2026-07-10强化）
```python
# 复制到目标目录
terminal(f'cp "{src}" "{dst}"')

# 验证JSON结构
with open(dst, 'r', encoding='utf-8') as f:
    card = json.load(f)
assert card['spec'] == 'chara_card_v2'
assert len(card['data']['character_book']['entries']) >= 20

# === 必做检查（来自 validate_card.py 逻辑）===
errors = []
entries = card['data']['extensions']['world']['entries']

# 1. 常驻条目keys必须为空
for e in entries:
    if e.get('constant') and e.get('keys'):
        errors.append(f"[{e['id']}]'{e['comment'][:20]}': 常驻条目必须keys=[]")

# 2. 常驻条目数量≤15（建议≤10）
constants = [e for e in entries if e.get('constant')]
if len(constants) > 15:
    errors.append(f"常驻{len(constants)}个>15上限")

# 3. Token负载检查
const_chars = sum(len(e.get('content','')) for e in constants)
fm = card['data'].get('first_mes', '')
triggered = set()
for e in entries:
    if e.get('constant'): continue
    for k in e.get('keys', []):
        if k and k in fm:
            triggered.add(e['id']); break
trig_chars = sum(len(entries[i].get('content','')) for i in triggered)
est_tokens = (const_chars + trig_chars) // 2
if est_tokens > 8000:
    errors.append(f"首轮token{est_tokens}>8000")
elif est_tokens > 5000:
    warnings.append(f"首轮token{est_tokens}偏高")

# 4. Emoji检查
for e in entries:
    for ch in e.get('content',''):
        if ord(ch) > 0xFFFF:
            errors.append(f"[{e['id']}]含emoji"); break
```

**验证→修复→重验循环**：
首轮构建后常驻条目过多是常见问题。修复步骤：
1. 将角色档案从constant改为触发式（保留keys）
2. 仅保留纯规则/世界观/状态栏为常驻（keys=[]）
3. 重跑token负载检查直到<8000

## 目标大小参考
| 小说规模 | 目标卡大小 | 条目数 |
|----------|-----------|--------|
| 3-5章短篇 | 80-100KB | 15-25 |
| 6-10章中篇 | 150-250KB | 30-50 |
| 10-20章长篇 | 250-500KB | 50-80 |
| 20章以上 | 500KB+ | 80+ |

## 条目分层设计（NTR/后宫题材专用）— 2026-07-10修订
| 层级 | 条目 | constant | order | 说明 |
|------|------|----------|-------|------|
| 系统层 | 全局规则与OOC防护 | **true** | 199 | 必须常驻 |
| 世界观 | 原作世界观 | **true** | 200 | 必须常驻 |
| 核心规则 | 沦陷值系统、性爱规则 | **true** | 186-189 | 纯规则常驻 |
| 状态栏 | 状态栏系统 | **true** | 197 | 每轮显示 |
| 风险检测 | 被发现风险 | **true** | - | 通用规则 |
| 主角 | 征服者/主人档案 | **false** | 195 | 触发！keys=[主角名] |
| 核心角色 | 行为模板+档案 | **false** | 190-193 | 触发！常驻不超过10条 |
| 其他角色 | 档案 | **false** | 180-185 | 触发 |
| 场景/事件 | 种子库 | false, enabled=false | 150-175 | 手动/AI判断 |
| 备选开场白 | 不同切入点 | false, enabled=false | 118-121 | enabled=false |
| 文风样本 | 原著摘录 | false, enabled=false | 50-59 | enabled=false |

**常驻条目上限：6-8个**（万恶后宫系统案例：24→6，token 8796→5032）
**主角档案不设常驻**：触发式加载，首轮仅在first_mes含关键词时才载入，节省token

## 注意事项
- 备选开场白设为 `enabled=False`，用户手动切换
- 文风样本设为 `enabled=False`，仅供AI参考
- first_mes 取第一章开头3000字左右（不要超过2500字以控制token消耗）
- mes_example 取2-3个经典场景片段
- 角色行为模板比角色档案更实用（给AI具体动作指导）
- **基于已有IP的小说**（如示例游戏项目、原神等）：需要额外搜索该IP的世界观设定，添加一个游戏/原作世界观条目（constant=True, order=200），让AI理解阵营、角色关系等背景知识
- **短篇小说（3-5章，<12万字）**：条目数控制在20-25条即可，不需要过于臃肿。系统条目合并精简，角色条目聚焦核心角色（出现3次以上的）

## 实际案例参考

| 小说 | 字数 | 章节 | 条目数 | 文件大小 | 倍率 | 说明 |
|------|------|------|--------|----------|------|------|
| 圣馨医院 | 9万 | 10 | 40 | 150KB+ | ~3.75 | 中篇医院题材 |
| 抵受不住亲姐姐 | 9.4万 | 56 | 54 | 180.7KB | 5.07 | 短章(每章1000-4500字)姐弟禁忌 |
| 示例角色项目 | 29万 | - | 136 | 203.7KB | 1.27 | 超长篇 |
| 叶无云 | 21万 | - | 90 | 336.9KB | 5.18 | 中篇NTR/催眠 |
| 万恶后宫系统 | 43万 | 47 | 38 | 206.7KB | 0.70 | 系统流后宫，常驻6个/触发32个，token5032 |

**关键发现**：倍率波动大（0.70x-5.18x），取决于extensions复杂度和条目数。万恶后宫系统倍率低（0.70x）因为43万字只做了38条目（角色权重分配，不追求条目数堆叠），但每条目内容充实。
