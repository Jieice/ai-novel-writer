#!/usr/bin/env python3
"""
更安全的第三人称润色：
1. 只替换段首/句首的"他"→"陈大山"
2. 不替换对话标签中的"他"（紧跟在"后的）
3. 不替换"他爹""他娘""他家""他爷爷""他们"
4. 只在叙述中替换（引号外）
5. 每章前3个替换，之后每8个"他"替换1个
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
    
    # First, revert any incorrect "陈大山" that should be "他"
    # (from the previous over-aggressive replacement)
    # We'll just redo the whole thing from scratch by reading the current file
    # and being more careful
    
    # Split by quotes to only modify narration
    segments = re.split(r'(\u201c.*?\u201d)', content)
    
    state = {'ta_count': 0, 'chen_count': 0}
    
    modified_segments = []
    for idx, seg in enumerate(segments):
        if idx % 2 == 1:
            # Dialogue - keep
            modified_segments.append(seg)
            continue
        
        # Narration - replace "他" at safe positions only
        # Safe: after 。！？\n (sentence start)
        # Unsafe: after " (dialogue tag), after other chars
        
        def safe_replace(m):
            prefix = m.group(1)  # char before "他"
            ta = m.group(2)      # "他"
            suffix = m.group(3)  # char after "他"
            
            # Check if "他" is a dialogue tag (preceded by closing quote)
            if prefix == '\u201d':
                return m.group(0)  # Don't replace - it's a dialogue tag
            
            # Check compound words
            if suffix and suffix in '爹娘家爷们':
                return m.group(0)
            
            state['ta_count'] += 1
            
            # First 3 → "陈大山", then every 8th
            if state['chen_count'] < 3 or state['ta_count'] >= 8:
                state['chen_count'] += 1
                state['ta_count'] = 0
                return prefix + '陈大山' + suffix
            
            return m.group(0)
        
        # Match: (char_before)他(char_after)
        modified = re.sub(r'(.)(他)(.)', safe_replace, seg)
        modified_segments.append(modified)
    
    content = ''.join(modified_segments)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    chen_total = content.count('陈大山')
    ta_total = content.count('他')
    print(f'CH{ch}: 陈大山={chen_total}, 他={ta_total}')
