# SillyTavern Reasoning Parser 与 PNG 角色卡格式（2026-07-08 实测）

## ST Reasoning Parser 行为

### 解析机制

ST 1.18.0 的 reasoning parser（`public/scripts/reasoning.js`）使用**字面量匹配**：

```javascript
// reasoning.js 第480行
if (parseTarget.startsWith(power_user.reasoning.prefix) && parseTarget.length > power_user.reasoning.prefix.length) {
    this.#isParsingReasoning = true;
    this.state = ReasoningState.Thinking;
}
```

- `startsWith` 是字面量匹配，**不支持正则表达式**
- prefix/suffix 存储在 `data/default-user/reasoning/Think XML.json`
- 默认值：`{"prefix": "

  - prefix/suffix 存储在 `data/default-user/reasoning/Think XML.json`
- 默认值：`{"prefix": "

    "suffix": "</think>", "separator": "\n"}`

### XML头导致解析失败

当模型（如Gemini通过代理）在 `` 前输出XML头时：
```
?xml version="1.0" encoding="UTF-8"?>
```

`startsWith("  - prefix/suffix 存储在 `data/default-user/reasoning/Think XML.json`
- 默认值：`{"prefix": "

    "suffix": "</think>", "separator": "\n"}`**，reasoning parser 不触发，thinking内容原样显示为正文。

### 为什么正则脚本无法修复

1. ST的正则引擎（AI_OUTPUT placement）在**消息渲染阶段**执行
2. Reasoning parser在**流式接收阶段**执行
3. 正则在reasoning之后运行，无法影响reasoning解析

```
流式接收 → reasoning parser (startsWith) → 消息保存 → 正则引擎 (AI_OUTPUT) → 渲染
```

### 可能的解决方案

1. **修复代理/模型**：让代理strip掉XML头再返回给ST
2. **换代理**：使用不添加XML头的API代理
3. **等待ST更新**：未来版本可能支持正则prefix匹配

### 配置位置

```
# Reasoning模板文件
<SILLYTAVERN_ROOT>/data/default-user/reasoning/Think XML.json

# Reasoning设置（UI）
ST设置 → AI响应格式 → Reasoning区域
  - Prefix:
  - Auto-parse: ✓
  - Reasoning select: Think XML

# Reasoning解析源码
<SILLYTAVERN_ROOT>/public/scripts/reasoning.js
```

## PNG 角色卡文件格式

### 存储位置
```
<SILLYTAVERN_ROOT>/data/default-user/characters/角色名.png
```

### 文件结构

ST的角色卡PNG文件 = 标准PNG图片 + tEXt chunk（嵌入JSON数据）

```
[PNG Signature 8字节]
[tEXt chunk: keyword="chara", value=base64(JSON)]
[IDAT chunk: 图片数据]
[IEND chunk]
```

### tEXt chunk格式
```
4字节: chunk长度
4字节: chunk类型 "tEXt"
N字节: chunk数据 = "chara\x00" + base64编码的角色卡JSON
4字节: CRC32校验
```

### 提取JSON的方法
```python
import struct, base64, json

with open("角色名.png", 'rb') as f:
    data = f.read()

pos = 8  # Skip PNG signature
while pos < len(data) - 12:
    length = struct.unpack('>I', data[pos:pos+4])[0]
    chunk_type = data[pos+4:pos+8].decode('ascii', errors='ignore')
    chunk_data = data[pos+8:pos+8+length]

    if chunk_type == 'tEXt':
        null_pos = chunk_data.find(b'\x00')
        if null_pos > 0 and chunk_data[:null_pos] == b'chara':
            encoded = chunk_data[null_pos+1:]
            card = json.loads(base64.b64decode(encoded).decode('utf-8'))
            # card 就是完整的角色卡JSON

    pos += 12 + length
```

### 修改PNG中的JSON

修改JSON后需要：
1. 重新base64编码
2. 重建tEXt chunk（keyword="chara" + base64数据）
3. 计算新的CRC32
4. 替换原PNG中的tEXt chunk
5. 写回PNG文件
6. 用户在ST中重新加载角色卡

完整代码见SKILL.md的"ST角色卡是PNG文件"章节。

### 多个PNG文件

同一角色可能有多个PNG文件（如`角色名.png`和`角色名1.png`）。ST使用文件名匹配，需要确认哪个是当前加载的。

## ST API 端点

### 端点列表（POST方法）
```
POST /api/characters/all     - 获取所有角色
POST /api/characters/get     - 获取单个角色
POST /api/characters/edit    - 编辑角色
POST /api/characters/create  - 创建角色
POST /api/characters/delete  - 删除角色
```

### CSRF保护
所有POST端点需要CSRF token。从浏览器内调用时自动携带，从外部curl调用会失败（`ForbiddenError: Invalid CSRF token`）。

### 认证
ST使用cookie认证。cookie存储在`data/cookie-secret.txt`中，但仅靠cookie不够——还需要CSRF token。

### 推荐调用方式
```javascript
// 在浏览器console中调用（自动携带cookie和CSRF）
$.post('/api/characters/all', {}).done(data => console.log(data));

// 或使用fetch
fetch('/api/characters/all', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: '{}',
  credentials: 'include'
}).then(r => r.json()).then(data => console.log(data));
```

## 酒馆助手（Tavern Assistant）

- 酒馆助手是"第三方扩展"（ThirdPartyExtension）扩展的子模块
- 版本4.8.14
- 提供AI对话、选项框、渲染交互等功能
- 不等于API代理——`api_server`是ST自己的API服务器端口
- 选项框功能会在AI回复末尾注入HTML/JS代码

## 参考资料

- `st-native-charcard-format.md` — ST角色卡JSON格式规范
- `st-truncation-diagnosis.md` — 截断/空回诊断
- `sillytavern-setup.md` — ST安装配置指南
