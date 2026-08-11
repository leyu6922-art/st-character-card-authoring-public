# 开场白文件化组装模式

## 问题

execute_code中的长中文字符串（1000+字符）容易出现：
1. 括号隐式拼接导致SyntaxError
2. 三引号嵌套导致字符串截断
3. 单引号/双引号混用导致转义噩梦
4. 多轮扩写时inline字符串每轮只增加70-100字符

## 解决方案：文件化模式

### Step 1: write_file 写开场白到 txt
用 `write_file()` 将每个开场白写入独立的txt文件：
```
/tmp/xxx_g1.txt  (first_mes)
/tmp/xxx_g2.txt  (alt[0])
/tmp/xxx_g3.txt  (alt[1])
...
```

**优势**：write_file直接接受中文文本，不需要转义。

### Step 2: execute_code 中读取+sup处理+组装
```python
def read_greeting(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    # 替换补充平面字符
    result = []
    for ch in text:
        if ord(ch) > 0xFFFF:
            result.append(f'[U+{ord(ch):04X}]')
        else:
            result.append(ch)
    return ''.join(result)

first_mes = read_greeting("/tmp/xxx_g1.txt")
alt_greetings = [read_greeting(f"/tmp/xxx_g{i}.txt") for i in range(2, 6)]
```

### Step 3: 迭代扩写
字数不达标时：
1. 在execute_code中用Python读取txt文件
2. 用str.replace()在指定锚点前后插入新段落
3. 写回txt文件
4. 重新组装验证

**扩写锚点选择技巧**：
- 选长且唯一的子串（≥20字符）
- 避免选新插入文本中也出现的子串
- 每轮用不同锚点，避免错位

### Step 4: 最终组装
```python
card['data']['first_mes'] = read_greeting("/tmp/xxx_g1.txt")
card['data']['alternate_greetings'] = [
    read_greeting(f"/tmp/xxx_g{i}.txt") for i in range(2, 6)
]
```

## 实测数据（示例角色项目v2）

| 轮次 | first_mes | alt[0] | alt[1] | alt[2] | alt[3] |
|------|-----------|--------|--------|--------|--------|
| 初始 | 768 | 703 | 541 | 635 | 677 |
| 第1轮扩写 | 1514 | 1363 | 1070 | 1100 | 1109 |
| 第2轮扩写 | 1514 | 1454 | 1352 | 1384 | 1306 |
| 第3轮扩写 | 1514 | 1454 | 1421 | 1407 | 1409 |

每轮扩写用str.replace()在不同锚点插入100-300字符的段落。

## 与execute_code inline模式的对比

| 维度 | 文件化模式 | inline模式 |
|------|-----------|-----------|
| 中文处理 | 安全，write_file原样写入 | 危险，括号/引号混用易报错 |
| 扩写效率 | 每轮可增加200-500字符 | 每轮只增加70-100字符 |
| 锚点替换 | 在Python中精确操作 | 受execute_code输出截断影响 |
| 适用场景 | 开场白≥500字符 | 短文本（<200字符） |
