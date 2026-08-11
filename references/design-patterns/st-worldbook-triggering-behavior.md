# ST 世界书触发机制实测文档

> **状态**：2026-07-13 实测（天仙配POC + Codex源码审查）
> **ST版本**：v1.18
> **验证方法**：API请求 `<Lore>` 检查 + Codex源码审查（world-info.js, index.html）

---

## 一、核心发现

### 1.1 ST 不二次扫描已插入的条目内容 ❌

**最重要的发现**：ST 的世界书扫描范围是 **chat history**（greeting + 用户消息 + AI 回复），**不包括已插入 prompt 的条目内容**。

这意味着：
- before_char 常驻 OOC 条目内容中的关键词 → **不会触发**其他世界书条目
- 只有 greeting 和用户/AI 消息中的关键词才能触发条目

**POC 验证**：OOC 条目录入中写了"苦主视角""寝取者视角"等关键词 → 即使在 `<Lore>` 中可见，也没有触发对应的视角段条目。

**结论**：触发关键词必须出现在 greeting 文本或用户/AI 消息中。不能依赖"在 OOC 条目里写关键词 → 递归触发视角段"的链条。

### 1.2 Selective / Secondary 逻辑：有副词时才进入 AND 判断

ST v1.18 源码逻辑（`world-info.js`）：

```text
先匹配 primary key；primary 不命中 → 不触发
若 entry.selective=true 且 keysecondary 非空 → 按 selectiveLogic 判断 secondary
若 selective=false 或 keysecondary=[] → primary-only 触发
```

默认 `selectiveLogic=0 (AND_ANY)`：primary key 任意一个命中 + secondary key 任意一个命中 → 条目加载。

**关键细节**：
- `selective=true` 但 `secondary_keys=[]` 不是死触发，会退化为 primary-only。大型结构化卡大量唯一专名条目就是这种模式。
- ST 读取的是**顶层** `selective` 字段；`extensions.selective` 单独为 true 不会启用 secondary AND 逻辑。
- 对 G 型 greeting 身份隔离，仍建议视角段必须有 secondary key，并与 greeting 首行精确对齐。

**POC 关键教训**：`苦主视角` ≠ `苦主体感`。Greeting 中有 `苦主体感`，但 entry 的 secondary key 是 `苦主视角` → 不匹配 → 条目不加载。

**修复**：secondary key 必须包含 greeting 中实际出现的全部变体词。

### 1.3 世界书必须导入绑定到角色 ⚠️

ST 对嵌入 lorebook 的逻辑：
1. 角色卡 JSON 中有 `data.character_book` → ST 提示"导入卡片世界书"
2. 用户执行导入 → World Info 保存 + **绑定到角色**
3. 未执行导入 → `getCharacterLore()` 找不到角色世界书 → `<Lore>` 只有角色基础字段

**POC 验证**：卡 JSON 有 11 条 `character_book.entries`，但未导入时 `<Lore>` 为空。导入后立即出现。

**注意**：`data.extensions.world` 为空 ≠ 世界书不存在。嵌入世界书存储位置在 `data.character_book`。

---

## 二、ST 机制确认（Codex 源码审查）

| 机制 | 行为 | 源码依据 |
|------|------|------|
| **扫描范围** | 默认扫描当前对话内容（chat history）。角色描述/persona 等不是默认扫描源（需在条目上启用 Additional matching sources） | world-info.js |
| **Key 匹配** | 默认不区分大小写；支持 JavaScript regex | world-info.js |
| **Selective/Secondary** | Primary 必须命中；仅当顶层 selective=true 且 secondary 非空时按 selectiveLogic 判断 secondary；secondary 空则 primary-only | world-info.js |
| **Recursive Scan** | 已激活条目内容可触发其他条目，前提：触发条目 `prevent_recursion=false` + 目标条目未被 `Non-recursable` 排除 + 全局 `Recursive Scan=ON` | world-info.js |
| **Token Budget** | `Context% × maxContext` 计算预算。`Budget Cap > 0` 时截断超预算条目。constant 条目优先 | world-info.js |
| **Budget Cap=0** | **取消预算上限**，不是禁用世界书。报告中的"Token Budget=0禁用世界书"判断不成立 | index.html |

---

## 三、推荐设置

### POC/测试

