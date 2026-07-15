"""AI Agent 考试题库 - 独立 SQLite 数据库"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

from backpack_quant_trading.config.settings import config

DB_PATH = config.data_dir / "ai_agent_quiz.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))
QuizBase = declarative_base()


def get_quiz_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_quiz_db() -> None:
    from backpack_quant_trading.quiz import models  # noqa: F401

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    QuizBase.metadata.create_all(bind=engine)
