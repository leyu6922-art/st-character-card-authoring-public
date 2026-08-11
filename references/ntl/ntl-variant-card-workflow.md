# NTL变体卡创建工作流（2026-07-11·示例角色项目案例）

## 工作流概述
从原版NTR卡创建NTL变体卡：复制JSON→修改现有条目→新增NTL系统条目→合并→validate_card.py→修复→再验证。

## 关键步骤

### 1. 复制原卡为独立文件
```python
import shutil
shutil.copy2(src_path, dst_path)
```

### 2. 修改元数据
name/description/personality/scenario/tags/first_mes/system_prompt → NTL版本

### 3. 修改现有条目（P0-P2优先级）
- **ID 0 全局规则**：移除"禁止变强"，加入NTL核心规则+三层阻力+信息差
- **ID 4 苦主体验**：双模式（苦主被动/夺回主动）+屈辱→愤怒转化
- **ID 5 防拒绝**：保留NSFW规则，增加夺回/唤醒场景同等描写待遇
- **ID 6 NPC系统**：弱点系统+被反转后行为+控制力削弱机制
- **ID 7 剧情推进**：四阶段NTL路线+唤醒升级链+四结局分支
- **ID 16 伯里档案**：预知天赋三阶段+战力设定+性格四阶段

### 4. 新增NTL系统条目
- **ID 33 唤醒系统**（constant=true）
- **ID 34 NTL状态栏**（constant=true，替换原版状态栏）
- **ID 35 夺回剧情树**（selective=true）
- **ID 36 反转道具系统**（selective=true）
- **ID 37 NTL随机事件**（constant=true）
- **ID 38 结局分支**（selective=true）
- **ID 39 NTL对话库**（selective=true）
- **ID 40 场景玩法系统**（selective=true，含NTR升级链）

### 5. 改写alternate_greetings
每条≥1400字，从NTL视角改写。alt[4]可保留为BAD END预览+旁白提示。

### 6. 合并脚本关键步骤
```python
# 从原版条目复制完整extensions模板
import copy
template_ext = original_entry['extensions'].copy()
for eid in modified_entry_ids:
    entries[eid]['extensions'] = copy.deepcopy(template_ext)
    entries[eid]['extensions']['position'] = 0 if pos=='before_char' else 4
    entries[eid]['addMemo'] = True

# 常驻条目清空keys
for e in entries:
    if e.get('constant'):
        e['keys'] = []

# 禁用原版状态栏（被NTL版替代）
for e in entries:
    if e['id'] == original_status_bar_id:
        e['enabled'] = False
```

### 7. validate_card.py验证
跑完后必须检查：
- errors中的"被禁用"条目→设计选择，非真error
- token负载→与原版对比，差异<20%则标记为已知结构性问题
- alternate_greetings字数→全部≥1400

## 场景玩法系统设计模式（ID40）
每个场景包含：
1. **动机设计**（为什么来——不是自愿被NTR）
2. **玩法规则**（骰子表+具体规则）
3. **NTR升级链**（Level 0→6，从原著提炼）
4. **NTL切入点**（5种干预方式）+ 玩法效果（数值影响）

## 已验证坑
- 坑9：子代理生成条目缺extensions/addMemo
- 坑10：子代理内容含emoji字符
- 坑11：变体卡greeting字数缩水
- 坑12：first_mes触发负载过高（原版结构性问题）
- 坑19：场景玩法系统设计模式
- 坑20：场景emoji（🎰→[赌场]等）
- 坑21：token负载对比验证方法
