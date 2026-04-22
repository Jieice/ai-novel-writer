#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节健康检查脚本 v2
设计目标：给弱模型（Qwen/Doubao/MiniMax）当强制守门员。
检查：对话引号、AI 模板词、冲突密度、口语化、字数、段落格式。

退出码：
  0 = 全部通过，可交付
  1 = CRITICAL FAIL，必须重写/修复（引号为0、模板词超限、口语化过低等致命问题）
  2 = WARNING，建议修复但允许交付

用法：
  python chapter_health_check.py --project <项目路径> --chapter <章节号>
  python chapter_health_check.py --project <项目路径> --chapter <章节号> --strict
"""

import re
import os
import sys
import io
import argparse
import csv
from datetime import datetime

try:
    import publish_readiness_audit as publish_audit
except Exception:
    publish_audit = None

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')


# ============ 硬阈值（FAIL = 必须重写） ============
# 设计原则：对弱模型（DS/MiniMax/Qwen）友好，避免死锁循环
THRESHOLD_CRITICAL = {
    'chinese_quotes_min': 6,        # 整章引号对 < 6 = FAIL（对话行≥6时才严格要求）
    'template_word_max': 8,         # AI 模板词总次数 > 8 = FAIL（从 6 放宽到 8）
    'template_single_max': 3,       # 单个模板词 > 3 次 = FAIL（从 2 放宽到 3）
    'ai_rate_max': 70.0,            # 预估 AI 率 > 70% = FAIL（从 60% 放宽到 70%）
}

# 警告阈值（不阻断交付）
THRESHOLD_WARNING = {
    'colloquial_min': 0.8,          # 口语化 >= 0.8/百字即可，读着顺
    'ai_rate': 55.0,
    'colloquial': 2.0,
    'conflict_gap': 3,
    'word_count_deviation': 20.0,
}


# ============ AI 模板词黑名单 ============
TEMPLATE_WORDS = [
    # 表情/动作类
    '笑了笑', '点了点头', '脸红了红',
    '眼睛一亮', '眼睛都直了', '嘴角微微上扬',
    # 心理类（AI 最爱用的套路化心理描写）
    '心里头一暖', '心里头那个高兴', '心里头有些异样',
    '心里头七上八下', '心里头咯噔', '心里咯噔',
    '心里头一紧', '心里头一沉', '心里头一软',
    '激动得心跳加速', '心跳加快', '脑子嗡的一声',
    # 身体反应类（套路化）
    '攥紧了拳头', '攥紧了车把', '深吸了口气', '深吸一口气',
    '眉头皱了皱', '眉头一挑', '冷哼了一声', '冷哼一声',
    # 叙述套路类
    '没搭理', '心里盘算', '心里头有了数',
    '消息传得比风还快',
]

# 口语化词刷分检测阈值
# 单个词占比：任一单词占所有口语词 > 35% 即判定为单词刷分（从40%收紧）
# 对话行尾滥用：对话行以"嘛/呗/呢/咯/咧/哩"结尾占比 > 40% 即判定为行尾滥用
ANTI_SPAM_THRESHOLD = 0.35
DIALOGUE_PARTICLE_ABUSE_THRESHOLD = 0.40
# 对话行尾语气词（每句挂语气词的识别标记）
DIALOGUE_END_PARTICLES = ['嘛', '呗', '呢', '咯', '咧', '哩', '哟', '喽']


# ============ 反派口头威胁检测词 ============
VILLAIN_VERBAL_ONLY = [
    '你给我等着', '你等着', '别怪我不客气',
    '你小子给我小心点', '你给我小心',
    '你最好识相点', '你试试看',
]

# 反派实质行动关键词（存在至少1个才算反派动手）
VILLAIN_ACTION = [
    '毁了', '砸了', '踹翻', '抢走', '拦路',
    '买通', '举报', '散播谣言', '传出去',
    '偷偷', '设局', '陷害', '动手',
    '堵', '烧', '扣押', '断了', '砍了',
]

# ============ 爽点关键词（打脸/翻身/赚钱/治病） ============
# 注意：删除了"等着"/"老子" —— 这些是中二独白词,不是爽点词
SHUANGDIAN_KEYWORDS = [
    '打脸', '当场', '一剂见效', '妙手回春', '扬眉吐气',
    '赚钱', '发财', '进账', '白花花的银子', '红彤彤的票子',
    '翻身', '出口气', '狠狠', '痛快', '解气',
    '治好', '痊愈', '药到病除',
    '拒绝了', '不答应', '给脸不要脸', '不识抬举',
    '仗义', '讲信誉', '讲义气', '有骨气', '硬气',
    '没认输', '走着瞧',
]

# ============ 中二独白黑名单 ============
# 读者最讨厌：主角每章咬牙切齿喊一遍"等着吧/十倍奉还"
# 这种词出现超过 1 次 = WARNING,超过 2 次 = CRITICAL
CRINGE_MONOLOGUE = [
    '等着吧', '十倍奉还', '付出代价', '不会认输',
    '迟早让你', '迟早要', '俺要让你', '他要让你',
    '走着瞧', '给我等着', '敢惹俺', '别怪俺',
    '总有一天', '总会让',
]

# ============ 主角挫折关键词 ============
# 脚本识别这些词，写作时至少使用一个
SETBACK_KEYWORDS = [
    '失败', '挫折', '赔了', '亏了', '毁了', '砸了',
    '受伤', '发烧', '头晕', '手抖', '体力不支',
    '被嘲笑', '被质疑', '被拒绝', '被威胁', '被打压',
    '倒霉', '不顺', '意外', '损失',
    '吃亏', '闷亏', '栽了', '碰壁', '受阻',
    '白忙活', '白费劲', '竹篮打水', '功亏一篑',
]

# ============ 金手指代价关键词 ============
# 脚本识别这些词，写作时至少使用一个
GOLDEN_FINGER_COST = [
    '疲惫', '累得', '体力消耗', '虚脱', '冒冷汗',
    '脸色发白', '脸色白了', '站不稳', '手发抖', '手抖',
    '发烧', '头晕目眩', '头晕', '眼前发黑', '发黑',
    '累倒', '歇了好一会儿', '歇了一阵', '喘着粗气', '浑身没劲',
    '腿软', '绊了一跤', '栽了一跤', '缓过劲儿', '打哆嗦', '哆嗦',
    '后脊梁全是冷汗', '冷汗',
    '代价', '付出', '掏空', '透支', '累瘫',
    '身子虚', '虚得', '撑不住', '扛不住',
    '眼前发花', '耳朵嗡嗡响', '嗓子眼发干',
]

# ============ 反派压迫感：村级 vs 镇级 ============
# 村级反派特征（弱）：本村人、小打小闹
# 镇级反派特征（强）：镇上/县城关系、买通官方、断财路
VILLIAN_TIED_TO_TOWN = [
    '镇上', '县城', '药行', '掌柜', '老板',
    '举报', '封杀', '断货', '断路', '断了财路',
    '买通', '收买', '后台', '关系',
]

# ============ 反派专名清单（铁律9：链条≤3 层）============
# 单章出现 >3 个反派专名 = WARNING, >4 个 = CRITICAL
# 读者记不住谁是 Boss,是因为反派链条过长。
VILLAIN_NAMES = [
    '赵老三', '张二狗', '孙大嘴',
    '赵老三婆娘', '张寡妇',
    '恒昌药行', '恒昌', '吴德明', '吴经理',
    '李万山', '李副总',
]

# ============ 套路心理描写合并黑名单（铁律10）============
# 单独"心里头咯噔"1-2 次没问题,但合并 >8 次 = AI 堆砌,必须 CRITICAL
AI_PSYCHOLOGY_CLICHE = [
    '心里头咯噔', '心里咯噔', '心里头一紧', '心里一紧',
    '心里头一沉', '心里一沉', '心里头一软', '心里一软',
    '心里头七上八下', '心里七上八下', '心里头咯噔了一下',
    '脑子嗡的一声', '脑袋嗡的一声', '脑子一片空白',
    '眼前发黑', '眼前一黑',
    '攥紧了拳头', '攥紧拳头', '握紧了拳头',
    '指甲掐进掌心', '指甲掐进',
    '深吸了口气', '深吸一口气', '深深吸了口气',
    '眉头皱了皱', '眉头微皱', '眉头一挑', '眉头紧锁',
    '冷哼了一声', '冷哼一声',
    '心跳加快', '心跳加速',
    '鼻子有点酸', '鼻子一酸',
]

# ============ Humanizer 结构性模式检测(新增) ============
# A类: 否定式排比、三段式、-ing结尾、谄媚语气、强行展望结尾
HUMANIZER_A_PATTERNS = {
    '否定式排比': ['不是', '也不是', '更不是', '既不', '也不', '还不能', '也不能'],
    '三段式堆砌': ['首先', '其次', '最后', '第一', '第二', '第三'],
    'ing结尾虚假分析': ['突出', '彰显', '确保', '反映', '体现', '为', '做出贡献', '培养', '促进'],
    '谄媚语气': ['当然', '毫无疑问', '无可否认', '您的观点', '承蒙', '拜谢'],
    '强行展望结尾': ['挑战与机遇并存', '光明的前途', '等待着', '未来一定', '必将'],
}
# B类: 填充短语、AI高频词、过度限定、虚假范围、刻意换词
HUMANIZER_B_PATTERNS = {
    '填充短语': ['总而言之', '值得注意的是', '实际上', '事实上', '从某种意义上说', '可以说', '严格来说'],
    'AI高频词': ['此外', '深入探讨', '至关重要', '不可或缺', '不容忽视'],
    '过度限定': ['可能', '也许', '大概', '应该', '似乎', '看上去', '一般来说', '基本上'],
    '虚假范围': ['从', '到'],
    '刻意换词': [],
}
# C类: 破折号、引号、加粗、表情符号
HUMANIZER_C_PATTERNS = {
    '破折号': ['——'],
    '加粗': ['**'],
    '弯引号': ['「', '」', '『', '』'],
    '表情符号': ['🎯', '🔥', '⭐', '✅', '⚠️', '💡', '✨'],
}


def check_humanizer_patterns(text):
    """Humanizer 结构性模式检测( WARNING 级别)
    A类 > 3次/章 = WARNING; B类 > 5次/章 = WARNING; C类 > 阈值 = WARNING
    """
    results = {'A': {}, 'B': {}, 'C': {}}

    for pattern_name, keywords in HUMANIZER_A_PATTERNS.items():
        count = sum(text.count(k) for k in keywords)
        if count > 0:
            results['A'][pattern_name] = count

    for pattern_name, keywords in HUMANIZER_B_PATTERNS.items():
        count = sum(text.count(k) for k in keywords)
        if count > 0:
            results['B'][pattern_name] = count

    for pattern_name, keywords in HUMANIZER_C_PATTERNS.items():
        count = sum(text.count(k) for k in keywords)
        if count > 0:
            results['C'][pattern_name] = count

    return results


def clean_text(raw):
    """清理标题和结尾"""
    text = re.sub(r'^【第\d+章[^】]*】\n', '', raw)
    text = re.sub(r'（本章完）\s*$', '', text)
    return text


def count_chinese_quotes(text):
    """统计引号对数（兼容中文弯引号 \u201c\u201d 和英文直引号 "）

    弱模型经常输出英文直引号而非弯引号，本脚本视为等效：
      - 直引号 " 按成对计数：76 个 " = 38 对
      - 中文弯引号 \u201c 数量 = 弯引号对数
    返回两者之和。
    """
    curly = text.count('\u201c')
    straight_pairs = text.count('"') // 2
    return curly + straight_pairs


def count_template_words(text):
    """统计 AI 模板词使用情况"""
    results = {}
    for word in TEMPLATE_WORDS:
        count = text.count(word)
        if count > 0:
            results[word] = count
    total = sum(results.values())
    return total, results


def check_villain_action(text):
    """检测反派是否只有口头威胁而无实质行动"""
    verbal_count = sum(text.count(w) for w in VILLAIN_VERBAL_ONLY)
    action_count = sum(text.count(w) for w in VILLAIN_ACTION)
    if verbal_count >= 1 and action_count == 0:
        return False, verbal_count, action_count
    return True, verbal_count, action_count


def get_chapter_phase(chapter_num, text=''):
    """根据章节号判断所处阶段，决定是否需要挫折检查

    规则：
      - 建立期(Ch1-3)：回村/发现金手指 → 豁免
      - 成长期(Ch4-10)：能力测试/小试牛刀 → 常规检查（有小冲突即可）
      - 冲突升级期(Ch11-14)：培育/赵老三报复 → 必须有挫折
      - 反击期(Ch15+)：暗中布局/反击 → 必须有挫折
      - 豁免章节：标题含"成功""风波"且无重大挫折情节的庆祝章
    """
    # 豁免章节（成功庆祝章/纯感情章，不要求挫折）
    exempt_titles = {
        9: '暗生情愫',   # 感情线，无冲突
        13: '天麻成功',   # 成功庆祝章
    }
    if chapter_num in exempt_titles:
        return 'exempt'
    if 1 <= chapter_num <= 3:
        return 'establishing'
    elif 4 <= chapter_num <= 10:
        return 'rising'
    elif 11 <= chapter_num <= 14:
        return 'escalation'
    else:
        return 'climax'


def check_protagonist_setback(text, chapter_num):
    """主角挫折检查（铁律4）- 考虑章节类型"""
    phase = get_chapter_phase(chapter_num, text)
    count = sum(text.count(w) for w in SETBACK_KEYWORDS)

    if phase == 'exempt':
        # 豁免：成功庆祝章/纯感情章，不要求挫折
        return True, count, phase, 'exempt_章节不要求挫折'

    if phase == 'establishing':
        # 建立期：主角刚起步，允许没有重大挫折，但要有"困境感"
        if count >= 1:
            return True, count, phase, '建立期有初步挫折 OK'
        return True, count, phase, '建立期允许无重大挫折'

    if phase == 'rising':
        # 成长期：必须有挫折（被人看不起/行动受阻/小失败）
        if count >= 1:
            return True, count, phase, '成长期有挫折 OK'
        return False, count, phase, '成长期主角必须有挫折'

    # 冲突升级期/反击期：必须有实质性挫折
    if count >= 1:
        return True, count, phase, '有挫折 OK'
    return False, count, phase, '冲突期/反击期主角必须有挫折！'


def check_golden_finger_cost(text, chapter_num):
    """金手指代价检查（铁律6）- 考虑章节类型

    返回: (has_cost, cost_count, reason)
    """
    phase = get_chapter_phase(chapter_num, text)
    has_lingzhu = '灵珠' in text
    cost_count = sum(text.count(w) for w in GOLDEN_FINGER_COST)

    if has_lingzhu and cost_count == 0:
        return False, 0, '用了灵珠但无代价'

    if not has_lingzhu:
        return True, cost_count, '未使用灵珠'

    if phase == 'exempt':
        return True, cost_count, '豁免章节'

    return True, cost_count, '有代价 OK'


def check_villain_threat_level(text):
    """检测反派压迫感等级：村级(弱) vs 镇级(强)"""
    town_count = sum(text.count(w) for w in VILLIAN_TIED_TO_TOWN)
    action_count = sum(text.count(w) for w in VILLAIN_ACTION)
    # 镇级关联词越多 + 有实质行动 = 压迫感强
    threat_level = 'weak'
    if town_count >= 2 and action_count >= 1:
        threat_level = 'strong'  # 镇上关系+实际行动 = BOSS级压迫
    elif action_count >= 1:
        threat_level = 'medium'  # 有行动但只在村里
    return threat_level, town_count, action_count


def check_shuangdian_density(text):
    """爽点密度检测：打脸/赚钱/治病翻身"""
    count = sum(text.count(w) for w in SHUANGDIAN_KEYWORDS)
    # 按字数归一化（每千字一个爽点为达标）
    density = count / (len(text) / 1000) if text else 0
    return density, count


def check_dialogue_particle_abuse(text):
    """检测对话行是否过度使用行尾语气词（嘛/呗/呢/咯/咧/哩）

    Trae 等弱模型为了过"口语化阈值"会疯狂给每句对话加语气词，
    结果读起来像嚼过的口香糖。此函数抓这种刷分行为。

    返回: (abuse_ratio, abuse_count, total_dialogue_lines)
    """
    # 匹配被中文引号包起来的对话内容
    dialogue_contents = re.findall(r'\u201c([^\u201c\u201d]{2,})\u201d', text)
    if not dialogue_contents:
        return 0.0, 0, 0

    abuse_count = 0
    for content in dialogue_contents:
        # 去掉结尾标点后看是否以语气词结尾
        cleaned = content.rstrip('。！？，,.!?…～~ ')
        if not cleaned:
            continue
        for particle in DIALOGUE_END_PARTICLES:
            if cleaned.endswith(particle):
                abuse_count += 1
                break

    ratio = abuse_count / len(dialogue_contents)
    return ratio, abuse_count, len(dialogue_contents)


def check_cringe_monologue(text):
    """检测中二独白出现次数

    "等着吧 / 十倍奉还 / 付出代价 / 不会认输" 这种咬牙切齿独白
    每章出现 > 1 次 = WARNING, > 2 次 = CRITICAL
    读者对这种词零容忍。

    返回: (total_count, matched_words)
    """
    matched = {}
    for phrase in CRINGE_MONOLOGUE:
        c = text.count(phrase)
        if c > 0:
            matched[phrase] = c
    total = sum(matched.values())
    return total, matched


def check_scene_breaks(text):
    """检测章内场景切换数（由"一、/二、/三、"或"## 小标题"标记）

    一章塞 3+ 场戏 → 每场戏都没展开 → 读者看完啥都记不住
    (典型反例：CH22 塞了"醒来/镇长归来/治疗完成/回村" 4 场)

    返回: (break_count, break_markers)
    """
    # 匹配独立成行的小标题："一、XXX" / "二、XXX" 等
    cn_markers = re.findall(r'^[一二三四五六七八九十]+、\s*\S*', text, re.MULTILINE)
    # 匹配 "## 小标题" 或 "# 小标题"（但排除章节主标题）
    md_markers = re.findall(r'^#{1,3}\s+(?!第\d+章)[^\n]+', text, re.MULTILINE)
    total = len(cn_markers) + len(md_markers)
    markers = cn_markers + md_markers
    return total, markers


def check_villain_chain(text):
    """检测章内反派链条长度（铁律9：链条 ≤ 3 层）

    单章出现 > 3 个反派专名 = WARNING, > 4 个 = CRITICAL FAIL
    读者记不住谁是 Boss,是因为反派链条过长。
    赵老三→张二狗→恒昌→李万山→省城王某某 = 5 层,读者第 3 章就懵了。

    返回: (count, names_found)
    """
    found = {}
    for name in VILLAIN_NAMES:
        c = text.count(name)
        if c > 0:
            found[name] = c
    # 同名变体去重:"恒昌药行"和"恒昌"算同一反派
    canonical = set()
    for name in found.keys():
        if '恒昌' in name or '吴德明' in name or '吴经理' in name:
            canonical.add('恒昌/吴德明')
        elif '赵老三' in name or '张二狗' in name:
            canonical.add('赵老三/张二狗')
        elif '李万山' in name or '李副总' in name:
            canonical.add('李万山')
        else:
            canonical.add(name)
    return len(canonical), found


def check_ai_psychology_density(text):
    """检测 AI 心理套路合并密度（铁律10）

    单独一个"心里头咯噔"没事,但一章里堆砌 9 次"心里头咯噔/脑子嗡/攥紧拳头/
    深吸一口气/眉头皱了皱" = AI 堆砌,读者立刻出戏。

    阈值: <=5 PASS, 6-8 WARNING, >8 CRITICAL FAIL

    返回: (total_count, matched_phrases)
    """
    matched = {}
    for phrase in AI_PSYCHOLOGY_CLICHE:
        c = text.count(phrase)
        if c > 0:
            matched[phrase] = c
    total = sum(matched.values())
    return total, matched


def check_unquoted_dialogue(text):
    """检测未加引号的对话(CH13 犯过的错)

    识别模式(收紧防误伤):
      - 独立成行的短句(<= 25 字)
      - 以问号/感叹号结尾 (不仅靠"咋/啥"等特征词,那些容易误伤叙事)
      - 不含多重逗号(>=2 个逗号 = 叙述)
      - 不含叙述视角词(他想/他觉得/仿佛/像是)
      - 本行未被引号包裹
    返回裸对话行数,占所有疑似对话行的比例

    返回: (missing_count, total_dialog_like, missing_ratio, samples)
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    narration_feature = ['他想', '他觉得', '她觉得', '仿佛', '好像是', '似乎',
                         '但他', '但她', '心里头', '心里想', '他寻思',
                         '就他', '那会儿', '这会儿']
    missing_lines = []
    total_dialog_like = 0

    for line in lines:
        # 过滤 1: 长度上限 (对话一般短)
        if len(line) > 25:
            continue
        # 过滤 2: 已带引号
        has_quote = '\u201c' in line or '\u201d' in line or '"' in line
        # 过滤 3: 必须以 ? ! 结尾（不再用"咋/啥"特征词,误伤率太高）
        ends_with_excl = bool(re.search(r'[？！]$', line))
        if not ends_with_excl:
            continue
        # 过滤 4: 排除多逗号（叙述）
        if line.count('，') >= 2 or line.count(',') >= 2:
            continue
        # 过滤 5: 排除含叙述视角词
        if any(w in line for w in narration_feature):
            continue
        # 过滤 6: 排除明显叙述（"XX + 动词"）
        is_narration = bool(re.search(r'(陈大山|林秀梅|张德贵|刘瘸子|王大娘|陈老实|赵老三|他|她).{0,6}(走|看|站|坐|想|转|回头|抬头|低头|伸手|拿|放|蹲|挠)', line))
        if is_narration:
            continue
        # 过滤 7: 必须至少 4 字
        if len(line) < 4:
            continue

        total_dialog_like += 1
        if not has_quote:
            missing_lines.append(line)

    missing_count = len(missing_lines)
    ratio = missing_count / total_dialog_like if total_dialog_like > 0 else 0
    return missing_count, total_dialog_like, ratio, missing_lines[:5]


