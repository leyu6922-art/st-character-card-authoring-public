# Final Delivery Gate 工程化经验（2026-07-16）

用于 `scripts/final_delivery_gate.py` / `check_build_sync.py` / `validate_card.py` / `enrichment_self_check.py` 的维护与审查。目标是把“validate 通过≠可交付”的经验脚本化，防止轻量模型口头宣布完成。

## 1. 落地原则

- 少改 `SKILL.md`：只放短硬提示和入口命令，不继续堆长文档。
- 优先扩展现有脚本：`validate_card.py` / `audit_worldbook_triggers.py` / `enrichment_self_check.py` 已覆盖大量规则，新增检查应先判断能否并入现有脚本。
- 只新增两个独立脚本：
  - `check_build_sync.py`：构建链路同步属于独立维度，适合单独脚本。
  - `final_delivery_gate.py`：聚合器，只判定不修复。
- 任何模型自述“完成”都不能作为事实；必须以脚本输出、报告路径、exit code 为准。

## 2. Gate 语义与交付话术

`final_delivery_gate.py <card.json> --project-dir <dir> [--prototype G]` 是判定器，不是修复器。R18 内容密度门控在本 NSFW 制卡流程中默认开启；只有审普通/非NSFW世界书时才加 `--no-r18`。Discord/社区只审发布简介/帖子文案，不审卡 JSON；发布专项需要时传 `--publish-text <简介.md> --strict-platform`，未成年词汇专项再加 `--strict-age`。

| exit | 含义 | 交付解释 |
|---:|---|---|
| 0 | 全部硬门控通过且无 warning | 可交付 |
| 1 | 有 error / 红项 / build 不同步 / 残留硬风险 | 不可交付，必须返修 |
| 2 | 仅 warning | 可人工确认，不等于完全通过 |
| 3 | gate 自身异常 | 门控无效，先修脚本/路径 |

**关键话术**：`exit=2` 只能写“硬门控通过，仍需人工确认 warning 是否可接受”，不能让模型口头翻译为“完全通过”。

## 3. `validate_card.py` 适合承载的门控

适合放入 validate 的检查：

- 开场白结构：段落数、一整段密集文本、截断尾巴、未闭合引号/括号、重复补字。
- G型选开结构：选开身份条目必须 `constant=true + enabled=false + keys=[]`。
- G型选开 greeting 中性：
  - 明确身份锁死句（如“你作为苦主/征服者/守护者”）→ error。
  - 疑似身份锁死短语（如“你的妻子/你本该/你刚放学”）→ warning，需人工确认。

注意：段落数不足和密集文本通常是 warning；截断尾巴、明确身份锁死、选开 keys 非空应是 error。

`validate_card.py` 必须支持 CLI：

```bash
python scripts/validate_card.py <card.json>
```

输出 `passed/errors/warnings`，退出码：

- `0`：无 error / warning
- `1`：有 error
- `2`：仅 warning

禁止出现“直接运行静默 exit 0”的状态，否则轻量模型容易假执行。

## 4. `enrichment_self_check.py` 适合承载的门控

适合放入 enrichment 的检查：

- R18内容空壳：final gate 默认启用；直接运行 `enrichment_self_check.py` 时用 `--r18` 启用。只有普通/非NSFW世界书才在 final gate 加 `--no-r18`。
- 检查对象只限核心素材：核心角色、NTR关系、明确 R18 事件种子、描写库、语料库、关键场景；不要检查 OOC/系统/状态栏。
- 判断“抽象规则 vs 可复用素材”，不要只数敏感词。可复用素材至少看五类链条：动作链、语言链、身体反应、场景链、阶段链。
- 黄项策略保持弹性：🔴 必须为 0；🟡 ≥3 默认不可交付；1～2 个 🟡 可人工解释后交付。

### R18 词链与误杀防线

已验证需要覆盖的词链：

- 动作链：插入、顶住、抵住、摩擦、套弄、含住、舔、吻、顶入、抽插、射、内射、压上去、撞击、推进等。
- 语言链：`「」`、`“”`、单引号、英文引号、说道、低声、喘着、求你、不要、继续、哀求等。
- 身体反应：龟头、肉壁、小穴、阴道、乳房、乳尖、湿润、紧致、包裹、颤栗、内壁、体液、精子等。
- 阶段链：堕落跃迁、突破、第一次、事后、临界点、终点等。

误杀教训：

