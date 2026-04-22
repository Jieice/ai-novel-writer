#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现有章节回填预处理脚本
扫描现有章节，提取可自动检测的信息（地名/人名/价格/时间/物品），
输出结构化报告，供 Trae/Claude 快速回填追踪文件。

用法：python backfill_chapters.py --project <项目路径> --start 1 --end 12
"""

import os
import re
import sys
import argparse
from collections import defaultdict


def get_chapter_files(project_path, start_chapter, end_chapter):
    """获取章节文件列表"""
    chapter_dir = os.path.join(project_path, '正文卷')
    if not os.path.exists(chapter_dir):
        print("❌ 找不到正文卷目录: {}".format(chapter_dir))
        return []

    files = []
    for f in sorted(os.listdir(chapter_dir)):
        match = re.match(r'第(\d+)章', f)
        if match and start_chapter <= int(match.group(1)) <= end_chapter:
            files.append((int(match.group(1)), os.path.join(chapter_dir, f)))

    files.sort(key=lambda x: x[0])
    return files


def read_chapter(chapter_file):
    """读取章节内容，清理标题"""
    with open(chapter_file, 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(r'^【第\d+章[^】]*】\n', '', content)
    content = re.sub(r'（本章完）\s*$', '', content)
    return content


def extract_chapter_title(chapter_file):
    """从文件名提取章节标题"""
    basename = os.path.basename(chapter_file)
    match = re.match(r'第(\d+)章[ _\-]*(.*?)\.txt', basename)
    if match:
        return int(match.group(1)), match.group(2)
    return 0, basename


def extract_characters(content, known_names=None):
    """提取出场角色（基于已知名字和频率分析）"""
    if known_names is None:
        known_names = []

    found = {}
    for name in known_names:
        count = content.count(name)
        if count > 0:
            found[name] = count

    # 检测对话中出现的"X哥/X叔/X婶/X大爷"等称呼
    titles = re.findall(r'[\u4e00-\u9fff]{1,2}(?:哥|叔|婶|大爷|大娘|嫂|姐|妹|弟|伯)', content)
    for t in titles:
        if t not in found:
            found[t] = found.get(t, 0) + 1

    return found


def extract_prices(content):
    """提取价格/金额信息"""
    prices = []

    # X块/X元/X毛/X角
    patterns = [
        (r'(\d+)\s*块', '块'),
        (r'(\d+)\s*元', '元'),
        (r'(\d+)\s*毛', '毛'),
        (r'(\d+)\s*角', '角'),
        (r'(\d+)\s*分', '分'),
    ]

    for pattern, unit in patterns:
        for match in re.finditer(pattern, content):
            # 取前后20字作为上下文
            start = max(0, match.start() - 20)
            end = min(len(content), match.end() + 10)
            context = content[start:end].replace('\n', ' ')
            prices.append({
                'amount': match.group(1),
                'unit': unit,
                'context': context
            })

    return prices


def extract_locations(content, location_keywords=None):
    """提取地点信息"""
    if location_keywords is None:
        location_keywords = [
            '镇上', '后山', '村口', '村里', '县城', '省城', '市里',
            '药田', '竹山', '河边', '山上', '山下', '院里', '屋里',
            '大队部', '供销社', '卫生所', '学校', '小学', '祠堂',
            '集市', '市场', '茶馆', '饭馆', '酒楼', '客栈',
        ]

    found = {}
    for loc in location_keywords:
        count = content.count(loc)
        if count > 0:
            found[loc] = count

    return found


def extract_time_refs(content):
    """提取时间引用"""
    time_refs = []

    # 年份
    for match in re.finditer(r'(19[89]\d|20\d{2})年', content):
        time_refs.append({'type': 'year', 'value': match.group(1)})

    # 月份
    for match in re.finditer(r'(\d{1,2})月', content):
        time_refs.append({'type': 'month', 'value': match.group(1)})

    # 时间段
    time_periods = ['早上', '上午', '中午', '下午', '傍晚', '晚上', '半夜', '凌晨',
                    '天刚亮', '太阳升起', '日落', '黄昏', '黎明']
    for tp in time_periods:
        if tp in content:
            time_refs.append({'type': 'period', 'value': tp})

    # 相对时间
    rel_time = ['第二天', '第三天', '过了几天', '一周后', '半个月后', '一个月后',
                '半年后', '一年后', '当天', '隔天', '翌日']
    for rt in rel_time:
        if rt in content:
            time_refs.append({'type': 'relative', 'value': rt})

    return time_refs


def extract_items(content):
    """提取物品信息"""
    item_keywords = [
        '灵珠', '天麻', '人参', '灵芝', '何首乌', '黄芪', '当归', '枸杞',
        '竹篓', '药篓', '镰刀', '锄头', '竹竿', '绳子',
        '粮票', '布票', '肉票', '自行车', '手表', '缝纫机', '收音机', '黑白电视',
        '柴刀', '扁担', '箩筐', '背篓',
    ]

    found = {}
    for item in item_keywords:
        count = content.count(item)
        if count > 0:
            found[item] = count

    return found


def extract_dialogues(content):
    """统计对话密度"""
    # 中文引号对话
    dialogues = re.findall(r'[""「」『』](.+?)[""「」『』]', content)
    return len(dialogues)


def extract_conflicts(content):
    """检测冲突相关词汇"""
    conflict_words = {
        '打脸': ['打脸', '啪啪', '响亮'],
        '威胁': ['威胁', '恐吓', '警告', '别怪我不客气'],
        '找茬': ['找茬', '刁难', '欺负', '看不起', '嘲笑', '讽刺'],
        '争吵': ['吵', '骂', '怒', '吼', '嚷', '喊'],
        '危机': ['危险', '危机', '糟糕', '不妙', '来不及'],
    }

    found = {}
    for category, words in conflict_words.items():
        for w in words:
            count = content.count(w)
            if count > 0:
                if category not in found:
                    found[category] = 0
                found[category] += count

    return found


def count_words(content):
    """统计中文字数"""
    clean = re.sub(r'[^\u4e00-\u9fff]', '', content)
    return len(clean)


def run_backfill_analysis(project_path, start_chapter, end_chapter):
    """运行完整的回填分析"""
    chapter_files = get_chapter_files(project_path, start_chapter, end_chapter)
    if not chapter_files:
        print("❌ 未找到第{}-{}章的章节文件".format(start_chapter, end_chapter))
        return

    print("=" * 60)
    print("📊 章节回填分析报告")
    print("=" * 60)
    print("扫描范围：第{}-{}章 (共{}章)".format(start_chapter, end_chapter, len(chapter_files)))
    print()

    # 读取所有已知角色名（从人物设定文件）
    char_file = os.path.join(project_path, '项目文件', '人物设定.md')
    known_names = []
    if os.path.exists(char_file):
        with open(char_file, 'r', encoding='utf-8') as f:
            char_content = f.read()
        # 尝试提取角色名
        for match in re.finditer(r'(?:姓名|名字|主角)[：:]\s*([^\s,，\n]{2,4})', char_content):
            known_names.append(match.group(1))
        # 提取章节中常见名字
        for match in re.finditer(r'[\u4e00-\u9fff]{2,3}(?=说|笑|想|看|走|站|坐|道)', char_content):
            name = match.group(0)
            if len(name) >= 2 and name not in known_names:
                known_names.append(name)

    # 汇总数据
    all_characters = defaultdict(list)
    all_prices = []
    all_locations = defaultdict(list)
    all_times = defaultdict(list)
    all_items = defaultdict(list)
    all_conflicts = defaultdict(list)
    chapter_stats = []

    for chapter_num, chapter_file in chapter_files:
        content = read_chapter(chapter_file)
        title_num, title_text = extract_chapter_title(chapter_file)
        word_count = count_words(content)

        # 提取信息
        chars = extract_characters(content, known_names)
        for name, count in chars.items():
            all_characters[name].append((chapter_num, count))

        prices = extract_prices(content)
        for p in prices:
            all_prices.append((chapter_num, p))

        locs = extract_locations(content)
        for loc, count in locs.items():
            all_locations[loc].append((chapter_num, count))

        times = extract_time_refs(content)
        for t in times:
            all_times[t['value']].append(chapter_num)

        items = extract_items(content)
        for item, count in items.items():
            all_items[item].append((chapter_num, count))

        conflicts = extract_conflicts(content)
        for cat, count in conflicts.items():
            all_conflicts[cat].append((chapter_num, count))

        dialogue_count = extract_dialogues(content)
        dialogue_density = round(dialogue_count / (word_count / 100), 1) if word_count > 0 else 0

        chapter_stats.append({
            'num': chapter_num,
            'title': title_text,
            'words': word_count,
            'dialogues': dialogue_count,
            'dialogue_density': dialogue_density,
            'characters': list(chars.keys()),
            'conflicts': list(conflicts.keys()),
        })

    # ====== 输出报告 ======

    # 1. 章节概览
    print("## 一、章节概览")
    print()
    print("| 章节 | 标题 | 字数 | 对话数 | 对话密度 | 出场角色 | 冲突类型 |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for s in chapter_stats:
        char_str = ', '.join(s['characters'][:5]) if s['characters'] else '-'
        conf_str = ', '.join(s['conflicts']) if s['conflicts'] else '-'
        print("| 第{}章 | {} | {}字 | {} | {}/百字 | {} | {} |".format(
            s['num'], s['title'][:10], s['words'], s['dialogues'],
            s['dialogue_density'], char_str, conf_str))
    print()

    # 2. 角色出场统计
    print("## 二、角色出场统计")
    print()
    print("以下是各角色在哪些章节出场，以及出场频率：")
    print()
    for name, chapters in sorted(all_characters.items(), key=lambda x: -len(x[1])):
        ch_list = ', '.join(['第{}章({}次)'.format(c, n) for c, n in chapters])
        print("- **{}**：出现在 {} 章节，共{}次".format(name, len(chapters), sum(n for _, n in chapters)))
        print("  章节：{}".format(ch_list))
    print()

    # 3. 价格信息
    if all_prices:
        print("## 三、价格/金额信息")
        print()
        print("| 章节 | 金额 | 单位 | 上下文 |")
        print("| --- | --- | --- | --- |")
        for ch_num, p in all_prices:
            print("| 第{}章 | {}{} | {} |".format(ch_num, p['amount'], p['unit'], p['context'][:30]))
        print()

    # 4. 地点统计
    print("## 四、地点出场统计")
    print()
    for loc, chapters in sorted(all_locations.items(), key=lambda x: -len(x[1])):
        ch_list = ', '.join(['第{}章'.format(c) for c, _ in chapters])
        total = sum(n for _, n in chapters)
        print("- **{}**：{}次，出现在 {}".format(loc, total, ch_list))
    print()

    # 5. 时间线
    print("## 五、时间引用")
    print()
    for time_val, chapters in sorted(all_times.items(), key=lambda x: -len(x[1])):
        ch_list = ', '.join(['第{}章'.format(c) for c in chapters])
        print("- **{}**：出现在 {}".format(time_val, ch_list))
    print()

    # 6. 物品统计
    if all_items:
        print("## 六、物品统计")
        print()
        for item, chapters in sorted(all_items.items(), key=lambda x: -len(x[1])):
            ch_list = ', '.join(['第{}章'.format(c) for c, _ in chapters])
            total = sum(n for _, n in chapters)
            print("- **{}**：{}次，出现在 {}".format(item, total, ch_list))
        print()

    # 7. 冲突统计
    print("## 七、冲突分布")
    print()
    for cat, chapters in sorted(all_conflicts.items(), key=lambda x: -len(x[1])):
        ch_list = ', '.join(['第{}章({}次)'.format(c, n) for c, n in chapters])
        total = sum(n for _, n in chapters)
        print("- **{}**：{}次关键词，出现在 {}".format(cat, total, ch_list))
    print()

    # 8. 给 AI 的回填指令
    print("=" * 60)
    print("## 回填指令")
    print("=" * 60)
    print()
    print("请 AI 根据以上分析报告，回填以下追踪文件：")
    print()
    print("1. **character_states.md**：根据「角色出场统计」，填写每个角色的状态快照、")
    print("   关系亲密度、性格锚点、独立剧情线")
    print()
    print("2. **plot_threads.md**：根据「冲突分布」和「章节概览」，识别主线、支线、")
    print("   感情线、冲突线等活跃线索")
    print()
    print("3. **pending_hooks.md**：根据「章节概览」中的伏笔和悬念，填写已埋伏笔")
    print("   和待埋伏笔，设置优先级和计划解决章节")
    print()
    print("4. **world_state.md**：根据「价格信息」「地点统计」「物品统计」「时间引用」，")
    print("   填写地点、物品、时代细节")
    print()
    print("5. **chapter_analysis.md**：逐章填写6维度分析（钩子/伏笔/剧情点/冲突/角色变化/质量评分）")
    print()
    print("6. **arc_summary.md**：根据所有章节分析，生成第一弧（第1-10章）的弧线摘要")


def main():
    parser = argparse.ArgumentParser(description='现有章节回填预处理')
    parser.add_argument('--project', required=True, help='项目根目录路径')
    parser.add_argument('--start', type=int, default=1, help='起始章节号')
    parser.add_argument('--end', type=int, default=12, help='结束章节号')
    args = parser.parse_args()

    if not os.path.exists(args.project):
        print("❌ 项目目录不存在: {}".format(args.project))
        return

    run_backfill_analysis(args.project, args.start, args.end)


if __name__ == '__main__':
    main()
