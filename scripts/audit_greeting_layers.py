#!/usr/bin/env python3
"""Audit hybrid Greeting layout: natural prose first, director appendix last.

The body and appendix are intentionally audited separately. The body must be
natural prose and contain roughly 1,500 CJK characters; the appendix is excluded
from that count and must use a visibly distinct Markdown style.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
DELIMITER_RE = re.compile(r"(?m)^\s*---\s*$")
TITLE_RE = re.compile(r"^\s*【[^\n】]+】\s*$")

# These are strong production/meta signals. Broad everyday words such as
# "当前" or "阶段" alone are deliberately excluded to avoid false positives.
POLLUTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"导演附录|导演规则|背景大纲", "导演附录/大纲语言"),
    (r"当前阶段|阶段包|阶段规则|阶段路由", "阶段路由语言"),
    (r"信息边界|玩家代理|玩家接管点", "玩家/信息边界语言"),
    (r"候选事件|事件候选|事件库|剧情种子", "事件库语言"),
    (r"禁止提前泄漏|不得提前泄漏|不可提前泄漏", "泄漏控制语言"),
    (r"NPC正在(?:行动|做什么)|NPC目标|NPC行动方向", "NPC导演语言"),
    (r"以下内容用于|供AI|给AI|生成规范|输出规范", "模型指令语言"),
    (r"世界书|World\s*Info|scan_depth|secondary_keys|selective", "工程实现语言"),
    (r"验证器|构建字段|条目key|触发锚点|触发条件", "构建/验证语言"),
)

STAGE_BRIEF_DIMENSIONS: tuple[str, ...] = (
    "当前节点",
    "人物状态",
    "情报边界",
    "推演方向",
    "关键冲突",
    "角色预计动向",
    "场景氛围",
    "潜在分歧点",
)
APPENDIX_STANDARD_MIN_CJK = {"stage_brief_v1": 800}


def cjk_count(text: str) -> int:
    return len(CJK_RE.findall(text))


def audit_appendix_standard(appendix: str, standard: str | None) -> list[dict[str, str]]:
    """Audit the optional content contract for a director appendix."""
    if not standard or standard == "none":
        return []
    if standard != "stage_brief_v1":
        return [{
            "severity": "error",
            "code": "UNKNOWN_APPENDIX_STANDARD",
            "message": f"不支持的导演附录标准：{standard}",
        }]

    issues: list[dict[str, str]] = []
    appendix_cjk = cjk_count(appendix)
    minimum = APPENDIX_STANDARD_MIN_CJK[standard]
    if appendix_cjk < minimum:
        issues.append({
            "severity": "error",
            "code": "APPENDIX_TOO_SHORT",
            "message": f"导演附录纯汉字 {appendix_cjk} 字，低于 {standard} 最低值 {minimum}",
        })

    positions: list[tuple[int, str]] = []
    for dimension in STAGE_BRIEF_DIMENSIONS:
        matches = list(re.finditer(re.escape(dimension), appendix))
        if not matches:
            issues.append({
                "severity": "error",
                "code": "APPENDIX_DIMENSION_MISSING",
                "message": f"{standard} 缺少维度：{dimension}",
            })
        else:
            positions.append((matches[0].start(), dimension))

    # A heading may exist while its section remains empty. Measure the text up
    # to the next known dimension rather than the whole appendix.
    ordered = sorted(positions)
    for index, (start, dimension) in enumerate(ordered):
        end = ordered[index + 1][0] if index + 1 < len(ordered) else len(appendix)
        section = appendix[start + len(dimension):end]
        if cjk_count(section) < 20:
            issues.append({
                "severity": "error",
                "code": "APPENDIX_DIMENSION_THIN",
                "message": f"{standard} 维度“{dimension}”缺少实质内容（纯汉字少于20）",
            })
    return issues


def split_layers(greeting: str) -> tuple[str, str, list[dict[str, str]]]:
    """Return (body, appendix, issues) using the first standalone --- boundary."""
    issues: list[dict[str, str]] = []
    match = DELIMITER_RE.search(greeting)
    if not match:
        return greeting.strip(), "", [{"severity": "error", "code": "MISSING_DELIMITER", "message": "缺少独立的 --- 正文/附录分隔线"}]

    body = greeting[:match.start()].strip()
    appendix = greeting[match.end():].strip()
    if not appendix:
        issues.append({"severity": "error", "code": "EMPTY_APPENDIX", "message": "分隔线后没有导演附录"})
    return body, appendix, issues


def remove_title(body: str) -> str:
    lines = body.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and TITLE_RE.match(lines[0]):
        lines.pop(0)
    return "\n".join(lines).strip()


def audit_one(
    greeting: str,
    label: str,
    min_cn: int,
    max_cn: int,
    appendix_standard: str | None = None,
) -> dict[str, Any]:
    body_with_title, appendix, issues = split_layers(greeting)
    body = remove_title(body_with_title)
    count = cjk_count(body)

    if count < min_cn:
        issues.append({"severity": "error", "code": "BODY_TOO_SHORT", "message": f"正文纯汉字 {count} 字，低于最低值 {min_cn}（导演附录未计入）"})
    elif count > max_cn:
        issues.append({"severity": "warning", "code": "BODY_TOO_LONG", "message": f"正文纯汉字 {count} 字，高于建议上限 {max_cn}（导演附录未计入）"})

    for pattern, category in POLLUTION_PATTERNS:
        found = re.findall(pattern, body, flags=re.I)
        if found:
            issues.append({"severity": "error", "code": "BODY_POLLUTED", "message": f"正文出现{category}：{', '.join(dict.fromkeys(found))}"})

    # Normal prose must not itself look like a Markdown appendix.
    for i, line in enumerate(body.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith(">") or stripped.startswith("- **") or stripped.startswith("* **"):
            issues.append({"severity": "error", "code": "BODY_SPECIAL_MARKUP", "message": f"正文第{i}行使用了附录式Markdown排版"})
            break

    if appendix and "导演附录" not in appendix:
        issues.append({"severity": "error", "code": "APPENDIX_UNMARKED", "message": "附录没有明确的“导演附录”标题"})
    if appendix and not re.search(r"(?:>\s*)?\*\*[^\n]*导演附录|(?:>\s*)?\*[^\n]*导演附录", appendix):
        issues.append({"severity": "error", "code": "APPENDIX_NOT_DISTINCT", "message": "导演附录没有使用加粗或斜体等特殊排版"})
    if appendix and not re.search(r"(?m)^\s*>", appendix):
        issues.append({"severity": "warning", "code": "APPENDIX_NOT_QUOTED", "message": "导演附录未使用引用块；建议用引用块强化视觉区分"})

    issues.extend(audit_appendix_standard(appendix, appendix_standard))

    return {
        "label": label,
        "body_cjk": count,
        "body_chars": len(body),
        "appendix_chars": len(appendix),
        "appendix_cjk": cjk_count(appendix),
        "appendix_standard": appendix_standard or "none",
        "issues": issues,
        "passed": not any(x["severity"] == "error" for x in issues),
    }


def get_greetings(card: dict[str, Any]) -> list[tuple[str, str]]:
    """Extract Greetings from either a CCv3 card or build/greetings.json."""
    data = card.get("data", card)
    result: list[tuple[str, str]] = []
    if isinstance(data.get("first_mes"), str):
        result.append(("first_mes", data["first_mes"]))
    for i, text in enumerate(data.get("alternate_greetings", []) or [], 1):
        if isinstance(text, str):
            result.append((f"alternate_greetings[{i}]", text))
    # prepare_build.py emits a stage-keyed mapping, e.g. {"P0": "..."}.
    # Do not treat arbitrary card metadata as Greetings: every value must be text.
    if not result and isinstance(card, dict) and card and all(isinstance(v, str) for v in card.values()):
        result.extend((str(label), text) for label, text in card.items())
    return result


def run_self_test() -> int:
    prose = ("夜色压在窗玻璃上，楼下的车灯从墙面缓慢掠过。李彤彤把文件收进抽屉，却没有锁上，项月心站在门边，手指轻轻敲着桌面。她们显然已经谈了很久，但谁也没有先说出那个名字。电话再次响起，李彤彤没有接，只把目光投向门口，等着李翔决定是否走近。")
    prose = prose * 15
    valid = "【开场：测试】\n" + prose + "\n\n---\n\n> **导演附录｜当前阶段背景**\n>\n> *只供模型维持背景，不是角色台词。*\n\n> **NPC正在行动**：项月心等待李翔回应。"
    polluted = "【开场：测试】\n" + prose.replace("李彤彤把", "当前阶段要求：李彤彤把", 1) + "\n\n---\n\n> **导演附录｜当前阶段背景**\n>\n> **信息边界**：后续秘密不可提前泄漏。"
    short = "【开场：测试】\n夜雨落在窗台。\n\n---\n\n> **导演附录｜当前阶段背景**\n>\n> **玩家接管点**：等待输入。"
    cases = [("valid", valid, True), ("polluted", polluted, False), ("short", short, False)]
    failed = False
    for label, text, expected in cases:
        result = audit_one(text, label, 1400, 1800)
        actual = result["passed"]
        print(f"{label}: passed={actual}, body_cjk={result['body_cjk']}")
        if actual != expected:
            failed = True
            print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Greeting natural-prose body and director appendix in a CCv3 card or build/greetings.json")
    parser.add_argument("card", nargs="?", help="CCv3 JSON card path")
    parser.add_argument("--min-cn", type=int, default=1400, help="minimum CJK characters in prose body (default: 1400)")
    parser.add_argument("--max-cn", type=int, default=1800, help="warning threshold for prose body (default: 1800)")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--appendix-standard", choices=("none", "stage_brief_v1"), default="none", help="optional director appendix content contract")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()
    if not args.card:
        parser.error("需要卡片JSON路径，或使用 --self-test")

    path = Path(args.card)
    try:
        card = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(f"ERROR: 无法读取JSON: {exc}", file=sys.stderr)
        return 2

    results = [audit_one(text, label, args.min_cn, args.max_cn, args.appendix_standard) for label, text in get_greetings(card)]
    if not results:
        print("ERROR: 未找到first_mes或alternate_greetings", file=sys.stderr)
        return 2

    failed = any(not r["passed"] or (args.strict and r["issues"]) for r in results)
    if args.format == "json":
        print(json.dumps({"card": str(path), "min_cn": args.min_cn, "max_cn": args.max_cn, "appendix_standard": args.appendix_standard, "passed": not failed, "greetings": results}, ensure_ascii=False, indent=2))
    else:
        print(f"Greeting layer audit: {'PASS' if not failed else 'FAIL'} | body target={args.min_cn}-{args.max_cn} CJK (appendix excluded) | appendix_standard={args.appendix_standard}")
        for r in results:
            print(f"- {r['label']}: body_cjk={r['body_cjk']}, appendix_chars={r['appendix_chars']}, {'PASS' if r['passed'] else 'FAIL'}")
            for issue in r["issues"]:
                print(f"  {issue['severity'].upper()} {issue['code']}: {issue['message']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
