"""钉钉自然语言意图：元问题 / FAQ，避免误入「手动评分」。"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def _plain(text: str) -> str:
    t = re.sub(r"@[^\s@　]+", " ", text or "", flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip()


def is_meta_question(text: str) -> bool:
    """系统说明 / 规则 / 权重 / 用法类问题（不是对某信号打分）。"""
    t = _plain(text)
    if not t:
        return False
    # 明确在问「权重/规则/怎么算」
    if any(
        k in t
        for k in (
            "评分权重",
            "打分权重",
            "权重是",
            "权重怎样",
            "权重如何",
            "怎么算分",
            "如何评分",
            "评分规则",
            "打分规则",
            "评分逻辑",
            "打分逻辑",
            "锚分",
            "breakdown",
            "硬规则",
            "hard_gate",
        )
    ):
        return True
    # 「…评分…怎样/什么/如何」且无具体开仓动作
    if "评分" in t or "打分" in t:
        if any(k in t for k in ("怎样", "怎么", "如何", "什么", "规则", "权重", "逻辑", "公式")):
            if not any(k in t for k in ("买入", "卖出", "开仓", "做多", "做空", "对 ")):
                return True
    # 通用用法
    if any(
        k in t
        for k in (
            "怎么用",
            "如何使用",
            "你会什么",
            "能做什么",
            "有哪些功能",
            "口令",
            "帮助",
            "help",
        )
    ):
        return True
    # 系统状态类
    if any(k in t for k in ("现在配置", "当前配置", "Agent 是什么", "小管家是什么")):
        return True
    return False


def classify_intent(text: str) -> str:
    """
    粗分意图：
      meta | analyze | score_signal | steward | exec | preference | review | chat | unknown
    """
    t = _plain(text)
    if not t:
        return "unknown"
    if is_meta_question(t):
        return "meta"
    try:
        from backpack_quant_trading.agents.execution_agent import parse_exec_command

        kind, _ = parse_exec_command(t)
        if kind:
            return "exec"
    except Exception:
        pass
    # 小管家关键词（避免循环 import dingtalk_bridge）
    if "小管家" in t or any(
        k in t
        for k in (
            "币种监视",
            "当前监视",
            "策略实例",
            "确认停止实例",
            "确认启动实例",
            "实例日志",
        )
    ):
        return "steward"
    try:
        from backpack_quant_trading.agents.memory import is_agent_preference_command

        if is_agent_preference_command(t):
            return "preference"
    except Exception:
        pass
    if t.startswith("复盘") or "复盘 " in t:
        return "review"
    if any(k in t for k in ("看看", "分析一下", "帮我看", "怎么看", "研判")):
        return "analyze"
    # 对某标的打分
    if any(k in t for k in ("买入", "卖出", "开仓")) and any(
        k in t for k in ("评分", "打分", "评一下")
    ):
        return "score_signal"
    if re.search(r"对\s+[A-Za-z0-9]{2,}.{0,20}(评分|打分)", t):
        return "score_signal"
    # 疑问句兜底 → 当 chat（Agent 简答）
    if any(k in t for k in ("吗", "呢", "？", "?", "为什么", "为何", "什么是", "是不是")):
        return "chat"
    return "unknown"


def detect_scoring_market(text: str) -> str:
    """从问句识别市场：us | crypto | a_share | all。"""
    t = _plain(text)
    if any(k in t for k in ("美股", "纳指", "标普", "标普500", "US股票", "us stock", "NVDA", "TSLA")):
        return "us"
    if any(k in t for k in ("A股", "沪深", "上证", "A 股", "a股")):
        return "a_share"
    if any(k in t for k in ("加密", "币圈", "合约", "BTC", "ETH", "crypto", "数字货币")):
        return "crypto"
    return "all"


def scoring_weights_crypto_markdown() -> str:
    """与 crypto_signal_scorer / compose_final_score 一致。"""
    return (
        "## 提醒 · 加密评分权重说明\n\n"
        "适用于加密「买入信号」AI 评分（DeepSeek + 本地锚分）。\n\n"
        "### 1. 最终分怎么合成\n"
        "- 本地先算 **锚分**（`compute_local_anchor_score` / `compute_local_buy_score`）与 **动能**（`rebound_strength`）\n"
        "- DeepSeek 给模型分后，综合分走 `compose_final_score`：\n"
        "  **≈ 0.50×动能 + 0.32×锚分 + 0.03×模型封顶参考 + 微调 − 0.50×执行惩罚**\n"
        "- 禁止脱离硬规则乱给 95+\n\n"
        "### 2. 锚分主要加减项\n"
        "- 结构/趋势、MACD 动能、量能、MTF（日线放量 / 1h·2h 金叉 / RSI 走强）\n"
        "- 强修复/反弹有额外抬升与下限保护\n\n"
        "### 3. 档位\n"
        "- ≥76 且可执行 → execute；52–75 → caution；&lt;52 或强制拒绝 → reject\n\n"
        "### 4. 硬规则优先\n"
        "- force_reject / force_caution_only / execute_eligible=false\n"
        "- 三层过滤未过、大周期死叉、明显缩量 → 通常只能 caution\n\n"
        "示例口令：`对 ETH 2h 买入 评分` / `分析一下 ETH 2h`\n"
    )


def scoring_weights_us_markdown() -> str:
    """与 us_stock_signal_scorer 一致。"""
    return (
        "## 提醒 · 美股评分权重说明\n\n"
        "适用于美股「买入/卖出信号」AI 评分（Massive K线 + 新闻 + DeepSeek + 本地锚分）。\n"
        "**与加密公式不同**：美股更强调消息面与可执行性惩罚。\n\n"
        "### 1. 最终分怎么合成\n"
        "- 本地锚分：`compute_local_buy_score(metrics)`\n"
        "- 动能刻度：`rebound_strength.strength_score`\n"
        "- 投影分 `_us_stock_project_score` → `compose_final_score`：\n"
        "  **≈ 0.50×动能 + 0.32×锚分 + 0.03×模型封顶参考 + 个股微调 − 0.50×execution_penalty**\n"
        "- 模型 raw 分会被限制在锚分/动能附近（约 +6 封顶），防虚高\n"
        "- 若仅允许 caution：综合分约 **0.25×模型分 + 0.75×锚分**，夹在 52–72\n\n"
        "### 2. 模型侧四维（score_breakdown）\n"
        "- structure 0–30 / momentum 0–25 / volume 0–20 / risk_penalty 0–25\n"
        "- **必须以 scoring_guidance.projected_score 为准**，勿盲跟模型 95+\n\n"
        "### 3. 美股专属：消息面\n"
        "- 必看 `recent_news`：业绩 beat/miss、指引、回购、诉讼/监管等\n"
        "- 利空（investigation/lawsuit/miss/下调等）→ 提高 execution_penalty（约 +8）\n"
        "- 利好（beat/上调/回购）→ 可减罚（约 −4）\n"
        "- 新闻与技术背离 → caution / reject；无新闻不臆造\n\n"
        "### 4. 执行惩罚（0–32，美股更严）\n"
        "- 极度缩量、贴压力位、RSI 过高、金叉缩量 → 加罚\n"
        "- 放量 / 多项 MTF → 可减罚\n\n"
        "### 5. 档位\n"
        "- ≥76 且 execute_eligible 且无重大利空 → execute\n"
        "- 52–75 或新闻中性 → caution\n"
        "- &lt;52 / force_reject / 重大利空 → reject\n"
        "- 强修复+放量常见 82–92；强反弹但缩量/贴压/RSI高常见 68–82 caution\n\n"
        "示例口令：`对 NVDA 4h 买入 评分` / `@美股分析师 NVDA` / `分析一下 SNDK 2h`\n"
    )


def scoring_weights_a_share_markdown() -> str:
    return (
        "## 提醒 · A股评分说明\n\n"
        "当前钉钉「信号评分卡」主路径是 **加密 / 美股** Webhook 评分；"
        "A股更多走 **@A股分析师** / `分析一下 茅台` 的 Agent 报告（技术面+基本面叙述），"
        "没有与美股完全同一套 `compose_final_score` 权重表。\n\n"
        "若要问美股权重请说：`现在美股的评分权重是怎样的`；"
        "加密请说：`现在加密评分权重是怎样的`。\n"
    )


def scoring_weights_markdown(market: str = "all") -> str:
    m = (market or "all").lower()
    if m in ("us", "us_stock"):
        return scoring_weights_us_markdown()
    if m in ("crypto", "加密"):
        return scoring_weights_crypto_markdown()
    if m in ("a_share", "a股"):
        return scoring_weights_a_share_markdown()
    # 未指明市场：两份都给，避免再答非所问
    return (
        "## 提醒 · 评分权重（请先看对应市场）\n\n"
        "你没有指定市场时，下面分别给出 **美股** 与 **加密**（二者公式不同）。\n\n"
        "---\n\n"
        + scoring_weights_us_markdown()
        + "\n---\n\n"
        + scoring_weights_crypto_markdown()
        + "\n下次可直接问：`现在美股的评分权重是怎样的` 或 `现在加密评分权重是怎样的`。\n"
    )


def usage_meta_markdown() -> str:
    return (
        "## 提醒 · 我能做什么\n\n"
        "【Agent】分析一下 ETH 2h / @美股分析师 NVDA / @A股分析师 茅台\n"
        "【周报】这周美股周报 / 这周A股周报\n"
        "【个股策略A】给我一份利通电子 策略A的报告\n"
        "【个股策略B】给我一份利通电子 策略B的报告\n"
        "【小管家】查看策略实例 / 当前监视状态 / 确认停止实例 &lt;id&gt;\n"
        "【问答】现在美股的评分权重是怎样的 / 现在加密评分权重 / 怎么用\n"
        "【旧评分】对 NVDA 4h 买入 评分 / 对 ETH 2h 买入 评分\n"
    )


def handle_meta_intent(text: str) -> Dict[str, Any]:
    t = _plain(text)
    if any(
        k in t
        for k in (
            "权重",
            "怎么算",
            "如何评分",
            "评分规则",
            "打分规则",
            "评分逻辑",
            "锚分",
            "硬规则",
        )
    ):
        market = detect_scoring_market(t)
        return {
            "ok": True,
            "intent": f"meta_scoring_weights_{market}",
            "market": market,
            "markdown": scoring_weights_markdown(market),
        }
    if any(k in t for k in ("怎么用", "如何使用", "你会什么", "能做什么", "帮助", "help", "口令")):
        return {"ok": True, "intent": "meta_usage", "markdown": usage_meta_markdown()}
    # 其它元问题：短 LLM，失败则给用法
    md = _llm_system_qa(t)
    if md:
        return {"ok": True, "intent": "meta_llm", "markdown": md}
    return {
        "ok": True,
        "intent": "meta_fallback",
        "markdown": usage_meta_markdown()
        + "\n\n（未识别到具体配置问题。可问：`现在美股的评分权重是怎样的`）",
    }


def _llm_system_qa(question: str) -> Optional[str]:
    """用 DeepSeek 简答系统问题；超时/失败返回 None。"""
    if os.getenv("AGENT_META_LLM", "1").strip().lower() in ("0", "false", "no", "off"):
        return None
    api_key = os.getenv("DEEPSEEK_API_KEY") or ""
    if not api_key:
        return None
    try:
        import json
        import requests

        model = os.getenv("DEEPSEEK_SCORE_MODEL", "deepseek-v4-flash")
        sys_p = (
            "你是沐龙量化钉钉助手。只根据已知能力回答，不要编造未实现功能。"
            "已知：多 Agent 分析（美股/A股/加密）、小管家监视、待确认下单、复盘。"
            "美股信号评分：0.50×动能+0.32×锚分+微调−0.50×惩罚，且必须结合新闻面。"
            "加密信号评分：同类 compose_final_score，但硬规则含三层过滤，无美股新闻维。"
            "用户若问美股，禁止用加密说明敷衍。回答用简体中文 Markdown，≤600 字。"
        )
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": sys_p},
                {"role": "user", "content": question},
            ],
            "temperature": 0.3,
            "thinking": {"type": "disabled"},
        }
        s = requests.Session()
        s.trust_env = False
        r = s.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=25,
        )
        data = r.json() if r.content else {}
        if r.status_code != 200:
            return None
        msg = ((data.get("choices") or [{}])[0].get("message") or {})
        text = str(msg.get("content") or "").strip()
        if text:
            return "## 提醒 · Agent 说明\n\n" + text[:2000]
    except Exception as exc:
        logger.debug("meta llm qa skipped: %s", exc)
    return None


def try_handle_intent(text: str, *, staff_id: str = "") -> Optional[Dict[str, Any]]:
    """若命中 meta/chat FAQ，直接返回结果；否则 None 交给后续编排。"""
    intent = classify_intent(text)
    if intent == "meta":
        return handle_meta_intent(text)
    if intent == "chat":
        md = _llm_system_qa(_plain(text))
        if md:
            return {"ok": True, "intent": "chat", "markdown": md}
        return {
            "ok": True,
            "intent": "chat",
            "markdown": usage_meta_markdown()
            + f"\n\n你刚说的是：`{_plain(text)[:120]}`。\n"
            "若要分析行情请带标的，例如：`分析一下 ETH 2h`；若问规则：`现在评分权重是怎样的`。",
        }
    return None
