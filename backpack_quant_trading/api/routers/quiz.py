"""考试题库 API"""
from __future__ import annotations

import random
import threading
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backpack_quant_trading.api.deps import require_user
from backpack_quant_trading.quiz.db import get_quiz_db, init_quiz_db
from backpack_quant_trading.quiz.models import (
    QuizAttempt,
    QuizAttemptAnswer,
    QuizCategory,
    QuizChapter,
    QuizQuestion,
)
from backpack_quant_trading.quiz.seed_data import seed_quiz_data

router = APIRouter()

_SEEDED = False
_SEED_LOCK = threading.Lock()


def _ensure_seeded() -> None:
    global _SEEDED
    if _SEEDED:
        return
    with _SEED_LOCK:
        if _SEEDED:
            return
        init_quiz_db()
        seed_quiz_data()
        _SEEDED = True


class ChapterOut(BaseModel):
    id: int
    slug: str
    title: str
    description: Optional[str]
    source_url: Optional[str]
    accent: str
    sort_order: int
    category_count: int
    question_count: int
    coming_soon: bool


class CategoryOut(BaseModel):
    id: int
    chapter_id: int
    name: str
    description: Optional[str]
    question_count: int


class OptionOut(BaseModel):
    key: str
    text: str


class QuestionOut(BaseModel):
    id: int
    category_id: int
    category_name: str
    question_type: str
    question_text: str
    options: List[OptionOut]


class QuestionReviewOut(QuestionOut):
    selected_key: str
    correct_key: str
    selected_text: Optional[str] = None
    correct_text: Optional[str] = None
    is_correct: bool
    skipped: bool = False
    explanation: Optional[str]


class StartExamIn(BaseModel):
    chapter_id: int
    category_id: Optional[int] = None
    limit: int = Field(default=10, ge=0, description="抽题数量，0 表示全部")


class StartExamOut(BaseModel):
    attempt_id: int
    total: int
    questions: List[QuestionOut]


class SubmitAnswerIn(BaseModel):
    question_id: int
    selected_option_key: str


class SubmitExamIn(BaseModel):
    attempt_id: int
    answers: List[SubmitAnswerIn]


class SubmitExamOut(BaseModel):
    attempt_id: int
    score: int
    total: int
    accuracy: float
    reviews: List[QuestionReviewOut]


class CheckAnswerIn(BaseModel):
    question_id: int
    selected_option_key: str


class CheckAnswerOut(BaseModel):
    question_id: int
    selected_key: str
    correct_key: str
    selected_text: Optional[str] = None
    correct_text: Optional[str] = None
    is_correct: bool
    explanation: Optional[str]


class AttemptSummary(BaseModel):
    id: int
    user_name: Optional[str]
    chapter_title: Optional[str]
    category_name: Optional[str]
    score: int
    total: int
    accuracy: float
    finished_at: Optional[datetime]


def _question_to_out(q: QuizQuestion) -> QuestionOut:
    opts = sorted(q.options, key=lambda o: o.option_key)
    return QuestionOut(
        id=q.id,
        category_id=q.category_id,
        category_name=q.category.name if q.category else "",
        question_type=q.question_type,
        question_text=q.question_text,
        options=[OptionOut(key=o.option_key, text=o.option_text) for o in opts],
    )


def _get_chapter_or_404(db: Session, chapter_id: int) -> QuizChapter:
    ch = db.query(QuizChapter).filter(QuizChapter.id == chapter_id).first()
    if not ch:
        raise HTTPException(404, "章节不存在")
    return ch


@router.get("/hub")
def quiz_hub(_user=Depends(require_user)):
    _ensure_seeded()
    return {
        "title": "学习中心",
        "subtitle": "基于菜鸟教程 AI Agent 系列，按章节刷题复习",
        "source_site": "https://www.runoob.com/ai-agent/ai-agent-core.html",
    }


@router.get("/chapters", response_model=List[ChapterOut])
def list_chapters(db: Session = Depends(get_quiz_db), _user=Depends(require_user)):
    _ensure_seeded()
    chapters = db.query(QuizChapter).order_by(QuizChapter.sort_order).all()
    cat_counts = dict(
        db.query(QuizCategory.chapter_id, func.count(QuizCategory.id))
        .group_by(QuizCategory.chapter_id)
        .all()
    )
    q_counts = dict(
        db.query(QuizCategory.chapter_id, func.count(QuizQuestion.id))
        .outerjoin(QuizQuestion, QuizQuestion.category_id == QuizCategory.id)
        .group_by(QuizCategory.chapter_id)
        .all()
    )
    return [
        ChapterOut(
            id=ch.id,
            slug=ch.slug,
            title=ch.title,
            description=ch.description,
            source_url=ch.source_url,
            accent=ch.accent or "#3b82f6",
            sort_order=ch.sort_order or 0,
            category_count=int(cat_counts.get(ch.id, 0)),
            question_count=int(q_counts.get(ch.id, 0)),
            coming_soon=bool(ch.coming_soon),
        )
        for ch in chapters
    ]


