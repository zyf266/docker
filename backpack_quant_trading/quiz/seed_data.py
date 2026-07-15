"""题库种子数据：按章节注册表导入"""
from __future__ import annotations

from sqlalchemy import inspect

from backpack_quant_trading.quiz.chapters.registry import ALL_CHAPTERS
from backpack_quant_trading.quiz.chapters.types import ChapterSeed
from backpack_quant_trading.quiz.db import SessionLocal, engine, init_quiz_db
from backpack_quant_trading.quiz.db import QuizBase
from backpack_quant_trading.quiz.models import (
    QuizAttempt,
    QuizAttemptAnswer,
    QuizCategory,
    QuizChapter,
    QuizMeta,
    QuizOption,
    QuizQuestion,
)

SCHEMA_VERSION = "2"


def _get_schema_version(db) -> str | None:
    row = db.query(QuizMeta).filter(QuizMeta.key == "schema_version").first()
    return row.value if row else None


def _set_schema_version(db, version: str) -> None:
    row = db.query(QuizMeta).filter(QuizMeta.key == "schema_version").first()
    if row:
        row.value = version
    else:
        db.add(QuizMeta(key="schema_version", value=version))


def _needs_migration(db) -> bool:
    if _get_schema_version(db) == SCHEMA_VERSION:
        return False
    inspector = inspect(engine)
    if not inspector.has_table("quiz_chapters"):
        return True
    cols = {c["name"] for c in inspector.get_columns("quiz_categories")}
    return "chapter_id" not in cols


def _reset_schema() -> None:
    from backpack_quant_trading.quiz import models  # noqa: F401

    QuizBase.metadata.drop_all(bind=engine)
    QuizBase.metadata.create_all(bind=engine)


def _clear_all(db) -> None:
    db.query(QuizAttemptAnswer).delete()
    db.query(QuizAttempt).delete()
    db.query(QuizOption).delete()
    db.query(QuizQuestion).delete()
    db.query(QuizCategory).delete()
    db.query(QuizChapter).delete()
    db.query(QuizMeta).delete()
    db.commit()


def _chapter_question_count(db, chapter_id: int) -> int:
    cat_ids = [c.id for c in db.query(QuizCategory).filter(QuizCategory.chapter_id == chapter_id).all()]
    if not cat_ids:
        return 0
    return db.query(QuizQuestion).filter(QuizQuestion.category_id.in_(cat_ids)).count()


def _import_chapter_questions(db, chapter: ChapterSeed, ch: QuizChapter) -> None:
    cat_map: dict[str, QuizCategory] = {}
    for name, desc, order in chapter.categories:
        cat = QuizCategory(chapter_id=ch.id, name=name, description=desc, sort_order=order)
        db.add(cat)
        db.flush()
        cat_map[name] = cat

    for cat_name, qtype, text, explanation, options in chapter.questions:
        q = QuizQuestion(
            category_id=cat_map[cat_name].id,
            question_type=qtype,
            question_text=text,
            explanation=explanation,
            source_url=chapter.source_url,
        )
        db.add(q)
        db.flush()
        for key, opt_text, correct in options:
            db.add(
                QuizOption(
                    question_id=q.id,
                    option_key=key,
                    option_text=opt_text,
                    is_correct=correct,
                )
            )


def _import_chapter(db, chapter: ChapterSeed) -> None:
    ch = QuizChapter(
        slug=chapter.slug,
        title=chapter.title,
        description=chapter.description,
        source_url=chapter.source_url,
        accent=chapter.accent,
        sort_order=chapter.sort_order,
        coming_soon=chapter.coming_soon,
    )
    db.add(ch)
    db.flush()

    if chapter.coming_soon or not chapter.questions:
        return

    _import_chapter_questions(db, chapter, ch)


def _sync_registry_chapters(db) -> int:
    """增量同步注册表中的新章节或空章节，不清空已有题库。"""
    registry_slugs = {c.slug for c in ALL_CHAPTERS}
    for ch in db.query(QuizChapter).filter(~QuizChapter.slug.in_(registry_slugs)).all():
        db.query(QuizAttempt).filter(QuizAttempt.chapter_id == ch.id).update(
            {QuizAttempt.chapter_id: None, QuizAttempt.category_id: None},
            synchronize_session=False,
        )
        cat_ids = [c.id for c in db.query(QuizCategory).filter(QuizCategory.chapter_id == ch.id).all()]
        if cat_ids:
            qids = [q.id for q in db.query(QuizQuestion).filter(QuizQuestion.category_id.in_(cat_ids)).all()]
            if qids:
                db.query(QuizOption).filter(QuizOption.question_id.in_(qids)).delete(synchronize_session=False)
            db.query(QuizQuestion).filter(QuizQuestion.category_id.in_(cat_ids)).delete(synchronize_session=False)
            db.query(QuizCategory).filter(QuizCategory.chapter_id == ch.id).delete(synchronize_session=False)
        db.delete(ch)

    added_questions = 0
    for chapter in ALL_CHAPTERS:
        ch = db.query(QuizChapter).filter(QuizChapter.slug == chapter.slug).first()
        if not ch:
            before = db.query(QuizQuestion).count()
            _import_chapter(db, chapter)
            added_questions += db.query(QuizQuestion).count() - before
            continue

        ch.title = chapter.title
        ch.description = chapter.description
        ch.source_url = chapter.source_url
        ch.accent = chapter.accent
        ch.sort_order = chapter.sort_order
        ch.coming_soon = chapter.coming_soon

        if not chapter.coming_soon and chapter.questions and _chapter_question_count(db, ch.id) == 0:
            before = db.query(QuizQuestion).count()
            _import_chapter_questions(db, chapter, ch)
            added_questions += db.query(QuizQuestion).count() - before
    return added_questions


def seed_quiz_data(*, force: bool = False) -> int:
    init_quiz_db()
    db = SessionLocal()
    try:
        migrate = force or _needs_migration(db)
        if not migrate and db.query(QuizQuestion).count() > 0:
            _sync_registry_chapters(db)
            db.commit()
            return db.query(QuizQuestion).count()
    finally:
        db.close()

    if migrate:
        _reset_schema()
        db = SessionLocal()
        try:
            for chapter in ALL_CHAPTERS:
                _import_chapter(db, chapter)
            _set_schema_version(db, SCHEMA_VERSION)
            db.commit()
            return db.query(QuizQuestion).count()
        finally:
            db.close()

    db = SessionLocal()
    try:
        for chapter in ALL_CHAPTERS:
            _import_chapter(db, chapter)
        _set_schema_version(db, SCHEMA_VERSION)
        db.commit()
        return db.query(QuizQuestion).count()
    finally:
        db.close()


if __name__ == "__main__":
    count = seed_quiz_data(force=True)
    print(f"已导入 {count} 道题目")
