# Content-File-First 构建模式（通用版）

> 来源：天仙配卡(2026-07-12)。将 greetings-file-assembly 模式推广到**所有内容字段**。

## 核心思想

**所有中文内容先写 .txt 文件，再用 execute_code 组装 JSON。** 不在 execute_code 中内联中文长文本。

## 适用场景

- 条目content ≥ 200字符（含中文标点/对话/引号）
- 卡壳字段（description/personality/scenario/system_prompt）
- 开场白（first_mes/alternate_greetings）
- 任何会被 execute_code 三引号/引号/括号拼接坑到的场景

## 目录结构

```
/tmp/<project>_content/
  world_08.txt        ← 世界观条目content
  world_09.txt        ← APP规则条目content
  scene_26.txt        ← 场景条目content
  scene_27.txt
  scene_28.txt
  char_11.json        ← 子代理产出的完整条目JSON
  char_12.json
  ...
  card_description.txt ← 卡壳字段
  card_personality.txt
  card_scenario.txt
  card_system_prompt.txt
  greeting_1.txt      ← first_mes
  greeting_2.txt      ← alternate_greetings[0]
  greeting_3.txt
  greeting_4.txt
  greeting_5.txt
```

## 流程

### Step 1: write_file 写内容到 .txt

直接用 `write_file()` 工具写中文内容到文件。write_file 不经过 Python 源码解析器，中文标点/引号/emoji 全部安全。

### Step 2: execute_code 读取 + 组装

```python
import json, os, glob

def read_content(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read().strip()

# 读取所有内容文件
description = read_content("/tmp/xxx_content/card_description.txt")
first_mes = read_content("/tmp/xxx_content/greeting_1.txt")
alt_greetings = [read_content(f"/tmp/xxx_content/greeting_{i}.txt") for i in range(2, 6)]

# 读取子代理产出的条目JSON
char_files = sorted(glob.glob("/tmp/xxx_content/char_*.json"))
entries = []
for cf in char_files:
    with open(cf, 'r', encoding='utf-8') as f:
        entries.append(json.load(f))

# 组装最终卡片
card = {
    "name": "...",
    "description": description,
    "first_mes": first_mes,
    # ...
}
```

### Step 3: 子代理写 char_*.json

子代理的 goal 中指定输出路径为 `/tmp/<project>_content/char_{id}.json`。
每个子代理写 3-6 个独立 JSON 文件。

### Step 4: 主代理合并 + 验证

execute_code 读取所有文件 → 合并 → validate_card.py。

## 与 greetings-from-file-assembly 的关系

- `greetings-from-file-assembly.md` 是本模式的**子集**（只覆盖开场白）
- 本模式将同一思想推广到**所有内容字段**
- 实际构建时，两者可混合使用

## 实测数据（天仙配卡 2026-07-12）

| 内容类型 | 文件数 | 每文件大小 | 写入方式 |
|---------|--------|-----------|---------|
| 系统条目content | 8 | 400-600字 | execute_code内联（短内容可内联） |
| 世界观条目content | 3 | 400-600字 | write_file → execute_code读取 |
| 场景条目content | 3 | 400-500字 | write_file → execute_code读取 |
| 角色条目content | 18 | 1200-2500字 | 子代理写char_*.json |
| 卡壳字段 | 4 | 900-1700字 | write_file → execute_code读取 |
| 开场白 | 5 | 1600-2300字 | write_file → execute_code读取 |

**经验法则**：
- content < 200字符 → execute_code内联OK
- content 200-1000字符 → write_file写.txt，execute_code读取
- content > 1000字符 → 子代理直接写完整JSON文件
