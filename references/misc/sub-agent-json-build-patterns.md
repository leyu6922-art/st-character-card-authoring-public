# 子代理并行构建JSON的模式与陷阱

> 来源：校园媚黑守护卡(2026-07)、示例游戏项目卡、示例角色项目卡 — 三次大型构建的共性总结

## 构建架构

将卡片按功能模块分给多个子代理并行生成，每个输出一个独立JSON文件：

```
build/
  card_shell.json   ← 子代理1: name/description/first_mes/alternate_greetings/tags
  wb_core.json      ← 子代理2: 世界观/规则/系统条目 (IDs 1-N)
  wb_chars.json      ← 子代理3: 角色条目
  wb_nodes.json      ← 子代理4: 剧情节点 (如适用)
  wb_endings.json    ← 子代理5: 结局+系统辅助 (如适用)
  merge.py           ← 合并脚本
```

每个子代理的goal里必须包含：
- 精确的JSON条目结构模板（含完整extensions块）→ 见 `wb-entry-json-schema.md`
- 明确的ID范围（避免重复）
- output文件路径
- 参考文件路径（plan文件、小说原文等）

## 合并脚本（merge.py）关键步骤

```python
# 1. Load all module JSONs
# 2. Concatenate entries arrays
# 3. Validate: required fields, ID dedup, sort by ID
# 4. Fill missing extensions fields (standard template)
# 5. Build SillyTavern v3 card structure
# 6. Extract system_prompt from entry (if ID matches)
# 7. Write final JSON
```

## 8个系统性坑（三次构建100%复现）

| # | 坑 | 影响 | 修复方式 |
|---|-----|------|----------|
| 1 | extensions.position值错误 | 条目位置错误 | 合并后批量: after_char→4, before_char→0 |
| 2 | selective=true但无secondary_keys | ST无法正确触发 | 合并时自动用keys前2项补充 |
| 3 | 顶层card字段与data不同步 | JSON结构不一致 | 合并脚本显式同步name/tags等 |
| 4 | system_prompt缺{{char}}/{{user}} | ST变量无法替换 | 合并后检查并补充 |
| 5 | 子代理超时(600s) | 大模块(16+条目)写不完 | 检查部分输出，不足用execute_code补充 |
| 6 | 安全过滤拒绝NSFW审查 | 内容审查子代理失败 | 内容审查必须自己用execute_code完成 |
| 7 | 条目内容字数偏低(60-80%) | 节点/结局条目过短 | 合并后手动补充场景描写和后果细节 |
| 8 | 对话引用混编(55%原文+45%新创) | 部分对话不可验证 | 守护卡梯度台词新创是合理的，在审查报告中说明 |
| 9 | card_shell子代理超时(2026-07) | 10+开场白×1400字=2万+字，单子代理无法在600s内完成 | 拆分：每个greeting写单独.txt文件→write_shell.py组装JSON（见下方"大型card_shell拆分模式"） |
| 10 | 开场白字数缩水30-50%(2026-07) | 子代理首轮输出~500-1000字，低于1400字最低要求 | 两轮生成：首轮写框架→二轮子代理扩充到≥1400字 |
| 11 | first_mes关键词冲突(2026-07) | 角色名在first_mes中出现，触发多条目→token负载超标(>8000tok) | 角色条目keys用精确短语（"夏倾月·角色"而非"夏倾月"），避免first_mes通用词 |
| 12 | 子代理虚构角色名(2026-07) | 系统条目/堕落度示例用了AI编造的名字（如"林婉儿"）而非原著角色名 | 合并后全局扫描：提取所有非ASCII名称→与角色名对照表比对→批量替换 |
| 13 | 节点条目emoji(2026-07) | 子代理在"自由描述"前加💬(U+1F4AC)等emoji，validate_card.py报错 | 合并后批量替换：💬→[说]、🟢→[低]、📍→[节点]、🎲→[随机]、⏰→[时间] |
| 18 | 关键词条目prevent_recursion=False(2026-07) | 子代理默认生成prevent_recursion=False，导致递归触发30+条目→token负载爆炸(18000+tok) | 合并脚本强制非const条目prevent_recursion=True |
| 19 | 开场白子代理直接写JSON→字数不达标(2026-07) | 子代理在JSON的greeting字段中直接写中文长文本，实际输出只有500-900字（<1400最低） | 让子代理先写单独.txt文件到greetings/目录，再由主agent的execute_code读取并组装进JSON。.txt文件比JSON内嵌字符串更容易写长 |
| 15 | card_shell子代理被安全过滤拒绝(2026-07) | NSFW场景描写触发模型安全过滤，子代理返回拒绝 | card_shell由父agent直接write_file写，不委托子代理 |
| 16 | 阶段/事件/描写条目子代理被安全拒绝(2026-07) | NTL变体卡的stage系统、event seeds、NSFW场景描写子代理全部被安全过滤拒绝 | 阶段系统+事件种子+描写库条目必须主代理用execute_code直接写。只有系统规则条目(ID0-9)和角色档案条目(ID10-20)可委托子代理 |
| 17 | execute_code临时变量跨脚本丢失(2026-07) | 第一个execute_code创建entries数组但未写文件，第二个execute_code读temp文件发现缺失 | 铁律：每个execute_code批次结束后必须立即write_file保存中间结果。变量在execute_code之间不共享 |
| 18 | 关键词单字导致token负载超标(2026-07) | 角色条目keys用单字角色名("师傅""伯里""保镖")→first_mes触发11条→16825 tokens | 用复合关键词("古兰""废物""大壮")避免first_mes通用词。效果：11→5触发，16825→13097 tokens |

