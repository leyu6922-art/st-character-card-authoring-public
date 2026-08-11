# NTR关系矩阵设计模式

> 当NTR卡有多个女性角色×多个NTR男性目标时，用矩阵结构系统化管理关系。

## 适用场景

- 小说有3+个被NTR的女性角色
- 每个女性角色被2+个不同男性目标征服
- 需要确保每个NTR目标都有独立的剧情线和开场白

## 矩阵结构

```
           NTR目标A    NTR目标B    NTR目标C    NTR目标D
女性1       ✅         ✅                      ✅
女性2       ✅                    ✅
女性3                  ✅         ✅          ✅
女性4       ✅         ✅         ✅          ✅
```

每对关系（女性×NTR目标）需要：
1. 独立的NTR场景描写（从原文提取）
2. 关键对话引用
3. NTR手段分类（暴力/金钱/魔法/身份便利/胁迫）

## NTR手段分类表

| NTR类型 | 控制手段 | 卡的核心系统 | 代表案例 |
|---------|---------|-------------|---------|
| 肉体征服型 | 性能力/暴力 | 好感度/堕落度系统 | 道家仙子美母 |
| 灵魂操控型 | 超自然道具/催眠 | 道具系统+觉醒线 | 示例玄幻项目 |
| 金钱购买型 | 金钱/债务 | 交易系统+债务追踪 | 示例角色项目（领主） |
| 魔法控制型 | 法术/法杖 | 道具效果+副作用 | 示例角色项目（爱德） |
| 身份便利型 | 职务/关系/环境 | 场景触发 | 示例角色项目（练武场） |

## 矩阵→条目映射

**方案A：按女性角色分条目**（推荐，条目数少）
- 每个女性角色1个条目，content内按NTR目标分段
- 适合NTR目标≤4的情况

**方案B：按关系对分条目**（内容深，条目多）
- 每对关系（女性×NTR目标）独立条目
- 适合NTR目标>4或每条关系线很长的情况

**方案C：混合模式**
- 核心女性角色用方案B（独立条目保证深度）
- 配角女性用方案A（合并节省条目数）

## 开场白分配

```
按NTR目标分配开场白（确保每个目标至少1条）：
NTR目标A（主角型）：3-4条开场白
NTR目标B：2条开场白
NTR目标C：1-2条开场白
NTR目标D：1条开场白
苦主发现视角：1条开场白
```

## 案例：示例角色项目（2026-07-10）

4女性×5NTR目标=20条关系线，实际用混合模式：
- 师傅/古兰（3729次）→ 独立条目，按NTR目标分段
- 伊丝娜（1647次）→ 独立条目
- 奥萝拉（1216次）→ 独立条目
- 妮丝（449次）→ 独立条目
- NTR男性目标各1个条目（爱德/肥猪领主/黑巨汉/黑兽人）
- 总计：4女+4男=8个角色条目 + 系统条目

## 角色频次扫描代码

```python
import os, re
from collections import Counter

base = "/path/to/novel_dir"
all_text = ""
for f in sorted(os.listdir(base)):
    if f.endswith('.txt'):
        with open(os.path.join(base, f), encoding='utf-8') as fh:
            all_text += fh.read()

# 已知角色名列表
known_chars = {"角色A": 0, "角色B": 0, ...}
for name in known_chars:
    known_chars[name] = len(re.findall(name, all_text))

for name, count in sorted(known_chars.items(), key=lambda x: -x[1]):
    print(f"  {name}: {count}次")

# 未知角色发现：对话归属模式
attr_pattern = re.findall(r'([^\s，。！？]{2,6})(?:说道|笑道|叫道|喊道|问道|答道|怒道|骂道)', all_text)
attr_freq = Counter(attr_pattern)
for name, count in attr_freq.most_common(20):
    if count >= 5:
        print(f"  {name}: {count}次")

# NTR主题关键词频率
ntr_keywords = {"肏": 0, "干": 0, "征服": 0, "臣服": 0, "精液": 0, "巨根": 0, ...}
for kw in ntr_keywords:
    ntr_keywords[kw] = len(re.findall(kw, all_text))
```
