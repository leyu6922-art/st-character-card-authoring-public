# 世界书清理与同步工作流

> 从示例玄幻项目清理案例提炼：死代码删除、多PNG清理、外部/嵌入世界书同步。

---

## 一、死代码识别与删除

### 死代码的典型表现

| 类型 | 特征 | 原因 |
|------|------|------|
| 变量系统条目 | 预处理脚本（@@preprocessing）、UpdateVariable标签 | 预设MVU模块OFF，变量只读不回写 |
| 被预设覆盖的规则 | 文风规范、NSFW比例、行动引导 | 预设有自己的版本，卡里的被覆盖 |
| 依赖未启用扩展的条目 | 使用getMessageVar/setMessageVar但扩展OFF | 脚本依赖ST扩展，扩展未启用 |

### 删除注意事项

**⚠️ 字符串key陷阱**：ST外部世界书的entries字典key是字符串（`"133"`），不是整数。用整数key删除会静默失败。

```python
# 正确做法
for uid in list(entries.keys()):
    e = entries[uid]
    if is_dead_code(e):
        del entries[uid]  # uid已经是字符串
```

**删除后验证**：打印条目数确认减少量与预期一致。

---

## 二、多PNG版本清理

ST中同一角色卡可能累积多个PNG版本（示例玄幻项目案例：6个版本）。

### 识别保留版本

```python
# 扫描所有PNG，检查内嵌世界书的关键标记
for f in os.listdir(char_dir):
    if '角色名' in f and f.endswith('.png') and '.bak' not in f:
        card = extract_card_from_png(path)
        entries = card['data']['character_book']['entries']
        has_uid998 = any(e.get('uid') == 998 for e in entries)  # 覆盖条目
        has_dead = any('预处理' in e.get('content','')[:30] for e in entries)
        print(f"{f}: uid998={'有' if has_uid998 else '无'}, 死代码={'有' if has_dead else '无'}")
```

### 清理步骤

1. 扫描所有PNG，找到有覆盖条目且无死代码的版本 → 保留
2. 备份其余版本为 `.pre-cleanup.bak`
3. 删除其余版本

---

## 三、外部世界书与PNG内嵌世界书同步

ST有两个世界书存储位置：
- **外部文件**：`data/default-user/worlds/角色名.json`（entries是dict，key为字符串）
- **PNG内嵌**：`data/default-user/characters/角色名.png` 的 tEXt chunk（entries是list）

修改其中一个不会自动同步另一个。必须手动保持一致。

### 同步方向

| 场景 | 源 → 目标 | 原因 |
|------|-----------|------|
| 清理死代码 | 两边都改 | 确保无论ST读哪个都是干净的 |
| 新增uid=998覆盖条目 | 两边都改 | 覆盖条目必须在两个位置都存在 |
| 大规模扩充 | PNG → 外部 | PNG是ST实际加载的，外部是备份 |

### PNG修改模板

```python
import base64, json, struct, zlib, shutil

png_path = "角色名.png"
with open(png_path, 'rb') as f:
    data = f.read()

# 解析PNG chunks
pos = 8
chunks = []
chara_idx = None
while pos < len(data):
    length = struct.unpack('>I', data[pos:pos+4])[0]
    chunk_type = data[pos+4:pos+8]
    chunk_data = data[pos+8:pos+8+length]
    chunks.append((chunk_type, chunk_data))
    if chunk_type == b'tEXt':
        null_idx = chunk_data.index(b'\x00')
        if chunk_data[:null_idx] == b'chara':
            chara_idx = len(chunks) - 1
    pos += 12 + length

# 提取并修改JSON
ct, cd = chunks[chara_idx]
chara_b64 = cd[cd.index(b'\x00')+1:].decode('latin-1')
card = json.loads(base64.b64decode(chara_b64))

# ... 修改 card['data']['character_book']['entries'] ...

# 重建PNG
new_b64 = base64.b64encode(json.dumps(card, ensure_ascii=False).encode()).decode('latin-1')
keyword = cd[:cd.index(b'\x00')].decode('latin-1')
new_text = keyword.encode('latin-1') + b'\x00' + new_b64.encode('latin-1')

def make_chunk(ct, cd):
    raw = ct + cd
    crc = struct.pack('>I', zlib.crc32(raw) & 0xFFFFFFFF)
    return struct.pack('>I', len(cd)) + raw + crc

output = b'\x89PNG\r\n\x1a\n'
for i, (ct, cd) in enumerate(chunks):
    output += make_chunk(ct if i != chara_idx else b'tEXt', new_text if i == chara_idx else cd)

shutil.copy2(png_path, png_path + '.bak')
with open(png_path, 'wb') as f:
    f.write(output)
```

---

## 四、与预设冲突的决策树

```
变量/脚本机制与预设冲突？
├─ 是 → 该预设是否支持MVU/变量系统？
│   ├─ 支持 → 保留变量系统，按预设要求调整格式
│   └─ 不支持 → 删除变量系统，改为纯文本描述型规则
│       └─ 用户明确说"预设优先"时 → 删除卡中的机制条目，不改预设
└─ 否 → 保留变量系统
```

**用户偏好（2026-07-09 明确指示）**：预设是最高优先级，因为多张卡共用同一预设。角色卡相比预设没那么重要，应适配预设而非反过来。