@router.get("/chapters/{slug}", response_model=ChapterOut)
def get_chapter(slug: str, db: Session = Depends(get_quiz_db), _user=Depends(require_user)):
    _ensure_seeded()
    ch = db.query(QuizChapter).filter(QuizChapter.slug == slug).first()
    if not ch:
        raise HTTPException(404, "章节不存在")
    cats = db.query(QuizCategory).filter(QuizCategory.chapter_id == ch.id).all()
    cat_ids = [c.id for c in cats]
    q_count = db.query(QuizQuestion).filter(QuizQuestion.category_id.in_(cat_ids)).count() if cat_ids else 0
    return ChapterOut(
        id=ch.id,
        slug=ch.slug,
        title=ch.title,
        description=ch.description,
        source_url=ch.source_url,
        accent=ch.accent or "#3b82f6",
        sort_order=ch.sort_order or 0,
        category_count=len(cats),
        question_count=q_count,
        coming_soon=bool(ch.coming_soon),
    )


@router.get("/chapters/{slug}/categories", response_model=List[CategoryOut])
def list_chapter_categories(slug: str, db: Session = Depends(get_quiz_db), _user=Depends(require_user)):
    _ensure_seeded()
    ch = db.query(QuizChapter).filter(QuizChapter.slug == slug).first()
    if not ch:
        raise HTTPException(404, "章节不存在")
    cats = db.query(QuizCategory).filter(QuizCategory.chapter_id == ch.id).order_by(QuizCategory.sort_order).all()
    cat_ids = [c.id for c in cats]
    q_counts = {}
    if cat_ids:
        q_counts = dict(
            db.query(QuizQuestion.category_id, func.count(QuizQuestion.id))
            .filter(QuizQuestion.category_id.in_(cat_ids))
            .group_by(QuizQuestion.category_id)
            .all()
        )
    return [
        CategoryOut(
            id=c.id,
            chapter_id=c.chapter_id,
            name=c.name,
            description=c.description,
            question_count=int(q_counts.get(c.id, 0)),
        )
        for c in cats
    ]


