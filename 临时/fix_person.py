#!/usr/bin/env python3
"""
1. 修CH9半角引号→全角
2. 将CH1/2/3/11/12从第一人称改写为第三人称
"""
import os, sys, re
sys.stdout.reconfigure(encoding='utf-8')
folder = r'd:\AI\AI小说创作系统\山村小神医\正文卷'

# === Step 1: 修CH9半角引号 ===
print("=== Step 1: 修CH9半角引号 ===")
for ch in [9]:
    matches = [f for f in os.listdir(folder) if f.startswith(f'第{ch}章')]
    path = os.path.join(folder, matches[0])
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    before = content.count('"')
    # Replace paired half-width quotes with full-width
    # Pattern: "text" → \u201ctext\u201d
    result = []
    in_quote = False
    for char in content:
        if char == '"':
            if not in_quote:
                result.append('\u201c')
                in_quote = True
            else:
                result.append('\u201d')
                in_quote = False
        else:
            result.append(char)
    content = ''.join(result)
    
    # Handle unclosed quotes - if odd number, the last opening quote needs closing
    left_q = content.count('\u201c')
    right_q = content.count('\u201d')
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    after = content.count('"')
    print(f'CH{ch}: 半角引号 {before}→{after}, 全角左{left_q}右{right_q}')

# === Step 2: 第一人称→第三人称 ===
print("\n=== Step 2: 第一人称→第三人称 ===")

# 替换规则：
# "我" → "陈大山" (句首/独立使用)
# "我的" → "陈大山的" / "他的"
# "我了" → "他了"  
# "我是" → "他是"
# "我在" → "他在"
# "我也" → "他也"
# "我就" → "他就"
# "我都" → "他都"
# "我把" → "他把"
# "我被" → "他被"
# "我给" → "他给"
# "我让" → "他让"
# "我向" → "他向"
# "我到" → "他到"
# "我从" → "他从"
# "我跟" → "他跟"
# "我和" → "他和"
# "我没" → "他没"
# "我也有" → "他也有"
# 独立的"我" → "他"
# 但：对话中的"我"不换！（引号内的第一人称要保持）

first_person_chapters = [1, 2, 3, 11, 12]

