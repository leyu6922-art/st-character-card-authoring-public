# ST 截断诊断完整流程

## 第一步：区分截断类型

截断有两种完全不同的根因，修复方式完全不同：

| 类型 | 症状 | 根因 | 修复 |
|------|------|------|------|
| **API预设膨胀** | 第一次发消息就被截断，第二次能跑 | 系统提示总token > max_context - max_tokens | 调ST设置/精简预设 |
| **世界书过载** | 每次回复都变短或截断 | 世界书条目总token过高 | 优化关键词/减少条目 |

**关键判断方法**：如果第一次截断、第二次正常 → 大概率是API预设膨胀，不是世界书问题。

## 第二步：如果是API预设膨胀

### 诊断方法
让用户提供ST的API请求日志（ST设置 → View Logs → 找到请求），分解各部分token：

```
SYSTEM消息总token = 角色卡system_prompt + 世界书条目 + 预设规则 + H-Guide + COT + Prism + ...
ASSISTANT消息token = 开场白 + 创作者备注 + 历史回复
USER消息token = 用户输入
```

### 常见膨胀来源（实测案例）
1. **预设规则重复加载** — 活人感基准、叙事推进基准、H特写规则各出现2次 → ~8000 tokens浪费
2. **创作者长信/作者备注** — 占ASSISTANT消息 → ~3500 tokens，不在世界书里
3. **H-Guide + Prism + COT** — 每次请求全量注入 → ~3000 tokens
4. **世界书条目** — 实际只占一小部分 → ~3000 tokens

### 修复方法
1. ST设置：max_context 调到 65536+，max_tokens 调到 3000-4000
2. 检查预设为什么规则重复加载（可能是预设+角色卡双重注入）
3. 创作者备注移到角色卡描述里，或用正则脚本在非首轮删除
4. 精简不必要的预设规则

## 第三步：如果是世界书过载

使用自动化脚本诊断：

```python
# Token负载分析
exec(open('<HERMES_HOME>/skills/creative/st-character-card-authoring/scripts/analyze_token_load.py').read())
analyze_token_load('/path/to/card.json')

# 自动优化
exec(open('<HERMES_HOME>/skills/creative/st-character-card-authoring/scripts/fix_card_format.py').read())
optimize_token_load('/path/to/card.json')
```

### Token预算参考
| 负载 | tokens | 状态 |
|------|--------|------|
| < 4000 | < 2000 | ✅ 优秀 |
| 4000-8000 | 2000-4000 | ✅ 正常 |
| 8000-12000 | 4000-6000 | ⚠️ 偏高 |
| > 12000 | > 6000 | ❌ 过高 |

### 优化4策略
1. 常驻条目 keys=[]（不带关键词）
2. 复合关键词（"{角色}身体描写" 而非 "{角色名}"）
3. 常驻转触发（只保留4-6条核心常驻）
4. 性爱规则按需加载（>800c的条目不放常驻）
