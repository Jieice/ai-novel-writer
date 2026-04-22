#!/usr/bin/env python3
"""
在5个第一人称→第三人称的章节中，适当插入"陈大山"消除歧义。
"""
import os, sys, re
sys.stdout.reconfigure(encoding='utf-8')
folder = r'd:\AI\AI小说创作系统\山村小神医\正文卷'

first_person_chapters = [1, 2, 3, 11, 12]

for ch in first_person_chapters:
    matches = [f for f in os.listdir(folder) if f.startswith(f'第{ch}章')]
    path = os.path.join(folder, matches[0])
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by quotes to only modify narration
    segments = re.split(r'(\u201c.*?\u201d)', content)
    
    state = {'ta_count': 0, 'chen_count': 0}
    
    modified_segments = []
    for idx, seg in enumerate(segments):
        if idx % 2 == 1:
            # Dialogue - keep
            modified_segments.append(seg)
            continue
        
        # Narration
        def replace_ta(m):
            state['ta_count'] += 1
            if state['chen_count'] < 3 or state['ta_count'] >= 5:
                state['chen_count'] += 1
                state['ta_count'] = 0
                return '陈大山'
            return '他'
        
        modified = re.sub(r'他(?!爹|娘|家|爷爷|们)', replace_ta, seg)
        modified_segments.append(modified)
    
    content = ''.join(modified_segments)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    chen_total = content.count('陈大山')
    ta_total = content.count('他')
    print(f'CH{ch}: 陈大山={chen_total}, 他={ta_total}')
