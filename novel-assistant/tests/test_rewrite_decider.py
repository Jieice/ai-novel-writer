#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rewrite_decider 测试"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))


class TestRewriteDecider(unittest.TestCase):
    def test_ch18_is_rewrite_a(self):
        from rewrite_decider import decide, parse_publish_info
        pub_out = '场戏数: 3\n裸对话: 4\n账本式说明: 0\n总结/计划句: 0\n讲述句: 1'
        pub = parse_publish_info(pub_out)
        self.assertEqual(pub['scene_count'], 3)
        decision, _ = decide(pub_rc=1, pub_out=pub_out, health_rc=0, health_out='')
        self.assertIn('A级', decision.value)

    def test_ch13_health_fail_with_empty_output_is_rewrite(self):
        from rewrite_decider import decide
        decision, reason = decide(pub_rc=0, pub_out='', health_rc=1, health_out='')
        self.assertIn('A级', decision.value)

    def test_auto_fix_when_health_rc1_with_output(self):
        from rewrite_decider import decide
        pub_out = """场戏数: 1
裸对话: 0
账本式说明: 0
总结/计划句: 0
讲述句: 0"""
        health_out = """中文引号对: 3
AI模板词总次数: 10
预估 AI 率: 35.2%
口语化: 2.1/百字"""
        decision, reason = decide(pub_rc=0, pub_out=pub_out, health_rc=1, health_out=health_out)
        self.assertIn('auto_fix', decision.value)

    def test_parse_publish_info_scene_count(self):
        from rewrite_decider import parse_publish_info

        output = """场戏数: 3
裸对话: 4
账本式说明: 0
总结/计划句: 0
讲述句: 1"""
        info = parse_publish_info(output)
        self.assertEqual(info['scene_count'], 3)

    def test_parse_health_info_quote_pairs(self):
        from rewrite_decider import parse_health_info

        output = """中文引号对: 15
AI模板词总次数: 3
预估 AI 率: 35.2%
口语化: 2.1/百字
[CRITICAL FAIL] xxxx
[WARNING] xxxx"""
        info = parse_health_info(output)
        self.assertEqual(info['quote_pairs'], 15)
        self.assertEqual(info['template_count'], 3)
        self.assertEqual(info['critical'], 1)
        self.assertEqual(info['warning'], 1)

    def test_decide_pass(self):
        from rewrite_decider import decide
        pub_out = """场戏数: 1
裸对话: 0
账本式说明: 0
总结/计划句: 0
讲述句: 0"""
        health_out = """中文引号对: 15
AI模板词总次数: 3
预估 AI 率: 35.2%
口语化: 2.1/百字"""
        decision, _ = decide(0, pub_out, 0, health_out)
        self.assertIn('PASS', decision.value)


if __name__ == '__main__':
    unittest.main(verbosity=2)
