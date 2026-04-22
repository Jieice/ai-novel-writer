#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说AI率检测脚本 v2
基于中文小说特性设计的AI检测方法

检测维度：
1. 词汇多样性 (TTR) - AI词汇单一，人类词汇丰富
2. 句长波动系数 - AI句长过于均匀，人类有自然跳跃
3. AI套话密度 - 检测AI特有表达模式
4. 动作/感官密度 - 人类写作动作描写多
5. 对话比例 - 小说应该有适当对话

阈值（针对中文小说调整）：
- AI率 < 50%：✅ 正常
- AI率 50-65%：⚠️ 警告
- AI率 > 65%：❌ 较高AI特征
"""

import re
import os
import sys
import math

if sys.platform == 'win32':
    import io
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')


# ============ AI套话模式（基于研究）============

# A类：否定式排比（学术/营销常见）
A_NEGATION_PARALLEL = [
    r'不是\s*[,，]\s*也不是\s*[,，]\s*更不是',
    r'不是\s*[,，]\s*也不是\s*[,，]\s*也不是',
    r'既不\s*[,，]\s*也不\s*[,，]\s*还不能',
]

# B类：三段式堆砌
B_TRIPLE_STRUCTURE = [
    r'首先\s*[,，]\s*其次\s*[,，]\s*最后',
    r'第一\s*[,，]\s*第二\s*[,，]\s*第三',
    r'第一\s*[、]\s*第二\s*[、]\s*第三',
]

# C类：-ing结尾动词（AI爱用）
C_ING_ENDING = [
    r'彰显', r'体现', r'确保', r'反映', r'做出贡献',
    r'培养', r'促进', r'推动', r'实现', r'完成',
]

# D类：AI高频填充词
D_FILLER_WORDS = [
    r'总而言之', r'值得注意的是', r'实际上', r'事实上',
    r'从某种意义上', r'可以说', r'严格来说',
]

# E类：AI高频副词
E_AI_ADVERBS = [
    r'此外', r'深入探讨', r'至关重要', r'不可或缺', r'不容忽视',
]

# F类：过度限定词
F_OVER_LIMIT = [
    r'可能[的地得]?', r'也许[的地得]?', r'大概[的地得]?',
    r'一般来说', r'基本上', r'看上去', r'似乎',
]


def calculate_ttr(text):
    """词汇多样性 (Type-Token Ratio)
    TTR = 不同词数 / 总词数
    AI写作词汇单一，TTR偏低
    """
    # 提取中文字符
    chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
    words = ''.join(chinese_chars)

    if len(words) < 50:
        return 0.5  # 文本太短

    # 简单按字符分词（粗略）
    unique_chars = set(words)
    ttr = len(unique_chars) / len(words)

    # 归一化：TTR在0.1-0.3之间算正常
    # 低于0.1说明词汇过于单一
    normalized = min(1.0, ttr / 0.15)
    return normalized


def calculate_sentence_variation(text):
    """句长波动系数 (Coefficient of Variation)
    AI写作句长过于均匀，CV偏低
    人类写作句长有自然变化，CV偏高
    """
    sentences = [s.strip() for s in re.split(r'[。！？\n]', text) if s.strip()]
    if len(sentences) < 5:
        return 0.5  # 句子太少

    lengths = [len(s) for s in sentences]
    avg = sum(lengths) / len(lengths)
    if avg == 0:
        return 0.5

    std = math.sqrt(sum((l - avg) ** 2 for l in lengths) / len(lengths))
    cv = std / avg  # 变异系数

    # 正常中文小说CV在0.4-0.8之间
    # 低于0.3说明过于均匀（AI特征）
    normalized = min(1.0, cv / 0.4)
    return normalized


def detect_ai_patterns(text):
    """AI套话密度检测
    返回：套话出现次数 / 总句数
    """
    sentences = [s.strip() for s in re.split(r'[。！？\n]', text) if s.strip()]
    sentence_count = max(1, len(sentences))
    total_patterns = 0

    # 检测各类模式
    pattern_groups = [
        A_NEGATION_PARALLEL,
        B_TRIPLE_STRUCTURE,
        C_ING_ENDING,
        D_FILLER_WORDS,
        E_AI_ADVERBS,
        F_OVER_LIMIT,
    ]

    for group in pattern_groups:
        for pattern in group:
            total_patterns += len(re.findall(pattern, text))

    # 密度 = 套话句数 / 总句数
    density = total_patterns / sentence_count

    # 归一化：每句0.1个套话以内算正常
    normalized = min(1.0, density / 0.15)
    return 1 - normalized  # 套话越多normalized越低


def calculate_action_density(text):
    """动作/感官描写密度
    人类写作动作描写多，AI写作偏叙述
    """
    action_verbs = [
        '看了看', '笑了笑', '摸了摸', '指了指', '摇了摇头',
        '点了点头', '皱了皱眉', '深吸', '攥紧', '松开',
        '转身', '抬头', '低头', '停下', '走过去',
        '拿起', '放下', '推开', '拉上', '转过身',
        '眼睛', '耳朵', '鼻子', '嘴巴', '脸',
        '手', '脚', '身子', '头', '背',
    ]

    total = sum(text.count(v) for v in action_verbs)
    density = total / (len(text) / 100)  # 每百字的动作词数

    # 正常小说应该2-5个动作词/百字
    # 低于1个说明偏叙述
    normalized = min(1.0, density / 2.0)
    return normalized


def calculate_dialogue_ratio(text):
    """对话比例
    小说对话比例应该在15%-60%之间
    """
    # 统计引号内的字符数
    quote_pattern = r'"[^"]*"'
    quotes = re.findall(quote_pattern, text)
    quote_chars = sum(len(q) for q in quotes)

    total_chars = len(text)
    if total_chars == 0:
        return 0.5

    ratio = quote_chars / total_chars

    # 理想对话比例在20%-50%
    if 0.20 <= ratio <= 0.50:
        return 1.0
    elif ratio < 0.10:
        return 0.3  # 对话太少，像说明书
    elif ratio > 0.70:
        return 0.5  # 对话太多，像剧本
    else:
        return 0.8


def calculate_ai_rate(text):
    """综合计算AI率

    返回值：0-100的百分比
    - < 50%: 正常
    - 50-65%: 警告
    - > 65%: 较高AI特征
    """
    ttr_score = calculate_ttr(text)  # 词汇多样性
    variation_score = calculate_sentence_variation(text)  # 句长波动
    pattern_score = detect_ai_patterns(text)  # AI套话
    action_score = calculate_action_density(text)  # 动作密度
    dialogue_score = calculate_dialogue_ratio(text)  # 对话比例

    # 加权平均
    # 词汇多样性(20%) + 句长波动(20%) + 套话密度(30%) + 动作密度(15%) + 对话比例(15%)
    ai_rate = (
        (1 - ttr_score) * 0.20 +
        (1 - variation_score) * 0.20 +
        (1 - pattern_score) * 0.30 +
        (1 - action_score) * 0.15 +
        (1 - dialogue_score) * 0.15
    )

    return {
        'ai_rate': round(ai_rate * 100, 1),
        'ttr_score': round(ttr_score * 100, 1),
        'variation_score': round(variation_score * 100, 1),
        'pattern_score': round(pattern_score * 100, 1),
        'action_score': round(action_score * 100, 1),
        'dialogue_score': round(dialogue_score * 100, 1),
        'details': {
            '词汇多样性': '正常' if ttr_score > 0.5 else '偏低(AI特征)',
            '句长波动': '正常' if variation_score > 0.5 else '过于均匀(AI特征)',
            'AI套话': '正常' if pattern_score > 0.5 else '过多(AI特征)',
            '动作密度': '正常' if action_score > 0.5 else '偏低(叙述过多)',
            '对话比例': '正常' if dialogue_score > 0.5 else '异常',
        }
    }


def main():
    if len(sys.argv) < 3:
        print('用法: python ai_rate_check_v2.py <项目路径> <章节号>')
        sys.exit(1)

    project_path = sys.argv[1]
    chapter_num = sys.argv[2]

    # 查找章节文件
    chapter_dir = os.path.join(project_path, '正文卷')
    chapter_file = None
    for f in os.listdir(chapter_dir):
        if f.startswith('第{}章'.format(chapter_num)):
            chapter_file = os.path.join(chapter_dir, f)
            break

    if not chapter_file:
        print('章节文件不存在: 第{}章'.format(chapter_num))
        sys.exit(1)

    with open(chapter_file, 'r', encoding='utf-8') as f:
        text = f.read()

    result = calculate_ai_rate(text)

    print('=' * 50)
    print('小说AI率检测 v2')
    print('=' * 50)
    print(f'章节: {os.path.basename(chapter_file)}')
    print()
    print(f"综合AI率: {result['ai_rate']}%")
    print()

    # 详细评分
    print('各维度评分:')
    print(f"  词汇多样性: {result['ttr_score']}% (越高越像人类)")
    print(f"  句长波动: {result['variation_score']}% (越高越自然)")
    print(f"  AI套话规避: {result['pattern_score']}% (越高越干净)")
    print(f"  动作描写: {result['action_score']}% (越高越生动)")
    print(f"  对话比例: {result['dialogue_score']}% (越高越合理)")
    print()

    print('维度分析:')
    for key, val in result['details'].items():
        print(f"  {key}: {val}")
    print()

    # 阈值判断
    ai_rate = result['ai_rate']
    if ai_rate < 50:
        status = '✅ 正常'
        exit_code = 0
    elif ai_rate < 65:
        status = '⚠️ 警告'
        exit_code = 0  # 警告但不阻塞
    else:
        status = '❌ 较高AI特征'
        exit_code = 1

    print(f"判定: {status}")
    print('=' * 50)

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
