# JSON组装坑点清单（2026-07-11 实测验证）

构建角色卡JSON时的已知坑点，来自守护卡v1构建实战。

## v3格式必填字段

卡必须是 `chara_card_v3` 格式，否则ST导入会出问题。merge脚本必须包含：

```python
card['spec'] = 'chara_card_v3'
card['spec_version'] = '3.0'
card['mes_example'] = ''          # 必须有，可空
card['creatorcomment'] = '...'    # 必须有
card['avatar'] = 'none'
card['talkativeness'] = '0.5'
card['fav'] = False
card['create_date'] = 'YYYY-MM-DD'
```

data层也必须有：
```python
data['mes_example'] = ''
data['post_history_instructions'] = ''
data['group_only_greetings'] = []
data['spec'] = 'chara_card_v3'
data['spec_version'] = '3.0'
# 顶层 first_mes/name/description/personality/scenario/mes_example 必须与 data 层同步
```

## 常驻条目keys必须为空

validate_card.py 会报错：`常驻条目必须keys=[]`。constant=true的条目不能有任何关键词，否则会导致截断。

```python
for e in entries:
    if e.get('constant') and e.get('keys'):
        e['keys'] = []  # 必须清空
```

## extensions.position映射

子代理生成的条目经常 position=after_char 但 extensions.position=1（应为4）。

映射表：
- `before_char` → extensions.position = 0
- `after_char` → extensions.position = 4（不是1！）
- `before_def` → extensions.position = 2
- `after_def` → extensions.position = 3

merge脚本中必须强制修正：
```python
POS_MAP = {'before_char': 0, 'after_char': 4, 'before_def': 2, 'after_def': 3}
for e in entries:
    pos = e.get('position', '')
    if pos in POS_MAP:
        e['extensions']['position'] = POS_MAP[pos]
```

## first_mes触发负载管理（高负载是诊断项，不是硬红线）

first_mes/alternate_greetings 会被 ST 扫描并触发世界书条目。问题不在于估算 token 是否超过某个固定值，而在于触发内容是否**相关、可用、无污染**。

**正确处理顺序：**
1. 运行 `validate_card.py` + `audit_worldbook_triggers.py` 查看逐 greeting 触发矩阵。
2. 优先修：单字/泛 key、secondary 被顶层 selective=false 忽略、extensions-only selective、多主题大条目、重复开场白。
3. 核心主档案保留自然角色名/常用称呼 key。不要把核心档案唯一 key 改成 `角色名档案/设定`。
4. 如果自然名触发完整档案确实导致 ST/模型截断，再用“中厚速览（自然名触发，自足）+ 深度档案（专用 key 按需）”。
5. 最终以 ST Prompt Itemization / <Lore> / API usage / countTokens 为准，脚本估算只做诊断。


## selective条目必须有secondary_keys

子代理生成的selective条目经常漏掉secondary_keys。validate_card.py会警告。

## addMemo字段

每个条目必须有 `addMemo` 字段（可设为false）。子代理经常漏掉。

## use_regex字段

每个条目必须有 `use_regex` 字段。子代理生成的条目有时漏掉。

## Emoji陷阱

条目content中不能有emoji字符（Unicode > U+FFFF）。validate_card.py会报错。
常见问题：🔴(U+1F534)、💀(U+1F480)等。
替换方案：用文字标记如 [!] 或 [警告]。

## display_index必须等于id

extensions.display_index 必须与条目id一致。merge脚本中需要同步设置。

## Python f-string 会吞掉 `{{user}}` 占位符

在构建脚本里用 f-string 写含 `{{user}}` 的长中文正文时，Python 会把 `{{user}}` 输出成 `{user}`，导致 ST 占位符失效。修复方式：

```python
import re

def fix_placeholders(obj):
    if isinstance(obj, str):
        return re.sub(r'(?<!\{)\{user\}(?!\})', '{{user}}', obj)
    if isinstance(obj, list):
        return [fix_placeholders(x) for x in obj]
    if isinstance(obj, dict):
        return {k: fix_placeholders(v) for k, v in obj.items()}
    return obj

card = fix_placeholders(card)
assert '{user}' not in json.dumps(card, ensure_ascii=False)
```

也可以在 f-string 中写 `{{{{user}}}}`，但批量生成时建议最终全卡扫描 `(?<!\{)\{user\}(?!\})`。

## 常驻条目数量限制

常驻条目建议≤15个。超过15个会警告。

## 子代理生成的安全过滤

子代理在生成NSFW相关内容时可能被安全过滤器拒绝（safety refusal）。对于NSFW卡片的内容审查部分，不要用子代理做——直接自己跑脚本+手动审查。
