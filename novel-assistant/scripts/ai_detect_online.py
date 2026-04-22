#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI率检测辅助脚本

由于在线AIGC检测API（朱雀/快搜）接口不稳定或需要验证码，
本脚本提供两种使用模式：

模式1 - 文本提取（默认）：
  提取章节纯文本、按段落分段，输出到控制台或文件，
  方便手动复制到朱雀(matrix.tencent.com/ai-detect/)或快搜(jiance.kuaisou.com)网页检测。

模式2 - API检测（需配置有效的API Key）：
  调用快搜AIGC API自动检测。目前API可能不可用，优先用模式1。

用法：
  python ai_detect_online.py --project <项目路径> --chapter 1           # 提取第1章文本
  python ai_detect_online.py --project <项目路径> --chapter 1-5         # 提取第1-5章
  python ai_detect_online.py --project <项目路径> --chapter 1 --api     # 用API检测
  python ai_detect_online.py --project <项目路径> --all                  # 提取全部章节
  python ai_detect_online.py --text "待检测文本"                         # 直接处理文本
  python ai_detect_online.py --project <项目路径> --chapter 1 --record 20.5  # 记录检测结果

AI检测推荐平台（手动）：
  - 朱雀AIGC检测：https://matrix.tencent.com/ai-detect/ai_gen （中文最准，免费）
  - 快搜AI检测：https://jiance.kuaisou.com/ （免费，需注册）

检测标准：
  < 20%  ✅ 优秀
  20-40% ⚠️ 可接受
  > 40%  ❌ 需精修