- “第一次插入 / 繁殖play”这类事件如果有动作、身体、语言、阶段，不得判为 0 类链条。
- 场景氛围库 / 描写库链条不足最多给黄项；核心角色、NTR关系、明确 R18 事件种子才可因空壳直接红。
- 心理/机制事件不应被强行当成 R18 肉戏素材。

### G型三路径不要泛化

G型是多视角架构，不等于守护卡。不要因为 `--prototype G` 就要求所有事件种子都有成功/失败/半成功。

推荐逻辑：

| 原型/模式 | 三路径门控 |
|---|---|
| B / D / 明确守护 | hard |
| C / 攻擂 / 成长 | soft |
| G | auto：只对含守护、破局、救援、反杀、争夺、保护、营救、拯救等攻防语义的事件 soft |
| A / E / 普通世界书 | none |

需要更宽检查时由人工显式传 `--three-path soft`，不要默认扩大。

## 5. `check_build_sync.py` 设计规则

`check_build_sync.py` 必须覆盖真实项目常见结构：

- `project_dir/build/all_entries.json`
- `project_dir/assemble_card.py`
- `project_dir/build/assemble_card.py`
- `project_dir/build_data/assemble_card.py`

规则：

1. assemble 脚本不得直接在原项目目录执行，必须复制到临时目录运行。
2. 默认不保留 `_gate_rebuild.json`，只有 `--keep-rebuild` 才保存。
3. 如果只比对了 `all_entries.json`，但没有运行 assemble，状态应为 `WARN`，不能假装完整 `PASS`。
4. 若 assemble 脚本疑似含绝对 JSON 输出路径，跳过执行并 warning，避免覆盖原卡。
5. PASS 必须代表：entries 源一致 + 临时目录 assemble 重组一致 + 重组卡 validate 通过。
6. 无 build 链路 → `N/A`，不直接失败；项目声明 file-first 但缺 build 链路时才用 `--require-build` 判失败。

## 6. 残留扫描归因

默认 `localization/residue scan` 应递归扫描 JSON 字符串内容，至少抓：

- `# -*- coding` / python 编码声明残留
- `import json`
- `event_x =` / 变量赋值残留
- `def make_entry`
- 三引号 `"""` / `'''`
- `pad_to`
- `TODO` / `PLACEHOLDER`
- `[U+XXXX]`
- `print(` 调试残留

年龄/校园词和社区平台敏感词不是卡本体风险项；`--strict-age` / `--strict-platform` 只扫描 `--publish-text` 指向的发布文案。未提供发布文案时跳过专项扫描；卡 JSON 不参与 Discord/社区审核。

注意：如果同时扫描 raw JSON 和 decoded strings，命中数量可能翻倍；数量只作参考，是否命中才是核心。优先考虑扫 decoded strings，raw 仅作非法转义/解析失败兜底。

## 7. 回归要求

新增或修改 gate 时必须有两层回归：

1. 最小 fixture：good/bad 小卡，覆盖开场白截断、G型身份锁死、选开 keys 非空、R18空壳、R18富素材、G普通事件不触发三路径、NTR关系薄、嵌套 build、build不同步、代码残留。
2. 真实卡回归：至少跑一张 G型、一张非G型、一张曾经出过问题的旧卡。

报告时必须给：命令、exit code、报告路径、PASS/FAIL/WARN摘要。不要只说“应该能跑”。

可信回归样例：

- 黑绿足球 G型：`exit=2`，R18空壳误杀和 G型三路径误杀消失；剩余为 warning，需人工确认。
- 周雨晴 E型：`exit=2`，R18事件误杀消失，build/assemble 临时重组 PASS。
- 绿冠星空 A-N：`exit=1`，代码残留 FAIL 可信（python编码声明、event变量、三引号等）。

## 8. 常见坑

- Python `dataclass` 动态导入脚本时，如果用 `importlib.util.module_from_spec()`，执行前要 `sys.modules[name] = mod`，否则 dataclass 可能报 `'NoneType' object has no attribute '__dict__'`。
- fixture 不要用“威胁档案”等会被触发审计当核心档案的词，除非这是刻意构造的坏例；否则会污染正例。
- 真实旧卡被 gate 判 `exit=1` 不一定代表新 gate 误杀；先看是新增检查导致，还是既有 `enrichment_self_check.py` 的黄项≥3/红项规则导致。
- `shutil.copytree(project_dir, tmp_root)` 对大目录可能慢；必要时优化为只复制 build、assemble、greeting、json 和必要源 txt。
- 不要继续堆 SKILL.md 长文；复杂细节放本 reference，SKILL.md 只保留入口和硬语义。
