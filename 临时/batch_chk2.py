import subprocess
import re
import sys

project = "D:/AI/AI小说创作系统/山村小神医"
script = "D:/AI/AI小说创作系统/novel-assistant/scripts/chapter_health_check.py"

results = []

for ch in range(1, 31):
    cmd = f'python "{script}" --project "{project}" --chapter {ch}'
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, encoding='utf-8', errors='replace')
        out = proc.stdout + proc.stderr

        # 真实退出码（Python脚本是否崩溃）
        ec = proc.returncode

        # 提取字数
        chars = re.search(r'字数: (\d+)', out)
        wc = int(chars.group(1)) if chars else 0

        # 提取AI率
        ai_m = re.search(r'预估 AI 率: ([\d.]+)%', out)
        ai = float(ai_m.group(1)) if ai_m else 0

        # 提取破折号
        dash_m = re.search(r'破折号[：:]\s*(\d+)', out)
        dash = int(dash_m.group(1)) if dash_m else 0

        # 提取退出码文本（脚本自己输出的）
        ec_m = re.search(r'\[SUMMARY\].*?退出码[：:\s]*(\d+)', out, re.DOTALL)
        ec_text = int(ec_m.group(1)) if ec_m else ec

        # AI模板词
        tmpl_m = re.search(r'\[2\] AI 模板词.*?总次数:\s*(\d+)', out, re.DOTALL)
        tmpl = int(tmpl_m.group(1)) if tmpl_m else 0

        # WARNING列表
        warnings = re.findall(r'\[WARNING\][^\n]*', out)

        status = "PASS" if ec_text == 0 else "FAIL"

        results.append({
            'ch': ch, 'wc': wc, 'ai': ai, 'dash': dash, 'tmpl': tmpl,
            'ec': ec_text, 'status': status, 'warnings': warnings
        })
    except Exception as e:
        results.append({'ch': ch, 'status': 'ERROR', 'error': str(e)})

print(f"{'CH':>3} | {'字数':>5} | {'AI率%':>6} | {'破折号':>4} | {'模板词':>4} | {'脚本退出码':>6} | {'状态':>5}")
print("-" * 90)
for r in results:
    if r['status'] == 'ERROR':
        print(f" CH{r['ch']:>2} | ERROR")
    else:
        print(f" CH{r['ch']:>2} | {r['wc']:>5} | {r['ai']:>6.1f} | {r['dash']:>4} | {r['tmpl']:>4} | {r['ec']:>6} | {r['status']:>5}")

print("-" * 90)
pass_cnt = sum(1 for r in results if r['status'] == 'PASS')
fail_cnt = sum(1 for r in results if r['status'] == 'FAIL')

print(f"\nPASS: {pass_cnt}/30  FAIL: {fail_cnt}/30\n")

# 按问题类型汇总
print("=== 问题汇总 ===")
all_warnings = []
for r in results:
    if 'warnings' in r:
        for w in r['warnings']:
            all_warnings.append((r['ch'], w))

# 统计各类问题
from collections import Counter
warn_counter = Counter()
for ch, w in all_warnings:
    # 简化WARNING文本
    if '破折号' in w: key = '破折号过多'
    elif 'A类结构性模式' in w: key = 'A类结构性模式'
    elif 'B类AI套话' in w: key = 'B类AI套话'
    elif 'C类' in w: key = 'C类/破折号'
    elif 'AI 率偏高' in w: key = 'AI率偏高'
    elif '口语化' in w: key = '口语化'
    elif '字数偏差' in w or '偏离目标' in w: key = '字数偏差'
    elif '对话未加引号' in w or '裸对话' in w: key = '裸对话'
    elif '爽点不够' in w: key = '爽点不够'
    elif '超长段落' in w: key = '超长段落'
    elif '场景过多' in w: key = '场景过多'
    elif '实质行动' in w: key = '反派无实质行动'
    elif '村级反派' in w: key = '反派村级'
    else: key = w[:40]
    warn_counter[key] += 1

for k, v in warn_counter.most_common():
    chs = [str(ch) for ch, w in all_warnings if k[:20] in w]
    print(f"  {k}: {v}章节 ({', '.join(chs[:8])})")
