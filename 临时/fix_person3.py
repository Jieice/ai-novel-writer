#!/usr/bin/env python3
"""
在5个章节中，将部分"他"替换为"陈大山"以消除歧义。
规则：
1. 章节前3次出现的叙述中"他"→"陈大山"
2. 每段第一个"他"→"陈大山"（如果该段超过3个"他"）
3. "他爹""他娘"→保留（这是陈大山称呼父母，第三人称OK）
4. 前面刚提过"赵老三"等男性角色后的第一个"他"→"陈大山"
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
    
    original = content
    
    # Rule 1: 每段开头前3次叙述中"他"→"陈大山"
    # 先在章节最开始出现"他"的地方替换
    # Split by quotes to only modify narration
    segments = re.split(r'(\u201c.*?\u201d)', content)
    
    narration_ta_count = 0  # Count "他" in narration so far
    
    modified_segments = []
    for i, seg in enumerate(segments):
        if i % 2 == 1:
            # Dialogue - keep as is
            modified_segments.append(seg)
            continue
        
        # Narration
        # Rule: First 3 "他" in narration → "陈大山"
        # But skip "他爹" "他娘" "他爷爷" "他家" etc (already clear)
        lines = seg.split('\n')
        new_lines = []
        for line in lines:
            new_line = line
            # Replace some "他" with "陈大山"
            # Pattern: standalone "他" at certain positions
            
            # If this line starts a paragraph and has "他", 
            # and we haven't used "陈大山" yet in this paragraph
            if '他' in new_line:
                # Replace first standalone "他" (not part of "他爹""他娘""他家""他爷爷""他们")
                # with "陈大山" if narration_ta_count < 3
                def replace_ta(m):
                    global narration_ta_count
                    prefix = m.group(1) if m.group(1) else ''
                    char_after = m.group(2)
                    # Skip if it's "他爹""他娘""他家""他爷爷""他们""他的""了他""着"
                    skip_chars = '爹娘家爷们的地了着过'
                    if char_after and char_after in skip_chars:
                        return m.group(0)
                    if narration_ta_count < 3:
                        narration_ta_count += 1
                        return prefix + '陈大山' + char_after
                    return m.group(0)
                
                # This won't work with global, let's do it differently
                pass
            
            new_lines.append(new_line)
        
        modified_segments.append(seg)  # Keep original for now
    
    # Different approach: simple targeted replacements
    # Just replace the first few "他" in the chapter with "陈大山"
    content = original
    
    # Find first 5 standalone "他" in narration and replace with "陈大山"
    segments = re.split(r'(\u201c.*?\u201d)', content)
    ta_count = 0
    max_replacements = 5
    
    modified_segments = []
    for i, seg in enumerate(segments):
        if i % 2 == 1:
            modified_segments.append(seg)
            continue
        
        # Narration
        if ta_count >= max_replacements:
            modified_segments.append(seg)
            continue
        
        # Replace standalone "他" with "陈大山"
        # "他" followed by certain characters = standalone usage
        # Skip "他爹" "他娘" "他家" "他爷爷" "他们" "他的" "了他" 
        result = []
        j = 0
        while j < len(seg) and ta_count < max_replacements:
            if seg[j] == '他':
                # Check what comes after
                next_char = seg[j+1] if j+1 < len(seg) else ''
                # Check what comes before
                prev_char = seg[j-1] if j > 0 else ''
                
                # Skip compound words
                skip_after = '爹娘家爷们'  # 他爹/他娘/他家/他爷爷/他们
                skip_before = '的替跟给被叫让冲比比'  # 的他/替他 etc (keep as 他)
                
                if next_char in skip_after:
                    result.append(seg[j])
                    j += 1
                elif ta_count < max_replacements:
                    result.append('陈大山')
                    ta_count += 1
                    j += 1
                else:
                    result.append(seg[j])
                    j += 1
            else:
                result.append(seg[j])
                j += 1
        
        # Append remaining
        result.append(seg[j:])
        modified_segments.append(''.join(result))
    
    content = ''.join(modified_segments)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    chen_count = content.count('陈大山')
    ta_count_total = content.count('他')
    print(f'CH{ch}: 陈大山={chen_count}, 他={ta_count_total}')
