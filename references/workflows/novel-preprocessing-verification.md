# 小说全方位提取报告交叉验证流程

> 当另一个窗口产出了一份「全方位预处理提取」.md 报告后，用本流程验证报告的准确性。
> 验证窗口不需要重读全文——只做抽样核验。

## 触发条件

- 收到另一窗口的全方位提取报告需要质检
- 用户说"看看报告是否真实"、"对照原文验证"

## Step 1：基础统计验证（Python 脚本，2分钟）

```python
import os, re
from collections import Counter

d = r'<小说目录路径>'
all_txt = sorted([f for f in os.listdir(d) if f.endswith('.txt')])

# 章节数：区分章节文件、序章、非章节文件
chapters = [f for f in all_txt if re.match(r'第\d+章', f)]
prologue = [f for f in all_txt if '序章' in f]
other = [f for f in all_txt if f not in chapters and f not in prologue]
print(f'章节文件: {len(chapters)}, 序章: {len(prologue)}, 其他: {len(other)}')

# 提取章节号，检测缺号/重号
nums = sorted([int(re.match(r'第(\d+)章', f).group(1)) for f in chapters])
expected = set(range(nums[0], nums[-1]+1))
missing = expected - set(nums)
dupes = {k for k,v in Counter(nums).items() if v > 1}
if missing: print(f'⚠️ 缺失章节: {sorted(missing)}')
if dupes: print(f'⚠️ 重复章节: {sorted(dupes)}')

# 总字数
total_chars = 0
cn_chars = 0
for f in all_txt:
    with open(os.path.join(d, f), encoding='utf-8-sig') as fh:
        text = fh.read()
        total_chars += len(text)
        cn_chars += sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
print(f'总字符: {total_chars}, 中文字: {cn_chars}')
```

**验证项**：报告的章节数、总字数、中文字数是否与脚本输出基本一致（误差<1%即可接受）。

## Step 2：角色频次验证（Python 脚本，1分钟）

```python
# 扫描报告提到的所有角色名
names_to_check = ['角色A', '角色B', ...]  # 从报告中提取
counts = {}
for f in all_txt:
    with open(os.path.join(d, f), encoding='utf-8-sig') as fh:
        text = fh.read()
        for name in names_to_check:
            counts[name] = counts.get(name, 0) + text.count(name)
for name, c in sorted(counts.items(), key=lambda x: -x[1]):
    print(f'{name}: {c}')
```

**验证项**：报告中的角色频次数字是否匹配（允许±5的误差）。

## Step 3：关键对话/引用抽查（5分钟）

对报告中每个角色的「对话样本」，抽查 2-3 句：

1. 从引用中取**5-8个连续汉字**的独特子串（不要取太通用的词如"阿姨"）
2. 用 Python 搜索确认存在于原文中：
   ```python
   for f in all_txt:
       with open(os.path.join(d, f), encoding='utf-8-sig') as fh:
           if '独特子串' in fh.read():
               print(f'✅ 找到于: {f}')
               break
   ```
3. 确认报告标注的**章节号**与实际文件一致
4. 如果报告引用了整句话，读出上下文验证是否被断章取义

## Step 4：事件/设定交叉验证（5分钟）

针对报告中的以下高风险项，各抽查 2-3 个：

| 类型 | 验证方法 |
|------|---------|
| **事件章节归属** | 搜索事件关键词（如"九局五胜"）确认在报告标注的章节中 |
| **机制/设定数字** | 搜索具体数字（如"192小时"）确认原文中存在 |
| **角色出场章节** | 搜索角色名，检查报告标注的章节是否都有出现，以及是否漏标 |
| **场景描述** | 搜索场景关键词（如"木栈道""喷泉"）确认存在 |

## Step 5：报告自身一致性检查（3分钟）

- [ ] 报告声称的覆盖度是否与实际内容匹配（如"120章全部扫描"但事件时间线中后段明显稀疏）
- [ ] 同一角色是否有重复条目（如档案写了两次）
- [ ] 引用的对话是否与角色档案中的"语言指纹"自洽
- [ ] 做卡建议中的章节编号是否与事件时间线中的章节编号一致

## 常见报告质量问题

| 问题 | 严重度 | 说明 |
|------|--------|------|
| 章节号偏移1位 | 🟡 轻微 | 如报告说"第54章"但实际在第55章，"第X章起"的表述有时能包容 |
| 角色频次偏差<5 | 🟢 极轻 | 计数方法差异可接受 |
| 角色出场章节错误 | 🟡 轻微 | 如报告说"第109章"但该角色实际不在该章 |
| 机制/数字不存在 | 🔴 严重 | 如"192小时协议"在原文中搜不到=报告可能虚构 |
| 对话引用无法查证 | 🔴 严重 | 报告可能捏造对话 |
| 覆盖度声明与内容不符 | 🟡 轻微 | 如声称"全文扫描"但中段内容稀疏 |

## 输出格式

验证完成后输出结构化报告：

```
### ✅ 已验证正确的项目（列出所有通过的维度）
### ⚠️ 发现的问题（按严重度排序）
### 📊 总体评价（1-5星 + 结论）
```

## 技术陷阱

- **search_files 对 CJK 失效**：utf-8-sig 文件中部分中文词 search_files 返回0。一律用 Python `str.count()` 验证（见 T106）
- **章节文件命名格式**：有些目录包含"第X章"开头的非章节文件（如"第51-80章详细总结报告.txt"），需要用 `re.match(r'第\d+章', f)` 精确匹配
- **序章不被正则捕获**：统计章节数时需单独检查"序章"文件
