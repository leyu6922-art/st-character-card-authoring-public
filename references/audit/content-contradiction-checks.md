## 卡内容矛盾检测（脚本审查Phase 2）

### 何时使用
validate_card.py 只做结构/格式检查。内容层矛盾需要额外脚本，输入为：JSON文件路径 + 规划书路径。

### 必检矛盾清单

#### 1. first_mes顶层 vs data层截断（v3格式高发bug）
```python
top_fm = card.get('first_mes', '')
data_fm = data.get('first_mes', '')
if top_fm != data_fm:
    if data_fm.startswith(top_fm):
        print(f"❌ 顶层first_mes({len(top_fm)}字)是data层({len(data_fm)}字)的截断前缀")
    else:
        print(f"❌ 顶层与data层first_mes内容完全不同")
```
**修复**：`card['first_mes'] = data['first_mes']` 然后写回。

#### 2. 叙事视角矛盾
```python
# 条目1(叙事控制)中不能有"不用'你'"的限制，如果开场白全部用"你"
e1 = entries[1]['content']
if '不用"你"' in e1 or "不用'你'" in e1:
    print("❌ 条目1限制'不用你'但开场白用'你'——删除限制")
```

#### 3. NTR矩阵：规划书vs条目内容
对每个女性角色条目，检查规划书中列出的NTR目标是否在条目content中被提及。
```python
# 读取规划书v2中的NTR矩阵，逐条核对
for eid, women_name in [(8,'师傅'), (9,'伊丝娜'), (10,'奥萝拉'), (11,'妮丝')]:
    content = entries[eid]['content']
    for target, should_exist in expected_matrix[women_name].items():
        found = any(kw in content for kw in target_keywords[target])
        if should_exist and not found:
            print(f"⚠️ {women_name}条目应含{target}但未找到")
```

#### 4. 状态栏控制者覆盖
```python
# 状态栏条目中每个女性的控制者选项必须覆盖v2矩阵中所有NTR目标
# 常见遗漏：伊丝娜缺"赌场/黑巨汉"
```

#### 5. 常驻条目token膨胀
```python
for e in entries:
    if e.get('constant') and len(e.get('content','')) > 3000:
        print(f"⚠️ ID{e['id']}常驻条目{len(e['content'])}字——需精简")
```
**修复策略**：保留核心逻辑骨架，删除重复的描写模板、骰子表展开描述等。

#### 6. 事件种子条目enabled一致性
```python
# 同类条目（如事件种子库21-26）应统一enabled状态
event_entries = [e for e in entries if 21 <= e['id'] <= 26]
enabled_states = set(e.get('enabled', True) for e in event_entries)
if len(enabled_states) > 1:
    print("⚠️ 事件种子条目enabled状态不一致")
```

#### 7. 条目间事件归属错误
```python
# 如"几分钟调教"是师傅的专属标签，出现在伊丝娜相关条目中就是矛盾
# 需要对每个"标签化事件"检查归属
tagged_events = {
    '几分钟调教': [8],  # 只应在师傅条目
    '骑大马': [12],      # 只应在爱德条目
}
for tag, allowed_ids in tagged_events.items():
    for e in entries:
        if tag in e['content'] and e['id'] not in allowed_ids:
            print(f"⚠️ '{tag}'出现在ID{e['id']}中，但只应出现在ID{allowed_ids}")
```
