#!/usr/bin/env python
"""
小说合集拆分脚本（通用模板）
================================
适用场景：从尚香书苑等来源下载的大txt文件（含多个故事、每个故事有章节）。
自动完成两步拆分：
  1. 合集拆分：按索引标题提取每个故事
  2. 章节拆分：按"第N章"标记拆分每个故事

用法：
  1. 修改 SOURCE_FILE 和 OUTPUT_DIR
  2. 修改 INDEX_STORIES 为索引中的故事标题列表
  3. 运行：python novel-collection-split-pattern.py

如果故事标题在正文中的起止行号已知，直接修改 STORY_BOUNDARIES。
"""

import os
import re

# ========== 配置部分 ==========
SOURCE_FILE = "D:\\小说资源\\COCO不当人啦合集纯绿版.txt"
OUTPUT_DIR = "D:\\小说资源\\coco合集"

# 索引中列出的故事标题（顺序对应正文中的出现顺序）
INDEX_STORIES = [
    # 示例格式，替换为实际标题
    "【黑色人生】我那魔鬼身材的芭蕾舞连体丝美母",
    "38G巨奶警花被迫献乳",
    # ...
]

# 如果已知精确起止行号（1-indexed），直接填这里：
# 格式：(start_line, end_line, 文件夹名)
STORY_BOUNDARIES = []  # 留空则自动搜索

# ========== 章节拆分配置 ==========
# 特殊配置：处理边缘情况
FIXED_CONFIG = {
    # 示例：缺少第一章标题的故事
    # "东瀛小鬼冰山美母白丝足穴": {"first_chapter": "第一章", "first_chapter_line": 1},
    # 示例：末尾"第一章"是下个故事预告
    # "骗奸峨眉第一艳魁": {"drop_last_chapter": True},
    # 示例：末尾的"第一章"是假阳性，保持单文件
    # "请用浓精灌满婆媳三代": {"no_chapters": True},
}

# ========== 工具函数 ==========


def find_stories_in_file(filepath, titles):
    """
    在文件正文中搜索每个故事标题的起始行号。
    返回 [(start_line, title), ...] 1-indexed
    """
    found = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line_num <= 4:  # 跳过页头
                continue
            for title in titles:
                # 用标题前40个字符搜索
                key = title[:40]
                if key in line:
                    found.append((line_num, title))
                    break
    return found


def detect_chapters(lines):
    """
    检测章节标记，返回 [(line_index, chapter_name), ...]
    line_index 是 0-indexed 行号
    """
    chapters = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        stripped = stripped.lstrip('\ufeff')  # 去除BOM

        # 模式1: 第N章 / 第N章 标题
        m = re.match(r'^第([一二三四五六七八九十百千万\d]+)[章节篇回](.*)', stripped)
        if m:
            chapters.append((i, stripped[:60]))
            continue
        # 模式2: 第一章上篇/下篇
        m = re.match(r'^第[一二三四五六七八九十\d]+章[上下]篇', stripped)
        if m:
            chapters.append((i, stripped[:60]))
            continue
        # 模式3: 第0章
        m = re.match(r'^第[0\d]章', stripped)
        if m:
            chapters.append((i, stripped[:60]))
            continue
    return chapters


def remove_line_prefix(line):
    """去掉行号前缀，如 '34|内容' → '内容'"""
    if '|' in line:
        parts = line.split('|', 1)
        if parts[0].strip().isdigit():
            return parts[1]
    return line


# ========== 主流程 ==========


def step1_split_collection():
    """第一步：按故事标题拆分合集"""
    if STORY_BOUNDARIES:
        boundaries = STORY_BOUNDARIES
    else:
        found = find_stories_in_file(SOURCE_FILE, INDEX_STORIES)
        # 构建边界：第N个故事从它的起始行到下一个故事的起始行
        boundaries = []
        for i, (ln, title) in enumerate(found):
            start = ln
            if i + 1 < len(found):
                end = found[i + 1][0]
            else:
                end = None  # 文件末尾
            boundaries.append((start, end, title[:40]))

    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for i, (start, end, title) in enumerate(boundaries):
        safe_name = re.sub(r'[\\/:*?"<>|]', '·', title).strip()
        story_dir = os.path.join(OUTPUT_DIR, safe_name)
        os.makedirs(story_dir, exist_ok=True)

        content = all_lines[start - 1: end - 1] if end else all_lines[start - 1:]
        content = [remove_line_prefix(l) for l in content]

        txt_path = os.path.join(story_dir, f'{safe_name}.txt')
        with open(txt_path, 'w', encoding='utf-8') as fh:
            fh.write(''.join(content))

        print(f"  #{i+1:2d} {safe_name[:40]:40s} | {len(content):>5}行")

    print(f"\n合集拆分完成，共 {len(boundaries)} 个故事")


def step2_split_chapters():
    """第二步：对每个故事的txt按章节拆分"""
    total_split = 0
    total_kept = 0

    for item in sorted(os.listdir(OUTPUT_DIR)):
        item_path = os.path.join(OUTPUT_DIR, item)
        if not os.path.isdir(item_path):
            continue

        txts = [f for f in os.listdir(item_path) if f.endswith('.txt') and not f.startswith('第')]
        if not txts:
            continue

        txt_path = os.path.join(item_path, txts[0])
        with open(txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        chapters = detect_chapters(lines)
        config = FIXED_CONFIG.get(item, {})

        if not chapters or config.get("no_chapters"):
            print(f"  📁 {item:30s} 保持单文件 ({len(lines)}行)")
            total_kept += 1
            continue

        # 处理特殊配置
        if "first_chapter_line" in config:
            chapters.insert(0, (0, config["first_chapter"]))

        # 删除末尾假阳性
        if config.get("drop_last_chapter") and len(chapters) >= 2:
            last = chapters[-1]
            if '第一章' in last[1] and last[0] >= len(lines) - 5:
                chapters = chapters[:-1]
                print(f"    删除末尾假阳性: L{last[0]+1}")

        # 构建边界
        boundaries = []
        for idx, (line_num, title) in enumerate(chapters):
            start = 0 if idx == 0 and any(l.strip() for l in lines[:line_num]) else line_num
            end = chapters[idx + 1][0] if idx + 1 < len(chapters) else len(lines)
            boundaries.append((start, end, title))

        print(f"  📁 {item:30s} → {len(boundaries)}章")
        for idx, (start, end, title) in enumerate(boundaries):
            content = ''.join(lines[start:end]).strip()
            if not content:
                continue

            ch_num = idx + 1
            title_clean = title.strip().rstrip('：:，,。.')
            fname = re.sub(r'[\\/:*?"<>|]', '·', title_clean)
            fname = f"第{ch_num}章 {fname}.txt" if fname else f"第{ch_num}章.txt"

            fpath = os.path.join(item_path, fname)
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(content)

            size_kb = os.path.getsize(fpath) / 1024
            print(f"      {fname:50s} {size_kb:>6.1f}KB")

        # 删除原始大文件
        os.remove(txt_path)
        total_split += 1

    print(f"\n章节拆分完成：拆分 {total_split} 个，保持 {total_kept} 个")


if __name__ == "__main__":
    print("=" * 60)
    print("  小说合集拆分工具")
    print("=" * 60)
    step1_split_collection()
    step2_split_chapters()
