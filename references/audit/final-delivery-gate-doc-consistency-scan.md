# Final Delivery Gate 文档一致性扫描规则（2026-07-16）

用于维护 `final_delivery_gate.py`、`check_build_sync.py`、`validate_card.py`、`enrichment_self_check.py` 及其配套文档时，防止主文档已修但周边 active 参考仍残留旧口径。

## 触发场景

- 修改 R18 / strict-age / strict-platform / residue / build sync / exit code 语义后。
- 独立审查窗口指出文档冲突后。
- 用户要求“看看修复结果”“复核流程/门控一致性”。

## 必跑扫描

在 skill 根目录运行等价脚本，排除 `_archived/`、`_maintenance_backups/`、`__pycache__/`、`.bak`：

```python
from pathlib import Path
base = Path(r'<LOCAL_PATH>\AppData\Local\hermes\skills\creative\st-character-card-authoring')
terms = [
    '全卡违禁词扫描',
    '年龄/学生风险',
    '默认修法',
    'G型 | 默认 none',
    '优先以 `归档` 下的成品 JSON 为准',
    '任何修改JSON内容的步骤结束后，立即重跑违禁词扫描',
    '每次扩写后立即重跑全卡违禁词扫描',
]
for p in base.rglob('*'):
    if not p.is_file():
        continue
    s = str(p)
    if any(skip in s for skip in ['__pycache__', '_archived', '_maintenance_backups']) or p.suffix == '.pyc' or '.bak' in p.name:
        continue
    if p.suffix.lower() not in ['.md', '.py', '.txt', '.json'] and p.name != 'SKILL.md':
        continue
    text = p.read_text(encoding='utf-8', errors='ignore')
    for term in terms:
        idx = text.find(term)
        if idx >= 0:
            print(f'{p.relative_to(base)}:{text[:idx].count(chr(10))+1}: {term}')
```

目标输出：`ACTIVE_STALE=NONE` 或人工确认命中只是“旧错误反例”而非指令。

## 当前统一口径

- `final_delivery_gate.py` 是默认交付聚合门控，只判定不修卡。
- R18 内容密度默认开启；普通/非 NSFW 世界书才 `--no-r18`。
- 年龄/校园词默认不阻塞；只有 `--publish-text <简介.md> --strict-age` 才扫描发布文案中的未成年/儿童化词。
- 社区平台敏感词默认不阻塞；只有 `--publish-text <简介.md> --strict-platform` 才扫描发布文案中的平台词。
- residue/构建/代码残留默认必须扫，命中硬风险阻塞。
- `exit=2` = 仅 warning，可人工确认，不等于完全通过。
- 成品卡路径先以用户当前给出的实际路径为准；没给路径再优先搜索 `归档`。
- build sync 应支持 `assemble_card.py`、`build/assemble_card.py`、`build_data/assemble_card.py`，并在临时目录运行 assemble。

## 修正文案模板

将旧“全卡违禁词扫描/年龄风险默认阻塞”统一改为：

```text
简介/帖子敏感词扫描：仅用于 Discord/社区发布简介、帖子正文、标题、标签等平台可见文案；Discord/社区不审卡 JSON/世界书/开场白，卡创作完全不受小说原文敏感词或角色年龄影响。默认质量门控仍是 final_delivery_gate.py 的 residue/R18/build 检查；发布时用 --publish-text <简介.md> --strict-platform，必要时再加 --strict-age。
```

## ⚠️ §5.1 陷阱汇总表盲区（T93教训）

§5.1是压缩的单行表格格式（`| 陷阱 | 说明 | 修复 |`），不像§5.3.1/§3.4有独立章节标题。批量政策修正时**必须单独grep §5.1区域**（约line 1330-1470）确认已更新，不能只搜独立章节。

## 复核要求

文档 patch 后至少验证：

1. active-tree stale scan 无旧冲突词。
2. `python -m py_compile scripts/check_build_sync.py scripts/final_delivery_gate.py` 通过。
3. build fixture：good=PASS，bad=FAIL。
4. `build_data/assemble_card.py` 临时 fixture PASS（若本轮碰到 build sync）。
5. 真实卡回归至少一张 G 型、一张非 G 型、一张曾有 residue 问题的旧卡。
6. **§5.1陷阱汇总表**：grep SKILL.md line 1330-1470 区域确认无旧政策残留（T93教训）。
