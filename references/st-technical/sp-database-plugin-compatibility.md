# SP-数据库插件兼容性指南

## 插件概况

- **名称**：酒馆助手脚本《数据库》（SP-数据库）
- **当前版本**：v7.1
- **加载方式**：`import 'https://gcore.jsdelivr.net/gh/AlbusKen/shujuku@spv7.1/index.js'`
- **源码**：约6.7MB的JS脚本，内含SQL.js（SQLite WebAssembly）
- **功能**：扫描世界书条目→构建数据库表→用"填表AI"自动填充→支持SQL查询召回

## 核心限制：maxEntriesPerChannel

数据库插件的**剧情推进/填表/最终生成**三个通道各有独立的世界书条目上限：

```json
"maxEntriesPerChannel": {
    "plot": 20,
    "tableFill": 20,
    "finalGeneration": 20
}
```

- **默认值**：每个通道 20 条
- **允许范围**：1-200（`normalizePositiveInt_ACU` 函数限制）
- **含义**：填表阶段最多只能激活20条世界书条目

### 常驻条目（constant=true）的特殊行为

常驻条目**不占通道名额**——它们始终注入，不受 `maxEntriesPerChannel` 限制。

但常驻条目的**总token消耗**会压缩填表AI的可用上下文。

### 实际影响示例

| 卡片 | 条目数 | 常驻条目 | 填表可用名额 | 问题 |
|------|--------|----------|-------------|------|
| 普通卡（20条目） | 20 | 5 | 15 | ✅ 正常 |
| 中型卡（50条目） | 50 | 10 | 10 | ⚠️ 大量条目不可见 |
| 示例角色项目（136条目） | 136 | 15 | 5 | ❌ 填表失败 |
| 道家仙子美母（106条目） | 106 | ~15 | ~5 | ❌ 填表失败 |

## 填表AI的工作流程

1. **背景设定注入**：`$C`（角色卡description）+ `$1`（激活的世界书条目内容）
2. **正文数据**：`$U`（用户基础设定）+ 上轮故事
3. **当前表格数据**：已有数据库表的CREATE TABLE + 当前数据
4. **填表AI处理**：读取背景设定→分析剧情变化→输出insertRow/updateRow/deleteRow指令

填表AI的提示词包含：
- `<背景设定>` 中的 `$C` 和 `$1` 是世界书内容的注入点
- 如果世界书条目太多（超过通道上限），`$1` 只包含被选中的20条
- 其余116条对填表AI**完全不可见**

## 诊断流程（当用户报告"数据库玩不了"时）

1. **检查卡文件大小**：>300KB 的卡大概率有问题
2. **统计条目数**：`data.character_book.entries` 的长度
3. **统计常驻条目**：`constant=true` 的数量和总字节数
4. **检查通道上限**：默认20，如果条目数>>20，填表AI看不到大部分设定
5. **检查开场白总大小**：>20KB 的开场白也会压缩可用上下文

### 快速诊断脚本

```python
import json, os

path = '角色卡.json'
with open(path, 'r', encoding='utf-8') as f:
    card = json.load(f)

entries = card['data']['character_book']['entries']
total = len(entries)
constants = [e for e in entries if e.get('constant', False)]
const_bytes = sum(len(e.get('content','').encode('utf-8')) for e in constants)
total_bytes = sum(len(e.get('content','').encode('utf-8')) for e in entries)

print(f"条目总数: {total}")
print(f"常驻条目: {len(constants)} ({const_bytes:,} bytes)")
print(f"填表可用名额: max(0, 20 - 0) = 20 (常驻不占名额但占token)")
print(f"内容总量: {total_bytes:,} bytes ({total_bytes/1024:.1f} KB)")
print(f"文件大小: {os.path.getsize(path):,} bytes")

if total > 50:
    print(f"⚠️ 条目数({total})远超通道上限(20)，数据库填表大概率失败")
if const_bytes > 20000:
    print(f"⚠️ 常驻条目过大({const_bytes/1024:.1f}KB)，会压缩填表AI上下文")
```

## 解决方案

### 方案1：调整通道上限（用户侧）

在数据库插件设置中增大 `maxEntriesPerChannel.tableFill`：
- 推荐值：50-80
- 上限：200
- 注意：增大后填表AI的输入token会增加，需要模型有足够上下文窗口

### 方案2：精简世界书（制卡侧）

当条目数>60时，应该在制卡阶段就控制膨胀：
- 合并"扩展1/扩展2/扩展3"类重复条目
- 把同角色的行为/对话/场景扩展合并到单条
- 减少常驻条目数量——非必要条目改为关键词触发
- 目标：总条目数控制在40-60以内

### 方案3：常驻条目优化

15个常驻条目中，很多可以改为关键词触发：
- "性爱规则·姿势·淫语库" → 触发词：做爱、性交、插入
- "状态栏模板" → 可以保留常驻（每轮都需要）
- "对话示例库" → 触发词：对话、说话
- "文风示例库" → 触发词：描写、叙述

## 与其他插件的交互

### 预设脚本"双人成行悬浮窗"

用户使用的预设可能包含独立的数据库脚本（如v7.0悬浮窗），这些脚本有自己的世界书处理逻辑，可能与SP-数据库的通道限制叠加。

### Agent接管世界书

数据库插件支持"Agent接管世界书"模式（`agentWorldbookControl`），此时由AI决定激活哪些条目，不受固定通道上限限制。但这个模式需要额外配置。

## 制卡建议（面向数据库用户）

如果你知道目标用户会使用数据库插件：
1. 条目数控制在40-60以内
2. 常驻条目≤10个，每个≤3KB
3. 避免"扩展N"递增编号的膨胀模式
4. 在Discord简介中注明"建议数据库用户调大tableFill通道上限"
