"""章节题库数据结构（新增章节只需实现一个模块并注册到 registry）"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

OptionTuple = Tuple[str, str, bool]  # key, text, is_correct
QuestionTuple = Tuple[str, str, str, str, List[OptionTuple]]  # category, type, text, explanation, options


@dataclass
class ChapterSeed:
    slug: str
    title: str
    description: str
    source_url: str
    sort_order: int = 0
    accent: str = "#3b82f6"
    categories: List[Tuple[str, str, int]] = field(default_factory=list)
    questions: List[QuestionTuple] = field(default_factory=list)
    coming_soon: bool = False