def analyze_ai_features(text):
    """AI 率估算（基于句式均匀度+口语化+逻辑词）"""
    sentences = [s.strip() for s in re.split(r'[。！？\n]', text) if s.strip()]
    if sentences:
        lengths = [len(s) for s in sentences]
        avg = sum(lengths) / len(lengths)
        std = (sum((l - avg) ** 2 for l in lengths) / len(lengths)) ** 0.5
        uniform = max(0, 100 - std * 2) / 100
    else:
        uniform = 0.5

    logic_words = ['但是', '不过', '然而', '因此', '所以', '首先', '其次', '最后', '综上']
    logic_freq = sum(text.count(w) for w in logic_words) / (len(text) / 100) if text else 0

    # 口语化统计（扩展词表：除语气词外加入口语结构词）
    colloquial = [
        # 语气词
        '咋', '啥', '呗', '嘛', '呢', '啊', '呀', '咯', '喽', '哟', '哼',
        # 口语动词/思考词
        '琢磨', '寻思', '盘算', '合计',
        # 口语指称/结构
        '玩意儿', '咱们', '那小子', '这小子', '那会儿', '这会儿',
        '可不是', '不是嘛', '咋的', '咋不', '瞧', '看那个',
        # 乡土语气
        '吆喝', '搭话', '嘀咕',
    ]
    # 记录每个词各自出现次数，用于反刷分检测
    word_counts = {w: text.count(w) for w in colloquial}
    coll_total = sum(word_counts.values())
    coll_freq = coll_total / (len(text) / 100) if text else 0

    # 反刷分：找占比最大的口语词
    top_word = None
    top_ratio = 0.0
    if coll_total > 0:
        top_word, top_count = max(word_counts.items(), key=lambda x: x[1])
        top_ratio = top_count / coll_total
    else:
        top_count = 0

    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) > 1:
        plen = [len(p) for p in paragraphs]
        pavg = sum(plen) / len(plen)
        pstd = (sum((l - pavg) ** 2 for l in plen) / len(plen)) ** 0.5
        puniform = max(0, 100 - pstd) / 100
    else:
        puniform = 0.5

    logic_score = min(100, logic_freq * 10) / 100
    coll_score = min(100, coll_freq * 20) / 100
    ai_score = uniform * 0.25 + logic_score * 0.25 + (1 - coll_score) * 0.25 + puniform * 0.25

    return {
        'ai_rate': round(ai_score * 100, 1),
        'uniformity': round(uniform * 100, 1),
        'logic_freq': round(logic_freq, 2),
        'colloquial_freq': round(coll_freq, 2),
        'colloquial_total': coll_total,
        'top_colloquial_word': top_word,
        'top_colloquial_count': top_count,
        'top_colloquial_ratio': round(top_ratio * 100, 1),
    }


