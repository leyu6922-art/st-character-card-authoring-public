## 中文字符的字节/字符比（2026-07-04 叶无云案例）

**关键发现**：中文字符在UTF-8中占3字节。JSON文件大小 ≈ content字符数 × 3 + JSON结构开销。

**实测数据（叶无云角色卡，53条目211.8KB）**：
- 10个系统条目，content共7,697字符 → 文件34,285字节（~4,455字节/条目）
- 每个条目content约1,000-1,800字符 → 对应文件约4,000-6,000字节
- 最终53条目，总content约40,000字符 → 文件216,925字节（211.8KB）

**大小规划公式**：
- 目标文件大小KB ÷ 4 ≈ 需要的content字符数（万字）
- 例：180KB目标 → 需要约45,000 content字符
- 每条目平均1,000-1,500字符 → 需要30-45个条目
- 每条目平均2,000-3,000字符 → 需要15-23个条目

**批次规划**：
- 每个execute_code调用构建7-9条目 → 约20KB文件增量
- 180KB目标 → 需要约9个execute_code调用
- 每个调用的content总量约6,000-8,000字符

## 括号隐式拼接在变量赋值中可用（2026-07-04 叶无云案例）

**发现**：`("str1" "str2")` 拼接在**变量赋值**中稳定可用，但**不能直接用在函数参数中**。

```python
# ✅ 正确 — 变量赋值中使用括号隐式拼接
content = (
"第一段内容\n"
"第二段内容\n"
"第三段内容"
)
entries.append(make_entry(0, ["keys"], [], "标题", content))

# ❌ 错误 — 直接在函数参数中使用（不稳定）
entries.append(make_entry(0, ["keys"], [], "标题",
("第一段" "第二段")))
```

**优势**：相比 `+=` 拼接，括号隐式拼接更简洁，不需要反复写 `content +=`，且不会因为漏掉 `\n` 导致行粘连。

**与三引号字符串的区别**：三引号 `"""..."""` 会保留源码中的缩进和换行，而括号拼接每行都是独立字符串，完全控制格式。

## 原始内容（问题7）

## 问题7：tuple语法在函数调用中导致SyntaxError（2026-07-04）

**场景**：在 `execute_code` 中用 tuple 语法传递多行内容给函数参数。

**症状**：
```
SyntaxError: invalid syntax. Perhaps you forgot a comma?
```

**示例**：
```python
# ❌ 错误 — tuple语法在函数调用中不稳定
entries.append(make_entry(19, ["keys"], [], "title",
('【苏倾城×杰克 · NTR关系线】\n\n'
 '一、关系定位\n'
 '主NTR线。')))

# ✅ 正确 — 先赋值给变量，再传参
content = '【苏倾城×杰克 · NTR关系线】\n\n'
content += '一、关系定位\n'
content += '主NTR线。'
entries.append(make_entry(19, ["keys"], [], "title", content))
```

**原因**：Python解析器在函数调用上下文中，对 `(` 开始的 tuple 语法处理与独立赋值不同。当 tuple 的第一个元素以 `(` 开头且包含中文字符时，解析器可能将其误判为嵌套的函数调用。

**通用规则**：
- 在函数调用中传递多行字符串时，始终先赋值给变量
- 使用 `content = 'line1\n'` + `content += 'line2\n'` 拼接模式
- 不要使用 `('line1' 'line2')` 的隐式拼接（在函数参数中不稳定）

## 新变体：TypeError: list.append() takes no keyword arguments（2026-07-04 抵受不住亲姐姐案例）

**场景**：在 `execute_code` 中用括号隐式拼接作为 `make_entry()` 的 content 参数，再传给 `list.append()`。

**症状**：
```
TypeError: list.append() takes no keyword arguments
```

**示例**：
```python
# ❌ 错误 — 括号拼接在函数参数内被误解析
entries.append(make_entry(51, ['key'], [], 'comment', (
    '第一行内容\n'
    '第二行内容\n'
)))

# ✅ 正确 — 先赋值给变量
content = (
    '第一行内容\n'
    '第二行内容\n'
)
entries.append(make_entry(51, ['key'], [], 'comment', content))
```

