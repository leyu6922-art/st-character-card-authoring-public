## /tmp/ 文件污染问题（2026-07-04 闷骚健身美母案例）

**问题**：多批次构建时，`/tmp/entries_partN.json` 文件可能包含上一个session的旧数据。`execute_code` 写入 `/tmp/` 的文件在后续调用中仍然存在，如果写入失败或被跳过，旧数据会混入最终卡。

**症状**：
- 条目名称正确但内容来自另一个角色卡
- 例：条目名「全局规则与OOC防护」但内容写着「你正在扮演周雨晴」
- 验证时 `assert '周雨晴' not in content` 会失败

**根因**：
1. `execute_code` 每次调用是独立沙箱，但 `/tmp/` 文件系统在调用间持久化
2. 前一个session的 `/tmp/entries_part1.json` 仍然存在
3. 新session的 execute_code 可能因为 SyntaxError 等原因未成功写入，但旧文件仍在
4. 后续合并调用读取到的是旧数据

**解决方案**：

### 方案A：单次构建（推荐，条目数≤50时）
在**一个** execute_code 调用中构建所有条目，不依赖 `/tmp/` 文件传递。

```python
# ✅ 正确：单次调用构建所有条目
def make_entry(...): ...

entries = []
entries.append(make_entry(0, ...))  # 系统条目
entries.append(make_entry(1, ...))
# ... 所有条目在同一个调用中完成

card = {"spec": "chara_card_v2", "data": {..., "character_book": {"entries": entries}}}
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(card, f, ensure_ascii=False, indent=2)
```

### 方案B：多批次构建（条目数>50时）
如果必须分批，每次写入前先清理旧文件，写入后立即验证。

```python
# 写入前清理
import os
if os.path.exists("/tmp/entries_part1.json"):
    os.remove("/tmp/entries_part1.json")

# 写入
with open("/tmp/entries_part1.json", "w", encoding="utf-8") as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)

# 立即验证
with open("/tmp/entries_part1.json", "r", encoding="utf-8") as f:
    verify = json.load(f)
assert verify[0]['content'][:20] == '预期内容前20字', "写入验证失败！"
```

### 方案C：最终合并时全量验证
合并所有 part 后，对每个条目内容做关键词检查：

```python
all_entries = part1 + part2 + part3
for e in all_entries:
    assert '前一个角色名' not in e['content'], f"Entry {e['id']} 有旧数据！"
    assert '当前角色名' in e['content'] or '通用关键词' in e['content']
```

## 浮点数文件大小显示陷阱（2026-07-04）

**问题**：`file_size/1024` 显示为 `140.0 KB` 但实际可能是 `139.99 KB`。

```python
# ❌ 不可靠
print(f"文件大小：{file_size/1024:.1f} KB")  # 可能显示 140.0 但实际 139.99

# ✅ 可靠
print(f"精确文件大小：{file_size} 字节")
print(f"目标：{140*1024} 字节")
print(f"{'达标' if file_size >= 140*1024 else '未达标'}")
```

**原因**：`.1f` 格式化会四舍五入。143,347 字节 = 139.99 KB 但显示为 140.0 KB。

## 字符串引号混用导致 SyntaxError（2026-07-04）

**问题**：在 execute_code 中，长字符串开始用 `"` 但结束用 `'`（或反之），导致 SyntaxError。

```python
# ❌ 错误 — 引号不匹配
content = "剧情节点 — 第八九章：三亚温泉旅游',  # " 开头 ' 结尾

# ✅ 正确 — 统一使用单引号（避免中文引号转义问题）
content = '剧情节点 — 第八九章：三亚温泉旅游'

# ✅ 正确 — 统一使用双引号
content = "剧情节点 — 第八九章：三亚温泉旅游"
```

**最佳实践**：
- 中文内容统一用**单引号**包裹（避免中文双引号 `""` 需要转义）
- 英文内容统一用**双引号**包裹
- 不要在同一个字符串上混用