def get_publish_readiness_blockers(project_path, chapter_num, text):
    """调用发布审稿的核心规则，判断本章是否存在结构性阻断项。

    目的不是替代 publish_readiness_audit.py，而是让健康检查在给 AI 率/口语化
    警告前，先知道这章结构上到底是不是已经可发。
    """
    if publish_audit is None:
        return []

    lines = text.splitlines()
    scenes = publish_audit.collect_scene_markers(text)
    naked_dialogue_hits = publish_audit.collect_naked_dialogue(lines)
    bookkeeping_hits = publish_audit.collect_bookkeeping_hits(lines)
    summary_hits = publish_audit.collect_marker_hits(lines, publish_audit.SUMMARY_MARKERS, min_markers=1)
    telling_hits = publish_audit.collect_telling_hits(lines)
    return publish_audit.score_blockers(
        scene_count=len(scenes),
        naked_dialogue=len(naked_dialogue_hits),
        bookkeeping=len(bookkeeping_hits),
        summary=len(summary_hits),
        telling=len(telling_hits),
    )


def check_conflict_density(project_path, current_chapter):
    """基于 progress.md 判断冲突密度"""
    progress_file = os.path.join(project_path, '项目文件', 'progress.md')
    if not os.path.exists(progress_file):
        return None, '找不到 progress.md'

    with open(progress_file, 'r', encoding='utf-8') as f:
        content = f.read()

    keywords = ['打脸', '冲突', '找茬', '威胁', '挑战', '对决', '危机', '风波', '刁难', '欺压']
    last_ch = 0
    for line in content.split('\n'):
        for kw in keywords:
            if kw in line:
                m = re.search(r'第(\d+)章', line)
                if m:
                    n = int(m.group(1))
                    if last_ch < n <= current_chapter:
                        last_ch = n

    if last_ch == 0:
        return current_chapter, '未找到冲突记录'
    return current_chapter - last_ch, '最近冲突在第{}章'.format(last_ch)


