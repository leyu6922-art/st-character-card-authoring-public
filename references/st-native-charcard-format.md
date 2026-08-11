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

## 正确的角色卡内嵌世界书格式（2026-07-04 实测修正）

### ⚠️ 重大修正：导入格式 vs 导出格式差异很小

之前文档记录的"导入格式"（`secondary_keys`/`insertion_order`/巨型`extensions`）是**错误的**。
实测对比多张能正常工作的角色卡后，确认ST导入格式与导出格式**几乎相同**，只有两个字段不同：

| 用途 | 导出格式 | ✅ 实际导入格式 |
|------|---------|---------------|
| 关键词 | `key` | `keys` |
| 次要关键词 | `keysecondary` | `keysecondary`（不变！） |
| 启用控制 | `disable: false` | `enabled: true` |
| 位置 | `position: 4` | `position: "after_char"` |
| 排序 | `order` | `order`（不变！） |
| ID | `uid` | `id` |
| extensions | `{}` | `{}`（空对象！不要填30+字段） |

**关键发现**：`secondary_keys`、`insertion_order`、巨型`extensions`对象是**错误的字段名/结构**，会导致：
- 文件体积膨胀（每个条目多2-3KB无用extensions）
- alternate_greetings可能无法被ST正确识别
- 条目解析异常

### 顶层结构

```json
{
  "spec": "chara_card_v2",
  "spec_version": "2.0",
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
      "description": "世界书说明",
      "scan_depth": 100,
      "token_budget": 30000,
      "recursive_scanning": true,
      "extensions": {},
      "entries": [{条目1}, {条目2}]
    }
  }
}
```

**⚠️ 必须包含的data层字段（缺少会导致ST解析异常）**：
- `alternate_greetings`（字符串数组）— 放在data层，不是extensions里！
- `group_only_greetings`（空数组）
- `creator_notes`（字符串）
- `character_book` 必须包含 `description`、`scan_depth`、`token_budget`、`recursive_scanning`、`extensions`

**⚠️ 不要有的字段**：
- `mes_example` — 空字符串可能干扰ST解析，直接省略此字段

### 条目字段（实测验证格式）

```json
{
  "id": 0,
  "keys": ["关键词1", "关键词2"],
  "keysecondary": [],
  "comment": "条目标题",
  "content": "条目正文",
  "constant": true,
  "enabled": true,
  "selective": false,
  "selective_logic": 0,
  "addMemo": false,
  "order": 0,
  "position": "after_char",
  "extensions": {}
}
```

**注意**：`extensions` 必须是空对象 `{}`。不要填入30+个字段，这会导致文件膨胀且可能干扰ST解析。

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

#### ❌ 错误4：添加多余字段（addMemo, characterFilter等）
- ST导入时可能因为多余字段而跳过条目
- 结果：条目不显示或显示异常

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
