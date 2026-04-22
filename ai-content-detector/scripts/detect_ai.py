#!/usr/bin/env python3
"""
AI内容检测辅助脚本
提供文本预处理和结果汇总功能
配合各平台Web界面使用
"""

import argparse
import json
import sys
import re
from typing import Dict, List
from datetime import datetime


class AIDetectionHelper:
    """AI检测辅助工具"""
    
    def __init__(self):
        self.results = []
    
    def preprocess_text(self, text: str) -> str:
        """预处理文本，清理格式标记"""
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'`(.+?)`', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        return text
    
    def split_text(self, text: str, max_length: int = 2000) -> List[str]:
        """分割长文本"""
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
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def add_result(self, platform: str, ai_probability: float, notes: str = ""):
        """添加检测结果"""
        self.results.append({
            'platform': platform,
            'ai_probability': ai_probability,
            'human_probability': round(100 - ai_probability, 2),
            'notes': notes,
            'timestamp': datetime.now().isoformat()
        })
    
    def generate_report(self, output_format: str = 'markdown') -> str:
        """生成检测报告"""
        if not self.results:
            return "暂无检测结果"
        
        ai_probs = [r['ai_probability'] for r in self.results]
        avg_ai_prob = sum(ai_probs) / len(ai_probs)
        
        if output_format == 'json':
            return json.dumps({
                'results': self.results,
                'summary': {
                    'average_ai_probability': round(avg_ai_prob, 2),
                    'platforms_tested': len(self.results)
                }
            }, ensure_ascii=False, indent=2)
        
        report = []
        report.append("\n" + "━" * 50)
        report.append("AI内容检测报告")
        report.append("━" * 50)
        report.append("")
        report.append("| 平台 | AI概率 | 人类概率 | 备注 |")
        report.append("|------|--------|----------|------|")
        
        for r in self.results:
            report.append(f"| {r['platform']} | {r['ai_probability']}% | {r['human_probability']}% | {r['notes']} |")
        
        report.append("")
        report.append("━" * 50)
        report.append(f"平均AI率: {round(avg_ai_prob, 2)}%")
        report.append(f"检测平台数: {len(self.results)}")
        
        if avg_ai_prob < 20:
            level = "极低"
            suggestion = "文本具有高度人类写作特征"
        elif avg_ai_prob < 40:
            level = "低"
            suggestion = "文本具有较多人类写作特征"
        elif avg_ai_prob < 60:
            level = "中等"
            suggestion = "文本存在混合特征，建议进一步优化"
        elif avg_ai_prob < 80:
            level = "高"
            suggestion = "文本具有较多AI特征，建议降重优化"
        else:
            level = "极高"
            suggestion = "文本具有高度AI特征，强烈建议降重"
        
        report.append(f"综合判定: {level}")
        report.append(f"建议: {suggestion}")
        report.append("━" * 50)
        
        return "\n".join(report)
    
    def save_results(self, filepath: str):
        """保存检测结果"""
        data = {
            'results': self.results,
            'exported_at': datetime.now().isoformat()
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"结果已保存到: {filepath}")


def print_platform_guide():
    """打印平台使用指南"""
    guide = """
╔══════════════════════════════════════════════════════════════╗
║              AI检测平台使用指南                               ║
╠══════════════════════════════════════════════════════════════╣
║  1. ZeroGPT                                                  ║
║     网址: https://www.zerogpt.com/                           ║
║     特点: 免费无限制，支持中文                                ║
║     使用: 复制文本粘贴到网页即可检测                          ║
╠══════════════════════════════════════════════════════════════╣
║  2. Writer.com AI Detector                                   ║
║     网址: https://writer.com/ai-content-detector/            ║
║     特点: 简洁易用，结果直观                                  ║
║     使用: 复制文本粘贴到网页即可检测                          ║
╠══════════════════════════════════════════════════════════════╣
║  3. Sapling AI Detector                                      ║
║     网址: https://sapling.ai/ai-content-detector             ║
║     特点: MIT出品，准确度高                                   ║
║     使用: 复制文本粘贴到网页即可检测                          ║
╠══════════════════════════════════════════════════════════════╣
║  4. Content at Scale                                         ║
║     网址: https://contentatscale.ai/ai-content-detector/     ║
║     特点: 详细分析，支持长文本                                ║
║     使用: 复制文本粘贴到网页即可检测                          ║
╠══════════════════════════════════════════════════════════════╣
║  5. GPTZero                                                  ║
║     网址: https://gptzero.me/                                ║
║     特点: 专业检测，学术界认可                                ║
║     使用: 免费注册后使用，每月有限额                          ║
╠══════════════════════════════════════════════════════════════╣
║  6. 朱雀AI（国内）                                           ║
║     网址: 腾讯云平台                                          ║
║     特点: 中文优化，国内访问快                                ║
║     使用: 需要腾讯云账户                                      ║
╚══════════════════════════════════════════════════════════════╝

使用流程:
1. 使用本脚本预处理文本: python detect_ai.py --file 文件路径 --preprocess
2. 复制输出的文本
3. 访问上述平台网站
4. 粘贴文本进行检测
5. 记录各平台结果
6. 使用本脚本汇总: python detect_ai.py --record
"""
    print(guide)