def check_word_count(text, target=2800, tolerance=600):
    clean = re.sub(r'[^\u4e00-\u9fff]', '', text)
    wc = len(clean)
    if target - tolerance <= wc <= target + tolerance:
        return wc, True
    return wc, False


def check_paragraph_format(text):
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    long_p = 0
    for p in paragraphs:
        s = [x for x in re.split(r'[。！？]', p) if x.strip()]
        if len(s) > 3:
            long_p += 1
    return len(paragraphs), long_p


def run_check(project_path, chapter_num, strict=False):
    chapter_dir = os.path.join(project_path, '正文卷')
    if not os.path.exists(chapter_dir):
        print('[ERROR] 找不到正文卷目录: {}'.format(chapter_dir))
        return 1

    chapter_file = None
    for f in os.listdir(chapter_dir):
        if f.startswith('第{}章'.format(chapter_num)):
            chapter_file = os.path.join(chapter_dir, f)
            break

    if not chapter_file:
        print('[ERROR] 找不到第{}章文件'.format(chapter_num))
        return 1

    with open(chapter_file, 'r', encoding='utf-8') as f:
        raw = f.read()
    text = clean_text(raw)
    publish_blockers = get_publish_readiness_blockers(project_path, chapter_num, text)
    publish_ready = len(publish_blockers) == 0
    phase = get_chapter_phase(chapter_num, text)

    print('=' * 55)
    print('[第{}章] 健康检查 v2 (strict={})'.format(chapter_num, strict))
    print('=' * 55)

    critical_fails = []
    warnings = []

    # ========== CRITICAL 硬阈值 ==========

    # 1. 引号检查（最致命）
    quote_count = count_chinese_quotes(text)
    print()
    print('[1] 对话引号检查')
    print('    中文引号对: {} (阈值: >= {})'.format(quote_count, THRESHOLD_CRITICAL['chinese_quotes_min']))
    if quote_count < THRESHOLD_CRITICAL['chinese_quotes_min']:
        print('    [CRITICAL FAIL] 对话没加引号！必须用 \u201c \u201d 包裹所有对话')
        critical_fails.append('对话引号不足: {}对 (需 >= {})'.format(quote_count, THRESHOLD_CRITICAL['chinese_quotes_min']))
    else:
        print('    [PASS]')

    # 1b. 裸对话检查（CH13 犯过：引号总数过但大量对话没加引号）
    missing_cnt, dialog_total, missing_ratio, samples = check_unquoted_dialogue(text)
    print()
    print('[1b] 裸对话检查（铁律 1:对话必须 ""包裹）')
    print('    疑似对话行: {}  其中未加引号: {} ({}%)'.format(
        dialog_total, missing_cnt, round(missing_ratio * 100, 1)))
    if samples:
        print('    示例:')
        for s in samples[:3]:
            print('      - {}'.format(s[:40]))
    if missing_cnt >= 5 and missing_ratio >= 0.30:
        msg = '裸对话过多: {} 行对话未加引号 ({}%)'.format(missing_cnt, round(missing_ratio * 100, 1))
        critical_fails.append(msg)
        print('    [CRITICAL FAIL] {}'.format(msg))
        print('    建议: 跑 auto_fix_chapter.py 自动补引号,或人工逐行 ""包裹')
    elif missing_cnt >= 2:
        warnings.append('少量裸对话: {} 行'.format(missing_cnt))
        print('    [WARNING] 有少量对话未加引号')
    else:
        print('    [PASS]')

    # 2. AI 模板词
    total_tpl, tpl_detail = count_template_words(text)
    print()
    print('[2] AI 模板词检查')
    print('    总次数: {} (阈值: <= {})'.format(total_tpl, THRESHOLD_CRITICAL['template_word_max']))
    if tpl_detail:
        for word, cnt in sorted(tpl_detail.items(), key=lambda x: -x[1]):
            flag = ' [SINGLE FAIL]' if cnt > THRESHOLD_CRITICAL['template_single_max'] else ''
            print('      "{}": {}次{}'.format(word, cnt, flag))

    if total_tpl > THRESHOLD_CRITICAL['template_word_max']:
        critical_fails.append('AI 模板词超限: {}次 (需 <= {})'.format(total_tpl, THRESHOLD_CRITICAL['template_word_max']))
        print('    [CRITICAL FAIL] 模板词总量超标')
    over_single = [w for w, c in tpl_detail.items() if c > THRESHOLD_CRITICAL['template_single_max']]
    if over_single:
        critical_fails.append('单词超限: {} 各出现>2次'.format('、'.join(over_single)))
        print('    [CRITICAL FAIL] 单词超限: {}'.format('、'.join(over_single)))
    if not critical_fails or (total_tpl <= THRESHOLD_CRITICAL['template_word_max'] and not over_single):
        if total_tpl <= THRESHOLD_CRITICAL['template_word_max']:
            print('    [PASS]')

    # 3. 反派口头威胁检查
    has_action, verbal, action = check_villain_action(text)
    print()
    print('[3] 反派行动检查')
    print('    口头威胁: {}次  实质行动: {}次'.format(verbal, action))
    if not has_action:
        warnings.append('反派仅口头威胁未动手 (验证关键词: 毁/砸/买通/举报/烧 等)')
        print('    [WARNING] 反派只有口头威胁，没有实质行动')
    else:
        print('    [PASS]')

    # 3b. 反派压迫感等级（GPT建议强化）
    threat_level, town_count, action_count = check_villain_threat_level(text)
    print()
    print('[3b] 反派压迫感等级')
    print('    压迫等级: {} (村级={}, 镇上关联={})'.format(threat_level, action_count, town_count))
    if threat_level == 'weak':
        warnings.append('反派压迫感弱：仅村级行动，未绑定镇上势力')
        print('    [WARNING] 赵老三仍是村级反派，建议绑定镇上势力（恒昌药行）增强压迫感')
    elif threat_level == 'strong':
        print('    [PASS] BOSS级压迫感')
    else:
        print('    [INFO] 中等级：建议后续绑定镇上关系')

    # 4. 爽点密度（GPT建议强化）
    shuangdian_density, shuangdian_count = check_shuangdian_density(text)
    print()
    print('[4] 爽点密度 (打脸/赚钱/治病翻身)')
    print('    爽点密度: {}/千字  爽点词次数: {}'.format(round(shuangdian_density, 2), shuangdian_count))
    if shuangdian_density < 0.5:
        warnings.append('爽点不足: {}/千字（建议 >= 1.0/千字）'.format(round(shuangdian_density, 2)))
        print('    [WARNING] 爽点不够狠，建议增加打脸/赚钱/翻身情节')
    elif shuangdian_density >= 1.5:
        print('    [PASS] 爽点充足')
    else:
        print('    [INFO] 爽点适中')

    # 4b. 主角挫折检查（铁律4）- 按章节类型判断
    has_setback, setback_count, phase, phase_msg = check_protagonist_setback(text, chapter_num)
    print()
    print('[4b] 主角挫折检查 (铁律4) - 章节类型: {}'.format(phase))
    print('    挫折关键词: {}次  阶段: {}'.format(setback_count, phase_msg))
    if not has_setback:
        critical_fails.append('主角无挫折: {}章节类型 "{}" 主角必须有挫折！'.format(phase, phase_msg))
        print('    [CRITICAL FAIL] {} {}'.format(phase, phase_msg))
    else:
        print('    [PASS]')
        print('    [PASS]')

    # 4c. 金手指代价检查（铁律6）
    has_cost, cost_count, cost_reason = check_golden_finger_cost(text, chapter_num)
    print()
    print('[4c] 金手指代价检查 (铁律6)')
    print('    代价关键词出现: {}次  状态: {}'.format(cost_count, cost_reason))
    if not has_cost:
        critical_fails.append('金手指无代价: 使用灵珠但未写出身体代价（铁律6违规）')
        print('    [CRITICAL FAIL] 使用灵珠必须有代价！')
    else:
        print('    [PASS]')

    # 5. AI 率
    ai = analyze_ai_features(text)
    print()
    print('[5] AI 率估算')
    print('    预估 AI 率: {}%  (CRITICAL阈值 > {}%)'.format(ai['ai_rate'], THRESHOLD_CRITICAL['ai_rate_max']))
    print('    句式均匀度: {}%  逻辑词: {}/百字  口语化: {}/百字'.format(
        ai['uniformity'], ai['logic_freq'], ai['colloquial_freq']))
    if ai['ai_rate'] > THRESHOLD_CRITICAL['ai_rate_max']:
        critical_fails.append('AI 率过高: {}%'.format(ai['ai_rate']))
        print('    [CRITICAL FAIL] AI 率过高')
    elif ai['ai_rate'] > THRESHOLD_WARNING['ai_rate'] and not publish_ready:
        warnings.append('AI 率偏高: {}%'.format(ai['ai_rate']))
        print('    [WARNING] AI 率偏高，建议进一步降重')
    elif ai['ai_rate'] > THRESHOLD_WARNING['ai_rate'] and publish_ready:
        print('    [INFO] AI率估算偏高,但发布审稿已通过,本项不单独判警告')
    else:
        print('    [PASS]')

    # 6. 口语化（WARNING，不阻断交付）
    print()
    print('[6] 口语化程度')
    print('    频率: {}/百字 (WARNING阈值 >= {})'.format(ai['colloquial_freq'], THRESHOLD_WARNING['colloquial_min']))
    if ai['colloquial_freq'] < THRESHOLD_WARNING['colloquial_min'] and not publish_ready:
        print('    [WARNING] 口语化略低，读着顺即可，不必硬凑语气词')
    elif ai['colloquial_freq'] < THRESHOLD_WARNING['colloquial_min'] and publish_ready:
        print('    [INFO] 口语化偏低,但结构审稿已通过,不建议为过线硬补语气词')
    else:
        print('    [PASS]')

    # 6b. 口语词刷分检测（反堆砌）
    if (ai['top_colloquial_word']
            and ai['colloquial_total'] >= 10
            and ai['top_colloquial_count'] >= 4
            and ai['top_colloquial_ratio'] >= ANTI_SPAM_THRESHOLD * 100):
        msg = '口语化疑似刷分: "{}" 占所有口语词 {}% (阈值 {}%)'.format(
            ai['top_colloquial_word'], ai['top_colloquial_ratio'], int(ANTI_SPAM_THRESHOLD * 100))
        print('    [CRITICAL FAIL] {}'.format(msg))
        print('    建议: 替换部分"{}"为其他口语词（吧/嘛/呢/咋/啥/琢磨/盘算等）'.format(ai['top_colloquial_word']))
        critical_fails.append(msg)

    # 6c. 对话行尾语气词滥用检测（反"每句都挂嘛/呗/呢"）
    particle_ratio, abuse_count, total_dialogs = check_dialogue_particle_abuse(text)
    print()
    print('[6c] 对话行尾语气词检测 (反"每句挂嘛呗呢")')
    if total_dialogs > 0:
        print('    对话行 {} 句,  以语气词结尾 {} 句 ({}%)'.format(
            total_dialogs, abuse_count, round(particle_ratio * 100, 1)))
        if particle_ratio >= DIALOGUE_PARTICLE_ABUSE_THRESHOLD:
            msg = '对话行尾语气词滥用: {}% 对话以"嘛/呗/呢/咯"结尾 (阈值 {}%)'.format(
                round(particle_ratio * 100, 1), int(DIALOGUE_PARTICLE_ABUSE_THRESHOLD * 100))
            critical_fails.append(msg)
            print('    [CRITICAL FAIL] {}'.format(msg))
            print('    建议: 减少行尾语气词,让对话有呼吸感——2 句带语气词,1 句直说,1 句靠动作带')
        else:
            print('    [PASS]')
    else:
        print('    [INFO] 无对话或对话引号未正确包裹')

    # 6d. 中二独白检测（反"等着吧/十倍奉还"泛滥）
    cringe_total, cringe_matched = check_cringe_monologue(text)
    print()
    print('[6d] 中二独白检测 (等着吧/十倍奉还/付出代价)')
    if cringe_total > 0:
        detail = ', '.join(['"{}" x{}'.format(w, c) for w, c in cringe_matched.items()])
        print('    总次数: {}  详情: {}'.format(cringe_total, detail))
        if cringe_total > 2:
            msg = '中二独白泛滥: 本章出现 {} 次 (阈值: 2 次)'.format(cringe_total)
            critical_fails.append(msg)
            print('    [CRITICAL FAIL] {}'.format(msg))
            print('    建议: 改用动作/细节代替——"把名片揣进兜里,指头使劲捏了捏" 比 "俺十倍奉还" 更有劲')
        elif cringe_total > 1:
            warnings.append('中二独白偏多: {} 次 (建议 <= 1 次)'.format(cringe_total))
            print('    [WARNING] 中二独白偏多,建议删一处')
        else:
            print('    [PASS] 1 次可接受')
    else:
        print('    [PASS] 无中二独白')

    # 6e. 场景切换检测（反"一章塞三场戏"）
    break_count, break_markers = check_scene_breaks(text)
    print()
    print('[6e] 场景切换检测 (一章最多 2 场戏)')
    print('    小标题数: {}'.format(break_count))
    if break_markers:
        for m in break_markers[:5]:
            print('      - {}'.format(m.strip()))
    if break_count > 2:
        msg = '场景过多: {} 场戏挤一章 (铁律 7: 最多 2 场)'.format(break_count)
        warnings.append(msg)
        print('    [WARNING] {}'.format(msg))
        print('    建议: 拆成两章。每场戏展开写透,比挤一章走马观花强')
    else:
        print('    [PASS]')

    # 6f. 反派链条长度检测（铁律 9：反派链条 ≤ 3 层）
    villain_count, villain_found = check_villain_chain(text)
    print()
    print('[6f] 反派链条检测 (铁律9: 单章反派专名 <= 3)')
    if villain_count > 0:
        detail = ', '.join(['"{}" x{}'.format(w, c) for w, c in villain_found.items()])
        print('    出现 {} 个反派(去重后),详情: {}'.format(villain_count, detail))
        if villain_count > 4:
            msg = '反派链条过长: 单章出现 {} 个反派势力 (阈值: 4)'.format(villain_count)
            critical_fails.append(msg)
            print('    [CRITICAL FAIL] {}'.format(msg))
            print('    建议: 砍掉中间层。赵老三→恒昌→李万山→... 读者记不住谁是 Boss')
        elif villain_count > 3:
            warnings.append('反派偏多: {} 个,建议砍中间层'.format(villain_count))
            print('    [WARNING] 反派偏多,建议合并或砍中间层')
        else:
            print('    [PASS]')
    else:
        print('    [INFO] 本章无反派正面出现')

    # 6g. AI 心理套路合并密度检测（铁律 10）
    psych_total, psych_matched = check_ai_psychology_density(text)
    print()
    print('[6g] AI 心理套路密度 (铁律10: 心里头咯噔/脑子嗡/攥紧拳头 合并)')
    if psych_total > 0:
        # 只列前 5 个
        sorted_matched = sorted(psych_matched.items(), key=lambda x: -x[1])[:5]
        detail = ', '.join(['"{}" x{}'.format(w, c) for w, c in sorted_matched])
        print('    合并出现: {} 次  高频: {}'.format(psych_total, detail))
        if psych_total > 8:
            msg = 'AI 心理套路泛滥: 合并 {} 次 (阈值: 8)'.format(psych_total)
            critical_fails.append(msg)
            print('    [CRITICAL FAIL] {}'.format(msg))
            print('    建议: 换具体动作——"捏着筷子手顿住,菜夹一半又放回碗里" 代替 "心里头咯噔"')
        elif psych_total > 5:
            warnings.append('AI 心理套路偏多: {} 次 (建议 <= 5)'.format(psych_total))
            print('    [WARNING] AI 心理套路偏多,建议替换几处为具体动作')
        else:
            print('    [PASS]')
    else:
        print('    [PASS] 无 AI 套路心理')

    # 6h. Humanizer 结构性模式检测( WARNING 级别)
    hm_results = check_humanizer_patterns(text)
    print()
    print('[6h] Humanizer 结构性模式检测 (新增 WARNING)')
    a_total = sum(hm_results['A'].values())
    b_total = sum(hm_results['B'].values())
    c_total = sum(hm_results['C'].values())
    hw = []
    if hm_results['A']:
        detail_a = ', '.join(['{}:{}次'.format(k, v) for k, v in hm_results['A'].items()])
        print('    A类: {}  (否定排比/三段式/-ing结尾/谄媚/强行展望)'.format(detail_a))
    if hm_results['B']:
        detail_b = ', '.join(['{}:{}次'.format(k, v) for k, v in hm_results['B'].items()])
        print('    B类: {}  (填充短语/AI高频词/过度限定)'.format(detail_b))
    if hm_results['C']:
        detail_c = ', '.join(['{}:{}次'.format(k, v) for k, v in hm_results['C'].items()])
        print('    C类: {}  (破折号/加粗/弯引号/表情)'.format(detail_c))
    if a_total > 3:
        hw.append('A类结构性模式: {}次 > 3 (阈值)'.format(a_total))
    if b_total > 5:
        hw.append('B类AI套话: {}次 > 5 (阈值)'.format(b_total))
    if hm_results['C'].get('破折号', 0) > 3:
        hw.append('破折号: {}次 > 3 (阈值)'.format(hm_results['C'].get('破折号', 0)))
    if hm_results['C'].get('弯引号', 0) > 0:
        hw.append('弯引号「」出现: {}次 (铁律1要求用"")'.format(hm_results['C'].get('弯引号', 0)))
    if hm_results['C'].get('表情符号', 0) > 0:
        hw.append('表情符号: {}次 (正文不应有)'.format(hm_results['C'].get('表情符号', 0)))
    if hw:
        relaxed_hm = publish_ready and a_total <= 15 and b_total <= 25 and hm_results['C'].get('破折号', 0) <= 3 \
            and hm_results['C'].get('弯引号', 0) == 0 and hm_results['C'].get('表情符号', 0) == 0
        if relaxed_hm:
            print('    [INFO] 结构性模式计数偏高,但发布审稿已通过,本项不计入WARNING')
        else:
            for w in hw:
                warnings.append(w)
                print('    [WARNING] {}'.format(w))
    else:
        print('    [PASS]')

    # ========== WARNING 软阈值 ==========

    # 7. 冲突密度
    gap, gap_msg = check_conflict_density(project_path, chapter_num)
    print()
    print('[7] 冲突密度')
    if gap is not None:
        print('    距最近冲突: {}章 ({})'.format(gap, gap_msg))
        if phase == 'exempt':
            print('    [INFO] 豁免章/成功章不以冲突密度单独告警')
        elif gap >= THRESHOLD_WARNING['conflict_gap']:
            warnings.append('冲突密度: 已{}章无冲突'.format(gap))
            print('    [WARNING]')
        else:
            print('    [PASS]')

    # 8. 字数
    wc, wc_ok = check_word_count(text)
    print()
    print('[8] 字数检查')
    print('    字数: {} (目标 2200-3400)'.format(wc))
    if not wc_ok:
        warnings.append('字数偏差: {}字'.format(wc))
        print('    [WARNING] 偏离目标范围')
    else:
        print('    [PASS]')

    # 9. 段落
    total_p, long_p = check_paragraph_format(text)
    print()
    print('[9] 段落格式')
    print('    段落数: {}  超长段落(>3句): {}'.format(total_p, long_p))
    if long_p > 0 and not (publish_ready and long_p <= 2):
        warnings.append('有{}段超过3句'.format(long_p))
        print('    [WARNING] 建议拆分')
    elif long_p > 0:
        print('    [INFO] 有少量长段,但发布审稿已通过')
    else:
        print('    [PASS]')

    # ========== 总结 ==========
    print()
    print('=' * 55)
    print('[SUMMARY]')
    print('=' * 55)

    if critical_fails:
        print('[CRITICAL FAIL] 必须修复后重新检查:')
        for x in critical_fails:
            print('  - {}'.format(x))

    if warnings:
        print('[WARNING] 建议修复:')
        for x in warnings:
            print('  - {}'.format(x))

    if not critical_fails and not warnings:
        print('[PASS] 本章健康检查全部通过!')
        exit_code = 0
    elif critical_fails:
        print()
        print('>>> 退出码 1: 当前章节不达交付标准 <<<')
        print('>>> 建议: 先跑 auto_fix_chapter.py 修复引号+模板词，再重新检查 <<<')
        print()
        print('⚠️ 死循环保护提示:')
        print('   如果你已经尝试重写 >= 3 次仍 FAIL，请停止重写并告诉用户：')
        print('   "重写 N 次后仍未通过，剩余问题：[列出具体指标]。建议人工介入或放宽阈值。"')
        print('   不要无限重试——这会污染上下文并浪费 token。')
        exit_code = 1
    elif warnings and strict:
        print()
        print('>>> 退出码 2: WARNING (strict 模式下需处理) <<<')
        exit_code = 2
    else:
        exit_code = 0

    # 趋势数据落盘（CSV）
    _append_trend_csv(project_path, chapter_num, {
        'exit_code': exit_code,
        'ai_rate': ai['ai_rate'],
        'colloquial_freq': ai['colloquial_freq'],
        'uniformity': ai['uniformity'],
        'word_count': wc,
        'villain_threat_level': threat_level,
        'villain_action_count': action_count,
        'villain_town_count': town_count,
        'shuangdian_density': round(shuangdian_density, 2),
        'shuangdian_count': shuangdian_count,
        'setback_count': setback_count,
        'setback_phase': phase,
        'golden_finger_cost_count': cost_count,
        'long_paragraph_count': long_p,
        'dialogue_particle_ratio': round(particle_ratio * 100, 1),
        'cringe_monologue_count': cringe_total,
        'scene_break_count': break_count,
        'critical_count': len(critical_fails),
        'warning_count': len(warnings),
        'hm_a_count': a_total,
        'hm_b_count': b_total,
        'hm_dash_count': hm_results['C'].get('破折号', 0),
        'hm_bracket_count': hm_results['C'].get('弯引号', 0),
        'hm_emoji_count': hm_results['C'].get('表情符号', 0),
    })

    return exit_code


