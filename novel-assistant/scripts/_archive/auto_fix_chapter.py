#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动修复脚本 v2 - 引号 + AI 模板词 + 口语化注入
设计目标：给弱模型（Qwen/Doubao/MiniMax）做后处理兜底。

修复能力：
  1. 对话引号自动补齐（多种模式识别）
  2. AI 模板词随机替换（每词多样化）
  3. 口语化词注入（可选，--inject-colloquial）

退出码：
  0 = 修复成功，达到交付标准
  1 = 修复后仍有 CRITICAL 问题，需要人工重写

用法：
  python auto_fix_chapter.py --project <项目路径> --chapter <章节号>              # 修复并保存
  python auto_fix_chapter.py --project <项目路径> --chapter <章节号> --dry-run    # 预览
  python auto_fix_chapter.py --project <项目路径> --chapter <章节号> --strict     # 修复后还不达标就退出 1
"""

import re
import os
import sys
import io
import argparse
import random
import importlib.util


def _configure_stdio():
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')


def _load_publish_audit():
    try:
        import publish_readiness_audit as mod
        return mod
    except Exception:
        path = os.path.join(os.path.dirname(__file__), 'publish_readiness_audit.py')
        if not os.path.exists(path):
            return None
        spec = importlib.util.spec_from_file_location('publish_readiness_audit', path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod


PUBLISH_AUDIT = _load_publish_audit()


# ============ AI 模板词替换表 ============
TEMPLATE_REPLACEMENTS = {
    '笑了笑': ['没说话', '嘴角动了动', '深吸了口气', '摸了摸鼻子', '把目光移开', '嗯了一声没接话'],
    '点了点头': ['嗯了一声', '收回目光', '把话咽回去', '眉头微皱', '没接话', '看了对方一眼'],
    '脸红了红': ['低下了头', '咬住了下唇', '耳根子有点热', '转过身去', '假装没听见'],
    '心里头一暖': ['鼻子有点酸', '嗓子眼堵了什么东西', '低头没说话', '吸了吸鼻子'],
    '心里头那个高兴': ['嘴角压不住', '差点笑出声', '手都有点抖', '心里头像吃了蜜'],
    '心里头有些异样': ['心里动了一下', '心里有些不对劲', '没想到会这样'],
    '眼睛一亮': ['盯着看了好几遍', '手里的动作停了', '眉头挑了一下', '不自觉地凑近了'],
    '眼睛都直了': ['愣在原地', '嘴张了张没说出话', '手一抖差点掉了', '整个人僵住了'],
    '激动得心跳加速': ['手心全是汗', '深吸了两口气', '握了握拳头', '攥紧了手里的东西'],
    '没搭理': ['装没听见', '头也没抬', '继续干自己的事'],
    '消息传得比风还快': ['很快村里人都知道了', '这事没过半天就传遍了', '没等晌午，消息就传到了村东头'],
}

# 常见人名（用于识别对话引导）
CHARACTERS = ['陈大山', '林秀梅', '赵老三', '赵老四', '赵四婆',
              '王大娘', '陈老实', '刘瘸子', '张德贵', '王大壮',
              '赵有德', '大山', '秀梅']

# 对话引导动词
SAY_VERBS = ['说', '道', '问', '答', '喊', '叫', '笑', '嘀咕', '嘟囔',
             '吼', '喝', '嘿', '哼', '叹', '低声说', '压低声音',
             '一边说', '接着说', '继续说', '开口', '吆喝']


def clean_and_preserve(raw):
    """分离章节标题和正文，避免破坏"""
    m = re.match(r'^(【第\d+章[^】]*】\n*)', raw)
    if m:
        return m.group(1), raw[len(m.group(1)):]
    return '', raw


def convert_guillemets_to_curly(text):
    """把中文书名号「」转换成标准弯引号「」是历史遗留格式，
    脚本需要统一转换为健康检查认可的「」curly quotes。
    """
    converted = 0
    text = text.replace('\u300c', '\u201c')
    text = text.replace('\u300d', '\u201d')
    converted += text.count('\u201c')
    return text, converted


def convert_straight_quotes(text):
    """把 ASCII 直引号 " 按出现顺序交替转换成中文弯引号 \u201c \u201d

    规则：第 1、3、5... 个直引号 → 左引号 \u201c
         第 2、4、6... 个直引号 → 右引号 \u201d
    理由：弱模型（DeepSeek/MiniMax/Qwen）常输出直引号而非弯引号，
         脚本必须自动转换，否则 health_check 会误判为"引号 0 对"导致死循环。
    """
    parts = text.split('"')
    if len(parts) == 1:
        return text, 0
    result = parts[0]
    converted = 0
    for i, part in enumerate(parts[1:]):
        if i % 2 == 0:
            result += '\u201c' + part
        else:
            result += '\u201d' + part
        converted += 1
    return result, converted


def fix_quotes(text):
    """为对话添加中文引号 \u201c \u201d

    识别模式：
      1. 短句独立成行且以 ！？结尾 -> 整行加引号
      2. 对话, XX说/道 -> 对话前后加引号
      3. XX说, 对话 -> 对话前后加引号
      4. 短独立行未加引号但在对话密集区 -> 加引号
    """
    lines = text.split('\n')
    result = []
    changes = 0

    char_alt = '|'.join(CHARACTERS)
    verb_alt = '|'.join(SAY_VERBS)

    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append(line)
            continue

        # 已带引号的行跳过
        if '\u201c' in stripped or '\u201d' in stripped or '"' in stripped:
            result.append(line)
            continue

        new_line = line

        # 模式 A: XX + say_verb + , + 对话内容 [。！？]?
        # 例: 陈大山说，我回来了。
        pattern_a = r'^((?:' + char_alt + r'|他|她)(?:' + verb_alt + r'|[一-\u9fff]{1,6}(?:' + verb_alt + r'))[，:：])([^。！？\n]{2,80}[。！？]?)\s*$'
        m = re.match(pattern_a, stripped)
        if m:
            prefix, dialog = m.group(1), m.group(2).rstrip('。')
            fixed = prefix + '\u201c' + dialog + '\u201d'
            new_line = line.replace(stripped, fixed)
            result.append(new_line)
            changes += 1
            continue

        # 模式 B: 对话内容，+ XX + say_verb ...
        # 例: 没事，陈大山笑了笑，就是不想在城里待了。
        pattern_b = r'^([^，。！？\n]{2,30})，((?:' + char_alt + r'|他|她)[^，。！？\n]{0,20}(?:' + verb_alt + r')[^，。！？\n]*)([，。].*)?$'
        m = re.match(pattern_b, stripped)
        if m:
            dialog, tag, rest = m.group(1), m.group(2), m.group(3) or ''
            fixed = '\u201c' + dialog + '。\u201d' + tag + rest
            new_line = line.replace(stripped, fixed)
            result.append(new_line)
            changes += 1
            continue

        # 模式 C: 短独立行以 ！或 ？ 或 疑问/感叹词结尾，且不含叙述特征
        if len(stripped) <= 30 and re.search(r'[！？]$', stripped):
            has_narration = any(k in stripped for k in ['走', '看', '拿', '放', '站', '坐', '回头', '转身'])
            has_character = any(c in stripped for c in CHARACTERS)
            if not has_narration and not has_character:
                fixed = '\u201c' + stripped + '\u201d'
                new_line = line.replace(stripped, fixed)
                result.append(new_line)
                changes += 1
                continue

        # 模式 D: 称呼开头的短对话（CH11/CH13/CH20 犯过的错）
        # 例: "大山，你这么早起来干啥？" / "秀梅，你怎么来了？" / "娘，我去后山转转"
        # 判定: 行首是"人名/昵称+逗号"，且整行 <= 40 字，以 ?/!/. 结尾，不含叙述动词
        pattern_d = r'^(' + char_alt + r'|爹|娘|婶|叔|大爷|大娘|哥|嫂|周老|吴经理|张掌柜)(啊|呀|嘛|呗|哩|咧|)，[^，\n]{2,40}[。！？]?$'
        if len(stripped) <= 45 and re.match(pattern_d, stripped):
            narration_verbs = ['走进', '走出', '走到', '抬头', '低头', '回头', '转身', '拿起',
                               '放下', '站起', '坐下', '推开', '拍了', '拉住', '望着', '看着',
                               '一边', '接过', '递给', '拿着']
            has_action = any(v in stripped for v in narration_verbs)
            if not has_action:
                fixed = '\u201c' + stripped + '\u201d'
                new_line = line.replace(stripped, fixed)
                result.append(new_line)
                changes += 1
                continue

        # 模式 E: 以 "你/我/俺/咱" 起头的短对话疑问/感叹句（无人名前缀）
        # 例: "你咋来了" / "俺没事儿" / "我听说你回来了"
        if (len(stripped) <= 30 and re.match(r'^[你我俺咱][^，\n]', stripped) and
                re.search(r'[。！？]$', stripped)):
            narration_verbs = ['走进', '走出', '走到', '抬头', '低头', '回头', '转身',
                               '拿起', '放下', '站起', '坐下', '推开', '望着', '看着']
            has_action = any(v in stripped for v in narration_verbs)
            if not has_action:
                fixed = '\u201c' + stripped + '\u201d'
                new_line = line.replace(stripped, fixed)
                result.append(new_line)
                changes += 1
                continue

        result.append(new_line)

    return '\n'.join(result), changes


def fix_templates(text):
    """替换 AI 模板词，相邻替换选不同的词"""
    changes = 0
    for old, replacements in TEMPLATE_REPLACEMENTS.items():
        count = text.count(old)
        if count == 0:
            continue
        shuffled = list(replacements)
        random.shuffle(shuffled)
        for i in range(count):
            text = text.replace(old, shuffled[i % len(shuffled)], 1)
            changes += 1
    return text, changes


def fix_structural_noise(text):
    """删除明显的账本句/总结句整行噪音，保留对话与场景动作。

    只做低风险删除：
    - 命中 publish_readiness_audit 的账本式说明行
    - 命中总结/计划句整行
    - 已带引号的对话一律不删
    """
    if PUBLISH_AUDIT is None:
        return text, 0

    lines = text.split('\n')
    bookkeeping_hits = PUBLISH_AUDIT.collect_bookkeeping_hits(lines)
    summary_hits = PUBLISH_AUDIT.collect_marker_hits(lines, PUBLISH_AUDIT.SUMMARY_MARKERS, min_markers=1)
    delete_line_nos = {hit.line_no for hit in bookkeeping_hits}
    delete_line_nos.update(hit.line_no for hit in summary_hits)

    result = []
    changes = 0
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if idx in delete_line_nos:
            # 对话、过短行、明显动作行不删
            if ('\u201c' in stripped or '\u201d' in stripped or '"' in stripped
                    or len(stripped) < 20
                    or any(word in stripped for word in ['走', '看', '伸手', '转身', '抬头', '低头', '扶住', '按住'])):
                result.append(line)
                continue
            changes += 1
            continue
        result.append(line)
    return '\n'.join(result), changes


def get_publish_blockers(text):
    """返回当前文本仍存在的发布阻断项。"""
    if PUBLISH_AUDIT is None:
        return []

    lines = text.split('\n')
    scenes = PUBLISH_AUDIT.collect_scene_markers(text)
    naked_dialogue_hits = PUBLISH_AUDIT.collect_naked_dialogue(lines)
    bookkeeping_hits = PUBLISH_AUDIT.collect_bookkeeping_hits(lines)
    summary_hits = PUBLISH_AUDIT.collect_marker_hits(lines, PUBLISH_AUDIT.SUMMARY_MARKERS, min_markers=1)
    telling_hits = PUBLISH_AUDIT.collect_telling_hits(lines)
    return PUBLISH_AUDIT.score_blockers(
        scene_count=len(scenes),
        naked_dialogue=len(naked_dialogue_hits),
        bookkeeping=len(bookkeeping_hits),
        summary=len(summary_hits),
        telling=len(telling_hits),
    )


def count_chinese_quotes(text):
    return text.count('\u201c')


def count_templates(text):
    return sum(text.count(w) for w in TEMPLATE_REPLACEMENTS)


def find_chapter_file(project_path, chapter_num):
    chapter_dir = os.path.join(project_path, '正文卷')
    if not os.path.exists(chapter_dir):
        return None
    for f in os.listdir(chapter_dir):
        if f.startswith('第{}章'.format(chapter_num)):
            return os.path.join(chapter_dir, f)
    return None


def main():
    _configure_stdio()
    parser = argparse.ArgumentParser(description='章节自动修复 v2')
    parser.add_argument('--project', required=True, help='项目根目录路径')
    parser.add_argument('--chapter', type=int, required=True, help='章节号')
    parser.add_argument('--dry-run', action='store_true', help='只显示不修改')
    parser.add_argument('--strict', action='store_true', help='修复后仍不达标则退出码 1')
    args = parser.parse_args()

    chapter_file = find_chapter_file(args.project, args.chapter)
    if not chapter_file:
        print('[ERROR] 找不到第{}章文件'.format(args.chapter))
        sys.exit(1)

    with open(chapter_file, 'r', encoding='utf-8') as f:
        raw = f.read()

    title, body = clean_and_preserve(raw)

    before_quotes = count_chinese_quotes(body)
    before_templates = count_templates(body)
    before_blockers = get_publish_blockers(body)

    print('=' * 55)
    print('[第{}章] 自动修复 v2'.format(args.chapter))
    print('=' * 55)
    print()
    print('[修复前]')
    print('  中文引号对: {}'.format(before_quotes))
    before_lines = len([x for x in body.split('\n') if x.strip()])
    print('  AI 模板词总数: {}'.format(before_templates))
    print('  有效行数: {}'.format(before_lines))
    print('  发布阻断项: {}'.format(len(before_blockers)))

    if before_templates > 0:
        print('  模板词详情:')
        for phrase in TEMPLATE_REPLACEMENTS:
            c = body.count(phrase)
            if c > 0:
                print('    - "{}": {}次'.format(phrase, c))

    # 执行修复
    body, straight_converted = convert_straight_quotes(body)  # 先把 " 转成 \u201c \u201d
    body, guillemets_converted = convert_guillemets_to_curly(body)  # 再把 「」 转成 \u201c \u201d
    body, quote_changes = fix_quotes(body)
    body, template_changes = fix_templates(body)
    body, structural_changes = fix_structural_noise(body)

    after_quotes = count_chinese_quotes(body)
    after_templates = count_templates(body)
    after_lines = len([x for x in body.split('\n') if x.strip()])
    after_blockers = get_publish_blockers(body)

    print()
    print('[修复后]')
    print('  直引号转弯引号: {} 处'.format(straight_converted))
    print('  「」换标准引号: {} 处'.format(guillemets_converted))
    print('  中文引号对: {} (新增 {})'.format(after_quotes, quote_changes))
    print('  AI 模板词总数: {} (替换 {})'.format(after_templates, template_changes))
    print('  结构噪音行: {} (删除 {})'.format(after_lines, structural_changes))
    print('  发布阻断项: {} (减少 {})'.format(after_blockers.__len__(), len(before_blockers) - len(after_blockers)))
    if after_blockers:
        for blocker in after_blockers[:5]:
            print('    - {}'.format(blocker))
    print()

    # 判断 strict 模式下是否达标
    fail = False
    if args.strict:
        if after_quotes < 6:
            print('[STRICT FAIL] 修复后引号数仍 < 6，需人工重写对话')
            fail = True
        if after_templates > 6:
            print('[STRICT FAIL] 修复后模板词仍 > 6')
            fail = True
        if after_blockers:
            print('[STRICT FAIL] 修复后仍有发布阻断项:')
            for blocker in after_blockers[:5]:
                print('  - {}'.format(blocker))
            fail = True

    new_content = title + body

    if args.dry_run:
        print('[DRY-RUN] 未写入文件')
        print()
        print('--- 修复后前 60 行预览 ---')
        for i, line in enumerate(new_content.split('\n')[:60]):
            print('{:3d}: {}'.format(i + 1, line))
    else:
        with open(chapter_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print('[DONE] 已写入: {}'.format(chapter_file))

    if fail:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
