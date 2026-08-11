# Final delivery gate 二轮返修经验（2026-07-16）

适用场景：修改/审查 `validate_card.py`、`enrichment_self_check.py`、`check_build_sync.py`、`final_delivery_gate.py`，或把做卡经验沉淀成自动门控。

## 1. Gate 设计原则

- `final_delivery_gate.py` 是裁判，不是修复器：只聚合、报告、给 exit code，不自动改卡。
- fixture 通过不等于真实卡可用；每次扩 gate 后至少跑：
  - 1 张 G 型真实卡；
  - 1 张非 G 型真实卡；
  - 1 张含 build/assemble 链路的真实卡；
  - good/bad fixture。
- 真实卡误杀必须优先降级/收窄，不要为了“强门控”制造大量无关黄项。

## 2. check_build_sync.py 安全规则

真实项目常见 assemble 位置：

```text
project_dir/assemble_card.py
project_dir/build/assemble_card.py
project_dir/build_data/assemble_card.py
```

必须同时识别。执行 assemble 时：

1. 不要在原项目目录直接运行；很多旧脚本忽略 argv，会直接覆盖最终 JSON。
2. 先复制项目到临时目录，再在临时目录运行 assemble。
3. 默认不要把 `_gate_rebuild.json` 留在项目根目录；只有显式 `--keep-rebuild` 才保存。
4. 如果只比对了 `build/all_entries.json`，但没有真正验证 assemble，状态应为 WARN/Notes，不应伪装成完整 PASS。
5. 如果 assemble 含绝对路径或疑似固定输出到原项目，跳过执行并 WARN。

## 3. R18 空壳检查：词表 + 分级

本制卡流程默认都是 NSFW/R18 卡，因此 `final_delivery_gate.py` 默认启用 R18 检查；只有审普通/非NSFW世界书时才加 `--no-r18`。直接运行 `enrichment_self_check.py` 时仍用 `--r18` 显式启用。不要把 R18 检查扩展到 OOC/系统/状态栏等非素材条目。

必须识别的链条词：

- 动作链：插入、顶住、抵住、摩擦、套弄、含住、舔、吻、顶入、抽插、射、内射、压上去、撞击、推进。
- 身体链：龟头、肉壁、小穴、阴道、乳房、乳尖、下腹、湿润、紧致、包裹、颤栗、内壁、体液、精子。
- 语言链：`「」`、`“”`、单引号、英文引号、说道、低声、喘着、求你、不要、继续、呢喃、哀求。
- 阶段链：第一次、突破、堕落跃迁、事后、临界点、终点、成功、失败、半成功、代价、反噬。

分级原则：

- 核心角色 / NTR关系：空壳可红。
- 明确 R18 肉戏事件：空壳可黄或红，视是否缺动作/身体链。
- 纯心理/机制/苦主崩溃事件：不要强当 R18 肉戏素材。
- 场景氛围库 / 描写库：链条不足最多黄；除非全卡没有任何强 R18 素材，才用全卡级红项。

## 4. G 型三路径检查要收窄

G 型是多视角架构，不等于守护卡。不要因为 `--prototype G` 就要求所有 disabled 事件种子都有成功/失败/半成功。

推荐规则：

| 原型/模式 | 三路径门控 |
|---|---|
| B/D/守护 | hard |
| C/攻擂/成长 | soft |
| G | auto：只对明确守护、破局、救援、反杀、争夺、保护、营救、拯救类事件 soft |
| A/E | none |

提供参数：

```bash
--three-path auto|hard|soft|none
```

注意：`无力阻止`、`身体攻防` 这类普通 NTR 叙述不应触发 G 型三路径检查。

## 5. residue scan 必须解析 JSON 字符串

只扫 raw JSON 会漏掉字符串里的代码残留。应先 `json.loads()` 后递归收集所有字符串并优先扫描 decoded strings；raw 仅作 JSON 解析失败或非法转义兜底，避免 raw+decoded 双重计数。

至少扫描：

- `# -*- coding`
- `import json`
- `event_x =`
- `def make_entry`
- 三引号 `"""` / `'''`
- `pad_to`
- `TODO` / `PLACEHOLDER`
- `[U+XXXX]`
- `print(`

命名要准确：默认报告名用 `localization/residue scan`；年龄/校园词、社区平台敏感词默认不报警。发布专项必须提供 `--publish-text <简介.md>`，再加 `--strict-platform` / `--strict-age` 才扫描简介/帖子文案；卡 JSON 不参与平台扫描。

## 6. validate_card.py CLI

`validate_card.py` 不能只有函数入口。必须支持：

```bash
python scripts/validate_card.py <card.json>
```

输出：

```text
passed=False
errors=N
warnings=N
```

exit code：

- `1`：有 errors；
- `2`：只有 warnings；
- `0`：无 errors/warnings。

否则低阶模型容易“运行了 validate_card.py 但静默 exit 0”，形成假验证。

## 7. 真实卡回归判据

二轮修复后的期望：

- 黑绿足球 G 型：不再出现 `R18空壳[场景氛围描写库]`，不再大面积 `缺三路径`；可为 exit 2（仅 warning）。
- 周雨晴 E 型：R18 事件不再误杀；`build/assemble_card.py` 应在临时目录验证，build sync PASS。
- 绿冠星空：若存在代码残留，应由 residue scan 直接 FAIL，而不是靠 R18 黄项间接失败。
