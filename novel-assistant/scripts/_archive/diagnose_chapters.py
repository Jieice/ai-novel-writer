#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯 Python 诊断脚本，直接解析章节文件获取指标，不 import chapter_health_check。
"""

import re
import sys
from pathlib import Path

PROJECT = Path('d:/AI/AI小说创作系统/山村小神医')
CHAPTERS = [1, 2, 3, 5, 8, 10, 11, 13, 15, 19, 22, 23, 26]  # 细修批次

TEMPLATE_PATTERNS = [
    '笑了笑', '点了点头', '脸红了红', '眼睛一亮', '眼睛都直了',
    '嘴角微微上扬', '深吸一口气', '攥紧拳头', '眉头皱了皱',
    '心里头一紧', '心里头七上八下', '心里头咯噔', '心里头一暖',
    '心里头有些', '心里头发酸', '心里头堵得慌', '脑子嗡的一声',
    '不由得', '念叨着', '寻思着', '琢磨着',
    '等着吧', '十倍奉还', '付出代价', '迟早让你', '走着瞧',
    '攥紧', '捏紧',
]

TELLING_PATTERNS = ['这意味着', '接下来要', '以后就能', '这说明']
SUMMARY_PATTERNS = ['算了一笔账', '这样一来', '总的来说', '总的来说']


def find_chapter(project: Path, num: int) -> Path:
    for f in project.glob('正文卷/*'):
        m = re.search(r'第' + str(num) + r'章', f.name)
        if m:
            return f
    return None


def get_metrics(text: str) -> dict:
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    quote_pairs = len(re.findall(r'[\u201c\u201d]', text)) // 2

    template_count = 0
    for pat in TEMPLATE_PATTERNS:
        template_count += len(re.findall(re.escape(pat), text))

    telling_count = sum(1 for p in TELLING_PATTERNS for _ in re.finditer(re.escape(p), text))
    summary_count = sum(1 for p in SUMMARY_PATTERNS for _ in re.finditer(re.escape(p), text))

    total_chars = len(text)
    total_words = total_chars / 500  # 粗估字数(万字)
    word_count = len(text)

    colloquial_count = sum(1 for c in text for c in [c] if c in '呢吧嘛咋啥呗')
    colloquial_rate = colloquial_count / (total_chars / 100) if total_chars > 0 else 0

    scene_markers = len(re.findall(r'^#{1,3}\s|^\s*[\"\"].*[\"\"\s]$', text, re.MULTILINE))
    title_count = len(re.findall(r'^#{1,3}\s|^第[一二三四五六七八九十百\d]+章', text, re.MULTILINE))

    return {
        'word_count': word_count,
        'quote_pairs': quote_pairs,
        'template_count': template_count,
        'telling_count': telling_count,
        'summary_count': summary_count,
        'colloquial_rate': round(colloquial_rate, 2),
        'colloquial_count': colloquial_count,
    }


def main():
    print()
    print('=' * 70)
    print('章节诊断报告（直接解析章节文件）')
    print('=' * 70)
    print()
    print(f'{"章节":<8} {"字数":<8} {"引号对":<8} {"模板词":<8} {"口语化率":<10} {"评估"}')
    print('-' * 70)

    for ch in CHAPTERS:
        fp = find_chapter(PROJECT, ch)
        if not fp:
            print(f'第{ch}章: 文件未找到')
            continue

        with open(fp, 'r', encoding='utf-8') as f:
            text = f.read()

        m = get_metrics(text)

        issues = []
        if m['template_count'] > 8:
            issues.append(f'模板词超标({m["template_count"]})')
        if m['quote_pairs'] < 6:
            issues.append(f'引号不足({m["quote_pairs"]})')
        if m['telling_count'] > 5:
            issues.append(f'讲述句过多({m["telling_count"]})')

        status = '⚠️ ' + '; '.join(issues) if issues else '✅ 正常'
        label = '🔴 FAIL' if issues else ('⚠️ WARN' if m['template_count'] > 5 else '✅ OK')

        print(f'第{ch:<4}章  {m["word_count"]:<8} {m["quote_pairs"]:<8} {m["template_count"]:<8} {m["colloquial_rate"]:<8} {label}  {status}')

    print()
    print('[阈值参考]')
    print('  模板词 > 8 = FAIL')
    print('  引号对 < 6 = FAIL')
    print('  讲述句 > 5 = WARNING')
    print('  口语化 < 0.8/百字 = WARNING')


if __name__ == '__main__':
    main()
