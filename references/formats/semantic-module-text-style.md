# 语义模块纯文本规范：`semantic_markdown_v1`

## 目的

本规范只约束**模型可见的纯文本正文**：Markdown 层级、模块专属章节、字段顺序和可读边界。它不负责变量、MVU、状态栏、运行时投影或知识状态；这些由 `semantic-module-manifest` 与现有语义门控负责。

## 四层分离

```text
text_profile       = 正文怎么排版
content_schema     = 这一类模块写哪些章节
contract_profile   = 项目怎样处理事实、候选、知识和玩家代理
runtime_projection = 运行时怎样加载条目
```

不要把四层内容塞进同一个万能模板。正文可以使用中文 Markdown；`module_type`、`content_schema` 等工程字段应保存在 manifest，由构建器按需生成，作者源文件不应手写重复元信息。

## 正文规则

1. 每个模块只能有一个 `#` 一级标题，并且必须是第一个非空行。
2. 主要章节使用 `##`，条件或子场景使用 `###`；不得使用四级以上标题。
3. 章节标题使用中文；英文只用于 manifest 中稳定的类型 ID。
4. 允许 `- **字段：**内容` 这种 Markdown 字段。禁止依赖精确缩进才能解释的 YAML 式数据树；若内容需要机器解析，应写入 manifest。
5. 普通正文不混用 XML、YAML、表格化数据库和自定义标签作为第二套主语法。
6. 条件化行为应写成“优先关注→常见反应→可替代反应”，不得写成所有场景都必须执行的固定步骤。
7. `不应误写` 只写本模块特有边界；全局禁令放在公共合同中。
8. `可开放变化` 必须写当前模块自己的变化轴，不能复制空泛的通用句。

## 模块写法

### 角色身份

`条目作用 → 核心身份锚点 → 关系与公开状态 → 不应误写 → 可开放变化`

身份模块只负责稳定身份、公开关系和当前可见状态；心理倾向、语言样例和关系变化分别交给对应模块。

### 角色心理

`条目作用 → 核心锚点 → 触发与响应 → 不应误写 → 可开放变化`

心理模块可以解释倾向，不能决定事件已经发生，也不能替玩家完成选择。

### 角色语言

`条目作用 → 基础语气 → 对象差异 → 语言样例 → 不应误写 → 可开放变化`

语言样例是可调用锚点，不是固定台词剧本。

### 地点

`条目作用 → 地点定位 → 空间布局 → 自然入口 → 现实规则 → 不应误写 → 可开放变化`

地点应说明进入、停留、观察、退出和被打断的现实条件。

### 互动机制

`条目作用 → 机制定位 → 前置条件 → 自然入口 → 执行流程 → 失败与偏离 → 不应误写 → 可开放变化`

机制必须包含拒绝、打断、条件不足和部分成功等偏离路径。

### 关系

`条目作用 → 关系锚点 → 当前状态 → 变化条件 → 不应误写 → 可开放变化`

完整知识状态只能有一个权威来源；其他模块只写局部依赖，不复制整份信息边界。

## 作者版与运行时版

作者源文件可以保留关联模块、审计说明和完整边界；运行时投影可以删除纯工程信息，只保留模型需要的锚点、条件、差异和局部红线。两者不能互相伪装：源文件负责维护，运行时正文负责生成。

## Manifest 接线

```json
{
  "text_profile": "semantic_markdown_v1",
  "module_records": {
    "角色/示例角色/核心心理与性格": {
      "module_type": "character_psychology",
      "content_schema": "character_psychology_v1",
      "contract_profile": "open_semantic_module_v1"
    }
  }
}
```

`module_type` 必须与 `content_schema` 匹配；文本审计会拒绝错配。现代模块还必须满足 `comment` 路径与 `module_type` 的命名空间映射：`角色/.../基础信息与关系锚点 → character_identity`、`角色/.../核心心理与性格 → character_psychology`、`角色/.../语言与称谓 → character_language`、`世界观/地点/... → place`、`机制/互动机制/... → interaction_mechanism`、`关系/... → relationship/character_relationship`。正式模块路径使用 `角色`、`世界观`、`关系`、`机制` 等命名空间。

开放路线锁定检查不把所有互动机制自动视为事件；当模块的 manifest record 或 projection 将 `runtime_role` 标记为 `event_candidate` 时，`open_sandbox` 下才执行 `OPEN_ROUTE_LOCKED` 检查。

`contract_profile` 不由文本审计器解释。当前 `module_records` 是声明式迁移范围：未登记的旧条目继续由旧语义门控处理，不会被本层静默判定为通过。运行：

```bash
python scripts/audit_semantic_text.py card.json --manifest build/semantic-module-manifest.json
```

未声明 `text_profile` 的旧卡会跳过本层审计，不改变既有兼容行为。
