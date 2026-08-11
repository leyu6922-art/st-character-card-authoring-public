# 修卡工作流（社区反馈/逻辑修复）

> 用于已发布/已交付角色卡收到反馈后的修复。修卡不是只改截图处：必须最小改动，但形成“反馈→全卡扫描→基线→修复→回归验证→报告”的闭环。

## 修卡 vs 增强

| 维度 | 修卡 | 增强/加厚 |
|---|---|---|
| 触发 | 社区反馈、逻辑漏洞、触发异常、导入问题 | 用户要求加厚、增加角色/语料/事件 |
| 原则 | 最小改动，保留原卡体验 | 扩充内容，可新增较多条目 |
| 必跑 | validate + 触发审计回归 | validate + 加料自检 + 触发审计 |

## 标准闭环

0. **备份与记录**
   - 复制原卡：`原文件.json.bak` 或另存版本号。
   - 保存反馈原话/截图要点：谁反馈、哪一轮、哪张卡版本、模型/预设（如果有）。

1. **反馈分类**
   - 内容错误：人物、剧情、设定、关系称谓。
   - 触发异常：泛key、secondary失效、条目不触发、误触发。
   - 结构导入：v3字段、extensions、addMemo、world绑定。
   - 截断/回空：先区分卡内问题 vs 运行环境。
   - 发布问题：Discord简介/违禁词/字段展示。

2. **不要只改截图处：生成全卡 scan list**
   - 从反馈中提取角色名、关系词、地点、机制词、key词。
   - 全卡扫描：description/system_prompt/first_mes/alternate_greetings/entry comment/keys/secondary_keys/content。
   - 关系类反馈重点扫：`自己的妹妹|亲妹妹|亲生母亲|自己的母亲|父亲|公公|婆婆|儿媳|侍妾|丫鬟|主人`。

3. **修改前跑 baseline**
   ```bash
   python scripts/validate_card.py <卡.json>
   python scripts/audit_worldbook_triggers.py <卡.json> -o <修前触发审计.md>
   ```
   必要时跑：
   ```bash
   python scripts/enrichment_self_check.py <卡.json>
   ```
   记录哪些是旧问题，哪些是本次反馈相关问题。

4. **设计最小修复方案**
   - 只改目标条目与被 scan list 命中的波及条目。
   - 大段中文内容用 file-first 模式：先写 `.txt`，再由 Python 读取组装。
   - 新增条目必须从完整 extensions 模板复制，保持 v3 字段一致。
   - 若改 `keys/secondary_keys/selective/constant/enabled/prevent_recursion/system_prompt/G型身份条目/greeting身份标记`，即使只改1条，也升级为触发专项回归。

5. **执行修改**
   - 新增条目：ID连续、display_index同步、addMemo双写。
   - 改现有条目：先按 comment/id 定位目标条目，再替换 content；不要全局 `str.replace`。
   - 删除/裁剪角色：同时扫系统条目、状态栏、开场白、事件种子中的残留引用。

6. **修改后回归验证**
   ```bash
   python scripts/validate_card.py <修后卡.json>
   python scripts/audit_worldbook_triggers.py <修后卡.json> -o <修后触发审计.md>
   ```
   验证目标：
   - 本次引入 error = 0。
   - 触发相关修复要有前后对比：secondary被忽略、泛key、普通句反证、first_mes触发条目。
   - 如果新增/重写内容，再跑 `enrichment_self_check.py`。
   - 如果涉及 Discord/社区发布或过审，只扫描简介/帖子等平台可见文案；普通本地卡与卡 JSON 不把该项作为阻塞。

7. **升级条件**
   以下任一满足，停止“外科手术式修卡”，改走完整制卡/全量审查门控：
   - 改动范围 >15条 或 >50%条目。
   - 改了系统提示、G型身份模式、世界书触发策略、常驻结构。
   - 触发审计显示大量旧结构腐烂：泛key多、secondary大面积失效、多主题大条目普遍存在。
   - 关系矩阵/身份锚点需要整体重写。

8. **输出修卡报告**
   报告必须包含：
   - 原反馈与分类。
   - 全卡扫描命中范围。
   - 修改条目列表和修改理由。
   - validate 结果。
   - 触发审计前后核心指标。
   - 遗留风险：哪些是运行环境问题，哪些是旧卡非本次范围问题。

## 常见陷阱

- **只改截图处**：关系称谓/触发key通常全卡多处同源错误，必须 scan list。
- **未跑修前 baseline**：无法判断问题是旧卡已有还是本次引入。
- **常驻 keys 误改**：普通常驻必须 `keys=[]`；选开身份是 `constant=true + enabled=false + comment含选开` 的例外。
- **触发字段小改不回归**：keys/secondary/selective 的小改也可能改变整轮加载。
- **外部预设背锅**：若触发审计通过、同卡多轮稳定，偶发截断按 `card-vs-runtime-boundary.md` 备注，不判卡失败。