for ch in first_person_chapters:
    matches = [f for f in os.listdir(folder) if f.startswith(f'第{ch}章')]
    if not matches:
        print(f'CH{ch}: 文件不存在，跳过')
        continue
    
    path = os.path.join(folder, matches[0])
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Strategy: Split by quotes, only modify text OUTSIDE quotes
    # Split into segments: alternating between non-quote and quote sections
    segments = re.split(r'(\u201c.*?\u201d)', content)
    
    modified_segments = []
    for i, seg in enumerate(segments):
        # Odd indices are quoted text (dialogue), even are narration
        if i % 2 == 1:
            # Inside quotes - keep as is
            modified_segments.append(seg)
        else:
            # Outside quotes - narration, replace first person with third person
            modified = seg
            
            # "我爹" → "他爹" (陈大山称呼父亲，第三人称叙述中应为"他爹")
            modified = re.sub(r'我爹', '他爹', modified)
            # "我娘" → "他娘" (同上)
            modified = re.sub(r'我娘', '他娘', modified)
            # "我爷爷" → "他爷爷"
            modified = re.sub(r'我爷爷', '他爷爷', modified)
            
            # "我的" → "他的"
            modified = re.sub(r'我的', '他的', modified)
            # "我了" → "他了"
            modified = re.sub(r'我了', '他了', modified)
            # "我是" → "他是"
            modified = re.sub(r'我是', '他是', modified)
            # "我在" → "他在"
            modified = re.sub(r'我在', '他在', modified)
            # "我也" → "他也"
            modified = re.sub(r'我也', '他也', modified)
            # "我就" → "他就"
            modified = re.sub(r'我就', '他就', modified)
            # "我都" → "他都"
            modified = re.sub(r'我都', '他都', modified)
            # "我把" → "他把"
            modified = re.sub(r'我把', '他把', modified)
            # "我被" → "他被"
            modified = re.sub(r'我被', '他被', modified)
            # "我给" → "他给"
            modified = re.sub(r'我给', '他给', modified)
            # "我让" → "他让"
            modified = re.sub(r'我让', '他让', modified)
            # "我向" → "他向"
            modified = re.sub(r'我向', '他向', modified)
            # "我到" → "他到"
            modified = re.sub(r'我到', '他到', modified)
            # "我从" → "他从"
            modified = re.sub(r'我从', '他从', modified)
            # "我跟" → "他跟"
            modified = re.sub(r'我跟', '他跟', modified)
            # "我和" → "他和"
            modified = re.sub(r'我和', '他和', modified)
            # "我没" → "他没'
            modified = re.sub(r'我没', '他没', modified)
            # "我还" → "他还"
            modified = re.sub(r'我还', '他还', modified)
            # "我又" → "他又"
            modified = re.sub(r'我又', '他又', modified)
            # "我已" → "他已"
            modified = re.sub(r'我已', '他已', modified)
            # "我正" → "他正"
            modified = re.sub(r'我正', '他正', modified)
            # "我只" → "他只"
            modified = re.sub(r'我只', '他只', modified)
            # "我才" → "他才"
            modified = re.sub(r'我才', '他才', modified)
            # "我能" → "他能"
            modified = re.sub(r'我能', '他能', modified)
            # "我会" → "他会"
            modified = re.sub(r'我会', '他会', modified)
            # "我想" → "他想"
            modified = re.sub(r'我想', '他想', modified)
            # "我知道" → "他知道"
            modified = re.sub(r'我知道', '他知道', modified)
            # "我看" → "他看" (但要小心"我看了一眼"→"他看了一眼" OK)
            modified = re.sub(r'我看', '他看', modified)
            # "我说" → "他说"
            modified = re.sub(r'我说', '他说', modified)
            # "我去" → "他去"
            modified = re.sub(r'我去', '他去', modified)
            # "我来" → "他来"
            modified = re.sub(r'我来', '他来', modified)
            # "我走" → "他走"
            modified = re.sub(r'我走', '他走', modified)
            # "我吃" → "他吃"
            modified = re.sub(r'我吃', '他吃', modified)
            # "我喝" → "他喝"
            modified = re.sub(r'我喝', '他喝', modified)
            # "我做" → "他做"
            modified = re.sub(r'我做', '他做', modified)
            # "我写" → "他写"
            modified = re.sub(r'我写', '他写', modified)
            # "我拿" → "他拿"
            modified = re.sub(r'我拿', '他拿', modified)
            # "我用" → "他用"
            modified = re.sub(r'我用', '他用', modified)
            # "我听" → "他听"
            modified = re.sub(r'我听', '他听', modified)
            # "我觉" → "他觉'
            modified = re.sub(r'我觉', '他觉', modified)
            # "我试" → "他试'
            modified = re.sub(r'我试', '他试', modified)
            # "我蹲" → "他蹲"
            modified = re.sub(r'我蹲', '他蹲', modified)
            # "我站" → "他站"
            modified = re.sub(r'我站', '他站', modified)
            # "我坐" → "他坐"
            modified = re.sub(r'我坐', '他坐', modified)
            # "我爬" → "他爬"
            modified = re.sub(r'我爬', '他爬', modified)
            # "我扛" → "他扛"
            modified = re.sub(r'我扛', '他扛', modified)
            # "我骑" → "他骑"
            modified = re.sub(r'我骑', '他骑', modified)
            # "我推" → "他推"
            modified = re.sub(r'我推', '他推', modified)
            # "我翻" → "他翻"
            modified = re.sub(r'我翻', '他翻', modified)
            # "我摘" → "他摘"
            modified = re.sub(r'我摘', '他摘', modified)
            # "我闭" → "他闭"
            modified = re.sub(r'我闭', '他闭', modified)
            # "我咽" → "他咽"
            modified = re.sub(r'我咽', '他咽', modified)
            # "我系" → "他系"
            modified = re.sub(r'我系', '他系', modified)
            # "我揣" → "他揣"
            modified = re.sub(r'我揣', '他揣', modified)
            # "我数" → "他数"
            modified = re.sub(r'我数', '他数', modified)
            # "我划" → "他划"
            modified = re.sub(r'我划', '他划', modified)
            # "我掰" → "他掰"
            modified = re.sub(r'我掰', '他掰', modified)
            # "我忍" → "他忍"
            modified = re.sub(r'我忍', '他忍', modified)
            # "我得" → "他得"
            modified = re.sub(r'我得', '他得', modified)
            # "我顾" → "他顾"
            modified = re.sub(r'我顾', '他顾', modified)
            # "我咽" → "他咽"
            modified = re.sub(r'我咽', '他咽', modified)
            # "我心里" → "他心里"
            modified = re.sub(r'我心里', '他心里', modified)
            # "我心里头" → "他心里头"
            modified = re.sub(r'我心里头', '他心里头', modified)
            # "我自个儿" → "他自个儿"
            modified = re.sub(r'我自个儿', '他自个儿', modified)
            # "我自己" → "他自己"
            modified = re.sub(r'我自己', '他自己', modified)
            
            # Catch remaining standalone "我" at sentence boundaries
            # "我。" → "他。"
            # "我，" → "他，"
            # "我！" → "他！"
            # "我？" → "他？"
            # "我——" → "他——"
            # "我\n" → "他\n"
            # "我 " → "他 "
            modified = re.sub(r'我([。，！？——\n\s])', r'他\1', modified)
            
            # "的我" at end → "的他"
            modified = re.sub(r'的我\b', '的他', modified)
            
            modified_segments.append(modified)
    
    content = ''.join(modified_segments)
    
    # Count remaining "我" outside quotes
    segments2 = re.split(r'(\u201c.*?\u201d)', content)
    remaining_wo = 0
    for i, seg in enumerate(segments2):
        if i % 2 == 0:
            remaining_wo += seg.count('我')
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    wo_in_original = original.count('我')
    wo_in_new = content.count('我')
    chen_in_new = content.count('陈大山')
    
    print(f'CH{ch}: 我 {wo_in_original}→{wo_in_new} (叙述中剩{remaining_wo}), 陈大山={chen_in_new}')

print("\n=== 完成 ===")
