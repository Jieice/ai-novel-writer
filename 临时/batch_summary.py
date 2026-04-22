import subprocess, re

project = "D:/AI/AI小说创作系统/山村小神医"
script = "D:/AI/AI小说创作系统/novel-assistant/scripts/chapter_health_check.py"

results = []
for ch in range(1, 31):
    cmd = f'python "{script}" --project "{project}" --chapter {ch}"'
    try:
        proc = subprocess.run(f'python "{script}" --project "{project}" --chapter {ch}',
            shell=True, capture_output=True, text=True, timeout=60, encoding='utf-8', errors='replace')
        out = proc.stdout + proc.stderr

        # Process exit code - did script crash?
        ec = proc.returncode

        chars = re.search(r'字数: (\d+)', out)
        wc = int(chars.group(1)) if chars else 0
        ai_m = re.search(r'预估 AI 率: ([\d.]+)%', out)
        ai = float(ai_m.group(1)) if ai_m else 0
        dash_m = re.search(r'破折号[：:]\s*(\d+)', out)
        dash = int(dash_m.group(1)) if dash_m else 0

        # 判断是否崩溃（退出码非0=崩溃）
        # WARNING列表
        warnings = re.findall(r'\[WARNING\][^\n]*', out)
        pass_found = '[PASS]' in out and '[FAIL]' not in out and ec == 0

        results.append({'ch': ch, 'wc': wc, 'ai': ai, 'dash': dash,
                        'ec': ec, 'warnings': warnings, 'pass': pass_found})
    except:
        results.append({'ch': ch, 'ec': -1, 'warnings': [], 'pass': False})

print("CH  | 字数   | AI率  | 破折号 | 状态  | 主要WARNING(前2个)")
print("-" * 90)
for r in results:
    w = "; ".join(r['warnings'][:2]) if r['warnings'] else ""
    status = "PASS" if r['pass'] else "WARN"
    ec_str = "崩溃" if r['ec'] != 0 else ""
    print(f"CH{r['ch']:>2} | {r['wc']:>5} | {r['ai']:>5.1f}% | {r['dash']:>6} | {status:>5} {ec_str} | {w[:60]}")

pass_cnt = sum(1 for r in results if r['pass'])
print(f"\n真实PASS(退出码0+无FAIL): {pass_cnt}/30")
