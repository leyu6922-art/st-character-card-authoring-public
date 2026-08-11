# NTL变体卡审查启动模板（通用版）

> **两种使用模式**：
> - **制卡流程内**（agent自审）：直接读取本模板内容，按步骤逐项执行，不复制到新窗口
> - **交叉验证**（用户手动）：复制本模板全部内容→替换所有 `[方括号]` → 在新Hermes窗口发送
>
> 替换所有 `[方括号]` 内容为实际值。
> NTL变体卡定义：{{user}}=NTR施加者（寝取者），主动征服别人爱人。与守护卡的区别：{{user}}身份从原主角变为NTR男性。

---

审查NTL变体卡。**按顺序完成以下步骤。不允许跳过。**

## 0. 跑脚本
```bash
python "<HERMES_HOME>/skills/creative/st-character-card-authoring/scripts/validate_card.py" "[卡文件路径]"
```
修完所有 error。token负载和模板17 warning对NTL卡通常是误报/结构继承。

## 1. 确认{{user}}身份 + system_prompt完整性
读取 system_prompt，明确回答：
- {{user}}=谁？（一句话身份）
- {{user}}的专属特征是什么？（武器/能力/领域/征服手段——列一个清单A）
- 其他NTR男性有哪些？各自的专属特征是什么？（列一个清单B——用于后续区分"合理残留"和"跨卡污染"）

**从哪提取清单B**：读NTR原版卡的NTR男性档案条目，或从计划书/小说分析中提取。

**⚠️ system_prompt完整性**（不只看身份，还要看覆盖）：
```python
# SP中提到的每个系统/机制，是否有对应条目？
sp_systems = ['状态栏', '旁白', '叙事视角', 'NTR关系矩阵', '禁止事项']
for sys in sp_systems:
    found = any(sys in e.get('comment','') or sys in e.get('content','')[:200] for e in entries)
    if not found:
        print(f"🟡 system_prompt提到'{sys}'但无对应条目覆盖")
```
- SP中列出的NTR关系矩阵 → 每个NTR男性是否有独立档案条目？

## 2. 条目类型分类 + 交叉对比
⚠️ **按comment关键词分类，不按ID数字。** 不同卡的ID编号可能不同（有的卡{{user}}主角在ID17而非ID19）。先处理否定——"非{{user}}"的条目是竞争者NPC。

```python
def classify_entry(comment, eid, const):
    if "非{{user}}" in comment: return "竞争者NPC"
    if "{{user}}" in comment or "主角档案" in comment: return "{{user}}主角"
    if any(kw in comment for kw in ["征服阶段","寝取阶段","反抗","当面绿帽","经济控制","暴力控制","伪装"]):
        return "{{user}}征服阶段"
    if const and eid <= 9: return "{{user}}系统"
    if "竞争者" in comment: return "竞争者NPC"
    # ...按实际情况扩展
```

按条目类型分类后扫描：

| 条目类型 | 负向检查 | 正向检查 |
|---------|---------|---------|
| {{user}}系统 | 不应出现清单B中的词 | 应描述清单A中的{{user}}核心规则 |
| {{user}}主角档案 | **绝对不能**出现清单B中的词 | 应完整描述清单A中的身份/武器/手段 |
| {{user}}征服阶段 | 不能把竞争者的手段写成{{user}}的（"你的[竞争者特征]"） | 每个女主应有独立的征服路线 |
| 猎物档案 | 把"对竞争者的反应"写成"对{{user}}的反应" | — |
| 竞争者NPC | 可以出现该竞争者的专属特征词（合理残留） | — |

**⚠️ NTR矩阵覆盖完整性**（有原版卡/规划书时）：
```python
# 从system_prompt或原版卡提取NTR关系矩阵
# 检查每个NTR男性是否有独立档案条目（comment含"档案"）
ntr_males = ['[NTR男1]', '[NTR男2]', ...]  # 从SP/原版卡NTR矩阵提取
for male in ntr_males:
    has_entry = any(male in e.get('comment','') and '档案' in e.get('comment','') for e in entries)
    if not has_entry:
        print(f"🟡 NTR矩阵中的'{male}'无独立档案条目")
```

## 3. 上下文判断（避免假阳性）
关键词扫描必须取前后50字做语义判断。核心原则：**看动作主语是{{user}}还是其他人**。

- `"你的[清单B特征]贯入"` → 🔴 {{user}}没有这个
- `"[清单B特征]"出现在对竞争者的描述句中` → 🟢 描述NPC
- `"[清单B特征]"出现在对话/引诱猎物的语境中` → 🟢 可能是道具/诱饵
- `"不像[竞争者]的[特征]"` → 🟢 对比句式
- **不确定的：取前后80字上下文，人工读一遍再判断**

## 4. 多卡相似度对比（如果有2+张NTL卡）
全部读取，按条目ID做相似度对比（difflib.SequenceMatcher）。关注：
- {{user}}条目（系统/主角/征服阶段）跨卡相似度>85% → 🟡 可能从模板卡复制未充分改写
- 竞争者NPC条目跨卡相似度>85% → 🟢 预期内（同一NPC在不同卡中描述应相同）
- **区分"预期相似"和"应差异化"**：[苦主名]反抗系统在不同卡中应相同（苦主反应不变）；但征服阶段在不同{{user}}手中应不同（手段不同）

## 5. Find-replace残留检查（脚本扫不到的）
人工读{{user}}主角档案和四女档案，搜索以下模式：
- 内容中出现意义不明的括号标记，如"（[某角色]行动）""（已移除）""（已替换）"→ find-replace残留
- 句子读起来不通顺——可能是替换了关键词但没调整语序
- {{user}}的武器/手段被描述成另一个角色的特征

## 6. 输出审查报告
按🔴关键/🟡重要/🟢优化三级。每项给出：位置/上下文/根因/修复建议。

---

要审查的NTL卡目录：[路径]
NTR原版卡（基准）：[路径]
清单A（{{user}}专属特征）：[从Step1提取后填入]
清单B（其他NTR男性特征）：[从Step1提取后填入]
