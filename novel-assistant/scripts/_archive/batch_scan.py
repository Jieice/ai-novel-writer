#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量扫描所有章节，生成问题分流表

直接调用 publish_readiness_audit.py 和 chapter_health_check.py，
根据返回码和输出内容做决策。
"""

import re
import subprocess
import sys
from pathlib import Path


def _find_script(name: str) -> Path:
    return Path(__file__).parent / name


def run_script(script_name: str, project: str, chapter: int) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(_find_script(script_name)),
         '--project', project, '--chapter', str(chapter)],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        check=False,
    )
    return result.returncode, result.stdout + result.stderr


def parse_pub(output: str) -> dict:
    info = {
        'scene_count': 0, 'naked': 0, 'bookkeeping': 0,
        'summary': 0, 'telling': 0,
    }
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
        elif line.startswith('裸对话:'):
            try:
                info['naked'] = int(line.split(':')[-1].strip())
            except ValueError:
                pass
    return info


def parse_health(output: str) -> dict:
    info = {
        'quote_pairs': 0, 'template_count': 0,
        'ai_rate': 0.0, 'colloquial': 0.0,
        'critical': 0, 'warning': 0,
    }
    for line in output.split('\n'):
        line = line.strip()
        if '中文引号对' in line:
            m = re.search(r'(\d+)', line)
            if m:
                info['quote_pairs'] = int(m.group(1))
        elif '模板词' in line and '总次数' in line:
            m = re.search(r'(\d+)', line)
            if m:
                info['template_count'] = int(m.group(1))
        elif '预估' in line and 'AI率' in line:
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
    return info


def decide(pub_rc: int, pub: dict, health_rc: int, health: dict) -> tuple[str, str]:
    if pub_rc == 1:
        if pub['scene_count'] > 2:
            return 'A级_整章重写', f"场景过多({pub['scene_count']}场)"
        structural = sum([
            pub['bookkeeping'] >= 6,
            pub['summary'] >= 5,
            pub['telling'] >= 5,
        ])
        if structural >= 2:
            return 'B级_整章重写', f"结构噪音(账本{pub['bookkeeping']}/总结{pub['summary']}/讲述{pub['telling']})"
        return 'A级_整章重写', f"发布审稿FAIL"

    if health_rc == 1:
        if health['quote_pairs'] < 6 and health['critical'] >= 2:
            return 'C级_整章重写', f"引号缺失({health['quote_pairs']}对)"
        return 'auto_fix_细修', f"健康检查FAIL"

    if health['template_count'] > 8 or health['quote_pairs'] < 6:
        return 'auto_fix_细修', f"模板词{health['template_count']}/引号{health['quote_pairs']}"

    if health['critical'] > 0:
        return 'auto_fix_细修', f"CRITICAL({health['critical']})"

    if health_rc == 2 or health['warning'] > 0:
        return 'WARNING_可跳过', f"WARNING({health['warning']})"

    return 'PASS_可交付', '通过'


def main():
    project = 'd:/AI/AI小说创作系统/山村小神医'

    print()
    print('=' * 70)
    print('章节批量扫描报告')
    print('=' * 70)
    print()
    print(f'{"章节":<8} {"发布审稿":<10} {"健康检查":<10} {"决策":<22} {"详情"}')
    print('-' * 70)

    stats = {'PASS': 0, 'SKIP': 0, 'FIX': 0, 'REWRITE': 0}
    results = []

    for ch in range(1, 28):
        pub_rc, pub_out = run_script('publish_readiness_audit.py', project, ch)
        health_rc, health_out = run_script('chapter_health_check.py', project, ch)

        pub = parse_pub(pub_out)
        health = parse_health(health_out)

        decision, reason = decide(pub_rc, pub, health_rc, health)

        pub_label = 'FAIL' if pub_rc == 1 else ('PASS' if pub_rc == 0 else str(pub_rc))
        health_label = 'FAIL' if health_rc == 1 else ('PASS' if health_rc == 0 else str(health_rc))

        if '重写' in decision:
            stats['REWRITE'] += 1
        elif 'auto_fix' in decision:
            stats['FIX'] += 1
        elif 'WARNING' in decision:
            stats['SKIP'] += 1
        else:
            stats['PASS'] += 1

        status = '❌' if '重写' in decision else ('🔧' if 'auto_fix' in decision else ('⚠️' if 'WARNING' in decision else '✅'))
        print(f'第{ch:<4}章  {pub_label:<10} {health_label:<10} {status} {decision:<20} {reason[:30]}')
        results.append((ch, pub_rc, pub, health_rc, health, decision, reason))

    print()
    print('=' * 70)
    print('统计汇总')
    print('=' * 70)
    print(f'  ✅ PASS (可交付):        {stats["PASS"]} 章')
    print(f'  ⚠️  WARNING (可跳过):    {stats["SKIP"]} 章')
    print(f'  🔧 auto_fix (细修):    {stats["FIX"]} 章')
    print(f'  ❌ REWRITE (整章重写):  {stats["REWRITE"]} 章')
    print(f'  总计: {sum(stats.values())} 章')
    print()

    rewrite = [(ch, d, r) for ch, _, _, _, _, d, r in results if '重写' in d]
    fix = [(ch, d, r) for ch, _, _, _, _, d, r in results if 'auto_fix' in d]
    skip = [(ch, d, r) for ch, _, _, _, _, d, r in results if 'WARNING' in d]
    passes = [(ch, d, r) for ch, _, _, _, _, d, r in results if d == 'PASS_可交付']

    if rewrite:
        print('【需要整章重写】(优先级最高，结构性/硬阈值问题)')
        for ch, d, r in rewrite:
            print(f'  第{ch}章: {r}')
        print()
    if fix:
        print('【需要细修】(auto_fix 可处理)')
        for ch, d, r in fix:
            print(f'  第{ch}章: {r}')
        print()
    if skip:
        print('【可跳过】(WARNING 不阻断交付)')
        for ch, d, r in skip:
            print(f'  第{ch}章: {r}')
        print()
    if passes:
        print('【可直接交付】')
        for ch, d, r in passes:
            print(f'  第{ch}章: {r}')


if __name__ == '__main__':
    main()
