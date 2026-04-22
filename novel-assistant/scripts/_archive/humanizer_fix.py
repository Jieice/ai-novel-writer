#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Humanizer 降重集成脚本 v2
基于 chapter_health_check.py 的准确 AI 率检测，实现双阈值控制流程

双阈值流程：
  1. AI率 < 55%：无需降重
  2. AI率 55-70%：自动应用 Humanizer 规则降重
  3. AI率 > 70%：需要人工重写

用法：
  python humanizer_fix.py --project <项目路径> --chapter <章节号>    # 自动降重
  python humanizer_fix.py --project <项目路径> --chapter <章节号> --dry-run  # 预览
"""

import re
import os
import sys
import io
import argparse
import subprocess

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')


# ============ Humanizer A类模式（中文小说适配）============

HUMANIZER_A_PATTERNS = {
    # 否定式排比：不是...也不是...更不是... → 简化为直接陈述
    '否定式排比': [
        (r'不是[　\s]*也不是[　\s]*更不是', '不是'),
        (r'不是[　\s]*也不是[　\s]*也不是', '不是'),
        (r'既不[　\s]*也不[　\s]*还不能', '也不能'),
    ],
    # 三段式堆砌：首先...其次...最后... → 改为两项
    '三段式堆砌': [
        (r'首先[，,][　\s]*其次[，,][　\s]*最后', '然后'),
        (r'第一[，,][　\s]*第二[，,][　\s]*第三', '一方面另一方面'),
        (r'第一[、][　\s]*第二[、][　\s]*第三', '一方面另一方面'),
    ],
    # ing结尾虚假分析
    'ing结尾': [
        (r'彰显了', ''),
        (r'体现了', ''),
        (r'确保了', ''),
        (r'反映了', ''),
        (r'做出了贡献', ''),
        (r'培养了', ''),
        (r'促进了', ''),
    ],
    # 强行展望结尾
    '强行展望': [
        (r'挑战与机遇并存[，,]?', ''),
        (r'光明的前途[，,]?', ''),
        (r'未来一定[^\n，,。]*', ''),
        (r'必将[^\n，,。]*', ''),
        (r'等待着[^\n，,。]*', ''),
    ],
}

# ============ Humanizer B类模式（中文小说适配）============

HUMANIZER_B_PATTERNS = {
    # 填充短语
    '填充短语': [
        (r'总而言之[，,]?', ''),
        (r'值得注意的是[，,]?', ''),
        (r'实际上[，,]?', ''),
        (r'事实上[，,]?', ''),
        (r'从某种意义上说[，,]?', ''),
        (r'可以说[，,]?', ''),
        (r'严格来说[，,]?', ''),
    ],
    # AI高频词
    'AI高频词': [
        (r'此外[，,]?', ''),
        (r'深入探讨[^\n，,。]*', ''),
        (r'至关重要', '重要'),
        (r'不可或缺', '必须有'),
        (r'不容忽视', ''),
    ],
    # 过度限定
    '过度限定': [
        (r'可能[的地得]?', ''),
        (r'也许[的地得]?', ''),
        (r'大概[的地得]?', ''),
        (r'一般来说[，,]?', ''),
        (r'基本上[，,]?', ''),
        (r'看上去', '看着'),
        (r'似乎', '像'),
    ],
}


def apply_humanizer_a(text):
    """应用 A 类模式修复"""
    changes = 0
    for pattern_type, replacements in HUMANIZER_A_PATTERNS.items():
        for old_pattern, new_pattern in replacements:
            new_text, count = re.subn(old_pattern, new_pattern, text)
            if count > 0:
                changes += count
                text = new_text
    return text, changes


def apply_humanizer_b(text):
    """应用 B 类模式修复"""
    changes = 0
    for pattern_type, replacements in HUMANIZER_B_PATTERNS.items():
        for old_pattern, new_pattern in replacements:
            new_text, count = re.subn(old_pattern, new_pattern, text)
            if count > 0:
                changes += count
                text = new_text
    return text, changes


def get_ai_rate_from_health_check(project_path, chapter_num):
    """调用 chapter_health_check.py 并解析 AI 率"""
    try:
        result = subprocess.run(
            [sys.executable,
             os.path.join(os.path.dirname(__file__), 'chapter_health_check.py'),
             '--project', project_path,
             '--chapter', str(chapter_num)],
            capture_output=True,
            encoding='utf-8',
            errors='ignore',
            timeout=60
        )
        output = result.stdout + result.stderr

        # 解析 AI 率：查找 "预估 AI 率: XX.X%"
        match = re.search(r'预估 AI 率:\s*(\d+\.?\d*)%', output)
        if match:
            return float(match.group(1)), []

        # 解析 WARNING 信息
        warnings = []
        if 'A类结构性模式' in output:
            warn_match = re.search(r'A类结构性模式:\s*(\d+)\s*次\s*>', output)
            if warn_match:
                warnings.append(('A类', int(warn_match.group(1))))
        if 'B类AI套话' in output:
            warn_match = re.search(r'B类AI套话:\s*(\d+)\s*次\s*>', output)
            if warn_match:
                warnings.append(('B类', int(warn_match.group(1))))

        return None, warnings

    except Exception as e:
        print('调用 health_check 失败: {}'.format(e))
        return None, []


def find_chapter_file(project_path, chapter_num):
    """查找章节文件"""
    chapter_dir = os.path.join(project_path, '正文卷')
    if not os.path.exists(chapter_dir):
        return None
    for f in os.listdir(chapter_dir):
        if f.startswith('第{}章'.format(chapter_num)):
            return os.path.join(chapter_dir, f)
    return None


def main():
    parser = argparse.ArgumentParser(description='Humanizer 降重脚本 v2')
    parser.add_argument('--project', required=True, help='项目根目录路径')
    parser.add_argument('--chapter', type=int, required=True, help='章节号')
    parser.add_argument('--dry-run', action='store_true', help='只显示不修改')
    args = parser.parse_args()

    # 1. 查找章节文件
    chapter_file = find_chapter_file(args.project, args.chapter)
    if not chapter_file:
        print('章节文件不存在: 第{}章'.format(args.chapter))
        sys.exit(1)

    print('检测章节: {}'.format(os.path.basename(chapter_file)))

    # 2. 调用 chapter_health_check.py 获取准确 AI 率
    ai_rate, warnings = get_ai_rate_from_health_check(args.project, args.chapter)

    if ai_rate is not None:
        print('当前 AI 率: {}%'.format(ai_rate))
    else:
        print('无法获取 AI 率，基于模式检测判断...')
        # 从警告中估算
        if warnings:
            a_count = sum(count for name, count in warnings if name == 'A类')
            b_count = sum(count for name, count in warnings if name == 'B类')
            # 简单估算
            ai_rate = min(55 + a_count * 2 + b_count, 80)
            print('估算 AI 率: {}%'.format(ai_rate))
        else:
            ai_rate = 50  # 默认

    # 3. 读取章节内容
    with open(chapter_file, 'r', encoding='utf-8') as f:
        original_text = f.read()

    # 4. 根据 AI 率决定处理流程
    if ai_rate < 55:
        print('AI 率 < 55%，无需降重')
        sys.exit(0)

    if ai_rate > 70:
        print('AI 率 > 70%，建议人工重写')
        print('自动修复可能效果有限，建议：')
        print('  1. 重新设计对话，减少模板化表达')
        print('  2. 增加具体动作细节，替代抽象心理描写')
        print('  3. 缩短句子长度，避免过长复合句')
        sys.exit(1)

    # 5. AI 率在 55-70% 之间，自动降重
    print('AI 率 55-70%，开始自动降重...')

    text = original_text

    # 5.1 先调用 auto_fix（修复引号+模板词）
    print('\n[1] 调用 auto_fix 修复引号和模板词...')
    try:
        result = subprocess.run(
            [sys.executable,
             os.path.join(os.path.dirname(__file__), 'auto_fix_chapter.py'),
             '--project', args.project,
             '--chapter', str(args.chapter)],
            capture_output=True,
            encoding='utf-8',
            errors='ignore',
            timeout=30
        )
        if result.returncode == 0:
            # 重新读取修复后的内容
            with open(chapter_file, 'r', encoding='utf-8') as f:
                text = f.read()
            print('    auto_fix 完成')
        else:
            print('    auto_fix 返回: {}'.format(result.returncode))
    except Exception as e:
        print('    auto_fix 跳过: {}'.format(e))

    # 5.2 应用 Humanizer A 类修复
    print('\n[2] 应用 Humanizer A 类修复...')
    text, a_changes = apply_humanizer_a(text)
    print('    A类修复: {} 处'.format(a_changes))

    # 5.3 应用 Humanizer B 类修复
    print('\n[3] 应用 Humanizer B 类修复...')
    text, b_changes = apply_humanizer_b(text)
    print('    B类修复: {} 处'.format(b_changes))

    # 6. 统计总修改
    total_changes = a_changes + b_changes
    print('\n总修改: {} 处'.format(total_changes))

    # 7. 如果是 dry-run，不保存
    if args.dry_run:
        print('\n[DRY-RUN] 预览降重结果（前1000字）:')
        print(text[:1000] + '...' if len(text) > 1000 else text)
        sys.exit(0)

    # 8. 保存降重结果
    with open(chapter_file, 'w', encoding='utf-8') as f:
        f.write(text)

    print('\n降重完成！文件已保存。')

    # 9. 再次检测 AI 率
    print('\n[4] 再次检测 AI 率...')
    new_ai_rate, _ = get_ai_rate_from_health_check(args.project, args.chapter)
    if new_ai_rate is not None:
        print('降重后 AI 率: {}%'.format(new_ai_rate))
        improvement = ai_rate - new_ai_rate
        if improvement > 0:
            print('改善: {:.1f}%'.format(improvement))
    else:
        print('无法获取降重后 AI 率')

    # 10. 判断结果
    if new_ai_rate and new_ai_rate > 70:
        print('\n⚠️ 警告: AI 率仍 > 70%，建议人工重写')
        sys.exit(1)
    elif new_ai_rate and new_ai_rate > 55:
        print('\n⚠️ 警告: AI 率仍 > 55%，可以接受但建议继续优化')
        sys.exit(2)
    else:
        print('\n✅ 降重成功，AI 率降至 55% 以下')
        sys.exit(0)


if __name__ == '__main__':
    main()