"""

import re
import os
import sys
import io
import json
import argparse
import time
from datetime import datetime

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')

# ============ 配置 ============
MAX_TEXT_LENGTH = 10000  # 检测平台单次最大字符数
API_URL = "https://xueshu.kuaisou.com/v1/aigc-api/ai/doDetect"
RATE_LIMIT_SECONDS = 15
RESULTS_FILE = "ai_detect_results.json"  # 检测结果记录文件


def preprocess_text(text):
    """预处理文本：去除Markdown格式标记"""
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text


def split_text(text, max_length=MAX_TEXT_LENGTH):
    """将长文本按段落分割，每段不超过max_length"""
    if len(text) <= max_length:
        return [text]

    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_length:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            if len(para) > max_length:
                sentences = re.split(r'(?<=[。！？])', para)
                sub_chunk = ""
                for s in sentences:
                    if len(sub_chunk) + len(s) <= max_length:
                        sub_chunk += s
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk.strip())
                        sub_chunk = s
                if sub_chunk:
                    current_chunk = sub_chunk + "\n\n"
                else:
                    current_chunk = ""
            else:
                current_chunk = para + "\n\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def find_chapter_file(project_path, chapter_num):
    """查找章节文件"""
    chapter_dir = os.path.join(project_path, '正文卷')
    if not os.path.exists(chapter_dir):
        return None
    for f in os.listdir(chapter_dir):
        if f.startswith(f'第{chapter_num}章'):
            return os.path.join(chapter_dir, f)
    return None


def extract_chapter_text(project_path, chapter_num):
    """提取章节纯文本"""
    chapter_file = find_chapter_file(project_path, chapter_num)
    if not chapter_file:
        return None, None

    with open(chapter_file, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    clean_text = preprocess_text(raw_text)
    return clean_text, os.path.basename(chapter_file)


def print_extract(text, chapter_name="", chunk_index=None, total_chunks=None):
    """打印提取的文本，方便复制到检测平台"""
    prefix = ""
    if chunk_index is not None and total_chunks and total_chunks > 1:
        prefix = f" (第{chunk_index+1}/{total_chunks}段)"
    
    print(f"\n{'='*50}")
    print(f"📄 {chapter_name}{prefix}")
    print(f"字数: {len(text)}")
    print(f"{'='*50}")
    print()
    print(text)
    print()
    print(f"{'='*50}")
    print("↑ 复制以上文本到检测平台：")
    print("  朱雀: https://matrix.tencent.com/ai-detect/ai_gen")
    print("  快搜: https://jiance.kuaisou.com/")
    print(f"{'='*50}")


def detect_with_api(api_key, text):
    """调用快搜AIGC API检测（可能不可用）"""
    try:
        import requests
    except ImportError:
        print('[ERROR] 需要安装 requests: pip install requests')
        return None

    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except:
        pass

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {"text": text, "api-key": api_key}

    try:
        response = requests.post(API_URL, json=data, headers=headers, timeout=30, verify=False)
        result = response.json()

        if result.get('errcode') == 0:
            return result['data']
        else:
            print(f"  API错误: {result.get('errmsg', result.get('msg', '未知错误'))} (code: {result.get('errcode', result.get('code'))})")
            return None
    except Exception as e:
        print(f"  请求失败: {e}")
        return None


def record_result(project_path, chapter_num, ai_rate, platform="朱雀"):
    """记录检测结果到JSON文件"""
    results_path = os.path.join(project_path, RESULTS_FILE)
    
    # 读取已有结果
    if os.path.exists(results_path):
        with open(results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
    else:
        results = {"chapters": [], "last_updated": ""}
    
    # 更新或添加
    found = False
    for ch in results['chapters']:
        if ch['chapter'] == chapter_num:
            ch['ai_rate'] = ai_rate
            ch['platform'] = platform
            ch['date'] = datetime.now().strftime('%Y-%m-%d')
            found = True
            break
    
    if not found:
        results['chapters'].append({
            'chapter': chapter_num,
            'ai_rate': ai_rate,
            'platform': platform,
            'date': datetime.now().strftime('%Y-%m-%d')
        })
    
    results['chapters'].sort(key=lambda x: x['chapter'])
    results['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 第{chapter_num}章检测结果已记录: AI率 {ai_rate}% ({platform})")
    print(f"   保存位置: {results_path}")


def show_results(project_path):
    """显示已记录的所有检测结果"""
    results_path = os.path.join(project_path, RESULTS_FILE)
    
    if not os.path.exists(results_path):
        print("暂无检测记录")
        return
    
    with open(results_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print(f"\n{'='*60}")
    print("AI率检测结果汇总")
    print(f"{'='*60}")
    print(f"{'章节':<8} {'AI率':<10} {'平台':<8} {'日期':<12} {'状态'}")
    print("-" * 55)
    
    for ch in results['chapters']:
        rate = ch['ai_rate']
        if rate < 20:
            status = "✅ 优秀"
        elif rate < 40:
            status = "⚠️ 可接受"
        else:
            status = "❌ 需精修"
        print(f"第{ch['chapter']}章   {rate}%       {ch['platform']:<8} {ch['date']:<12} {status}")
    
    if results['chapters']:
        avg = sum(ch['ai_rate'] for ch in results['chapters']) / len(results['chapters'])
        print(f"\n平均AI率: {avg:.1f}%")
    
    print(f"\n最后更新: {results.get('last_updated', '未知')}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='AI率检测辅助工具')
    parser.add_argument('--project', type=str, help='项目根目录路径')
    parser.add_argument('--chapter', type=str, help='章节号（单个或范围如 1-30）')
    parser.add_argument('--text', type=str, help='直接处理文本')
    parser.add_argument('--all', action='store_true', help='处理全部章节')
    parser.add_argument('--api', action='store_true', help='使用API检测（默认仅提取文本）')
    parser.add_argument('--record', type=float, help='记录检测结果（AI率百分比，如 20.5）')
    parser.add_argument('--platform', type=str, default='朱雀', help='检测平台名称（默认朱雀）')
    parser.add_argument('--results', action='store_true', help='显示已记录的检测结果')
    args = parser.parse_args()

    # 显示结果
    if args.results and args.project:
        show_results(args.project)
        return

    # 记录结果
    if args.record is not None:
        if not args.project or not args.chapter:
            print('[ERROR] 记录结果需要 --project 和 --chapter 参数')
            sys.exit(1)
        if '-' in args.chapter:
            print('[ERROR] 记录结果只支持单个章节')
            sys.exit(1)
        record_result(args.project, int(args.chapter), args.record, args.platform)
        return

    # 确定要处理的章节
    chapters = []
    if args.text:
        text = preprocess_text(args.text)
        chunks = split_text(text)
        for i, chunk in enumerate(chunks):
            print_extract(chunk, "直接输入文本", i, len(chunks))
        return

    if args.project:
        if args.chapter:
            if '-' in args.chapter:
                start, end = map(int, args.chapter.split('-'))
                chapters = list(range(start, end + 1))
            else:
                chapters = [int(args.chapter)]
        elif args.all:
            chapter_dir = os.path.join(args.project, '正文卷')
            for f in sorted(os.listdir(chapter_dir)):
                m = re.match(r'第(\d+)章', f)
                if m:
                    chapters.append(int(m.group(1)))
        else:
            print('请指定 --chapter 或 --all')
            sys.exit(0)
    else:
        print('用法:')
        print('  # 提取文本（手动去网页检测）')
        print('  python ai_detect_online.py --project <项目路径> --chapter 1')
        print('  python ai_detect_online.py --project <项目路径> --chapter 1-5')
        print('  python ai_detect_online.py --project <项目路径> --all')
        print()
        print('  # 记录检测结果')
        print('  python ai_detect_online.py --project <项目路径> --chapter 1 --record 20.5')
        print()
        print('  # 查看检测记录')
        print('  python ai_detect_online.py --project <项目路径> --results')
        print()
        print('  # 直接处理文本')
        print('  python ai_detect_online.py --text "待检测文本"')
        print()
        print('检测平台：')
        print('  朱雀: https://matrix.tencent.com/ai-detect/ai_gen')
        print('  快搜: https://jiance.kuaisou.com/')
        sys.exit(0)

    # API模式
    use_api = args.api
    api_key = None
    if use_api:
        api_key = os.environ.get('AIGC_API_KEY', '')
        if not api_key:
            print('[ERROR] API模式需要设置 AIGC_API_KEY 环境变量')
            print('  注意：快搜AIGC API目前可能不可用，建议使用文本提取模式')
            sys.exit(1)

    # 处理每个章节
    for ch_num in chapters:
        text, chapter_name = extract_chapter_text(args.project, ch_num)
        if text is None:
            print(f"\n第{ch_num}章文件不存在，跳过")
            continue

        chunks = split_text(text)

        if use_api:
            # API检测模式
            print(f"\n章节: {chapter_name}")
            print(f"文本长度: {len(text)} 字，分为 {len(chunks)} 段检测")

            total_ai_rate = 0
            total_weight = 0
            all_para_results = []

            for i, chunk in enumerate(chunks):
                if i > 0:
                    time.sleep(RATE_LIMIT_SECONDS)
                print(f"  检测第 {i+1}/{len(chunks)} 段...", end=" ", flush=True)
                result = detect_with_api(api_key, chunk)
                if result and 'details' in result:
                    ai_rate = result['details'].get('ai_rate', 0)
                    weight = len(chunk)
                    total_ai_rate += ai_rate * weight
                    total_weight += weight
                    para_results = result['details'].get('paragraph_result', [])
                    all_para_results.extend(para_results)
                    print(f"AI率: {ai_rate}%")
                else:
                    print("失败（API可能不可用，请用文本提取模式）")

            if total_weight > 0:
                weighted_rate = round(total_ai_rate / total_weight, 1)
                print(f"\n综合AI率: {weighted_rate}%")
                if weighted_rate < 20:
                    print("✅ 优秀")
                elif weighted_rate < 40:
                    print("⚠️ 可接受")
                else:
                    print("❌ 需精修")
        else:
            # 文本提取模式（默认）
            for i, chunk in enumerate(chunks):
                print_extract(chunk, chapter_name, i, len(chunks))


if __name__ == '__main__':
    main()
