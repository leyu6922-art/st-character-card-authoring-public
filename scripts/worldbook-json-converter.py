#!/usr/bin/env python3
"""
SillyTavern 世界书 JSON 转换器
将分批撰写的 Markdown 条目自动组装为 SillyTavern 可导入的 JSON 文件。

使用方法：
1. 定义 entries 列表（每个条目的元数据）
2. 将条目正文写入 markdown 文件，用 ## 标题分隔各条目
3. 运行此脚本自动提取并组装

关键字段说明：
- uid: 唯一ID（从0开始）
- key: 主关键词列表（触发激活）
- keysecondary: 次要关键词列表（selective模式下需同时匹配）
- constant: True=常驻激活, False=关键词触发
- selective: True=需要同时匹配主次关键词
- order: 同位置排序优先级（数字越大越靠前）
- position: 0=角色定义前, 1=角色定义后
"""
import json
import re
import os

def extract_section(content, section_name):
    """从markdown中提取指定section的内容（两个##标题之间的部分）。"""
    pattern = rf'(?:^|\n)## {re.escape(section_name)}'
    match = re.search(pattern, content)
    if not match:
        for line in content.split('\n'):
            if section_name in line and line.startswith('##'):
                match = re.search(re.escape(line.strip()), content)
                break
    if not match:
        return f"[Section not found: {section_name}]"

    start = match.start()
    if start > 0 and content[start] == '\n':
        start += 1

    rest = content[start:]
    lines = rest.split('\n')
    end_offset = len(rest)
    first_line = True
    for i, line in enumerate(lines):
        if first_line:
            first_line = False
            continue
        if line.startswith('## ') and not line.startswith('### '):
            end_offset = sum(len(l) + 1 for l in lines[:i])
            break

    section_content = rest[:end_offset].strip()
    section_content = re.sub(r'^## .+\n+', '', section_content)
    return section_content.strip()


def build_worldbook(entries, content_files, name, description, scan_depth=100, token_budget=5000):
    """构建 SillyTavern 世界书 JSON。"""
    world_book = {
        "entries": {},
        "name": name,
        "description": description,
        "scan_depth": scan_depth,
        "token_budget": token_budget,
        "recursive_scanning": True,
        "extensions": {
            "position": 0,
            "override_presets": {},
            "prompt_budget": 100
        }
    }

    for entry_def in entries:
        uid = entry_def["uid"]
        content = extract_section(content_files[entry_def["content_file"]], entry_def["section"])

        st_entry = {
            "uid": uid,
            "key": entry_def["key"],
            "keysecondary": entry_def.get("keysecondary", []),
            "comment": entry_def["comment"],
            "content": content,
            "constant": entry_def["constant"],
            "vectorized": False,
            "selective": entry_def.get("selective", not entry_def["constant"]),
            "addMemo": True,
            "order": entry_def.get("order", 50),
            "position": entry_def.get("position", 0),
            "disable": False,
            "excludeRecursion": False,
            "preventRecursion": False,
            "delayUntilRecursion": False,
            "probability": 100,
            "useProbability": True,
            "depth": 4,
            "group": "",
            "groupOverride": False,
            "groupWeight": 100,
            "scanDepth": None,
            "caseSensitive": None,
            "matchWholeWords": None,
            "automationId": "",
            "role": None,
            "vectorModel": "",
            "embeddingModel": "",
            "extensions": {
                "position": 0,
                "role": None,
                "scan_depth": None,
                "case_sensitive": None,
                "match_whole_words": None,
                "automation_id": None,
                "vector_model": "",
                "embedding_model": "",
            }
        }
        world_book["entries"][str(uid)] = st_entry

    return world_book


# === 示例用法 ===
if __name__ == "__main__":
    BASE_DIR = "/path/to/your/worldbook"

    # 1. 定义条目元数据
    entries = [
        {
            "uid": 0,
            "comment": "00-原著兼容总则",
            "key": ["兼容", "总则"],
            "constant": True,
            "order": 100,
            "content_file": "part1.md",
            "section": "条目 00：原著兼容总则",
        },
        # ... 更多条目
    ]

    # 2. 读取markdown文件
    content_files = {}
    for fname in ["part1.md", "part2.md"]:
        with open(os.path.join(BASE_DIR, fname), 'r', encoding='utf-8') as f:
            content_files[fname] = f.read()

    # 3. 构建并输出JSON
    wb = build_worldbook(entries, content_files, "世界书名称", "描述")
    output_path = os.path.join(BASE_DIR, "worldbook.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(wb, f, ensure_ascii=False, indent=2)
    print(f"Written {len(wb['entries'])} entries to {output_path}")
