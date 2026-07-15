"""章节注册表 — 新增章节：创建 chapters/xxx.py 并加入 ALL_CHAPTERS"""
from backpack_quant_trading.quiz.chapters.ai_agent_core import CHAPTER as AI_AGENT_CORE
from backpack_quant_trading.quiz.chapters.ai_agent_architecture import CHAPTER as AI_AGENT_ARCHITECTURE
from backpack_quant_trading.quiz.chapters.ai_agent_terminology import CHAPTER as AI_AGENT_TERMINOLOGY
from backpack_quant_trading.quiz.chapters.ai_agent_prompt_engineering import CHAPTER as PROMPT_ENGINEERING
from backpack_quant_trading.quiz.chapters.ai_agent_reasoning_planning import CHAPTER as REASONING_PLANNING
from backpack_quant_trading.quiz.chapters.ai_agent_vector_database import CHAPTER as VECTOR_DATABASE
from backpack_quant_trading.quiz.chapters.ai_agent_rag_retrieval import CHAPTER as RAG_RETRIEVAL
from backpack_quant_trading.quiz.chapters.ai_agent_context_engineering import CHAPTER as CONTEXT_ENGINEERING
from backpack_quant_trading.quiz.chapters.ai_agent_agent_architecture_patterns import CHAPTER as AGENT_ARCHITECTURE_PATTERNS
from backpack_quant_trading.quiz.chapters.types import ChapterSeed

AI_AGENT_WORKFLOW = ChapterSeed(
    slug="ai-agent-workflow",
    title="AI Agent 工作原理",
    description="Agent 从输入到输出的完整工作流程（待导入题库）。",
    source_url="https://www.runoob.com/ai-agent/ai-agent-workflow.html",
    sort_order=4,
    accent="#10b981",
    coming_soon=True,
)

ALL_CHAPTERS: list[ChapterSeed] = [
    AI_AGENT_CORE,
    AI_AGENT_TERMINOLOGY,
    AI_AGENT_ARCHITECTURE,
    AI_AGENT_WORKFLOW,
    PROMPT_ENGINEERING,
    REASONING_PLANNING,
    VECTOR_DATABASE,
    RAG_RETRIEVAL,
    CONTEXT_ENGINEERING,
    AGENT_ARCHITECTURE_PATTERNS,
]
