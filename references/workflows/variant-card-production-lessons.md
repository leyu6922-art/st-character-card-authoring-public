# 变体卡生产经验（异世界系列+校园女友验证，2026-07-11）

## 一、变体卡制作清单

制作NTL/守护/反杀等变体卡时，以下字段**必须重写**（不是patch）：

- [ ] ID0 全局规则（核心理念变化，不能只改禁止项）
- [ ] system_prompt（角色列表/NTR矩阵/核心机制）
- [ ] description / personality / scenario / tags
- [ ] first_mes（必须从新版本视角重写）
- [ ] alternate_greetings 逐条改写（不含原版元素）
- [ ] 状态栏模板（新增字段如唤醒值/控制力/愤怒值）
- [ ] 原版描写库加变体上下文说明（"仅XX模式使用"）
- [ ] 新增系统用独立条目（不塞进原条目，会token爆炸）
- [ ] 事件种子条目enabled状态确认
- [ ] Discord简介重新生成（≤2000字符）

## 二、子代理输出JSON规范

子代理生成的条目JSON常缺字段。prompt中必须明确要求：

```json
{
  "id": 0,
  "keys": [],
  "secondary_keys": [],
  "comment": "条目名称",
  "content": "完整内容",
  "constant": true,
  "enabled": true,
  "selective": false,
  "position": "before_char",
  "use_regex": true,
  "addMemo": true,
  "extensions": {
    "position": 0,
    "display_index": 0,
    "prevent_recursion": true,
    "probability": 100,
    "depth": 4,
    "vectorized": false,
    "group": "",
    "group_override": false,
    "group_weight": 100,
    "scan_depth": null,
    "case_sensitive": null,
    "match_whole_words": null,
    "automation_id": null,
    "role": null,
    "uid": 0,
    "exclude_recursion": false,
    "delayUntilRecursion": false,
    "displayVersion": "",
    "sticky": null,
    "cooldown": null,
    "delay": null
  }
}
```

**关键规则：**
- constant=true的条目：keys必须=[]（否则触发链爆炸）
- selective=true的条目：必须有secondary_keys
- extensions必须有30+字段（从模板复制，只改position和display_index）
- position映射：before_char→0, after_char→4
- 必须有addMemo=true

## 三、合并后自动修复脚本模式

```python
# 合并子代理输出后，批量修复常见缺陷
for e in entries:
    # 1. constant条目清空keys
    if e.get('constant') and e.get('keys'):
        e['keys'] = []

    # 2. 补全extensions
    if not e.get('extensions') or len(e.get('extensions', {})) < 10:
        e['extensions'] = template_extensions.copy()

    # 3. 补全position映射
    pos = e.get('position', 'after_char')
    e['extensions']['position'] = 0 if pos == 'before_char' else 4

    # 4. 补全addMemo
    if 'addMemo' not in e:
        e['addMemo'] = True

    # 5. selective条目补secondary_keys
    if e.get('selective') and not e.get('secondary_keys'):
        e['secondary_keys'] = []  # 需要手动填入
```

## 四、交替_greetings字数验证

validate_card.py要求每个greeting≥1400字。变体卡改写greetings时常见问题：
- 改写后字数缩水（原版1200字→改写后600字）
- 保留了原版的苦主元素（"废物"/"自欺"）
- 顶层alternate_greetings和data层alternate_greetings不同步

**修复：**改写后必须 `assert len(g) >= 1400` 验证每条greeting。

## 五、token负载现实

异世界卡的token负载（常驻+触发）：
- 苦主版：8常驻+8触发 = 14425tok
- NTL版：11常驻+8触发 = 16412tok

validate_card.py的阈值是8000tok。但**只要first_mes提到所有角色名，所有角色档案条目就会被触发**——这是结构性问题，不是缺陷。

**现实对策：**
- 常驻条目控制在12条以内
- 角色档案条目content控制在3000字以内
- 接受token负载会超过8000tok（原版就超标了）

## 六、已验证的10个坑（按时间线）

1. first_mes顶层/data层截断 → 合并脚本中强制统一
2. 叙述视角矛盾（条目说"不用你"，开场白全用"你"）→ 删除条目限制
3. NTR标签跨角色误用（"几分钟调教"从师傅→伊丝娜）→ 事件条目对照角色档案
4. system_prompt过短 → 扩充到600+字含核心骨架
5. 常驻条目token膨胀 → 拆分到触发条目
6. 子代理缺extensions字段 → 合并后批量补全
7. 子代理常驻条目误加keys → 合并后批量清空
8. alternate_greetings沿用原版 → 逐条改写
9. 状态栏控制者选项不完整 → 对照NTR矩阵补全
10. 条目含emoji → 替换为纯文本标记
