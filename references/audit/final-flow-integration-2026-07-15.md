# 2026-07-15 全流程整合终审知识沉淀

## 适用场景
当用户要求“最终审查/完善 skill 流程/让 agent 完整跑通制卡流程”时，不能只改 `SKILL.md` 或只写报告；必须把审查发现落到 **主流程入口 + 模板 + 参考文档 + 可执行脚本门控** 四层，并用最小 fixture 验证闭环。

## 关键裁决
本次终审发现：主流程文档已经较完整，真正会让后续 agent 跑错的风险在脚本和引用文件不闭环：

- `fix_card_format.py` 修出来的卡必须能被 `validate_card.py` 通过；否则“自动修复”是伪闭环。
- high token 不是硬错误；触发质量才是硬问题。不要为了压 token 把核心角色档案唯一 key 改成 `角色名档案/设定`，这会制造死 key。
- G 型默认是选开模式；Greeting 模式只是发布/免 UI 操作备选。审查必须拆成 G-Common / 选开专项 / Greeting 专项。
- 加料自检必须有退出码门控：任何 🔴 或 `🟡 >= 3` 都不能交付。
- 修卡不是只改截图处；必须跑 baseline、全卡 scan list、修后 validate、触发审计回归，必要时 enrichment。

## 四层回灌清单

### 1. SKILL.md 主入口
必须让 agent 从快速索引/决策树/构建阶段/交付门控/审查模板表自然抵达新规则。新增模式时用 6 点自检：

1. 决策树是否有入口？
2. 原型表是否有行？
3. 模板匹配是否能选中？
4. 构建阶段是否有步骤？
5. 交付门控是否引用？
6. 审查模板和 §7 索引是否有指针？

### 2. 脚本闭环
- `validate_card.py`：负责硬门控，不只提示。
- `fix_card_format.py`：负责生成能通过 validate 的结构。
- `audit_worldbook_triggers.py`：负责触发可达性、泛 key、死 key、无关污染。
- `enrichment_self_check.py`：负责内容厚度/语料/速览/关系条目门控，并用退出码表达失败。

### 3. 模板/参考文档
模板负责让 agent 知道“什么时候跑什么脚本”和“人工要看什么”。参考文档负责保存具体坑点、案例和解释。两者不能互相替代。

### 4. 最小 fixture 验证
完成 skill 修复后至少构造临时卡验证：

- 合法最小卡 validate 通过；
- top/data `first_mes` 不一致会报错；
- 重复开场白/重复旁白会报错；
- 核心档案只有 `角色名档案/设定` 会报死 key；
- fix 后再 validate 能通过；
- enrichment 有 🔴 或 >=3 🟡 时返回非零退出码；
- audit 报告能把死 key 放入硬风险。

## 反模式

- 只写一份终审报告，不改 skill/script。
- 只 patch `SKILL.md`，不改脚本门控。
- 只改脚本，不把新规则写回模板，导致下次 agent 不知道要跑。
- 把外部预设/API/模型安全截断当成卡质量失败；skill 只审卡内世界书触发、常驻、内容厚度和结构。
- 用固定 token 阈值替代触发质量判断。

## 推荐最终汇报格式
向用户汇报时必须包含：

1. 已修改文件列表；
2. 已修复的问题类别；
3. 实际验证命令与结果；
4. 仍保留的 P2/非阻塞项；
5. 备份位置。

## 2026-07-15 终极复核追加（v6.42 / scripts v5.1）

终审报告通过后仍要做“反向最小 fixture”复核：不要只验证脚本能抓旧问题，还要验证修复脚本不会制造新问题、内容门控不会误杀系统条目。本轮追加发现并修复三类二阶断点：

1. `fix_card_format.py v5.0` 会把旧卡 numeric `position=0` 错映射为 `after_char`，并且 top `position='before_char' + extensions={}` 会修后 validate 失败。v5.1 增加 `POS_NUM_TO_STR/POS_STR_TO_NUM`，保留 before/after 语义并同步 `extensions.position`。
2. `fix_card_format.py v5.0` 没补齐旧条目的 `constant/enabled/insertion_order/secondary_keys` 等顶层必填字段。v5.1 在字段名迁移后统一 `setdefault`，旧稀疏条目能进入 validate 闭环。
3. `enrichment_self_check.py v5.0` 把任何 comment 含 `NTR` 的条目都当 NTR 关系条目，导致 `NTR叙事节奏规则` 这类系统条目被 600 字关系门控误杀。v5.1 改为只识别 `× / NTR关系 / NTR线 / NTR矩阵 / 关系矩阵 / 攻略线 / 侵犯史 / 堕落线` 等真正关系/矩阵条目。

追加回归建议：

- fix 旧卡 fixture：`position='before_char' + extensions={}` → 修后 validate 必须通过，且 `extensions.position=0`。
- fix 旧卡 fixture：`position=0` → 修后仍为 `before_char`，不能被改成 `after_char`。
- fix 稀疏条目 fixture：只有 `uid/key/comment/content/position` → 修后不应因缺顶层字段失败。
- enrichment fixture：`NTR叙事节奏规则` 不应触发 NTR关系厚度 🔴；`男主×女主` 或 `NTR关系` 仍应触发关系门控。
