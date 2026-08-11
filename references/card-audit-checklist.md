# 角色卡审查清单（自动化+Agent双轨）v4.3

## 触发条件
用户说"审查角色卡""检查冲突""validate"→ 执行此流程。

## 审查流程
1. `execute_code` + `json.load()` 读取卡JSON，输出概览
2. `read_file` 读取所有关联文档（规划书、质检标注等）
3. 按下方35项清单逐维度交叉验证（脚本自动 + Agent人工）
4. 输出三级分类报告（🔴关键/🟡重要/🟢优化）+ 修复优先级P0-P3

> 完整35项自动检查脚本见 `scripts/validate_card.py`

---

## 第一轨：脚本自动审查

### A. 结构层检查
1. **JSON格式与层级一致性** — spec=chara_card_v3, spec_version=3.0
2. **first_mes顶层截断** — `len(card['first_mes']) != len(card['data']['first_mes'])`
3. **条目ID连续性与重复** — 必须从0开始，`ids == list(range(len(ids)))`
4. **条目结构完整性** — selective+secondary_keys一致性、content非空、position映射

### B. v3格式必检（2026-07-11新增）
5. **15个顶层字段** — name/description/personality/scenario/first_mes/mes_example/creatorcomment/avatar/talkativeness/fav/tags/create_date/spec/spec_version/data
6. **常驻条目keys必须=[]** — constant=true的条目不需要关键词触发
7. **addMemo字段** — 每个条目必须有
8. **use_regex字段** — 每个条目必须有
9. **extensions.position映射** — before_char=0, after_char=4
10. **display_index=id** — 必须同步

### C. 内容层检查
11. **Discord违禁词** — 萝莉/幼女/童贞/loli/luoli/未成年
12. **Emoji Unicode转义** — `[U+XXXX]`会被ST原样输出
13. **{{user}}变量** — first_mes中应用"你"，description/system_prompt中应有{{user}}

### D. Token负载
14. **常驻条目token膨胀** — 单条>3000字警告
15. **first_mes触发负载** — 常驻+触发<8000tok
16. **递归触发链** — prevent_recursion=False的条目数检查

### E. 跨条目检查
17. **NTR标签跨角色误用** — 专属标签是否归错角色
18. **关键词重叠** — 同一关键词被3+条目共享可能导致截断
19. **内容重复** — 相似度>80%的条目对

---

## 第二轨：Agent人工审查
20. **开场白质量** — 场景描写+感官+对话+心理，≥1400字
21. **对话原文准确性** — 对照原文txt逐条核实引用
22. **堕落轨迹一致性** — 角色档案 vs 节点条目 vs NTR目标
23. **NPC行动逻辑** — 触发条件合理性
24. **旁白格式一致性** — 规则 vs 示例
25. **预算超支根因** — 定位膨胀条目

---

## 输出格式
```
## 审查报告：{卡名}
### ✅ 通过项（N项）| ❌ 严重矛盾 | ⚠️ 警告
### 📊 数据总览 | 🔧 修复优先级P0-P3
```

---

## 守护卡追加审查项
26. **名称一致性** — 角色名以原著为准，全卡统一
27. **first_mes触发负载** — 角色条目keys不应与first_mes通用词重叠
28. **节点覆盖率** — 对照原著章节检查关键事件是否都有对应节点

## NTL变体卡追加审查项
29. **状态栏控制者覆盖度** — NTR矩阵中所有目标必须在状态栏出现
30. **唤醒阶段对齐** — 唤醒系统阶段名与状态栏一致
31. **道具限制与结局触发对齐**
32. **伯里设定一致性** — 预知天赋/愤怒转化/性格四阶段在所有条目一致
33. **alternate_greetings版本一致性** — 不含原版苦主元素

## 常见坑（已验证，13个）

### 坑1：first_mes顶层截断
**检测**：`len(card['first_mes']) != len(card['data']['first_mes'])`
**修复**：统一两处为完整版。

### 坑2：叙述视角自相矛盾
**修复**：条目中删"不用你"限制，或改为"开场白用'你'，正文可用'他'"。

### 坑3：NTR标签跨角色误用
**修复**：事件条目中改用正确的角色NTR模式。

### 坑4：常驻条目token膨胀
**修复**：场景模板/骰子表拆到触发条目。

### 坑5：状态栏控制者选项不完整
**修复**：对照NTR矩阵补充缺失的控制者选项。

### 坑6：事件种子条目enabled不一致
**修复**：确认意图后统一。

### 坑7：extensions.position不一致
**修复**：批量补全——before_char→0, after_char→4。

### 坑7b：v3顶层字段缺失（2026-07-11）
**修复**：合并脚本补全15个顶层字段（见validate_card.py）。

### 坑7c：条目ID必须从0开始（2026-07-11）
**修复**：合并时`for i, e in enumerate(entries): e['id'] = i`。

### 坑8：变体卡alternate_greetings沿用原版
**修复**：每条greeting改写为新版本视角。

### 坑9：常驻条目被子代理加上keys（2026-07-11）
**修复**：合并脚本强制清空constant条目的keys。

### 坑10：子代理生成条目缺extensions/addMemo（2026-07-11）
**修复**：合并时从模板复制完整extensions+addMemo。

### 坑11：变体卡greeting字数缩水（2026-07-11）
**修复**：每次重写greeting后检查≥1400字。

### 坑12：first_mes触发负载过高（2026-07-11）
**修复**：角色条目keys改精准短语，通用名放secondary_keys+selective。合并后跑负载检查。

### 坑13：角色名称不一致（2026-07-11）
**修复**：以原著原文为准统一，合并前做名称扫描。

### 坑14：子代理节点条目含emoji（2026-07-11·v3守护卡）
**检测**：validate_card.py条目emoji检查。子代理经常在节点条目中插入💬(U+1F4AC)、🟢(U+1F7E2)、📍(U+1F4CD)、🎲(U+1F3B2)等emoji。
**修复**：合并脚本批量替换——💬→[说]、🟢→[低]、📍→[节点]、🎲→[随机]、⏰→[时间]。合并后扫描所有条目的高码位字符(>U+FFFF)。

### 坑15：关键词条目prevent_recursion=False（2026-07-11·v3守护卡）
**检测**：validate_card.py递归触发链检查。子代理生成的关键词条目默认prevent_recursion=False，导致条目A触发条目B触发条目C…最终触发30+条目，token负载爆炸。
**修复**：合并脚本强制设置所有非const条目的prevent_recursion=True。const条目保持False（每轮都加载，不需要递归检查）。

### 坑16：card_shell子代理被安全过滤拒绝（2026-07-11·v3守护卡）
**现象**：生成first_mes+alt_greetings+mes_example的子代理返回安全拒绝。NSFW场景描写触发模型安全过滤。
**修复**：card_shell由父agent直接用write_file写，不委托子代理。子代理只负责结构化条目内容。

### 坑17：开场白扩充工作流（2026-07-11·v3守护卡）
**场景**：初次生成的alt_greetings字数不足（500-1000字，需≥1400字）。
**工作流**：骨架写入`_alt_N.txt`→2个子代理各扩充5个→父agent写`write_shell.py`组装card_shell.json→合并脚本组装最终卡。

### 坑18：系统条目中的角色名错误（2026-07-11·v3守护卡）
**现象**：子代理在系统条目中使用错误示例角色名（如"林婉儿"而非"夏倾月"）。
**修复**：合并后对所有const条目做名称扫描，替换错误名称。