def interactive_record():
    """交互式记录检测结果"""
    helper = AIDetectionHelper()
    
    print("\n" + "=" * 50)
    print("AI检测结果记录工具")
    print("=" * 50)
    print("\n请依次输入各平台的检测结果（输入q退出）:\n")
    
    platforms = ['ZeroGPT', 'Writer', 'Sapling', 'ContentScale', 'GPTZero', '朱雀AI']
    
    for platform in platforms:
        while True:
            user_input = input(f"{platform} AI率 (%): ").strip()
            
            if user_input.lower() == 'q':
                break
            
            try:
                ai_prob = float(user_input)
                if 0 <= ai_prob <= 100:
                    notes = input(f"  备注（可选）: ").strip()
                    helper.add_result(platform, ai_prob, notes)
                    break
                else:
                    print("  请输入0-100之间的数字")
            except ValueError:
                print("  请输入有效的数字")
    
    if helper.results:
        print("\n" + helper.generate_report())
        
        save = input("\n是否保存结果？(y/n): ").strip().lower()
        if save == 'y':
            filepath = input("保存路径（默认: ai_detection_result.json）: ").strip()
            if not filepath:
                filepath = "ai_detection_result.json"
            helper.save_results(filepath)


def main():
    parser = argparse.ArgumentParser(description='AI内容检测辅助工具')
    parser.add_argument('--file', type=str, help='指定检测文件路径')
    parser.add_argument('--text', type=str, help='直接输入检测文本')
    parser.add_argument('--preprocess', action='store_true', help='预处理文本')
    parser.add_argument('--record', action='store_true', help='交互式记录检测结果')
    parser.add_argument('--guide', action='store_true', help='显示平台使用指南')
    parser.add_argument('--output', type=str, default='markdown', help='输出格式')
    parser.add_argument('--max-length', type=int, default=2000, help='文本分割最大长度')
    
    args = parser.parse_args()
    
    if args.guide:
        print_platform_guide()
        return
    
    if args.record:
        interactive_record()
        return
    
    if args.file or args.text:
        helper = AIDetectionHelper()
        
        if args.file:
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    text = f.read()
            except Exception as e:
                print(f"读取文件失败: {e}")
                sys.exit(1)
        else:
            text = args.text
        
        if args.preprocess:
            text = helper.preprocess_text(text)
            
            print("\n" + "=" * 50)
            print("预处理后的文本")
            print("=" * 50)
            print(f"\n文本长度: {len(text)} 字符\n")
            
            chunks = helper.split_text(text, args.max_length)
            
            if len(chunks) > 1:
                print(f"文本已分割为 {len(chunks)} 部分:\n")
                for i, chunk in enumerate(chunks, 1):
                    print(f"--- 第 {i} 部分 ({len(chunk)} 字符) ---")
                    print(chunk[:500] + "..." if len(chunk) > 500 else chunk)
                    print()
            else:
                print(text)
            
            print("\n" + "=" * 50)
            print("请复制上述文本到各检测平台进行检测")
            print("检测完成后运行: python detect_ai.py --record")
            print("=" * 50)
        else:
            print(f"\n文本长度: {len(text)} 字符")
            print("使用 --preprocess 参数进行文本预处理")
    
    else:
        print_platform_guide()


if __name__ == '__main__':
    main()
