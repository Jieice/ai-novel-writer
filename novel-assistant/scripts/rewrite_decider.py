#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节重写决策脚本 (rewrite_decider.py)

通过 subprocess 运行子脚本，输出直接打印到终端（绕过 Windows subprocess 兼容问题）。
解析子脚本输出的关键指标，综合决策。

决策逻辑:
  A级 - 整章重写: 场景 > 2 场，或发布审稿 FAIL
  B级 - 整章重写: 结构噪音 ≥ 2 项（账本/总结/讲述同时超标）
  C级 - 整章重写: 引号 < 6 且 CRITICAL ≥ 2
  D级 - auto_fix: 模板词 > 8 或引号 < 6 或 CRITICAL > 0
  E级 - SKIP: 仅 WARNING
  F级 - PASS: 全部通过

退出码:
  0 = PASS / SKIP / WARNING（可跳过或细修）
  1 = 需要整章重写（A/B/C级）
  2 = 需要 auto_fix 细修（D级）

用法:
  python rewrite_decider.py --project <项目路径> --chapter <章节号>
  python rewrite_decider.py --project <项目路径> --chapter 1 --verbose
"""

import argparse
import io
import re
import subprocess
import sys
from enum import Enum
from pathlib import Path

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')


class Decision(Enum):
    REWRITE_A = "A级_整章重写_场景过多"
    REWRITE_B = "整章重写_结构阻断"
    REWRITE_C = "整章重写_引号严重缺失"
    FIX_AUTO = "auto_fix_细修"
    SKIP = "WARNING_可跳过"
    PASS = "PASS_可交付"


def _find_script(name: str) -> Path:
    return Path(__file__).parent / name


def run_with_output(script_name: str, project_path: str, chapter_num: int) -> tuple[int, str]:
    """运行脚本，输出直接打印到终端，返回退出码和输出文本。"""
    script = _find_script(script_name)
    result = subprocess.run(
        [sys.executable, str(script), '--project', project_path, '--chapter', str(chapter_num)],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        check=False,
    )
    output = result.stdout + result.stderr
    if output:
        print(output)
    return result.returncode, output


def parse_publish_info(output: str) -> dict:
    info = {'scene_count': 0, 'bookkeeping': 0, 'summary': 0, 'telling': 0, 'has_blockers': False}
    for line in output.split('\n'):
        line = line.strip()
        if line.startswith('场戏数:'):
            try:
                info['scene_count'] = int(line.split(':')[-1].strip())
            except ValueError:
                pass
        elif line.startswith('账本式说明:'):
            try:
                info['bookkeeping'] = int(line.split(':')[-1].strip())
            except ValueError:
                pass
        elif line.startswith('总结/计划句:'):
            try:
                info['summary'] = int(line.split(':')[-1].strip())
            except ValueError:
                pass
        elif line.startswith('讲述句:'):
            try:
                info['telling'] = int(line.split(':')[-1].strip())
            except ValueError:
                pass
        elif any(k in line for k in ['场景过多', '账本式说明过多', '总结/计划句过多', '讲述句过多']):
            info['has_blockers'] = True
    return info


def parse_health_info(output: str) -> dict:
    info = {
        'quote_pairs': 0, 'template_count': 0, 'ai_rate': 0.0,
        'colloquial': 0.0, 'critical': 0, 'warning': 0,
    }
    for line in output.split('\n'):
        line = line.strip()
        if '中文引号对' in line:
            m = re.search(r'(\d+)', line)
            if m:
                info['quote_pairs'] = int(m.group(1))
        elif 'AI模板词' in line and '总次数' in line:
            m = re.search(r'(\d+)', line)
            if m:
                info['template_count'] = int(m.group(1))
        elif '预估 AI 率' in line:
            m = re.search(r'([\d.]+)', line)
            if m:
                try:
                    info['ai_rate'] = float(m.group(1))
                except ValueError:
                    pass
        elif '口语化' in line and '百字' in line:
            m = re.search(r'([\d.]+)', line)
            if m:
                try:
                    info['colloquial'] = float(m.group(1))
                except ValueError:
                    pass
        elif '[CRITICAL FAIL]' in line:
            info['critical'] += 1
        elif '[WARNING]' in line:
            info['warning'] += 1
    if info['template_count'] == 0:
        for line in output.split('\n'):
            if '模板词' in line and '总次数' in output:
                m = re.search(r'(\d+)', line)
                if m:
                    info['template_count'] = int(m.group(1))
                    break
    return info


def decide(pub_rc: int, pub_out: str, health_rc: int, health_out: str) -> tuple[Decision, str]:
    pub = parse_publish_info(pub_out)
    health = parse_health_info(health_out)

    if pub['scene_count'] > 2:
        return Decision.REWRITE_A, f"场景过多: {pub['scene_count']} 场 > 2 场上限"

    if pub_rc == 1:
        if pub['has_blockers'] or pub['scene_count'] > 0:
            structural = 0
            if pub['bookkeeping'] >= 6:
                structural += 1
            if pub['summary'] >= 5:
                structural += 1
            if pub['telling'] >= 5:
                structural += 1
            if structural >= 2:
                return Decision.REWRITE_B, f"结构噪音 ≥ 2 项 (账本{pub['bookkeeping']}/总结{pub['summary']}/讲述{pub['telling']})"
            return Decision.REWRITE_A, "发布审稿 FAIL（结构性阻断项）"
        if pub_out.strip() == '' or pub['scene_count'] == 0:
            return Decision.REWRITE_A, "发布审稿 FAIL（场景/结构问题）"

    if health_rc == 1:
        if health['quote_pairs'] < 6 and health['critical'] >= 2:
            return Decision.REWRITE_C, f"引号仅 {health['quote_pairs']} 对且 CRITICAL ≥ 2，引号缺失严重"
        if health_out.strip() == '' or health['quote_pairs'] == 0:
            return Decision.REWRITE_A, "健康检查 FAIL（严重技术问题）"
        return Decision.FIX_AUTO, f"健康检查 FAIL（引号{health['quote_pairs']}/模板{health['template_count']}/AI率{health['ai_rate']}%）"

    if health['template_count'] > 8 or health['quote_pairs'] < 6:
        return Decision.FIX_AUTO, f"模板词 {health['template_count']} 个或引号 {health['quote_pairs']} 对"

    if health['critical'] > 0:
        return Decision.FIX_AUTO, f"CRITICAL 问题 {health['critical']} 个"

    if health_rc == 2 or health['warning'] > 0:
        return Decision.SKIP, f"仅 WARNING {health['warning']} 个，不阻断交付"

    return Decision.PASS, "健康检查通过"


def main():
    parser = argparse.ArgumentParser(description='章节重写决策脚本')
    parser.add_argument('--project', required=True, help='项目根目录路径')
    parser.add_argument('--chapter', type=int, required=True, help='章节号')
    parser.add_argument('--verbose', action='store_true', help='显示详细诊断')
    args = parser.parse_args()

    print()
    print('=' * 55)
    print(f'[第{args.chapter}章] 重写决策')
    print('=' * 55)
    print()
    print('[发布审稿]')
    pub_rc = 0
    pub_out = ''
    try:
        pub_rc, pub_out = run_with_output('publish_readiness_audit.py', args.project, args.chapter)
    except Exception:
        pub_rc = 1

    print()
    print('[健康检查]')
    health_rc = 0
    health_out = ''
    try:
        health_rc, health_out = run_with_output('chapter_health_check.py', args.project, args.chapter)
    except Exception:
        health_rc = 1

    decision, reason = decide(pub_rc, pub_out, health_rc, health_out)

    print()
    print('=' * 55)
    print('[决策结果]')
    print(f'  等级: {decision.value}')
    print(f'  原因: {reason}')
    print()

    if decision in (Decision.REWRITE_A, Decision.REWRITE_B, Decision.REWRITE_C):
        print('[建议] 整章重写')
        print('  结构性/硬阈值问题，auto_fix 无法解决，需要整章重写')
        sys.exit(1)
    elif decision == Decision.FIX_AUTO:
        print('[建议] auto_fix 细修')
        print(f'  提示: python auto_fix_chapter.py --project <path> --chapter {args.chapter} --strict')
        sys.exit(2)
    elif decision == Decision.SKIP:
        print('[建议] 可跳过或细修')
        print('  仅 WARNING，不阻断交付')
        sys.exit(0)
    else:
        print('[结论] PASS - 本章可交付')
        sys.exit(0)


if __name__ == '__main__':
    main()
