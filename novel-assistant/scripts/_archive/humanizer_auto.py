#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Humanizer-zh 自动化降重脚本
基于 humanizer-zh/SKILL.md 规则实现
"""

import re
import sys
import os
import glob

# A类模式：结构性AI模式
A_PATTERNS = {
    '否定排比': [
        r'不是\s*[^\s，、。，；;]+，也不是\s*[^\s，、。，；;]+，更不是\s*[^\s，、。，；;]+',
        r'不会\s*[^\s，、。，；;]+，也不会\s*[^\s，、。，；;]+，也不会\s*[^\s，、。，；;]+',
        r'不是\s*[^\s，、。，；;]+\s*，?\s*也不是\s*[^\s，、。，；;]+\s*，?\s*更不是\s*[^\s，、。，；;]+',
        r'不会\s*[^\s，、。，；;]+\s*，?\s*也不会\s*[^\s，、。，；;]+\s*，?\s*也不会\s*[^\s，、。，；;]+',
    ],
    '三段式': [
        r'首先\s*[^\s，、。，；;]+，其次\s*[^\s，、。，；;]+，最后\s*[^\s，、。，；;]+',
        r'有的\s*[^\s，、。，；;]+，有的\s*[^\s，、。，；;]+，最[^\s，、。，；;]+',
    ],
    'ing结尾': [
        r'[^\s，、]着[^\s，、]',
        r'[^\s，、]彰显着',
        r'[^\s，、]体现着',
        r'[^\s，、]确保了',
        r'[^\s，、]反映了',
        r'[^\s，、]标志着',
        r'[^\s，、]代表着',
    ],
}

# B类模式：AI高频词和虚假范围填充
B_PATTERNS = {
    '虚假范围': [
        (r'实际上', ''),
        (r'值得注意的是', ''),
        (r'毫无疑问', ''),
        (r'从某种意义上', ''),
        (r'从某种程度上', ''),
        (r'从一定角度', ''),
        (r'总的来说', ''),
        (r'综上所述', ''),
        (r'不难发现', ''),
        (r'显而易见', ''),
    ],
    'AI高频词': [
        (r'此外', ''),
        (r'与此同时', ''),
        (r'更加重要', '重要'),
        (r'至关重要', '重要'),
        (r'深入探讨', '探讨'),
        (r'进一步表明', '表明'),
        (r'充分体现', '体现'),
        (r'有效促进', '促进'),
        (r'积极作用', ''),
        (r'深远影响', '影响'),
        (r'持续深化', '深化'),
        (r'不断推进', '推进'),
        (r'日益突出', '突出'),
        (r'全面提升', '提升'),
        (r'显著增强', '增强'),
        (r'稳步推进', '推进'),
        (r'协调推进', '推进'),
        (r'深入推进', '推进'),
    ],
    '过度限定': [
        (r'可以说', ''),
        (r'可以说得上是', ''),
        (r'某种程度上', ''),
        (r'在一定意义上', ''),
        (r'多多少少', ''),
        (r'或多或少', ''),
    ],
    '谄媚语气': [
        (r'好问题', ''),
        (r'您说得完全正确', ''),
        (r'这是一个很好的观点', ''),
        (r'希望这对您有帮助', ''),
        (r'如果您想让我', ''),
        (r'请告诉我', ''),
    ],
}


def detect_ai_patterns(text):
    """检测AI模式，返回问题统计"""
    stats = {
        'A类_否定排比': 0,
        'A类_三段式': 0,
        'A类_ing结尾': 0,
        'B类_虚假范围': 0,
        'B类_AI高频词': 0,
        'B类_过度限定': 0,
        'B类_谄媚语气': 0,
        'C类_破折号': 0,
        '总计': 0,
    }

    # A类检测
    for pattern_type, patterns in A_PATTERNS.items():
        for pattern in patterns:
            try:
                matches = re.findall(pattern, text)
                stats[f'A类_{pattern_type}'] += len(matches)
                stats['总计'] += len(matches)
            except:
                pass

    # B类检测
    for pattern_type, patterns in B_PATTERNS.items():
        for pattern, _ in patterns:
            try:
                matches = re.findall(pattern, text)
                stats[f'B类_{pattern_type}'] += len(matches)
                stats['总计'] += len(matches)
            except:
                pass

    # C类检测（破折号）
    dash_count = text.count('——') + text.count('—')
    stats['C类_破折号'] = dash_count
    stats['总计'] += dash_count

    return stats


def apply_humanizer_rules(text):
    """应用Humanizer规则降重"""
    original = text

    # 1. 处理破折号
    text = text.replace('——', '，')
    text = text.replace('—', '，')

    # 2. 处理A类模式
    # 否定式排比 - 保留一个，删除其余
    negation_patterns = [
        r'不是\s*[^\s，、。，；;。，]+，也不是\s*[^\s，、。，；;。，]+，更不是\s*[^\s，、。，；;。，]+',
        r'不会\s*[^\s，、。，；;。，]+，也不会\s*[^\s，、。，；;。，]+，也不会\s*[^\s，、。，；;。，]+',
    ]
    for pattern in negation_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            parts = re.split(r'[，,]', match)
            if len(parts) >= 2:
                text = text.replace(match, '，'.join(parts[:2]), 1)

    # 三段式堆砌 - 保留两项
    triple_patterns = [
        r'首先\s*[^\s，、。，；;。，]+，其次\s*[^\s，、。，；;。，]+，最后\s*[^\s，、。，；;。，]+',
        r'有的\s*[^\s，、。，；;。，]+，有的\s*[^\s，、。，；;。，]+，最[^\s，、。，；;。，]+',
    ]
    for pattern in triple_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            parts = re.split(r'[，,]', match)
            if len(parts) >= 3:
                text = text.replace(match, '，'.join(parts[:2]), 1)

    # 3. 处理B类模式
    for pattern_type, patterns in B_PATTERNS.items():
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)

    # 4. 额外清理
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'，\s*，', '，', text)
    text = re.sub(r'。\s*。', '。', text)

    # 5. 处理"而且"类连接词
    text = re.sub(r'，而且', '，', text)
    text = re.sub(r'，此外', '，', text)
    text = re.sub(r'，同时', '，', text)

    return text


def humanize_file(input_path, dry_run=False):
    """处理单个文件"""
    if not os.path.exists(input_path):
        print(f"文件不存在: {input_path}")
        return False

    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检测前统计
    stats_before = detect_ai_patterns(content)

    # 应用规则
    humanized = apply_humanizer_rules(content)

    # 检测后统计
    stats_after = detect_ai_patterns(humanized)

    # 输出结果
    if not dry_run:
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(humanized)
        print(f"已处理: {input_path}")

    # 打印统计
    print("\n=== Humanizer 降重统计 ===")
    print(f"文件: {os.path.basename(input_path)}")
    print(f"\n降重前:")
    print(f"  A类模式: {stats_before['A类_否定排比'] + stats_before['A类_三段式'] + stats_before['A类_ing结尾']}")
    print(f"  B类AI套话: {stats_before['B类_虚假范围'] + stats_before['B类_AI高频词'] + stats_before['B类_过度限定']}")
    print(f"  破折号: {stats_before['C类_破折号']}")
    print(f"  总计: {stats_before['总计']}")

    print(f"\n降重后:")
    print(f"  A类模式: {stats_after['A类_否定排比'] + stats_after['A类_三段式'] + stats_after['A类_ing结尾']}")
    print(f"  B类AI套话: {stats_after['B类_虚假范围'] + stats_after['B类_AI高频词'] + stats_after['B类_过度限定']}")
    print(f"  破折号: {stats_after['C类_破折号']}")
    print(f"  总计: {stats_after['总计']}")

    reduction = stats_before['总计'] - stats_after['总计']
    if reduction > 0:
        print(f"\n减少: {reduction} 处 ({reduction/max(stats_before['总计'],1)*100:.1f}%)")

    return True


def humanize_chapter(project_path, chapter_num):
    """处理指定章节"""
    chapter_file = os.path.join(project_path, '正文卷', f'第{chapter_num}章_*.md')
    files = glob.glob(chapter_file)

    if not files:
        print(f"未找到章节文件: {chapter_file}")
        return False

    chapter_path = files[0]
    return humanize_file(chapter_path)


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python humanizer_auto.py <项目路径> <章节号>")
        print("  python humanizer_auto.py <文件路径> --dry-run")
        print("\n示例:")
        print("  python humanizer_auto.py D:/AI/山村小神医 3")
        print("  python humanizer_auto.py D:/AI/山村小神医/正文卷/第3章.md --dry-run")
        sys.exit(1)

    arg1 = sys.argv[1]

    if '--dry-run' in sys.argv:
        humanize_file(arg1, dry_run=True)
    elif os.path.exists(arg1) and os.path.isfile(arg1):
        humanize_file(arg1)
    elif os.path.exists(arg1) and os.path.isdir(arg1):
        chapter_num = int(sys.argv[2])
        humanize_chapter(arg1, chapter_num)
    else:
        print(f"路径不存在: {arg1}")
        sys.exit(1)


if __name__ == '__main__':
    main()
