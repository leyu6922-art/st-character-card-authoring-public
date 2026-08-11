# 多视角内置角色卡设计模式（G型·✅ POC已验证）

> **状态**：2026-07-13 POC验证通过（天仙配卡）
> **验证环境**：ST v1.18 + 三人逆行预设 + MIMO-v2.5-pro
> **完整报告**：天仙配目录下 `多视角卡_动机到验证_完整报告.md`
> **当前默认**：G型生产流程默认用「选开模式」（`manual-toggle-identity-pattern.md`）。本文主要描述「Greeting 模式」备选：适合发布给完全不操作世界书 UI 的用户；自用/需中途切换身份时先读 `manual-toggle-identity-pattern.md`。

---

## 一、问题：为什么需要 G 型

### 1.1 旧模式的系统性缺陷

当前 skill 的 §3.7（NTR→NTL 转换）本质是"先生成 NTR 卡，再修改成 NTL 卡"。实证问题：

1. **AI 注意力分散**：创作完 300KB+ 的 NTR 卡后，注意力已分散到几百 KB 内容中，再做全局视角翻转几乎必然遗漏
2. **隐式视角残留无法根除**：行为模板触发条件、关系描述角度、事件叙述视角中散落的 `{{user}}`=苦主假设，不是字符串替换能清理的
3. **独立卡维护成本高**：3 张卡共享 60-70% 内容但需要 3 倍维护
4. **这是任务结构问题，不是模型能力问题**

### 1.2 G 型的核心思想

**从"分两次生成两个版本"改为"一次生成、多角色内置"**：

- 世界书零 `{{user}}`，用具体角色名
- 视角段用 selective keys 按身份选择性加载
- 玩家选 greeting = 选身份 → 对应视角条目自动加载

一张卡替代三张卡，token 预算节省 67%。

---

## 二、架构

### 2.0 共用层{{user}}清理规则（2026-07-13·示例G型卡世家G型生产级实证）

从已有NTR卡重构为G型时，共用层条目需要批量清理{{user}}引用。清理前先统计再替换：

| 条目类型 | {{user}}处理 | 理由 |
|---------|-------------|------|
| 系统常驻（OOC/状态栏/隐奸规则/反顺从） | **保留** | 描述"当前玩家行为/视角"而非世界事件 |
| 角色档案/描写库/语料库 | **替换为具体名字** | 共用层描述不绑定身份 |
| 场景/世界观/物品 | **替换为具体名字** | 客观事实不绑定身份 |
| 事件种子 | **替换为具体名字** | 事件事实用角色名描述 |
| 选开身份条目 | **保留** | `{{user}}是XXX` 定义当前玩家身份 |
| system_prompt | **保留** | 条件分支 `当{{user}}=A时→规则X` |

清理流程：`content.count('{{user}}')` 统计 → `replace('{{user}}', '具体角色名')` 批量替换 → 验证零残留。
典型规模：19文件71处替换（示例G型卡世家案例）。
**系统条目可保留{{user}}的例外必须逐条判断——只有描述"当前玩家行为/视角"的条目才保留。**

### 2.1 双层世界书结构

```
┌──────────────────────────────────────────────┐
│  共用层（所有身份都加载）                        │
│  [0] OOC防护+身份规则    (before_char, constant) │
│  [1] 文风锚点            (before_char, constant) │
│  [2] 状态栏              (@D, constant)         │
│  [3] 女性角色档案         (keyword: 角色名)      │
│  [4] 男性角色档案(中性)    (keyword: 角色名)      │
│  [5] 场景描述             (keyword: 场景词)      │
│  [6] 事件·事实段          (keyword: 事件名)      │
├──────────────────────────────────────────────┤
│  视角层（selective, 按身份选择性加载）            │
│                                                 │
│  身份 A 视角段:                                  │
│    [A1] 感官反应      selective: 身份key        │
│    [A2] 心理变化      selective: 身份key        │
│                                                 │
│  身份 B 视角段:                                  │
│    [B1] 体验描写      selective: 身份key        │
│    [B2] 互动模式      selective: 身份key        │
│  ...                                            │
└──────────────────────────────────────────────┘
```

### 2.2 世界书铁律

事件/角色/场景条目的 content 中**零 `{{user}}` 引用**。全部用具体角色名（李明、麦克、约翰）。

系统条目（OOC、状态栏）引用 `{{user}}` 是例外——描述"当前玩家"而非世界事件。

### 2.3 Selective Keys 设计

```
条目触发条件 = Primary Key 命中 AND Secondary Key 命中（AND ANY）
```

**设计原则**：
- Primary key：身份标识词（如"苦主体感""寝取者视角"）
- Secondary key：额外的身份确认词，防单 key 误匹配
- 视角段的 primary + secondary key 都必须出现在对应 greeting 文本中

**关键教训（问题 3）**：`苦主视角` ≠ `苦主体感`——字符串精确匹配，一字之差全断。构建时必须用 Python 验证：