def _append_trend_csv(project_path, chapter_num, metrics):
    """追加一行趋势数据到 项目文件/quality_trend.csv"""
    csv_path = os.path.join(project_path, '项目文件', 'quality_trend.csv')
    header = [
        'timestamp', 'chapter', 'exit_code',
        'ai_rate', 'colloquial_freq', 'uniformity',
        'word_count',
        'villain_threat_level', 'villain_action_count', 'villain_town_count',
        'shuangdian_density', 'shuangdian_count',
        'setback_count', 'setback_phase',
        'golden_finger_cost_count',
        'long_paragraph_count',
        'dialogue_particle_ratio', 'cringe_monologue_count', 'scene_break_count',
        'critical_count', 'warning_count',
        'hm_a_count', 'hm_b_count', 'hm_dash_count', 'hm_bracket_count', 'hm_emoji_count',
    ]
    row = {'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'chapter': chapter_num}
    row.update(metrics)

    file_exists = os.path.exists(csv_path)
    try:
        with open(csv_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=header)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except Exception as e:
        print('[WARN] 趋势CSV写入失败: {}'.format(e))


def main():
    parser = argparse.ArgumentParser(description='章节健康检查 v2 (弱模型强制守门)')
    parser.add_argument('--project', required=True, help='项目根目录路径')
    parser.add_argument('--chapter', type=int, required=True, help='章节号')
    parser.add_argument('--strict', action='store_true', help='严格模式: WARNING 也作为失败')
    args = parser.parse_args()

    code = run_check(args.project, args.chapter, strict=args.strict)
    sys.exit(code)


if __name__ == '__main__':
    main()
