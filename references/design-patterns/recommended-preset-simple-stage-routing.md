# 推荐预设版：阶段P# 简化触发路由

适用场景：SillyTavern 角色卡需要发布给普通用户，配套推荐预设可稳定输出状态栏/route_state；复杂 `ROUTE_STAGE=P#`、secondary 过滤或自然语言关键词导致条目漏触发，而裸 `P1/P2` 又会被用户切阶段指令误撞。

## 核心原则

发布友好版优先保证稳定触发：

```text
状态栏输出 阶段P1 → 世界书加载 阶段P1 条目
状态栏输出 阶段P2 → 世界书加载 阶段P2 条目
```

不要同时混用复杂自然语言 key、`ROUTE_STAGE=P#`、`当前阶段：P#`、事件 marker 和 secondary 过滤器。

## 推荐 route_state 格式

预设每轮在正文前输出且只输出一个：

```xml
<route_state>
阶段P#
</route_state>
```

其中 `阶段P#` 只能是 `阶段P0`-`阶段P6`。不要输出 `ROUTE_STAGE` / `ROUTE_MODE` / `ROUTE_EVENT` / `ROUTE_SCENE` 等复杂字段。

## 为什么不用裸 P#

裸 `P1/P2` 会被用户自然切阶段指令撞上：

```text
上一轮 AI：<route_state> P1 </route_state>
当前用户：进入P2
scan_depth=2 同时扫描到 P1 + P2 → 双阶段触发
```

改成 `阶段P2` 后，用户说“进入P2”不会命中；只有预设输出 `<route_state>阶段P2</route_state>` 后，下一轮才触发新阶段。

## 角色卡世界书修改规则

对阶段相关条目：

```json
{
  "keys": ["阶段P1"],
  "secondary_keys": [],
  "selective": false,
  "extensions": {
    "selective": false,
    "scan_depth": 2,
    "match_whole_words": false,
    "sticky": 0
  }
}
```

多阶段场景可用：

```json
"keys": ["阶段P2", "阶段P3", "阶段P4"]
```

基础人物档案不必强行改成全阶段触发；若已用角色名稳定触发，可保留，避免全阶段常驻抬高负载。

## 预设修改规则

- 使用独立变量，如 `route_state_top`，不要抢 `status_top`。
- Core 中放在 `status_top` 前：`{{getvar::route_state_top}}`。
- 如需隐藏显示，regex 只能影响显示，不能删除 outgoing prompt。
- HTML 注释删除 regex 可保留，因为 route_state 不使用 `<!-- -->`。

## 验证门控

必须跑：

1. `validate_card.py`：errors=0。
2. `enrichment_self_check.py --r18`：0🔴；少量 OOC 黄项可人工接受。
3. `audit_worldbook_triggers.py`：硬风险 0。
4. 路由契约脚本（先跑）：
   ```bash
   python scripts/verify_simple_stage_route.py <卡.json> \
     --forbid ROUTE_STAGE --forbid ROUTE_MODE --forbid '当前阶段：'
   ```
   脚本强制检查每条 greeting 恰有一个 `<route_state>阶段P#</route_state>`、P0-P6 均有冷启动入口、阶段条目不混入其他 key/secondary/selective、`scan_depth=2`，并扫描旧锚点残留。
5. 静态扫描（脚本通过后抽查）：
   - greeting route_state 只包含 `阶段P#`。
   - card/preset 中无 `ROUTE_STAGE` / `ROUTE_MODE` 残留。
   - 阶段相关条目无 secondary 残留。
   - 顶层 `selective` 与 `extensions.selective` 同步。
   - 阶段 key 条目 `scan_depth=2`。
   - 裸 `P0/P1/.../P6` 不作为世界书 key 残留。
6. 双阶段反证模拟：
   - `阶段P1 + 进入P2` 只能触发 P1 条目。
   - `阶段P1 + 以后P4会怎样` 只能触发 P1 条目。
   - `进入P2` 本身不得触发 P2。

## 取舍

这会导致同一阶段下加载更多条目，可能出现高负载 warning；这是发布友好版的可接受取舍。优先级：稳定触发 > 极限省 token。