```python
greeting_keywords = set(greeting_text.split())
entry_secondary_keys = set(e['secondary_keys'])
assert greeting_keywords & entry_secondary_keys, f"entry {e['id']} secondary keys don't match greeting"
```

---

## 三、Greeting 触发机制

### 3.1 触发链

```
Greeting文本（chat history中）
    ↓ ST每轮重扫描全文
Primary Key命中 + Secondary Key命中
    ↓ selective AND逻辑
视角段条目加载到 <Lore>
```

### 3.2 Greeting 格式规范

```
【▎身份：XXX｜视角描述】 key1 key2 key3

（正文内容...）
```

示例：
- 苦主：`【▎身份：苦主·李明｜丈夫视角｜NTR体验】 苦主体感 李明体感`
- 麦克：`【▎身份：寝取者·麦克｜征服者视角｜NTL体验】 寝取者视角 麦克体感 征服者视角`
- 约翰：`【▎身份：寝取者·约翰｜掠夺者视角｜NTL体验】 约翰视角 约翰体感 掠夺者视角`

### 3.3 多轮维持

Greeting 始终在 chat history 中 → ST 每轮重新扫描 → 视角段持续加载。

**后备机制**：OOC 条目录入指示 AI 在回复中自然使用身份关键词（"苦主体感""寝取者视角"等）→ 即使 greeting 在超长会话中被截断，AI 回复中的关键词也可触发视角段。

---

## 四、构建规则（生产环境）

### 4.1 条目设置

```python
# 视角段条目模板
{
    "constant": false,
    "selective": true,           # ← 关键
    "prevent_recursion": true,   # 防跨视角污染
    "keys": ["苦主体感", "李明体感", ...],       # primary keys
    "secondary_keys": ["苦主体感", "苦主视角"],   # 至少包含greeting中出现的全部变体
    "position": 0,               # before_char
    "enabled": true
}
```

### 4.2 构建检查清单

| # | 检查项 | 方法 |
|---|--------|------|
| 1 | 事件/角色/场景条目零 `{{user}}` | grep 全卡 content |
| 2 | 每个 greeting 首行含全部身份key | 肉眼 + Python 验证 |
| 3 | 视角段 secondary_keys 与 greeting 关键词有交集 | Python: `greeting_keywords & entry_secondary_keys` |
| 4 | 共用层：系统条目 constant=true, keys=[] | validate_card.py check 26 |
| 5 | 视角段：constant=false, selective=true, keys非空 | 逐条检查 |
| 6 | 每个视角段至少 2 条（1 条感官 + 1 条心理） | 人类判断 |
| 7 | `prevent_recursion: true` 全部条目 | validate_card.py |

### 4.3 导入说明（必须交付给用户）

```
1. 导入JSON到ST
2. ⚠️ 在ST中执行「导入卡片世界书」——将嵌入的character_book绑定到角色
   （跳过此步 = 世界书完全不加载 = <Lore>为空）
3. 选择对应greeting启动会话
4. 🔍 验证：生成后打开消息「...」菜单 → 「提示词拆分」→ 检查<Lore>是否含视角段条目
5. 可选：安装扩展 WorldInfoInfo 查看已激活条目列表
```

---

## 五、已验证的架构事实

| 验证项 | 方法 | 结果 |
|--------|------|:--:|
| 共用层 4 条全部身份加载 | API请求 `<Lore>` 检查 | ✅ |
| 视角隔离（苦→[A], 麦→[B], 约→[C]，零交叉） | 3次独立会话对比 | ✅ |
| 多轮维持（4轮连续对话） | 每轮API请求检查 | ✅ |
| Greeting触发优于before_char递归 | 源码审查 + POC实测 | ✅ |
| Token Budget=0 ≠ 禁用世界书 | Codex源码审查 | ✅ |
| 世界书导入到角色是必须步骤 | POC实测 | ✅ |

### 已验证的"不可行"

- ❌ 依赖 before_char 常驻条目内容触发视角段——ST 不二次扫描已插入条目
- ❌ Selective key 用 greeting 中不存在的词——AND 逻辑下 secondary 不匹配 = 不加载

---

## 六、适用边界

| 场景 | 用 G 型 | 用旧方法 |
|------|:--:|:--:|
| 小说有明确苦主+NTL角色，双方都可玩 | ✅ | ❌ |
| 小说只有 NTL 视角（`{{user}}` 天生征服者） | ❌ 过度设计 | C 型 |
| 已有 NTR 卡，只要 NTL 版 | ❌ 推倒重来浪费 | §3.7 转换 |

---

## 七、Token 效率

| 方案 | 条目数 | token 预算 | 维护成本 |
|------|:--:|------|------|
| 三张独立卡 | ~120 条 | ~960KB | 3× |
| 一张 G 型卡 | ~45 条（共用25+视角20）| ~320KB | 1× |

节省 67%。随可扮演角色增加，效率优势更明显。

---

*创建时间：2026-07-13 · POC验证完成后*
*关联文件：`st-worldbook-triggering-behavior.md`、天仙配目录下完整POC报告*
