# 已有卡质量评估流程（2026-07-11 校园媚黑守护卡v2评估验证）

## 适用场景
用户拿一张已有的卡让你评估质量、判断是否需要修改——不是从零创作，而是"审一张现有卡"。

## 评估流程

### Phase 1：结构概览（execute_code + json.load）
1. 读取JSON，输出：spec版本、顶层字段完整性、data子字段
2. 统计：first_mes长度、alternate_greetings数量及各自长度、mes_example长度
3. character_book统计：const条目数/keyword条目数、各条目keys/len/enabled
4. system_prompt长度及内容概要

### Phase 2：Token负载分析
```python
# 常驻负载（每轮都注入）
const_chars = sum(len(e['content']) for e in entries if e.get('constant'))
# 关键词触发负载
kw_chars = sum(len(e['content']) for e in entries if not e.get('constant'))
# system_prompt + description 开销
sys_chars = len(system_prompt) + len(description)
# 估算总tokens（中文约1.5字/token）
total_tokens = (const_chars + sys_chars) / 1.5
```
**阈值**：常驻负载>5000 tokens报warning，>8000 tokens报error。

### Phase 3：内容质量逐条审查
1. **first_mes**：是否有场景描写+感官+对话+心理？是否有非叙事内容（状态栏/选项）混入？
2. **alternate_greetings**：时间线是否逻辑有序？内容是否连贯可衔接？
3. **角色条目**：是否有具体场景化行为模板？还是只有抽象梯度描述？
4. **节点条目**：是否有原著精确台词？还是只有概述？
5. **system_prompt与const条目**：是否有内容重复？

### Phase 4：原著对照（如有原文）
1. 读取原著提取文档（novel_extraction.md或原文txt）
2. 逐节点对照：原著关键事件是否有对应节点？
3. 角色对话准确性：条目中的对话是否来自原著原文？
4. 缺失事件清单（node_gap_analysis格式）

### Phase 5：输出评估报告
格式：总体结论 → 6个核心问题（按严重度排序） → 保留的优势 → 修改优先级P0-P3 → 建议方案（修补vs重写）

---

## 新发现的结构性坑（2026-07-11验证）

### 坑14：状态栏嵌入first_mes尾部
**现象**：first_mes末尾拼接════状态栏════和【可选行动】格式。
**后果**：SillyTavern将first_mes作为AI的"第一条回复"模板。AI会从first_mes结尾处续写，把状态栏格式当作"应该继续的格式模板"，导致每条回复都机械复制该格式结构。
**修复**：first_mes只保留叙事部分。状态栏/选项格式由system_prompt的指令控制AI在每次回复末尾自动生成。
**对比**：原版全员恶堕v2的first_mes完全没有状态栏——纯叙事。

### 坑15：alternate_greetings时间线倒序
**现象**：first_mes=9/1上午，alt[1]=9/1清晨，alt[2]=8/31下午——时间线在first_mes之前。
**后果**：玩家选了alt[2]再选first_mes就时空错乱。
**修复**：greetings按时间线正序排列，或至少在每个greeting末尾加"下一步"衔接提示。

### 坑16：mes_example为空导致格式失控
**现象**：mes_example=""。
**后果**：mes_example是ST中AI学习回复格式的最重要参考。没有它，AI完全依赖system_prompt的文字描述来决定输出格式，效果远不如"看一个实际例子"。对于需要维护状态栏、决策系统、堕落度追踪等复杂格式的卡尤其致命。
**修复**：写一个完整的对话示例，包含：场景叙事(1000字+) + 状态栏 + 叶云观察 + 可选行动 + AI对玩家选择的回应。

### 坑17：const条目与system_prompt内容重复
**现象**：守护卡总则在const[0]和system_prompt中各有一份（各600-700字）。
**后果**：浪费约400-500 tokens/轮。
**修复**：const条目和system_prompt各管各的职责，不要重复。system_prompt管全局格式指令，const条目管具体机制细节。

### 坑18：600字条目长度限制丢失关键内容
**现象**：所有条目被压缩到500-700字符以通过validate_card.py。
**后果**：角色的精确对话、感官描写、心理活动全部丢失。AI没有足够"素材"来还原角色语言风格和场景氛围。
**修复**：关键条目（角色行为模板、核心节点）放宽到1000-1200字。或将大条目拆分为多个子条目。

### 坑19：开场白数量与小说章节数不匹配
**现象**：15章小说只有4个开场白，缺少中后期节点入口。
**后果**：玩家无法从经典场景（初夜、操场羞辱、台球厅摊牌等）开始体验。
**修复**：按原著关键转折点设计8-10个开场白，覆盖：开局→前期冲突→中期高潮→后期决战。每个开场白1600-2200字。
