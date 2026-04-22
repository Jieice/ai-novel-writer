#!/usr/bin/env python3
"""彻底替换：叙述中所有"我"→"他"，对话内保持不变"""
import os, sys, re
sys.stdout.reconfigure(encoding='utf-8')
folder = r'd:\AI\AI小说创作系统\山村小神医\正文卷'

first_person_chapters = [1, 2, 3, 11, 12]

for ch in first_person_chapters:
    matches = [f for f in os.listdir(folder) if f.startswith(f'第{ch}章')]
    path = os.path.join(folder, matches[0])
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Strategy: Split by full-width quote pairs
    # Only replace "我" in segments OUTSIDE quotes
    # Use a state machine approach
    result = []
    in_quote = False
    i = 0
    while i < len(content):
        # Check for opening quote
        if content[i] == '\u201c' and not in_quote:
            in_quote = True
            result.append(content[i])
            i += 1
        # Check for closing quote
        elif content[i] == '\u201d' and in_quote:
            in_quote = False
            result.append(content[i])
            i += 1
        # Replace "我" only outside quotes
        elif content[i] == '我' and not in_quote:
            result.append('他')
            i += 1
        else:
            result.append(content[i])
            i += 1
    
    content = ''.join(result)
    
    # Now fix specific third-person issues:
    # "他爹" in narration referring to 陈大山's father → keep as "他爹" (OK)
    # "他娘" in narration → keep as "他娘" (OK)
    # "他爷爷" → keep (OK)
    # "他自个儿" → keep (OK)
    
    # But some "他" should actually be "陈大山" for clarity at chapter starts
    # or when first mentioned. Let's add "陈大山" at the very first "他" in narration
    # (if it doesn't already have "陈大山" in the chapter)
    
    # Count results
    wo_count = content.count('我')
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f'CH{ch}: 我→{wo_count} (对话中的"我"保留)')

# Verify: count "我" in narration vs dialogue for each chapter
print("\n=== 验证 ===")
for ch in first_person_chapters:
    matches = [f for f in os.listdir(folder) if f.startswith(f'第{ch}章')]
    path = os.path.join(folder, matches[0])
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by quotes
    segments = re.split(r'(\u201c.*?\u201d)', content)
    narration_wo = 0
    dialogue_wo = 0
    for i, seg in enumerate(segments):
        wo = seg.count('我')
        if i % 2 == 0:
            narration_wo += wo
        else:
            dialogue_wo += wo
    
    chen = content.count('陈大山')
    ta = content.count('他')
    print(f'CH{ch}: 叙述中我={narration_wo}, 对话中我={dialogue_wo}, 陈大山={chen}, 他={ta}')