**原因**：Python解析器将 `make_entry(...)` 后面的 `(` 视为新的表达式开始（函数调用或tuple），而非字符串拼接的括号。这导致 `append()` 收到了意外的关键字参数。

**通用规则（最终版）**：
1. **变量赋值中**：括号隐式拼接 `content = ("str1" "str2")` ✅ 稳定可用
2. **函数参数中**：括号隐式拼接 ❌ 不稳定，会报 TypeError 或 SyntaxError
3. **安全做法**：永远先赋值给变量，再传参

## 新变体：null vs None（2026-07-04 人妻妈妈娼馆案例）

**场景**：从JSON格式复制make_entry模板时，误将Python的`None`写成JSON的`null`。

**症状**：
```
NameError: name 'null' is not defined
```

**修复**：Python中没有`null`，用`None`。JSON中的`null`对应Python的`None`。

## 新变体：中文引号在双引号字符串中导致SyntaxError（2026-07-04）

**场景**：在execute_code中写含中文引号的字符串。

**症状**：
```
SyntaxError: invalid character '"' (U+201C)
```

**示例**：
```python
# ❌ 错误 — 中文左引号"在Python字符串中被视为非法字符
c = "妈妈说"你好""

# ✅ 正确 — 用单引号包裹含中文双引号的字符串
c = '妈妈说"你好"'

# ✅ 正确 — 用Unicode转义
c = "妈妈说\u201c你好\u201d"
```

**通用规则**：中文内容中含中文引号时，用单引号包裹Python字符串。

## 新变体：Emoji/特殊Unicode字符在execute_code中导致SyntaxError（2026-07-05 无尽骚妈案例）

**场景**：在execute_code中写含emoji或特殊Unicode字符（❤、📍、🕐、🔥等）的Python字符串。

**症状**：
```
SyntaxError: invalid character '❤' (U+2764)
```

**示例**：
```python
# ❌ 错误 — emoji ❤ 在Python源码中被视为非法字符
content = "没事~❤妈妈扭头对着我温柔一笑"

# ❌ 错误 — Unicode转义能解决emoji但目录名容易写错
path = "/mnt/.../\u65e0\u5c3a\u9a9a\u5988/"  # 容易把"尽"写成"尺"
```

**根本原因**：虽然execute_code沙箱配置了UTF-8编码，但Python源码解析器对emoji字符（Unicode 6.0+的非BMP字符）的处理仍然不一致。emoji不在Python标识符合法字符范围内，即使出现在字符串字面量中也可能触发解析错误。

**解决方案（write-to-file-first模式）**：
1. 用 `write_file` 将含emoji的中文内容写入 .txt 文件（write_file不经过Python源码解析）
2. 在 execute_code 中用 `open()` 读取该 .txt 文件
3. 读取的内容中emoji正常显示，可直接赋值给变量或写入JSON

```python
# ✅ 正确 — write_file写入，execute_code读取
# 步骤1：在execute_code外用write_file写入 /tmp/scene.txt
# 步骤2：在execute_code中读取
with open("/tmp/scene.txt", "r", encoding="utf-8") as f:
    first_mes = f.read()  # ❤ emoji正常显示
```

**触发条件**：开场白、对话示例等包含❤、📍、🕐、🔥等emoji的文本内容。

**注意**：Unicode转义符 `\u2764` 在Python字符串中可以替代❤，但会使源码可读性极差。对于包含大量emoji的长文本（如开场白），write-to-file-first模式是更清洁的方案。

**中文目录名问题**：不要在execute_code中用Unicode转义构造中文目录名（如 `\u65e0\u5c3a` 容易拼错）。直接用中文字符或让terminal创建目录。

## 新变体：三引号中文字符串在写入.py文件后执行报SyntaxError（2026-07-05 健身美母案例）

**场景**：在 `write_file` 写入的 Python 脚本中使用三引号 `"""..."""` 包裹大段中文内容，然后用 `terminal("python3 /tmp/script.py")` 执行。

