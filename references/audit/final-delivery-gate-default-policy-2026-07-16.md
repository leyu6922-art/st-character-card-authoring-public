# Final Delivery Gate 默认策略（2026-07-16）

用于维护 `scripts/final_delivery_gate.py` 以及后续制卡交付审查。该文件记录本次会话沉淀的**默认门控策略**，避免后续模型把平台专项规则误当成普通酒馆卡交付红线。

## 1. 成品卡默认位置

用户做完的卡通常归档到：

```text
<PROJECT_DIR>/archive/\
```

审查旧卡或重跑 gate 时，先以用户当前给出的实际路径为准；若用户没给路径，再优先在 `归档` 下搜索成品 JSON。旧报告里若仍写 `未发合集` 等路径，视为历史报告路径，不作为当前卡位置事实。

## 2. R18 / NSFW 是默认要求

本用户的 SillyTavern 制卡任务默认都是 NSFW/R18 卡。`final_delivery_gate.py` 应默认启用 R18 内容密度门控：

```bash
python scripts/final_delivery_gate.py <卡.json> --project-dir <项目目录> [--prototype G]
```

只有审普通/非 NSFW 世界书时才显式关闭：

```bash
python scripts/final_delivery_gate.py <卡.json> --project-dir <项目目录> --no-r18
```

不要把 R18 检查当作额外可选项而忘跑；用户反馈“不色/没肉文感/只有规则没有过程”时，R18 素材链条检查是核心门控。

## 3. 未成年词汇默认不是卡本体阻塞项

年龄、年级、校园词（如 `高一`、`初中`、`未成年` 等）在普通酒馆/虚构角色卡交付中**默认不报警、不阻塞**。用户已明确：社区主要审发布简介/帖子文案；卡 JSON/世界书/开场白不受这些词影响，且角色年龄小于18岁本身不是问题。

只有发布文案专项严格审核时才启用，并且必须提供简介/帖子文件：

```bash
--publish-text <discord简介.md> --strict-age
```

该模式只扫描发布文案中的幼女/萝莉/未成年等词汇；不扫描卡 JSON，也不因角色年龄小于18岁而阻塞。

## 4. 社区平台敏感词默认不是普通卡阻塞项

`萝莉`、`幼女`、`童贞`、`loli`、`未成年` 等未成年/儿童化词只在发布文案专项审核时扫描；普通本地 ST 卡审查默认不因这些词 FAIL。非未成年向 NSFW 词不作为本社区默认平台阻塞项。

平台专项命令：

```bash
--publish-text <discord简介.md> --strict-platform
```

该模式只用于 Discord/社区简介、帖子正文、标题、标签等发布文案；不要默认套到成品卡 JSON。Discord/社区不审卡内世界书/开场白/JSON，卡创作不受小说原文词汇影响。

## 5. 默认仍必须扫描残留

默认 gate 仍必须扫描构建/代码/本地化残留，例如：

- `# -*- coding` / `import json`
- `event_x =` / `def make_entry`
- 三引号 `"""` / `'''`
- `pad_to` / `TODO` / `PLACEHOLDER`
- `[U+XXXX]` / `print(`

这些属于卡自身质量问题，默认应阻塞或警告。

## 6. 报告解释口径

- `exit=0`：可交付。
- `exit=1`：不可交付，必须修。
- `exit=2`：硬门控通过但仍有 warning，需人工确认；不能被模型翻译成“完全通过”。
- `exit=3`：gate 自身异常，先修脚本/路径。

当用户要求“审查旧卡”时，报告必须区分：

```text
真实旧卡问题 / gate误杀 / gate漏检 / 归因不准
```

不要只根据 `exit=1` 直接判旧卡彻底失败。
