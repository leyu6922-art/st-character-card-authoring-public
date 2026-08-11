# 多章小说→角色卡 完整工作流（2026-07-03 圣馨医院案例）

## 概述
将10章中篇小说（约9万字）转化为150KB+角色卡（含40条世界书条目）的完整流程。

## 工作流

### Phase 0: 模板库审查（写规划书前必做！）
```
1. skill_view("st-character-card-authoring", "references/game-mechanics-template-library.md")
2. 逐个模板对照小说特点，输出"采用/不采用"表格
3. 将采用的模板融入后续条目设计
```
⚠️ 不要跳过这步直接写规划书——模板选择会改变条目架构设计。

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

| 层级 | 条目 | constant | order |
|------|------|----------|-------|
| 系统层 | 防OOC、全局规则 | true | 199 |
| 世界观 | 医院设定、护理体系 | true | 200 |
| 主角 | 唐沐详细档案 | true | 195 |
| 核心角色 | 唐若曦（常驻，因戏份最重） | true | 190 |
| 系统条目 | 性爱规则、文风控制、关系矩阵 | true | 186-188 |
| 剧情 | 已发生事件、推进指南、状态栏 | true | 150-183 |
| 角色 | 萧婉清/苏凝/林南卿/宁夕/赵玟曼 | false | 165-185 |
| 补充 | 行为模板、描写库、场景库 | false | 129-145 |
| 备选开场白 | 从不同章节切入 | false, enabled=false | 118-120 |
| 文风样本 | 原著章节摘录 | false, enabled=false | 50-59 |

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

### Phase 5: 部署与验证
```python
# 复制到目标目录
terminal(f'cp "{src}" "{dst}"')

# 验证JSON结构
with open(dst, 'r', encoding='utf-8') as f:
    card = json.load(f)
assert card['spec'] == 'chara_card_v2'
assert len(card['data']['character_book']['entries']) >= 20
```

## 目标大小参考
| 小说规模 | 目标卡大小 | 条目数 |
|----------|-----------|--------|
| 3-5章短篇 | 80-100KB | 15-25 |
| 6-10章中篇 | 150-250KB | 30-50 |
| 10-20章长篇 | 250-500KB | 50-80 |
| 20章以上 | 500KB+ | 80+ |

## 条目分层设计（NTR/后宫题材专用）
| 层级 | 条目 | constant | order |
|------|------|----------|-------|
| 系统层 | 全局规则与OOC防护 | true | 199 |
| 世界观 | 原作世界观（游戏/动漫设定） | true | 200 |
| 主角 | 征服者/肌肉男/主人 | true | 195 |
| 核心角色 | 戏份最重的女性角色（常驻） | true | 190 |
| 指挥官/苦主 | 被绿帽的丈夫/男友 | true | 196 |
| 系统条目 | 催眠/药物/NTR关系矩阵 | true | 197-198 |
| 系统条目 | 性爱规则、文风控制 | true | 186-188 |
| 堕落度系统 | 堕落阶段定义和触发条件 | true | 189 |
| 其他角色 | 按出场顺序排列 | false | 180-185 |
| 场景库 | 关键场景描述 | false | 170-175 |
| 剧情节点 | 关键剧情事件 | false, enabled=false | 150-160 |
| 备选开场白 | 不同堕落阶段切入 | false, enabled=false | 118-121 |
| 补充设定 | 游戏机制、世界知识 | false, enabled=false | 165-170 |

## 🆕 超大规模小说处理（100+章节）

当小说超过100章（如338章的《催眠助理》、120章的《艳母的荒唐赌约》），有**两种策略**：

### 策略A：战略采样（适合快速做卡）
```
1. 读前5-10章：理解起源/设定/核心角色
2. 读后3-5章：了解终局状态/制度/权力体系
3. 中间章节采样：用 `ls | grep -i "keyword"` 定位关键主题章节
4. 读每个故事阶段的1-2个代表性章节
5. 总阅读量目标：40-80章（不足20%总章节数即可覆盖）
```

### 策略B：并行子代理全量读取（适合深度提取，2026-07-17验证）
```
1. 主代理精读前20章（角色介绍+世界观+核心设定）
2. 同时派3个delegate_task子代理分别读取：
   - 子代理1：第21-50章
   - 子代理2：第51-80章
   - 子代理3：第81-末章
3. 子代理产出：各章角色/事件/对白/描写摘要（中文）
4. 主代理综合子代理产出 + 自己的精读 → 写入分析文档
5. 完整产出：40-60KB的全方位提取文档
```

**context中必须包含**：已知角色名+身份、小说目录路径、输出格式要求
**子代理限制**：每个子代理约能处理30-40章（受context限制）

**产出模板**：见 `references/workflows/novel-full-extraction-template.md`（10维度全方位提取）

### 跨窗口管道工作流（2026-07-15新增，2026-07-17扩展）
```
Window 1（当前窗口）：读 + 分析 + 输出分析文档
  → 产出：{小说目录}/【小说名】_全方位提取.md
  → 文档结构见 `references/workflows/novel-full-extraction-template.md`（10维度深度提取）
  → 或 `references/workflows/analysis-document-template.md`（轻量交接件，<30章用）

Window 2+（后续窗口）：读取分析文档 → 按skill流程做卡
  → 输入：分析记录文档
  → 无需重读小说（文档应包含角色/机制/事件/语料/建议全部信息）
```

### 分析文档必含要素（轻量版，见analysis-document-template.md）
| 要素 | 说明 |
|------|------|
| 故事分幕 | 每幕5-10行概括核心事件链 |
| 角色矩阵 | 全部核心角色+身份+关系+关键事件+重要性评级 |
| 机制提取 | 任何可复用的系统规则单独章节描述 |
| 关系矩阵 | 恋爱/权力/情感/控制关系表 |
| 事件记录 | 每个关键章节的核心事件实录 |
| 做卡建议 | 原型选择+时间节点+条目规划+注意事项 |

### 分析文档必含要素（深度版，见novel-full-extraction-template.md）
在轻量版基础上增加：
| 要素 | 说明 |
|------|------|
| 性格六维 | 公开人设/私下真实/核心欲望/核心恐惧/道德底线/弱点 |
| 语言指纹 | 称呼习惯/口头禅(原文+章节)/语气/对话样本(5-10句) |
| 行为语料库 | 情绪/互动/外貌/环境四类原文描写，每类≥3条 |
| 场景库 | 每场景7要素：地点/氛围/功能/角色/事件/道具/章节 |
| 叙事风格 | 视角/文风/技巧/风格样本(2-3段原文) |
| NSFW场景目录 | 逐场景参与者/行为链/情感/关键描写 |

### 关键技能
- `ls "第*章*" | grep -i "关键词"` 定位章节比逐章翻找高效10倍
- 角色名+文件标题的Unicode兼容问题：用 `ls` 获取精确文件名，不要猜
- 338章的分析文档产出规模约28KB，足够另一窗口做完整构建

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

**关键发现**：倍率波动大（1.27x-5.18x），取决于extensions复杂度和条目数。30-60条目时用5.0x作为默认乘数更安全。
