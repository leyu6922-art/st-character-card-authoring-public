# SillyTavern 角色卡内嵌世界书格式（2026-07-04 修正版）

## ⚠️ 关键教训：ST导出格式 ≠ ST导入格式

SillyTavern 有两个不同的世界书JSON格式：

1. **导出格式（v1.12+）**：ST导出独立世界书文件时使用。字段名：`key`/`keysecondary`/`uid`/`disable`/`position:4`/`order`
2. **导入格式（v1.11.x兼容）**：ST导入角色卡内嵌世界书时使用。字段名：`keys`/`secondary_keys`/`id`/`enabled`/`position:"after_char"`/`insertion_order`

**用错格式的后果**：世界书条目全部显示为关闭（👁️‍🗨️），需要手动逐个开启。

## 示例游戏项目案例（2026-07-04）

### 问题
导入角色卡后世界书自动链接成功，但所有71条条目都显示为关闭状态。

### 排查过程
1. 对比参考卡（道家仙子美母1.3版本）→ 发现它是独立世界书格式，不是角色卡内嵌格式
2. 对比参考卡（校园媚黑·全员恶堕角色卡）→ 发现它成功导入且条目全部开启
3. 逐字段对比发现关键差异：
   - 参考卡用 `enabled: true`，新卡用 `disable: false`
   - 参考卡用 `keys`，新卡用 `key`
   - 参考卡用 `position: "after_char"`，新卡用 `position: 4`
   - 参考卡用 `insertion_order`，新卡用 `order`
   - 参考卡用 `id`，新卡用 `uid`
   - 参考卡有 `use_regex: true`，新卡没有
   - 新卡有多余字段（addMemo, vectorized, characterFilter等），参考卡没有

### 根因
SKILL.md 文档记录的是ST导出世界书时的v1.12+格式，但ST导入角色卡时实际读取v1.11.x格式。两个格式的字段名和启用机制完全不同。

### 修复
将所有条目字段改为v1.11.x格式后，导入时条目全部显示为开启状态。

## 正确的角色卡内嵌世界书格式（2026-07-10 v3修正）

### ⚠️ 2026-07-10 重大修正：之前关于extensions的结论有误

之前文档记录的"extensions应为空对象"是**错误的**。经多张正常工作的v3角色卡验证（含validate_card.py自动校验），标准v3格式使用`secondary_keys`（非`keysecondary`）、`insertion_order`（非`order`）和31字段extensions。

| 用途 | 导出格式(独立世界书) | ✅ v3 chara card 内嵌格式 |
|------|---------|---------------|
| 关键词 | `key` | `keys` |
| 次要关键词 | `keysecondary` | `secondary_keys` |
| 启用控制 | `disable: false` | `enabled: true` |
| 位置 | `position: 4`(数字) | `position: "after_char"`(字符串) + extensions.position=4(数字) |
| 排序 | `order` | `insertion_order` |
| ID | `uid` | `id` |
| extensions | `{}` | 31字段完整对象 |

**示例游戏项目案例复盘**：该案例条目全部关闭的根因是`disable`/`enabled`字段混用，而非extensions字段数量问题。

### 顶层结构

```json
{
  "spec": "chara_card_v3",
  "spec_version": "3.0",
  "data": {
    "name": "角色名",
    "description": "...",
    "personality": "...",
    "scenario": "...",
    "first_mes": "...",
    "system_prompt": "...",
    "tags": [],
    "creator": "",
    "creator_notes": "简介/说明",
    "alternate_greetings": ["开场白1", "开场白2"],
    "group_only_greetings": [],
    "character_version": "1.0",
    "extensions": {
      "fav": false,
      "depth_prompt": {"prompt": "", "depth": 4, "token_budget": 500}
    },
    "character_book": {
      "name": "角色名-世界书",
      "entries": [{条目1}, {条目2}]
    }
  }
}
```

**⚠️ 必须包含的data层字段（v3规范要求）**：
- `alternate_greetings`（字符串数组）— 放在data层，不是extensions里！
- `group_only_greetings`（空数组）
- `creator_notes`（字符串）
- `mes_example`（字符串，可为空）
- `character_book` 只需 `name` + `entries`

### 条目字段（v3 标准格式，2026-07-10 修正）

```json
{
  "id": 0,
  "keys": ["关键词1", "关键词2"],
  "secondary_keys": [],
  "comment": "条目标题",
  "content": "条目正文",
  "constant": true,
  "enabled": true,
  "selective": false,
  "addMemo": true,
  "insertion_order": 0,
  "position": "after_char",
  "use_regex": true,
  "extensions": {
    "position": 4, "exclude_recursion": false, "display_index": 0,
    "probability": 100, "useProbability": true, "depth": 4,
    "selectiveLogic": 0, "outlet_name": "", "group": "", "group_override": false,
    "group_weight": 100, "prevent_recursion": true, "delay_until_recursion": false,
    "scan_depth": null, "match_whole_words": null, "use_group_scoring": false,
    "case_sensitive": null, "automation_id": "", "role": 0, "vectorized": false,
    "sticky": 0, "cooldown": 0, "delay": 0,
    "match_persona_description": false, "match_character_description": false,
    "match_character_personality": false, "match_character_depth_prompt": false,
    "match_scenario": false, "match_creator_notes": false, "triggers": [],
    "ignore_budget": false
  }
}
```

**关键规则**：
- `extensions`必须包含31个字段，空`extensions: {}`能导入但丢失所有设置
- `display_index`必须与`id`一致
- `prevent_recursion`建议全部设为`true`防止链式触发
- position映射：`before_char`=0, `after_char`=4
- `character_book`只需`name`+`entries`两个字段（无需description/scan_depth等）

### 常见错误

#### ❌ 错误1：用 `disable: false` 代替 `enabled: true`
- ST导入时忽略 `disable` 字段，只读 `enabled`
- 结果：所有条目显示为关闭

#### ❌ 错误2：用 `key` 代替 `keys`
- ST导入时无法识别 `key` 字段
- 结果：触发关键词不生效

#### ❌ 错误3：用 `position: 4` 代替 `position: "after_char"`
- ST导入时可能无法正确解析整数格式
- 结果：条目注入位置错误

#### ❌ 错误4：缺少必需字段（addMemo, use_regex, secondary_keys等）
- addMemo、use_regex、secondary_keys、insertion_order是v3格式的必需字段
- 缺少这些字段会导致条目行为异常或validate_card.py报错

#### ❌ 错误5：缺少 `use_regex: true`
- ST导入时可能默认不启用正则匹配
- 结果：关键词匹配异常

## 独立世界书导出格式（v1.12+）

如果要导出独立世界书文件（不是角色卡内嵌），使用v1.12+格式：

```json
{
  "entries": {
    "0": {
      "key": ["关键词"],
      "keysecondary": [],
      "comment": "条目标题",
      "content": "条目正文",
      "constant": true,
      "vectorized": false,
      "selective": true,
      "selectiveLogic": 0,
      "addMemo": true,
      "order": 1,
      "position": 4,
      "disable": false,
      ...
    }
  }
}
```

**注意**：这是ST导出世界书时的格式，与导入角色卡时的格式不同。
