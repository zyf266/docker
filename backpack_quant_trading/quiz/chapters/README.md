# 新增章节题库

1. 在 `chapters/` 下新建 `xxx.py`，定义 `CHAPTER = ChapterSeed(...)`
2. 在 `registry.py` 的 `ALL_CHAPTERS` 中注册
3. 运行 `python -m backpack_quant_trading.quiz.seed_data` 或调用 API `POST /api/quiz/reseed`

示例结构见 `ai_agent_core.py`。
