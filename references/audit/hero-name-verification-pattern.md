# 角色名幻觉验证模式（T60 · 2026-07-14）

## 触发条件
做卡完成后、审查阶段必做。特别是：
- 小说中角色有明确名字（非"勇者""魔王"等泛称）
- AI自行补充了角色名（计划书没写、或计划书写了但AI"觉得另一个名字更好"）
- NPC角色（NTR男性/配角等容易被AI自行命名的角色）

## 验证方法

```python
import os

novel_dir = "/path/to/novel/chapters"
# 从卡中提取所有可能的角色名（keys + comment + content中的人名）
suspect_names = ['亚伦', '艾尔诺', 'XXX']  # 待验证的名字

for name in suspect_names:
    total = 0
    chapters_found = []
    for fname in sorted(os.listdir(novel_dir)):
        if not fname.endswith('.txt'):
            continue
        with open(os.path.join(novel_dir, fname), 'r', encoding='utf-8') as f:
            text = f.read()
        count = text.count(name)
        if count > 0:
            total += count
            chapters_found.append((fname[:10], count))

    if total == 0:
        print(f"🔴 '{name}' → 小说中0次出现 — 幻觉名！")
    else:
        print(f"✅ '{name}' → {total}次/{len(chapters_found)}章")
```

## 实战案例

**示例关系卡卡（2026-07-14）**：
- 小说原文：`名为艾尔诺的勇者此时正在拿起一把崭新的长剑端详着`（第1章）
- 计划书正确写了"勇者艾尔诺"
- AI构建时在条目[8][9][11]中自行改成了"亚伦"（11处错误）
- 影响：洛希角色档案中称呼从"勇者大人"变成"亚伦"、NTR关系图谱标题写"勇者亚伦"——与小说完全矛盾
- 修复：全局替换"亚伦"→"艾尔诺"

## 常见幻觉模式
1. **NPC自行命名**：计划书只写了"神父"，AI给了他一个名字（如"霍普"）→ 需验证小说中是否有这个名字
2. **昵称混淆**：小说用全名"艾尔诺"，条目用昵称"小艾"→ 确认哪种称呼在小说中实际出现
3. **翻译变体**：同一角色在不同条目中用了不同音译→ 统一为小说中最常用的写法
4. **AI"美化"名字**：觉得原名不够好听/不够奇幻，自行改成另一个名字→ 铁律：用原文名字
