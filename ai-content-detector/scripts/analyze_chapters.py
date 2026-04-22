#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI内容特征分析脚本"""

import re
import os

def analyze_ai_features(text):
    results = {}
    
    sentences = re.split(r'[。！？\n]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        lengths = [len(s) for s in sentences]
        avg_len = sum(lengths) / len(lengths)
        variance = sum((l - avg_len)**2 for l in lengths) / len(lengths) if lengths else 0
        std_dev = variance ** 0.5
        uniformity_score = max(0, 100 - std_dev * 2) / 100
    else:
        uniformity_score = 0.5
    results['句子均匀度'] = round(uniformity_score * 100, 1)
    
    logic_words = ['但是', '不过', '然而', '因此', '所以', '首先', '其次', '最后', '总之', '综上所述']
    logic_count = sum(text.count(w) for w in logic_words)
    logic_freq = logic_count / (len(text) / 100) if text else 0
    logic_score = min(100, logic_freq * 10) / 100
    results['逻辑词频率'] = round(logic_freq, 2)
    
    colloquial_words = ['咋', '啥', '呗', '嘛', '呢', '啊', '呀', '咯', '喽', '琢磨', '寻思', '要得']
    colloquial_count = sum(text.count(w) for w in colloquial_words)
    colloquial_freq = colloquial_count / (len(text) / 100) if text else 0
    colloquial_score = min(100, colloquial_freq * 20) / 100
    results['口语化程度'] = round(colloquial_freq, 2)
    
    psych_patterns = ['心里一', '心里头', '心里有', '心里明白', '心里盘算']
    psych_count = sum(len(re.findall(p, text)) for p in psych_patterns)
    psych_freq = psych_count / (len(text) / 100) if text else 0
    results['心理描写频率'] = round(psych_freq, 2)
    
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) > 1:
        para_lengths = [len(p) for p in paragraphs]
        para_avg = sum(para_lengths) / len(para_lengths)
        para_variance = sum((l - para_avg)**2 for l in para_lengths) / len(para_lengths)
        para_std = para_variance ** 0.5
        para_uniformity = max(0, 100 - para_std) / 100
    else:
        para_uniformity = 0.5
    results['段落均匀度'] = round(para_uniformity * 100, 1)
    
    ai_score = (
        uniformity_score * 0.25 +
        logic_score * 0.25 +
        (1 - colloquial_score) * 0.25 +
        min(1, psych_freq * 5) * 0.15 +
        para_uniformity * 0.1
    )
    
    results['预估AI率'] = round(ai_score * 100, 1)
    results['预估人类率'] = round((1 - ai_score) * 100, 1)
    
    return results

chapters_dir = r'd:\AI\AI小说创作系统\山村小神医\正文卷'
chapter_files = [
    '第1章_回村的穷小子.md',
    '第2章_祖传秘方.md',
    '第3章_百草灵珠.md',
    '第4章_百草灵珠.md',
    '第5章_名声初显.md',
    '第6章_地契风波.md',
    '第7章_药铺老板.md',
    '第8章_风向变了.md',
    '第9章_暗生情愫.md'
]

print('=' * 60)
print('AI内容特征分析报告')
print('=' * 60)
print()

all_results = []

for i, filename in enumerate(chapter_files, 1):
    filepath = os.path.join(chapters_dir, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        
        text = re.sub(r'^【第\d+章[^】]*】\n', '', text)
        text = re.sub(r'（本章完）\s*$', '', text)
        
        results = analyze_ai_features(text)
        results['章节'] = '第{}章'.format(i)
        results['字数'] = len(text)
        all_results.append(results)
        
        print('第{}章 ({}字)'.format(i, results['字数']))
        print('  句子均匀度: {}%'.format(results['句子均匀度']))
        print('  逻辑词频率: {}次/百字'.format(results['逻辑词频率']))
        print('  口语化程度: {}次/百字'.format(results['口语化程度']))
        print('  心理描写: {}次/百字'.format(results['心理描写频率']))
        print('  段落均匀度: {}%'.format(results['段落均匀度']))
        print('  预估AI率: {}%'.format(results['预估AI率']))
        print()

if all_results:
    avg_ai = sum(r['预估AI率'] for r in all_results) / len(all_results)
    avg_colloquial = sum(r['口语化程度'] for r in all_results) / len(all_results)
    avg_logic = sum(r['逻辑词频率'] for r in all_results) / len(all_results)
    
    print('=' * 60)
    print('综合评估')
    print('=' * 60)
    print('平均预估AI率: {}%'.format(round(avg_ai, 1)))
    print('平均口语化程度: {}次/百字'.format(round(avg_colloquial, 2)))
    print('平均逻辑词频率: {}次/百字'.format(round(avg_logic, 2)))
    print()
    
    if avg_ai < 30:
        level = '极低'
        suggestion = '文本具有高度人类写作特征'
    elif avg_ai < 45:
        level = '低'
        suggestion = '文本具有较多人类写作特征'
    elif avg_ai < 60:
        level = '中等'
        suggestion = '文本存在混合特征，建议进一步优化'
    else:
        level = '高'
        suggestion = '文本具有较多AI特征，建议降重优化'
    
    print('综合判定: {}'.format(level))
    print('建议: {}'.format(suggestion))