```
Scan Depth: 2
Context %: 2-5
Budget Cap: 3000-6000（或 0=不限）
Recursive Scan: ON（测试用，生产可选）
```

### 生产环境

```
Scan Depth: 2
Context %: 3-5（按实际 context 大小调整，~270K context 时 1%已约2700 tokens）
Budget Cap: 0（不设上限，让 Context% 自然控制）
Recursive Scan: OFF（避免意外链式触发）
```

---

## 四、G 型多视角卡的触发方案

### 有效方案 ✅：Greeting 直接触发

```
Greeting 首行：【▎身份：XXX】 key1 key2 key3
    ↓ ST扫描greeting全文
视角段 selective: primary(key1) + secondary(key2)
    ↓ AND 逻辑匹配
条目加载到 <Lore>
```

每轮：greeting 在 chat history 中 → ST 重新扫描 → 条目持续加载。

### 无效方案 ❌：before_char 递归触发

```
OOC条目(before_char, constant):
  content: "AI应使用关键词「苦主体感」"
      ↓ prevent_recursion=true → 不会递归触发
视角段条目不加载 ❌
```

**即使 `prevent_recursion=false` 且 `Recursive Scan=ON`，也不推荐此方案作为主路径。** 原因：
1. 递归触发链控制复杂，容易 token 爆炸
2. 多条 sequential 依赖降低可靠性
3. Greeting 直接触发更简单、更可控

### 后备维持方案（长期会话）

```
OOC条目指令: "AI在回复中自然使用身份关键词"
    ↓ AI回复中出现"苦主体感"
    ↓ 下一轮 ST 扫描 chat history
视角段条目加载 ✅
```

用于超长会话（>50 轮）中 greeting 可能被截断的情况。

---

## 五、激活状态查看

ST 原生无"已激活条目列表"面板。查看方法：

1. **方法 A（推荐）**：生成后点消息 `...` 菜单 → `提示词拆分（Prompt Itemization）` → 查看 `<Lore>` 段
2. **方法 B**：直接看实际 API 请求中的 `<Lore>` 段（最底层证据）
3. **方法 C**：安装扩展 [SillyTavern-WorldInfoInfo](https://github.com/LenAnderson/SillyTavern-WorldInfoInfo)

---

## 六、常见坑点

| 坑 | 现象 | 修复 |
|----|------|------|
| 世界书未导入 | `<Lore>` 只有角色基础字段 | ST 中"导入卡片世界书" |
| secondary key 不匹配 | 有 secondary 的 selective 条目不加载 | Python 验证 greeting/chat ∩ secondary_keys；注意 secondary 空会 primary-only |
| prevent_recursion 全局 true | OOC 条目内容不触发其他条目 | 依赖 greeting 触发，不依赖递归 |
| Budget Cap=0 误认为禁用 | （不是坑，只是误解） | Budget Cap=0 = 取消上限 |
| constant 条目 keys 非空 | 额外触发条目 + token 膨胀 | constant=true → keys=[] |
| 中文卡 match_whole_words=true | 所有中文关键词匹配失败（Python `\W` 不匹配CJK字符） | 所有条目 `match_whole_words=false`（T93，2026-07-17 道家仙子美母实证） |
| 阶段条目 key 只写内部自然词 | 冷启动 greeting 能触发，但长对话/自然推进后，`当前阶段：P2`、`P2 新赌约`、`三男加入` 等内部词很少再出现在聊天记录，阶段条目掉出扫描范围后不再加载 | 跨预设稳定方案：不要依赖 AI 状态栏/story_record/多源聊天锚点。使用 **Author's Note 单一权威源**：AN 中只保留一行 `ROUTE_STAGE=P#`；阶段主条目 primary key 只认对应 `ROUTE_STAGE=P#`；阶段依赖条目的 secondary key 也只认对应 `ROUTE_STAGE=P#`；Quick Reply 只能作为可选配套，用 `/note ROUTE_STAGE=P#` 覆盖 AN；阶段 sticky 保持 0；不要伪装自动推进，阶段切换由用户/AN 控制。 |

---

*创建时间：2026-07-13 · POC验证完成后*
*最后更新：2026-07-17 · 新增中文match_whole_words坑（T93）*
*关联文件：`multi-perspective-card-design.md`、天仙配目录下完整POC报告*
