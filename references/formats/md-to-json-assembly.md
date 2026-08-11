# MD → JSON 组装参考

当MD文件已写好但JSON未生成时（session断了、thinking budget耗尽等），在CLI session中直接组装。

## 关键工具选择

- **读MD文件**：用 `terminal("cat '路径'")` 而非 `read_file()`
  - 原因：`read_file()` 在 `execute_code` 中有跨session缓存，对已读文件返回 `{"status": "unchanged"}` 而非内容
  - `terminal("cat ...")` 每次都返回实际文件内容

## 解析正则

### 解析世界书条目（条目00-19）

```python
import re
entry_pattern = r'# 条目(\d+)：([^\n]+)\n\n(.*?)(?=\n# 条目\d+：|\Z)'
matches = re.findall(entry_pattern, raw_text, re.DOTALL)

for m in matches:
    uid = int(m[0])       # 条目编号
    title = m[1].strip()  # 条目标题
    body = m[2].strip()   # 完整正文（含元数据+正文）
```

### 提取元数据

```python
is_constant = "常驻：是" in body
keywords_match = re.search(r'关键词：([^\n]+)', body)
keywords = [k.strip() for k in keywords_match.group(1).split('、')] if keywords_match else []
```

### 提取正文内容（## 正文之后）

```python
content_match = re.search(r'## 正文\n\n(.*?)(?=\n---|\Z)', body, re.DOTALL)
content = content_match.group(1).strip() if content_match else body
```

### 解析开场白

```python
opening_pattern = r'# 开场白\d+：[^\n]+\n\n(.*?)(?=\n---\n|\n---$|\Z)'
opening_matches = re.findall(opening_pattern, openings_raw, re.DOTALL)

openings = []
for m in opening_matches:
    content = m.strip()
    if content.endswith("---END---"):
        content = content[:-len("---END---")].strip()
    openings.append(content)
```

## 条目映射规则

| MD元数据 | character_book字段 | 值 |
|---|---|---|
| 常驻：是 | `constant: true` | 关键词留空，keys用标题简称 |
| 关键词：X、Y | `constant: false` | keys用关键词数组 |
| 所有条目 | `position: "after_char"` | 字符串 |
| 所有条目 | `extensions.position: 1` | 数字 |
| 条目编号 | `insertion_order: uid * 10` | 按编号×10排序 |

## 组装顺序

1. 用 `terminal("cat ...")` 读取所有MD文件
2. 用正则解析全部条目（按uid排序）和开场白
3. 构建 `character_book.entries[]` 数组
4. 构建顶层字段 + data层字段（spec/spec_version/create_date双层同步）
5. `first_mes` = 开场白[0]，`alternate_greetings` = 开场白[1:]
6. 写JSON文件
7. 用 `python3 -c "import json; json.load(open('文件'))"` 验证

## 组装后验证清单

组装完JSON后，用以下Python验证关键字段：

```python
import json
d = json.load(open('角色卡.json', 'r', encoding='utf-8'))
dd = d['data']
assert d.get('spec') == 'chara_card_v2', "顶层spec缺失"
assert dd.get('spec') == 'chara_card_v2', "data层spec缺失——会导致alternate_greetings不显示！"
assert dd.get('spec_version') == '2.0', "data层spec_version缺失"
assert dd.get('create_date'), "data层create_date缺失"
assert isinstance(dd['extensions'].get('group_only_greetings'), list), "group_only_greetings缺失"
assert len(dd.get('alternate_greetings', [])) > 0, "alternate_greetings为空"
assert len(dd['character_book']['entries']) > 0, "世界书条目为空"
constant_count = sum(1 for e in dd['character_book']['entries'] if e['constant'])
print(f"✓ {len(dd['character_book']['entries'])} entries ({constant_count} constant)")
print(f"✓ {len(dd['alternate_greetings'])} alternate_greetings")
```

## 常见坑

- 开场白正则如果用 `\n# 开场白\d+：` split，第一个元素是空的或包含标题头——用 findall 而非 split
- `---END---` 标记可能存在于MD末尾，需要strip掉
- 条目内容中的 `\n---\n` 分隔符可能被正则贪婪匹配吃掉，用 `(?=\n# 条目|\Z)` 作为前瞻
- 条目正文标记可能是 `## 正文` 或 `条目正文：`，两种格式都需要支持
- 提取正文后需要剥离元数据行（类别：/常驻：/关键词：/优先级：/---），否则这些会混入世界书内容
- **spec/spec_version必须同时在顶层和data层**——这是SillyTavern V2格式的硬性要求，缺少data层spec会导致alternate_greetings显示为1/1而非1/N
