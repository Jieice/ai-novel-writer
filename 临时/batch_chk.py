import subprocess
import re
import os

project = "D:/AI/AI小说创作系统/山村小神医"
script = "D:/AI/AI小说创作系统/novel-assistant/scripts/chapter_health_check.py"

results = []

for ch in range(1, 31):
    cmd = f'python "{script}" --project "{project}" --chapter {ch}'
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, encoding='utf-8', errors='replace')
        out = proc.stdout + proc.stderr

        # 提取关键指标
        chars = re.search(r'字数: (\d+)', out)
        ai_rate = re.search(r'预估 AI 率: ([\d.]+)%', out)
        dash = re.search(r'破折号: (\d+)次', out)
        template = re.search(r'AI 模板词.*总次数: (\d+)', out)
        exit_code = re.search(r'退出码(\d+)', out)

        wc = int(chars.group(1)) if chars else 0
        ai = float(ai_rate.group(1)) if ai_rate else 0
        dash_count = int(dash.group(1)) if dash else 0
        tmpl = int(template.group(1)) if template else 99
        ec = int(exit_code.group(1)) if exit_code else 99

        # 汇总WARNING信息
        warnings = []
        if 'WARNING' in out:
            warn_matches = re.findall(r'\[WARNING\].*', out)
            for w in warn_matches:
                w_clean = w.replace('\n', ' ').strip()[:80]
                warnings.append(w_clean)

        status = "PASS" if ec == 0 else "FAIL"

        results.append({
            'ch': ch,
            'wc': wc,
            'ai': ai,
            'dash': dash_count,
            'tmpl': tmpl,
            'ec': ec,
            'status': status,
            'warnings': warnings
        })
    except Exception as e:
        results.append({'ch': ch, 'ec': 99, 'status': 'ERROR', 'error': str(e)})

print("=" * 100)
print(f"{'CH':>3} | {'字数':>5} | {'AI率%':>6} | {'破折号':>4} | {'模板词':>4} | {'退出码':>4} | {'状态':>5} | 主要WARNING")
print("-" * 100)
for r in results:
    if r['status'] == 'ERROR':
        print(f" CH{r['ch']:>2} | ERROR: {r.get('error','')}")
    else:
        warn_str = "; ".join(r['warnings'][:2]) if r['warnings'] else ""
        print(f" CH{r['ch']:>2} | {r['wc']:>5} | {r['ai']:>6.1f} | {r['dash']:>4} | {r['tmpl']:>4} | {r['ec']:>4} | {r['status']:>5} | {warn_str[:60]}")

print("=" * 100)
pass_cnt = sum(1 for r in results if r['status'] == 'PASS')
fail_cnt = sum(1 for r in results if r['status'] == 'FAIL')
err_cnt = sum(1 for r in results if r.get('status') == 'ERROR')
print(f"PASS: {pass_cnt}/30  FAIL: {fail_cnt}/30  ERROR: {err_cnt}/30")
