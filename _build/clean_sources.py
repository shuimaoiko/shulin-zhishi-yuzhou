# -*- coding: utf-8 -*-
"""
清洗公众号 Markdown 数据源。

原则：
- 只处理公众号两个账号目录里的低质/重复宣传类源文档。
- 不直接删除原文，移动到「公众号/_清洗移除」作为可追溯归档。
- 清洗后 parse.py 只会读取「对木同学」「树成林Light」两个活跃目录，因此归档文件不再进入知识宇宙。
"""
from __future__ import annotations

import collections
import re
import shutil
from pathlib import Path


MP_ROOT = Path("/Users/水猫/文档/树林/公众号")
ARCHIVE_ROOT = MP_ROOT / "_清洗移除"
ACCOUNTS = ["对木同学", "树成林Light"]


EXACT_REMOVE_TITLES = {
    "分享图片": "分享图片文章",
    "小鹅通报名流程": "纯报名流程",
    "要买买买课程的同学看过来～": "纯课程咨询入口",
    "树成林百天规划报名": "课程报名宣传",
}

RECURRING_TITLE_RULES = [
    (re.compile(r"早起践行群"), "早起践行群重复报名/打卡营"),
    (re.compile(r"早起训练营"), "早起训练营重复宣传"),
]

COURSE_DUP_KEYWORDS = (
    "课程",
    "训练营",
    "成长营",
    "预备营",
    "觉醒营",
    "IP训练营",
    "规划课",
    "冲刺课",
    "全程课",
    "考纲单词",
    "考纲词汇",
)


def title_from_path(path: Path) -> str:
    stem = path.stem
    return stem.split("_", 1)[1] if "_" in stem else stem


def norm_title(title: str) -> str:
    title = re.sub(r"^「转」", "", title)
    title = re.sub(r"[\s，,。！!？?~～·：:—_\-（）()【】\[\]《》“”\"'、]+", "", title)
    return title.lower()


def active_files() -> list[Path]:
    files: list[Path] = []
    for account in ACCOUNTS:
        folder = MP_ROOT / account
        if folder.is_dir():
            files.extend(sorted(folder.glob("*.md")))
    return sorted(files)


def select_files() -> dict[Path, str]:
    selected: dict[Path, str] = {}
    files = active_files()

    for path in files:
        title = title_from_path(path)
        if title in EXACT_REMOVE_TITLES:
            selected[path] = EXACT_REMOVE_TITLES[title]
            continue
        for pattern, reason in RECURRING_TITLE_RULES:
            if pattern.search(title):
                selected[path] = reason
                break

    groups: dict[str, list[Path]] = collections.defaultdict(list)
    for path in files:
        groups[norm_title(title_from_path(path))].append(path)

    for paths in groups.values():
        if len(paths) <= 1:
            continue
        titles = [title_from_path(p) for p in paths]
        if not any(any(k in t for k in COURSE_DUP_KEYWORDS) for t in titles):
            continue
        # 同题课程/训练营宣传只保留日期最新的一篇，旧稿归档。
        for old_path in sorted(paths)[:-1]:
            selected.setdefault(old_path, "重复课程宣传旧稿")

    return dict(sorted(selected.items(), key=lambda item: str(item[0])))


def archive_path(path: Path) -> Path:
    account = path.parent.name
    return ARCHIVE_ROOT / account / path.name


def main() -> None:
    selected = select_files()
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    moved: list[tuple[Path, Path, str]] = []

    for src, reason in selected.items():
        if not src.exists():
            continue
        dst = archive_path(src)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            # 已归档过时保持归档文件不变，只移除活跃源。
            src.unlink()
        else:
            shutil.move(str(src), str(dst))
        moved.append((src, dst, reason))

    report = ARCHIVE_ROOT / "README.md"
    if not moved and report.exists():
        print("清洗移动 0 篇；保留既有清洗记录")
        return

    lines = [
        "# 清洗移除记录",
        "",
        "这些文件已从活跃公众号源目录移出，因此不会再进入 `树林知识宇宙` 的解析结果。",
        "原文保留在本目录下，便于之后复核或恢复。",
        "",
        f"- 本次命中：{len(moved)} 篇",
        "",
        "| 原路径 | 归档路径 | 原因 |",
        "|---|---|---|",
    ]
    for src, dst, reason in moved:
        lines.append(f"| `{src}` | `{dst}` | {reason} |")
    if not moved:
        lines.append("| - | - | 无新增移动 |")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"清洗移动 {len(moved)} 篇")
    for src, dst, reason in moved:
        print(f"- {reason}: {src} -> {dst}")


if __name__ == "__main__":
    main()
