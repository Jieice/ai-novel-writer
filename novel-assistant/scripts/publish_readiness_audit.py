#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄发布就绪审稿脚本

目标:
1. 补足 chapter_health_check.py 的缺口
2. 抓结构性 AI 痕迹,而不是只抓模板词
3. 给出更贴近"能不能发番茄"的阻断项

检查重点:
- 一章场景是否过多
- 是否大量"汇报式叙述/账本式说明"
- 是否存在裸对话
- 是否反复使用通用反应词
- 是否大量使用"总结/计划/展望"句来替代真实场景

退出码:
  0 = 基本达标
  1 = 存在发布阻断项,建议重写或大修
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
from dataclasses import dataclass

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding="utf-8")


SCENE_MARKERS_RE = re.compile(r"^[一二三四五六七八九十]+、\s*\S*|^#{1,3}\s+(?!第\d+章)[^\n]+", re.MULTILINE)

SUMMARY_MARKERS = [
    "这意味着",
    "这不只是",
    "说到底",
    "不过他知道",
    "他现在不着急",
    "他现在顾不上",
    "接下来要",
    "往后能赚的钱",
    "以后是不是",
    "到时候",
    "眼下这年月",
    "算了一笔账",
    "盘算着接下来的计划",
    "脑子里盘算着",
    "这在1992年的农村",
    "这在一九九二年的农村",
]

BOOKKEEPING_MARKERS = [
    "平均",
    "一共",
    "加起来",
    "每个",
    "一斤",
    "半斤",
    "一两",
    "块钱",
    "毛钱",
    "克左右",
    "目标",
    "计划",
    "品相",
    "品质",
    "价格",
    "供货",
    "规模做大",
    "扩大规模",
    "稳定供货",
]

GENERIC_REACTION_MARKERS = [
    "心里头一",
    "心里一",
    "嘴角动了动",
    "深吸了口气",
    "摸了摸鼻子",
    "没说话",
    "整个人僵住了",
    "眼睛刷的一下就亮了",
    "眼睛慢慢睁大了",
    "嘴张了张没说出话",
    "高兴得合不拢嘴",
]

TELLING_PATTERNS = [
    "他心里头",
    "他心里",
    "她心里",
    "他知道",
    "她知道",
    "他明白",
    "她明白",
    "这意味着",
    "说明",
    "证明",
    "确认",
    "意味着",
]


@dataclass
class LineHit:
    line_no: int
    text: str


def find_chapter_file(project_path: str, chapter_num: int) -> str | None:
    chapter_dir = os.path.join(project_path, "正文卷")
    if not os.path.isdir(chapter_dir):
        return None
    for name in os.listdir(chapter_dir):
        if name.startswith(f"第{chapter_num}章"):
            return os.path.join(chapter_dir, name)
    return None


def clean_text(raw: str) -> str:
    text = re.sub(r"^【第\d+章[^】]*】\s*", "", raw)
    text = re.sub(r"（本章完）\s*$", "", text)
    return text.strip()


def collect_scene_markers(text: str) -> list[str]:
    return SCENE_MARKERS_RE.findall(text)


def collect_naked_dialogue(lines: list[str]) -> list[LineHit]:
    hits: list[LineHit] = []
    narration_verbs = "走看站坐想转回头抬头低头伸手拿放蹲挠扶推"
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if "“" in stripped or "”" in stripped or '"' in stripped:
            continue
        if len(stripped) > 30:
            continue
        if not re.search(r"[？?！!]$", stripped):
            continue
        if re.search(rf"(陈大山|林秀梅|张德贵|赵老三|他|她).{{0,6}}[{narration_verbs}]", stripped):
            continue
        hits.append(LineHit(idx, stripped))
    return hits


def collect_marker_hits(lines: list[str], markers: list[str], min_markers: int = 1) -> list[LineHit]:
    hits: list[LineHit] = []
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        hit_count = sum(1 for marker in markers if marker in stripped)
        if hit_count >= min_markers:
            hits.append(LineHit(idx, stripped))
    return hits


def collect_bookkeeping_hits(lines: list[str]) -> list[LineHit]:
    hits: list[LineHit] = []
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or len(stripped) < 28:
            continue
        marker_count = sum(1 for marker in BOOKKEEPING_MARKERS if marker in stripped)
        digit_count = len(re.findall(r"\d+", stripped))
        if marker_count >= 2 or (marker_count >= 1 and digit_count >= 2):
            hits.append(LineHit(idx, stripped))
    return hits


