import os, sys, re
sys.stdout.reconfigure(encoding='utf-8')
folder = r'd:\AI\AI小说创作系统\山村小神医\正文卷'

for ch in [1, 2, 3, 11, 12]:
    matches = [f for f in os.listdir(folder) if f.startswith(f'第{ch}章')]
    path = os.path.join(folder, matches[0])
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by quotes to find "我" in narration only
    segments = re.split(r'(\u201c.*?\u201d)', content)
    
    narration_wo = []
    for i, seg in enumerate(segments):
        if i % 2 == 0 and '我' in seg:
            # Find each occurrence and show context
            for m in re.finditer(r'我', seg):
                pos = m.start()
                start = max(0, pos-6)
                end = min(len(seg), pos+6)
                ctx = seg[start:end].replace('\n', '↵')
                narration_wo.append(ctx)
    
    print(f'\nCH{ch} 叙述中残留"我" ({len(narration_wo)}个):')
    for j, ctx in enumerate(narration_wo[:15]):
        print(f'  {j+1}. ...{ctx}...')
    if len(narration_wo) > 15:
        print(f'  ... 还有{len(narration_wo)-15}个')