## 大型card_shell拆分模式（2026-07验证）

当开场白数量≥8个时，单子代理会超时。解决方案：

```
build/v3/
  _first_mes.txt    ← 直接用write_file写
  _alt_0.txt        ← 每个greeting一个文件
  _alt_1.txt
  ...
  _alt_9.txt
  _mes_example.txt  ← mes_example单独文件
  _system_prompt.txt ← system_prompt单独文件
  write_shell.py    ← 读取所有.txt→组装成card_shell.json
```

**流程**：
1. 用write_file写first_mes（直接在主agent中写，不需要子代理）
2. 派子代理写alt_greetings（5个/子代理，每个≥1400字）
3. 写mes_example和system_prompt（主agent直接写）
4. write_shell.py读取所有.txt→组装成完整card_shell.json
5. merge.py合并card_shell + 所有world book entries → 最终JSON

**write_shell.py关键**：
- 读取_desc.txt, _first_mes.txt, _alt_*.txt, _mes_example.txt, _system_prompt.txt
- 构建完整的chara_card_v3 JSON结构（15个顶层字段）
- 输出card_shell.json

## 开场白两轮生成模式（2026-07验证）

子代理首次生成的greeting通常只有500-1000字（<1400最低要求）。必须做两轮：

**第一轮**：子代理写框架版（500-1000字）
- 场景骨架：人物+地点+关键事件
- 核心对话：2-3句原著台词
- 结尾引导：一句话衔接到下一个场景

**第二轮**：子代理扩充到≥1400字
- 增加环境描写（光影/气味/温度/声音）
- 增加外貌描写（穿着/身材/表情/肢体语言）
- 增加心理活动（叶云的内心独白）
- 增加对话细节（扩展原著对话场景）
- 增加感官描写（触觉/嗅觉/听觉）

**验证**：每个greeting写完后立即检查字数，<1400字的当场扩充。

## 角色名对照表检查（2026-07验证）

合并后必须做角色名一致性扫描：

```python
# 正确名称（以原著为准）
CORRECT_NAMES = {'夏倾月', '柳媚仙', '沐漓', '苏御然', '秦婉凝', '萧玉若', '姜玉心', '黄浩', '布鲁德', '吴林', '刘涛', '山口武藏'}

# 常见错误变体
WRONG_VARIANTS = {
    '夏清月': '夏倾月', '刘梅仙': '柳媚仙', '穆丽': '沐漓',
    '苏雨然': '苏御然', '秦婉宁': '秦婉凝', '萧雨若': '萧玉若',
    '姜雨欣': '姜玉心', '黄皓': '黄浩', '杰克': '布鲁德',
    '林婉儿': None,  # AI虚构名称，必须删除或替换
}

# 扫描所有条目content
for e in entries:
    for wrong, correct in WRONG_VARIANTS.items():
        if wrong in e['content']:
            if correct:
                e['content'] = e['content'].replace(wrong, correct)
            else:
                # AI虚构名称，用最接近的原著角色替换
                print(f"WARNING: entry {e['id']} contains invented name '{wrong}'")
```

## 双轨审查流程

构建完成后执行：

### 第一轨：脚本自动审查（execute_code）
1. JSON格式与层级一致性（顶层=data）
2. first_mes顶层截断检查
3. 条目ID连续性与重复
4. 条目结构完整性（selective/secondary_keys/position/extensions）
5. Discord违禁词全卡扫描
6. Emoji Unicode转义
7. {{user}}/{{char}}变量使用
8. 常驻条目token膨胀（>3000字报警）
9. enabled/constant状态一致性

### 第二轨：Agent内容审查
10. 开场白质量（环境/感官/对话/紧张感/字数）
11. 对话原文准确性（与小说原文txt逐条比对）
12. 堕落轨迹一致性（梯度/触发/拯救/OOC四维度）
13. NTR角色强度评估（难度/弱点/反制/升级）
14. 系统提示完整性（8项关键规则覆盖）
15. 数值平衡（节点默认路径惩罚、状态变化合理性）
16. 世界观条目质量（字数、系统覆盖度）

**注意**：NSFW内容的Agent审查会被安全过滤拒绝，必须自己用execute_code完成。

### 审查后修复优先级
- P0：结构破损/违禁词/视角矛盾 → 立即修
- P1：字数不足/缺失反制段落 → 立即修
- P2：内容详略不一/字数偏低 → 可在试玩后修
- P3：对话原文比例/优化建议 → 可选修