def collect_generic_reaction_hits(lines: list[str]) -> list[LineHit]:
    return collect_marker_hits(lines, GENERIC_REACTION_MARKERS, min_markers=1)


def collect_telling_hits(lines: list[str]) -> list[LineHit]:
    hits: list[LineHit] = []
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or "“" in stripped or '"' in stripped:
            continue
        if sum(1 for pattern in TELLING_PATTERNS if pattern in stripped) >= 2:
            hits.append(LineHit(idx, stripped))
    return hits


def score_blockers(scene_count: int, naked_dialogue: int, bookkeeping: int, summary: int, telling: int) -> list[str]:
    blockers: list[str] = []
    if scene_count > 2:
        blockers.append(f"场景过多: {scene_count} 场戏挤在一章")
    if naked_dialogue >= 3:
        blockers.append(f"裸对话过多: {naked_dialogue} 行")
    if bookkeeping >= 6:
        blockers.append(f"账本式说明过多: {bookkeeping} 行")
    if summary >= 5:
        blockers.append(f"总结/计划句过多: {summary} 行")
    if telling >= 5:
        blockers.append(f"讲述句过多: {telling} 行")
    return blockers


def print_hits(title: str, hits: list[LineHit], limit: int = 5) -> None:
    print(title)
    if not hits:
        print("  - 无")
        return
    for hit in hits[:limit]:
        print(f"  - L{hit.line_no}: {hit.text}")
    if len(hits) > limit:
        print(f"  - ... 另有 {len(hits) - limit} 行")


def main() -> int:
    parser = argparse.ArgumentParser(description="番茄发布就绪审稿脚本")
    parser.add_argument("--project", required=True, help="项目根目录")
    parser.add_argument("--chapter", type=int, required=True, help="章节号")
    args = parser.parse_args()

    chapter_file = find_chapter_file(args.project, args.chapter)
    if not chapter_file:
        print(f"[ERROR] 找不到第{args.chapter}章文件")
        return 1

    with open(chapter_file, "r", encoding="utf-8") as f:
        raw = f.read()

    text = clean_text(raw)
    lines = text.splitlines()

    scenes = collect_scene_markers(text)
    naked_dialogue_hits = collect_naked_dialogue(lines)
    bookkeeping_hits = collect_bookkeeping_hits(lines)
    summary_hits = collect_marker_hits(lines, SUMMARY_MARKERS, min_markers=1)
    reaction_hits = collect_generic_reaction_hits(lines)
    telling_hits = collect_telling_hits(lines)

    blockers = score_blockers(
        scene_count=len(scenes),
        naked_dialogue=len(naked_dialogue_hits),
        bookkeeping=len(bookkeeping_hits),
        summary=len(summary_hits),
        telling=len(telling_hits),
    )

    print("=" * 55)
    print(f"[第{args.chapter}章] 番茄发布审稿")
    print("=" * 55)
    print()
    print("[核心指标]")
    print(f"  场戏数: {len(scenes)}")
    print(f"  裸对话: {len(naked_dialogue_hits)}")
    print(f"  账本式说明: {len(bookkeeping_hits)}")
    print(f"  总结/计划句: {len(summary_hits)}")
    print(f"  通用反应句: {len(reaction_hits)}")
    print(f"  讲述句: {len(telling_hits)}")
    print()

    if scenes:
        print("[场景标记]")
        for marker in scenes:
            print(f"  - {marker}")
        print()

    print_hits("[裸对话样例]", naked_dialogue_hits)
    print()
    print_hits("[账本式说明样例]", bookkeeping_hits)
    print()
    print_hits("[总结/计划句样例]", summary_hits)
    print()
    print_hits("[通用反应句样例]", reaction_hits)
    print()
    print_hits("[讲述句样例]", telling_hits)
    print()

    if blockers:
        print("[结论]")
        for blocker in blockers:
            print(f"  - {blocker}")
        print()
        print("建议: 先做场景级重写,不要继续用替换词硬补。")
        return 1

    print("[结论]")
    print("  - 未发现发布阻断项,可进入细修阶段。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
