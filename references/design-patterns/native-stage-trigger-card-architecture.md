# 阶段型小说原生开场标题触发架构

用于阶段递进明显的小说角色卡，尤其是“不绑定固定预设、单文件 Character Card V3、每个阶段加载本阶段全部事件”的卡。

## 默认选择

当前用户工作流中，此架构可作为阶段型小说卡的优先方案：

```text
常驻层
+ 普通场景 selective
+ 阶段 selective（由完整开场标题触发）
+ 当前阶段事件库
```

不依赖专属预设，不依赖模型输出变量，不依赖 EJS/getwi。玩家只需要选择某个开场。

## 关键结构

- 每个 Greeting 写完整自然标题；若使用 initvar，标题放在 `</initvar>` 后；若无 initvar，标题必须是 Greeting 首段，例如 `【开场：秘密日常·稳定时期｜P2】`。
- 阶段包 keys/key 使用完整标题，不能用 `P2`、条目名或短词。
- 阶段包 `enabled=true, constant=false, selective=true`。
- 阶段包单条 `extensions.scan_depth=999`，普通场景条目不升深度。
- P2 主开场和 P2 自由开场共享同一组 P2 阶段包。
- 事件库是当前阶段候选池，由剧情导演协议主动使用；事件进入聊天前不是已发生事实。

## 脚本选配，不是默认依赖

- 不做变量面板/状态恢复的普通卡或原生标题阶段卡：不加 MVU、不写 `<initvar>`、不加隐藏 Regex；阶段标题 + 原生 World Info 已能运行。
- 需要显示开局阶段、地点、关系、人物目标，或需要“重新读取初始变量”：加入 MVU/Tavern Helper 读取 `<initvar>`，再加 Regex 隐藏该技术块。
- 需要同聊天自动阶段升级、事件已用记录、复杂状态机：MVU 只是基础；必须另行构建并实测变量更新/TH脚本链路，不能误以为 MVU 本身会自动加载阶段包。

脚本层只做状态辅助；原生标题阶段包的触发不依赖脚本。没有明确价值时不要引入外链 bundle 依赖。

## 阶段素材密度硬门槛

明确阶段归属的事件种子和素材单元，comment/标题/内部标签必须带阶段标识：`事件种子_P5_01_...`、`成人体验_P5_03_...`、`场景体验_P5_02_...` 等。禁止无阶段标签的“通用事件种子”。

每个阶段的每类阶段包/库至少 6 个详尽素材单元：核心包≥6、成人体验包≥6、场景体验包≥6、事件库≥6；如有关系包/秘密包/策略包，也按≥6执行。优先从小说原文提取场景、对白、心理、动作链；原文不足时允许 agent 基于人物逻辑合理虚构补足，但必须保持原文风味、阶段一致和细节密度。像 P5 体验包只有2个补充、事件库只有4个种子，属于未达标，需补到≥6。

## 触发规则是本架构基础

阶段资料包不是靠玩家输入关键词触发，而是靠开场消息中已经存在的完整阶段标题触发。阶段包单条 `scan_depth=999`，所以 ST 会持续扫描到第一条 Greeting 的标题并持续激活该阶段核心/体验/场景/事件库。

普通场景条目则相反：它们只补充当前/近期场景，不决定阶段，不应 `scan_depth=999`。普通场景 key 必须是玩家会自然输入的简单场景词：`阳台`、`浴室`、`沙发`、`厨房`、`客厅` 等；不要只用“走到阳台栏杆前”这类复杂长句，否则用户输入“阳台”不会触发。

## 产品边界

这是“开场阶段锚定”，不是同聊天自动升级。选 P2 开场就长期加载 P2 资料；若要同聊天 P0→P1→P2 自动切换，必须另做 TH 脚本/按钮或其他经实测可执行的动态路由。

## 验证

- root.first_mes == data.first_mes；
- EJS残留为0；
- Greeting标题存在且与阶段 keys/key 同步；若使用initvar，再检查每条initvar可解析、其stage与标题阶段一致；
- 先加载 `standalone-card-stage-routing`。生产验证必须经合同派生 manifest 执行：`python <主skill>/scripts/final_delivery_gate.py <card.json> --native-stage-routing --stage-entry-contract <项目>/stage-entry-contract.json`；单独运行其 `scripts/audit_native_stage_architecture.py <card.json>` 时必须显式传 `--manifest`（无 `--manifest` 的默认 P0-P6 仅适用遗留 P0-P6 卡）。阶段集以合同声明为准，禁止为凑 P0-P6 伪造阶段；每个声明阶段仍须四包齐全、每包≥6、标题keys精确、阶段scan_depth=999、普通场景不抢999；
- 再运行其 `scripts/audit_stage_card_scripts.py <card.json>`：无脚本原生卡也必须通过；含initvar时强制MVU+隐藏Regex，MVU的export_with必须是对象；
- 每个Greeting必须只命中本阶段包、不命中其他阶段；普通场景因 Greeting 内真实场景词命中时只作相关性报告，不判为阶段失败；
- 阶段包数量、keys/key同步、scan_depth=999、prevent/exclude_recursion=true；
- 普通场景不含阶段标题、不scan_depth=999；
- WorldInfoInfo/Prompt Itemization实测确认阶段包激活。

专项细节见 `standalone-card-stage-routing` 的 `references/staged-novel-native-trigger-architecture.md`。
