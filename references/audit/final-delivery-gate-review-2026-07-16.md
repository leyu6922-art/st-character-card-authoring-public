# Final Delivery Gate 二轮审查经验（2026-07-16）

> 适用场景：扩展 `validate_card.py` / `enrichment_self_check.py` / `check_build_sync.py` / `final_delivery_gate.py`，或用 gate 审查旧卡时。核心结论：工程化门控方向正确，但 fixture 能过不等于真实卡可用；真实卡回归必须检查误杀、漏检和归因是否准确。

## 1. Gate 状态分级

- **工程骨架通过**：新增聚合器、build sync、fixture 能跑，说明方向正确。
- **生产级暂缓**：只要真实卡出现误杀/漏检/归因不准，就不能把 gate 当最终硬判据。
- **过渡期用途**：作为审查辅助工具；不可单独用“exit=1”判旧卡必定不可交付，必须读报告原因。

## 2. `check_build_sync.py` 必须安全处理真实 build 结构

真实项目常见结构不止一种：

```text
项目目录/assemble_card.py
项目目录/build/all_entries.json
项目目录/build/assemble_card.py
项目目录/build_data/assemble_card.py
```

硬规则：

1. 同时检测 `project_dir/assemble_card.py`、`project_dir/build/assemble_card.py`、`project_dir/build_data/assemble_card.py`。
2. 不要在原项目目录直接运行可能有副作用的 assemble 脚本。许多旧脚本会忽略 argv，直接覆盖最终 JSON。
3. 优先复制项目到临时目录后运行 assemble；或静态检测脚本确实支持输出参数后再运行。
4. 默认不要在项目根目录留下 `_gate_rebuild.json`；仅 `--keep-rebuild` 时保留。
5. 如果只比较了 `all_entries.json`、没有实际重组验证，状态不要简单写 PASS；至少在 Notes/WARN 明确“未验证 assemble”。

## 3. R18 空壳检查要避免真实卡误杀

`--r18` 是启发式，不是色情词计数。不要因为单个场景/氛围条目没有覆盖四类链条就直接红。

### 词表必须覆盖常见中文肉文表达

动作链补充：`插入`、`顶住`、`抵住`、`摩擦`、`套弄`、`含住`、`舔`、`吻`、`抱`、`顶入`、`抽插`、`射`、`内射`、`压上去`。

身体链补充：`龟头`、`肉壁`、`小穴`、`阴道`、`乳房`、`乳尖`、`下腹`、`湿润`、`紧致`、`包裹`、`颤栗`。

语言链补充：除 `「」` 外，还要识别 `'...'`、`"..."`、`说道`、`低声`、`喘着`、`求你`、`不要`、`继续`。

阶段链补充：`堕落跃迁`、`突破`、`第一次`、`事后`、`临界点`、`终点`。

### 条目类型分级

| 条目类型 | 空壳严重度 |
|---|---|
| 核心角色 / NTR关系 / 事件种子 | 可判红 |
| 场景氛围库 / 描写库 | 最多黄，除非全卡没有任何强 R18 素材 |
| 系统 / OOC / 状态栏 | 豁免 |

回归样本应包含真实卡片段：周雨晴 `事件·第一次插入`、`事件·繁殖play` 不应被判为“0类链条”；黑绿足球 `场景氛围描写库` 不应单条判红。

## 4. G型不等于三路径事件卡

不要把 `--prototype G` 直接等同于“三路径事件种子”。G型只是多视角架构，不代表每个事件都要有成功/失败/半成功。

推荐门控：

| 原型/语义 | 三路径门控 |
|---|---|
| B型守护 / D型守护觉醒 | hard |
| C型攻擂/成长线 | soft |
| G型 | `auto`：只对明确 `守护/破局/救援/反杀/争夺/保护/营救/拯救` 类事件 soft；普通 G 型事件不检查三路径 |
| A型/E型 | 默认 none |

可新增参数：`--three-path hard|soft|none|auto`，让 gate 调用时显式控制。

## 5. `final_delivery_gate.py` 的扫描名实一致

默认报告项应叫 `localization/residue scan` 并真正扫描本地化/构建残留；平台发布专项才加 `platform-forbidden` / `age` 维度。

最低构建残留词：

```text
# -*- coding
import json
event_.*=
"""
print(
def make_entry
pad_to
PLACEHOLDER
TODO
[U+XXXX]
```

绿冠星空 `事件：梦魇覆灭` / `事件：四女神公开化` 曾出现 `# -*- coding: utf-8 -*-`、`event_x = """` 残留，是好反例。

## 6. `validate_card.py` 必须支持 CLI

旧脚本只有函数 `validate_card(path)`，直接运行 `python scripts/validate_card.py <card>` 会静默 exit 0。工程化 gate 后必须补 CLI：

```bash
python scripts/validate_card.py <card.json>
```

建议退出码：

- errors > 0 → exit 1
- only warnings → exit 2（或 0，但必须输出 warning）
- clean → exit 0

## 7. 二轮审查最低回归集

每次改 gate 后至少跑：

- fixture 正反例；
- 周雨晴 E型：检查 R18事件不被误杀，且 build/assemble 真正验证；
- 绿冠星空 A-N：检查代码残留被准确归因；
- 黑绿足球 G型：检查场景氛围库不单条误红，G型三路径不过宽。

结论格式必须区分：

```text
真实旧卡问题 / gate误杀 / gate漏检 / 归因不准
```
