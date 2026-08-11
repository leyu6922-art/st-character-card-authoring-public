# SillyTavern 原生世界书导出格式

当用户提供SillyTavern导出的世界书JSON（非chara_card_v2格式）作为参考卡时，需要了解此格式。

## 与chara_card_v2的区别

| 特征 | chara_card_v2（内嵌世界书） | ST原生导出 |
|---|---|---|
| 条目容器 | `data.character_book.entries` (list) | `entries` (dict, 顶层) |
| 条目索引 | 列表下标 | 数字字符串key（"0", "1", ...） |
| 启用字段 | `enabled` | `constant`（常驻）+ `selective`（关键词） |
| 位置字段 | `position: "after_char"` | `position: 4`（@depth） |
| 插入顺序 | `insertion_order` | `order` |
| 禁用字段 | `enabled: false` | `disable: true` |
| 关键词字段 | `keys` | `key` |
| 次要关键词 | `secondary_keys` | `keysecondary` |
| 扩展字段 | `extensions.position: 1` | `extensions.position: 4` |
| 角色卡数据 | `data`（含description/personality等） | `originalData`（含name和entries） |

## ST原生格式条目结构

```json
{
  "key": ["关键词1", "关键词2"],      // 常驻时为 []
  "keysecondary": [],
  "comment": "条目名称",
  "content": "条目内容",
  "constant": true,                    // true=常驻（always on）
  "vectorized": false,
  "selective": false,                  // true=关键词触发
  "selectiveLogic": 0,
  "addMemo": true,
  "order": 1,                          // 插入顺序
  "position": 4,                       // 4=@depth（在聊天中注入）
  "disable": false,
  "ignoreBudget": false,
  "excludeRecursion": false,
  "preventRecursion": true,
  "probability": 100,
  "useProbability": true,
  "depth": 0,
  "role": 0,
  "sticky": 0,
  "cooldown": 0,
  "delay": 0,
  "triggers": [],
  "uid": 0,
  "displayIndex": 0,
  "extensions": {
    "position": 4,
    "exclude_recursion": false,
    "display_index": 0,
    "probability": 100,
    "useProbability": true,
    "depth": 0,
    "selectiveLogic": 0,
    "outlet_name": "",
    "group": "",
    "group_override": false,
    "group_weight": 100,
    "prevent_recursion": true,
    "delay_until_recursion": false,
    "scan_depth": null,
    "match_whole_words": null,
    "use_group_scoring": false,
    "case_sensitive": null,
    "automation_id": "",
    "role": 0,
    "vectorized": false,
    "sticky": 0,
    "cooldown": 0,
    "delay": 0,
    "match_persona_description": false,
    "match_character_description": false,
    "match_character_personality": false,
    "match_character_depth_prompt": false,
    "match_scenario": false,
    "match_creator_notes": false,
    "triggers": [],
    "ignore_budget": false
  },
  "characterFilter": {
    "isExclude": false,
    "names": [],
    "tags": []
  }
}
```

## 分析参考卡的execute_code模板

```python
import json, os

ref_path = "/path/to/reference.json"
with open(ref_path, 'r', encoding='utf-8') as f:
    ref = json.load(f)

entries = ref.get("entries", {})
print(f"条目总数: {len(entries)}")

total = 0
for key, entry in entries.items():
    content = entry.get("content", "")
    total += len(content)
print(f"条目内容总字数: {total}")
print(f"平均条目字数: {total // len(entries)}")

# 列出所有条目
for key in sorted(entries.keys(), key=lambda x: int(x)):
    e = entries[key]
    comment = e.get("comment", "")
    content = e.get("content", "")
    constant = e.get("constant", False)
    keys = e.get("key", [])
    status = "常驻" if constant else ("禁用" if e.get("disable") else "关键词")
    print(f"  {int(key):03d} [{status}] {comment}: {len(content)}字")
```

## position值含义

| 值 | 含义 |
|---|---|
| 0 | before_main_prompt |
| 1 | after_main_prompt |
| 2 | before_char |
| 3 | after_char |
| 4 | @depth（在聊天消息中注入） |

参考卡普遍使用 `position: 4`（@depth），这意味着世界书内容被注入到聊天上下文中，而不是放在系统提示里。
