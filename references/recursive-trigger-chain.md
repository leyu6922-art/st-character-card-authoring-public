# 递归触发链 - 完整诊断与修复

## 发现经过（2026-07-05 叶无云堕落版）

### 症状
- 叶无云堕落版角色卡在SillyTavern中，第一次发消息时AI回复被瞬间截断
- 第二次重复发送同样的消息可以正常输出完整内容
- 同一预设、同一ST设置下，其他角色卡（43000+字符）都能正常输出

### 排查过程
1. **Hermes初步分析**：token负载从11067降到4271（减61%），但仍有截断
2. **Codex深度分析**：发现递归触发链是隐藏根因
   - 非递归估算：10条目，~4271 tokens
   - 递归触发后：43条目，~15075 tokens（膨胀3.6倍！）
3. **根因定位**：所有触发条目的 `prevent_recursion=False`

### Codex的分析方法（可复用）
1. **二分法**：禁用所有世界书条目，看是否还截断
2. **对比法**：与能跑的卡（道家仙子美母106条目）逐字段对比
3. **递归模拟**：检查已触发条目的内容是否包含其他条目的关键词

## 根因详解

### 什么是递归触发链

当触发条目的 `extensions.prevent_recursion = False` 时：
1. first_mes 命中条目A
2. 条目A的内容包含条目B的关键词 → 条目B被激活
3. 条目B的内容包含条目C的关键词 → 条目C被激活
4. 链式反应持续，直到无新条目可触发

### 为什么第二次能跑
- 第一次的消息已进入上下文
- ST可能缓存了部分世界书条目
- 第二次的input token减少，output空间释放

### 与v2格式问题的区别

| 问题 | 症状 | 根因 |
|------|------|------|
| v2格式 | 完全无法输出（空回） | ST无法解析条目 |
| 递归触发链 | 能输出但截断 | 条目链式触发，token爆炸 |

## 修复步骤

### Step 1: 关闭递归触发
```python
for entry in entries:
    if not entry.get('constant', False):
        entry['extensions']['prevent_recursion'] = True
```

### Step 2: 开启selective筛选
```python
for entry in entries:
    if entry.get('secondary_keys') and not entry.get('selective'):
        entry['selective'] = True
```

### Step 3: 改进太泛的secondary_keys
```python
# 太泛的副关键词：角色/设定/场景/详细/系统/规则/模板/世界/关系
# 改进为具体关键词：如"小姨异常"、"Dave别墅"
```

## 验证方法

```python
# 检查prevent_recursion状态
for e in entries:
    pr = e.get('extensions', {}).get('prevent_recursion', '未设置')
    if not e.get('constant') and pr is not True:
        print(f"⚠️ [{e['id']}] {e['comment'][:30]}: prevent_recursion={pr}")

# 递归触发模拟（与非递归对比）
# 如果递归后条目数 > 非递归条目数 × 2，说明有严重的链式触发
```

## 修复效果（叶无云案例）

| 状态 | 触发条目 | tokens | 降幅 |
|------|---------|--------|------|
| 原始（递归） | 43条 | ~15075 | - |
| 关闭递归 | 10条 | ~4271 | -72% |
| +selective | 8条 | ~3760 | -75% |

## 关键教训

1. **递归触发是隐形杀手** — 条目不多也会爆炸
2. **selective需要配合有意义的副关键词** — 太泛的副词等于没有
3. **prevent_recursion必须在触发条目上开启** — 常驻条目开了没用
4. **修卡时必须force-set** — 不能只在缺失时添加，必须覆盖已有的false值
5. **修卡后必须验证** — 跑validate_card()确认递归触发链检查通过