@router.post("/start", response_model=StartExamOut)
def start_exam(
    body: StartExamIn,
    db: Session = Depends(get_quiz_db),
    user=Depends(require_user),
):
    _ensure_seeded()
    chapter = _get_chapter_or_404(db, body.chapter_id)
    if chapter.coming_soon:
        raise HTTPException(400, "该章节题库尚未导入")

    q = (
        db.query(QuizQuestion)
        .join(QuizCategory, QuizQuestion.category_id == QuizCategory.id)
        .filter(QuizCategory.chapter_id == body.chapter_id)
        .options(joinedload(QuizQuestion.category), joinedload(QuizQuestion.options))
    )
    if body.category_id:
        q = q.filter(QuizQuestion.category_id == body.category_id)
    questions = q.all()
    if not questions:
        raise HTTPException(404, "该分类暂无题目")

    picked = (
        questions
        if body.limit == 0 or len(questions) <= body.limit
        else random.sample(questions, body.limit)
    )
    random.shuffle(picked)

    attempt = QuizAttempt(
        user_name=user.get("username"),
        chapter_id=body.chapter_id,
        category_id=body.category_id,
        total=len(picked),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return StartExamOut(
        attempt_id=attempt.id,
        total=len(picked),
        questions=[_question_to_out(x) for x in picked],
    )


@router.post("/check-answer", response_model=CheckAnswerOut)
def check_answer(
    body: CheckAnswerIn,
    db: Session = Depends(get_quiz_db),
    _user=Depends(require_user),
):
    """练习模式：选题后立即返回对错与解析"""
    _ensure_seeded()
    selected = (body.selected_option_key or "").strip().upper()
    if not selected:
        raise HTTPException(400, "请先选择答案")

    q = (
        db.query(QuizQuestion)
        .options(joinedload(QuizQuestion.options))
        .filter(QuizQuestion.id == body.question_id)
        .first()
    )
    if not q:
        raise HTTPException(404, "题目不存在")

    correct_opt = next((o for o in q.options if o.is_correct), None)
    correct_key = correct_opt.option_key if correct_opt else ""
    correct_text = correct_opt.option_text if correct_opt else ""
    sel_opt = next((o for o in q.options if o.option_key == selected), None)
    selected_text = sel_opt.option_text if sel_opt else selected

    return CheckAnswerOut(
        question_id=q.id,
        selected_key=selected,
        correct_key=correct_key,
        selected_text=selected_text,
        correct_text=correct_text,
        is_correct=selected == correct_key,
        explanation=q.explanation,
    )


@router.post("/submit", response_model=SubmitExamOut)
def submit_exam(
    body: SubmitExamIn,
    db: Session = Depends(get_quiz_db),
    _user=Depends(require_user),
):
    _ensure_seeded()
    attempt = db.query(QuizAttempt).filter(QuizAttempt.id == body.attempt_id).first()
    if not attempt:
        raise HTTPException(404, "考试记录不存在")
    if attempt.finished_at:
        raise HTTPException(400, "该次考试已提交")

    answer_map = {a.question_id: a.selected_option_key.strip().upper() for a in body.answers}
    qids = list(answer_map.keys())
    if not qids:
        raise HTTPException(400, "没有可提交的题目")

    questions = (
        db.query(QuizQuestion)
        .options(joinedload(QuizQuestion.category), joinedload(QuizQuestion.options))
        .filter(QuizQuestion.id.in_(qids))
        .all()
    )
    q_by_id = {q.id: q for q in questions}

    score = 0
    reviews: List[QuestionReviewOut] = []
    # 按客户端题目顺序返回解析
    for qid in qids:
        selected = answer_map.get(qid, "")
        q = q_by_id.get(qid)
        if not q:
            continue
        correct_opt = next((o for o in q.options if o.is_correct), None)
        correct_key = correct_opt.option_key if correct_opt else ""
        correct_text = correct_opt.option_text if correct_opt else ""
        skipped = not selected
        selected_text = None
        if selected:
            sel_opt = next((o for o in q.options if o.option_key == selected), None)
            selected_text = sel_opt.option_text if sel_opt else selected
        is_correct = (not skipped) and selected == correct_key
        if is_correct:
            score += 1
        db.add(
            QuizAttemptAnswer(
                attempt_id=attempt.id,
                question_id=qid,
                selected_option_key=selected or "-",
                is_correct=is_correct,
            )
        )
        reviews.append(
            QuestionReviewOut(
                **_question_to_out(q).model_dump(),
                selected_key=selected,
                correct_key=correct_key,
                selected_text=selected_text,
                correct_text=correct_text,
                is_correct=is_correct,
                skipped=skipped,
                explanation=q.explanation,
            )
        )

    attempt.score = score
    attempt.total = len(reviews)
    attempt.finished_at = datetime.now()
    db.commit()

    total = attempt.total or 1
    return SubmitExamOut(
        attempt_id=attempt.id,
        score=score,
        total=attempt.total,
        accuracy=round(score / total * 100, 1),
        reviews=reviews,
    )


@router.get("/attempts", response_model=List[AttemptSummary])
def list_attempts(
    chapter_id: Annotated[Optional[int], Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_quiz_db),
    user=Depends(require_user),
):
    _ensure_seeded()
    username = user.get("username")
    q = db.query(QuizAttempt).filter(QuizAttempt.finished_at.isnot(None))
    if username:
        q = q.filter(QuizAttempt.user_name == username)
    if chapter_id is not None:
        q = q.filter(QuizAttempt.chapter_id == chapter_id)
    attempts = q.order_by(QuizAttempt.finished_at.desc()).limit(limit).all()

    result = []
    for a in attempts:
        ch_title = None
        cat_name = None
        if a.chapter_id:
            ch = db.query(QuizChapter).filter(QuizChapter.id == a.chapter_id).first()
            ch_title = ch.title if ch else None
        if a.category_id:
            cat = db.query(QuizCategory).filter(QuizCategory.id == a.category_id).first()
            cat_name = cat.name if cat else None
        total = a.total or 1
        result.append(
            AttemptSummary(
                id=a.id,
                user_name=a.user_name,
                chapter_title=ch_title,
                category_name=cat_name,
                score=a.score,
                total=a.total,
                accuracy=round((a.score or 0) / total * 100, 1),
                finished_at=a.finished_at,
            )
        )
    return result


@router.post("/reseed")
def reseed_questions(_user=Depends(require_user)):
    global _SEEDED
    count = seed_quiz_data(force=True)
    _SEEDED = True
    return {"ok": True, "question_count": count}