**症状**：
```
SyntaxError: invalid syntax. Perhaps you forgot a comma? (line 154, column 16)
```

**示例**：
```python
# ❌ 错误 — 三引号中文内容写入.py文件后执行
write_file("/tmp/build.py",
    'entry = {\n'
    '    "content": """【基本信息】赵雅琴（大姐大），38岁...\n'
    '    【外貌】冷艳高贵...\n'
    '    """\n'
    '}\n'
)
terminal("python3 /tmp/build.py")  # SyntaxError!
```

**根因**：三引号字符串中的中文标点（全角逗号、括号等）在.py文件被Python解析器执行时，可能被误判为语法元素。尤其当内容跨越多行且包含`{`、`(`、`[`等字符时。

**解决方案（content-from-file模式）**：
1. 将每个条目的长中文内容写入单独的 `.txt` 文件（`write_file` 不经过Python源码解析）
2. Python脚本用 `open()` 读取 `.txt` 文件内容
3. 脚本内用读取的字符串变量构建JSON

```python
# ✅ 正确 — content-from-file模式
# 步骤1：write_file写入内容到 /tmp/card_content/char_name.txt
# 步骤2：Python脚本读取
def read_content(filename):
    with open(f"/tmp/card_content/{filename}", "r") as f:
        return f.read().strip()

entry = {
    "id": 51,
    "keys": ["大姐大", "一路公交车"],
    "content": read_content("dajieda.txt"),  # 从文件读取
    # ...
}
```

**适用场景**：
- 增强已有卡片、添加新角色条目（每个角色内容1000+字符）
- 任何需要在Python脚本中使用大段中文内容的场景
- 内容中包含中文标点（全角逗号、括号、引号）的情况

**与execute_code直接写入的对比**：
- `execute_code` 沙箱已配置UTF-8，中文可直接写 → 适合构建新卡
- `write_file` + `terminal` 执行.py → 适合修改现有大文件（需要读取现有JSON再修改）
- 当两种方式都可以时，优先用 `execute_code`（更简洁）

## 新变体：全角/半角引号混用在括号拼接中导致SyntaxError（2026-07-05 示例角色项目案例）

**场景**：在 `execute_code` 中用括号隐式拼接写中文对话内容，字符串中混合了全角引号（`"` `"`）和半角引号（`"`）。

**症状**：
```
SyntaxError: unterminated string literal (detected at line N)
```

**示例**：
```python
# ❌ 错误 — 全角引号"被Python解析器视为普通字符，但半角引号"被当作字符串边界
content = (
    '张强："你信不信，只要老子想，随时都能把你妈按在床上肏得死去活来？那副骚样子，指不定比妓女还会叫床呢！"\n'
    '瘦猴："那对奶子，啧啧啧，至少有K罩杯吧？"\n'
    '妈妈："求求你，放过我……""不要……那里脏……""\n'  # ← 最后的""导致解析器认为字符串未闭合
)
```

**根因**：中文对话中常出现连续的引号组合（如 `……""不要`），Python解析器将第一个`"`视为字符串结束符，后面的中文内容变成了非法语法。

**解决方案**：
1. **write_file模式**（推荐）：用 `write_file` 将含对话的中文内容写入 .txt 文件，不经过Python源码解析。在 `execute_code` 中用 `open()` 读取。
2. **单引号包裹**：如果内容只含半角双引号，用单引号包裹Python字符串（如 `'他说"你好"'`）。但如果内容同时含全角和半角引号，仍可能出问题。
3. **转义半角引号**：用 `\"` 转义字符串内的半角引号，但对大量对话内容不实际。

**通用规则**：当开场白或条目内容包含角色对话（大量引号），优先用 write_file 模式写入 .txt 文件，再在 execute_code 中读取。

## 字符计数提醒（2026-07-04）

`len()` 在Python中计数Unicode codepoints，不是UTF-8字节。中文字符每个计1。
- 1000个中文字符 = len()返回1000
- 但JSON文件中UTF-8编码 = 3000字节
- 开场白目标1300字 = 1300个Unicode字符（不是1300字节）
