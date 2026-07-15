"""AI Agent 考试题库表结构"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backpack_quant_trading.quiz.db import QuizBase


class QuizMeta(QuizBase):
    __tablename__ = "quiz_meta"

    key = Column(String(64), primary_key=True)
    value = Column(String(255), nullable=False)


class QuizChapter(QuizBase):
    __tablename__ = "quiz_chapters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    source_url = Column(String(500), nullable=True)
    accent = Column(String(20), default="#3b82f6")
    sort_order = Column(Integer, default=0)
    coming_soon = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    categories = relationship("QuizCategory", back_populates="chapter", cascade="all, delete-orphan")


class QuizCategory(QuizBase):
    __tablename__ = "quiz_categories"
    __table_args__ = (UniqueConstraint("chapter_id", "name", name="uq_chapter_category_name"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    chapter_id = Column(Integer, ForeignKey("quiz_chapters.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)

    chapter = relationship("QuizChapter", back_populates="categories")
    questions = relationship("QuizQuestion", back_populates="category")


class QuizQuestion(QuizBase):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("quiz_categories.id"), nullable=False, index=True)
    question_type = Column(String(20), nullable=False, default="single")
    question_text = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    difficulty = Column(String(20), default="medium")
    source_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    category = relationship("QuizCategory", back_populates="questions")
    options = relationship("QuizOption", back_populates="question", cascade="all, delete-orphan")


class QuizOption(QuizBase):
    __tablename__ = "quiz_options"
    __table_args__ = (UniqueConstraint("question_id", "option_key", name="uq_question_option_key"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("quiz_questions.id"), nullable=False, index=True)
    option_key = Column(String(8), nullable=False)
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)

    question = relationship("QuizQuestion", back_populates="options")


class QuizAttempt(QuizBase):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String(100), nullable=True)
    chapter_id = Column(Integer, ForeignKey("quiz_chapters.id"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("quiz_categories.id"), nullable=True)
    score = Column(Integer, default=0)
    total = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.now)
    finished_at = Column(DateTime, nullable=True)

    answers = relationship("QuizAttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")


class QuizAttemptAnswer(QuizBase):
    __tablename__ = "quiz_attempt_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("quiz_questions.id"), nullable=False)
    selected_option_key = Column(String(8), nullable=False)
    is_correct = Column(Boolean, default=False)

    attempt = relationship("QuizAttempt", back_populates="answers")
