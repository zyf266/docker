#!/usr/bin/env python3
"""
钉钉 Stream 机器人：群内「回复信号 + @机器人 + 评分」→ 拉 K 线 → DeepSeek 评分 → 群内回复。
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from backpack_quant_trading.core.env_loader import load_project_env

    load_project_env()
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dingtalk_score_bot")


def _allowed_sender(sender_staff_id: str, sender_id: str) -> bool:
    raw = os.getenv("DINGTALK_MANUAL_SCORE_ALLOWED_STAFF_IDS", "").strip()
    if not raw:
        return True
    allowed = {x.strip() for x in raw.split(",") if x.strip()}
    return (sender_staff_id or "") in allowed or (sender_id or "") in allowed


def _user_text(incoming, raw: dict) -> str:
    from backpack_quant_trading.core.dingtalk_manual_score import extract_user_text_from_raw

    text = extract_user_text_from_raw(raw)
    if text:
        return text
    try:
        parts = incoming.get_text_list()
        if parts:
            return " ".join(str(p) for p in parts if p).strip()
    except Exception:
        pass
    if getattr(incoming, "text", None) and getattr(incoming.text, "content", None):
        return str(incoming.text.content).strip()
    return ""


class ManualScoreBotHandler:
    def __init__(self, handler: "dingtalk_stream.ChatbotHandler"):
        self._handler = handler

    def _a_share_ai_feedback_work(self, incoming, raw: dict, user_text: str) -> None:
        from backpack_quant_trading.core.a_share_ai_agent_feedback import (
            handle_a_share_ai_dingtalk_feedback,
        )

        sender_staff = str(raw.get("senderStaffId") or getattr(incoming, "sender_staff_id", "") or "")
        sender_id = str(raw.get("senderId") or getattr(incoming, "sender_id", "") or "")

        if not _allowed_sender(sender_staff, sender_id):
            self._handler.reply_text("无反馈权限，请联系管理员配置白名单。", incoming)
            return

        try:
            reply_body, result = handle_a_share_ai_dingtalk_feedback(
                user_text, raw, sender_id=sender_staff or sender_id,
            )
        except Exception as exc:
            logger.exception("[A股AI自适应点评] 异常: %s", exc)
            try:
                self._handler.reply_text(f"点评记录失败：{exc}", incoming)
            except Exception:
                pass
            return

        try:
            self._handler.reply_markdown("A股AI点评已记录", reply_body, incoming)
        except Exception:
            try:
                self._handler.reply_text(reply_body, incoming)
            except Exception:
                pass

    def _feedback_work(self, incoming, raw: dict, user_text: str) -> None:
        from backpack_quant_trading.core.score_feedback import handle_dingtalk_feedback

        sender_staff = str(raw.get("senderStaffId") or getattr(incoming, "sender_staff_id", "") or "")
        sender_id = str(raw.get("senderId") or getattr(incoming, "sender_id", "") or "")

        if not _allowed_sender(sender_staff, sender_id):
            self._handler.reply_text("无反馈权限，请联系管理员配置白名单。", incoming)
            return

        try:
            reply_body, result = handle_dingtalk_feedback(
                user_text, raw, sender_id=sender_staff or sender_id,
            )
        except Exception as exc:
            logger.exception("[钉钉评分反馈] 异常: %s", exc)
            try:
                self._handler.reply_text(f"反馈记录失败：{exc}", incoming)
            except Exception:
                pass
            return

        try:
            self._handler.reply_markdown("评分反馈已记录", reply_body, incoming)
        except Exception:
            try:
                self._handler.reply_text(reply_body, incoming)
            except Exception:
                pass

    def _work(self, incoming, raw: dict, parsed: dict, user_text: str) -> None:
        from backpack_quant_trading.core.dingtalk_manual_score import score_manual_parsed

        sender_staff = str(raw.get("senderStaffId") or getattr(incoming, "sender_staff_id", "") or "")
        sender_id = str(raw.get("senderId") or getattr(incoming, "sender_id", "") or "")

        logger.info(
            "[钉钉手动评分] 执行 source=%s symbol=%s action=%s tf=%s user_text=%s",
            parsed.get("resolve_source"),
            parsed.get("symbol"),
            parsed.get("action"),
            parsed.get("timeframe"),
            user_text[:120],
        )

        if not _allowed_sender(sender_staff, sender_id):
            self._handler.reply_text("无手动评分权限，请联系管理员配置白名单。", incoming)
            return

        try:
            reply_body, result = score_manual_parsed(parsed, sender_id=sender_staff or sender_id)
        except Exception as exc:
            logger.exception("[钉钉手动评分] 评分线程异常: %s", exc)
            try:
                self._handler.reply_text(f"评分异常：{exc}", incoming)
            except Exception:
                pass
            return

        try:
            if result and result.get("reply_markdown"):
                title = str(result.get("reply_title") or "AI 信号评分")
                try:
                    from backpack_quant_trading.core.score_feedback import remember_last_signal_context

                    remember_last_signal_context(
                        symbol=str(result.get("symbol") or parsed.get("symbol") or ""),
                        timeframe=str(result.get("timeframe") or parsed.get("timeframe") or ""),
                        score=int(result["score"]) if result.get("score") is not None else None,
                        recommendation=str(result.get("recommendation") or ""),
                        source="manual_score",
                    )
                except Exception:
                    pass
                self._handler.reply_markdown(title, reply_body, incoming)
            else:
                self._handler.reply_text(reply_body, incoming)
        except Exception as exc:
            logger.exception("钉钉回复失败: %s", exc)
            try:
                self._handler.reply_text(f"评分结果发送失败：{exc}", incoming)
            except Exception:
                pass

    def _agent_work(self, incoming, raw: dict, user_text: str) -> None:
        from backpack_quant_trading.agents.dingtalk_bridge import handle_agent_text

        sender_staff = str(raw.get("senderStaffId") or getattr(incoming, "sender_staff_id", "") or "")
        sender_id = str(raw.get("senderId") or getattr(incoming, "sender_id", "") or "")
        if not _allowed_sender(sender_staff, sender_id):
            self._handler.reply_text("无 Agent 权限，请联系管理员配置白名单。", incoming)
            return
        try:
            result = handle_agent_text(user_text, staff_id=sender_staff or sender_id)
            body = str(result.get("markdown") or result.get("error") or "无输出")
            title = "Agent 分析" if result.get("ok") else "Agent 提示"
            try:
                from backpack_quant_trading.core.score_feedback import (
                    parse_score_card_from_reply,
                    remember_last_signal_context,
                )

                reports = result.get("reports") or []
                if reports:
                    r0 = reports[0]
                    raw0 = getattr(r0, "raw", None) or {}
                    tf = ""
                    if isinstance(raw0, dict):
                        tf = str(raw0.get("timeframe") or "")
                    remember_last_signal_context(
                        symbol=str(getattr(r0, "symbol", "") or ""),
                        timeframe=tf,
                        score=int(r0.score) if getattr(r0, "score", None) is not None else None,
                        recommendation=str(
                            (raw0.get("structured") or {}).get("recommendation")
                            if isinstance(raw0, dict)
                            else ""
                        ),
                        source="agent",
                    )
                else:
                    sym, tf, sc = parse_score_card_from_reply(body)
                    if sym:
                        remember_last_signal_context(
                            symbol=sym, timeframe=tf, score=sc, source="agent_md"
                        )
            except Exception:
                pass
            try:
                parts = result.get("markdown_parts")
                if isinstance(parts, list) and len(parts) > 1:
                    for idx, part in enumerate(parts):
                        part_title = title if idx == 0 else f"{title}（续{idx + 1}）"
                        try:
                            self._handler.reply_markdown(part_title, str(part), incoming)
                        except Exception:
                            self._handler.reply_text(str(part)[:3500], incoming)
                else:
                    self._handler.reply_markdown(title, body, incoming)
            except Exception:
                # 过长时分段文本兜底
                if len(body) > 1800:
                    for i in range(0, len(body), 1700):
                        self._handler.reply_text(body[i : i + 1700], incoming)
                else:
                    self._handler.reply_text(body[:1800], incoming)
        except Exception as exc:
            logger.exception("[钉钉Agent] 异常: %s", exc)
            try:
                self._handler.reply_text(f"Agent 异常：{exc}", incoming)
            except Exception:
                pass

    def handle(self, incoming, raw: dict) -> None:
        from backpack_quant_trading.core.dingtalk_manual_score import (
            is_manual_score_command,
            resolve_signal_for_scoring,
            _summarize_replied_msg,
        )
        from backpack_quant_trading.core.score_feedback import is_feedback_command
        from backpack_quant_trading.agents.dingtalk_bridge import (
            should_route_to_agent,
            usage_hint,
        )

        user_text = _user_text(incoming, raw)
        stream_mode = os.getenv("_DINGTALK_STREAM_MODE", "score")
        logger.info(
            "[钉钉手动评分] 入站 mode=%s text=%s isReply=%s",
            stream_mode,
            user_text[:160],
            raw.get("text"),
        )

        # A股 AI 自适应卡片点评（优先于通用评分反馈）
        try:
            from backpack_quant_trading.core.a_share_ai_agent_feedback import (
                should_handle_a_share_ai_feedback,
            )

            if should_handle_a_share_ai_feedback(user_text, raw):
                threading.Thread(
                    target=self._a_share_ai_feedback_work,
                    args=(incoming, raw, user_text),
                    daemon=True,
                    name="dingtalk-a-share-ai-feedback",
                ).start()
                try:
                    self._handler.reply_text("收到，正在记录你对 A股AI自适应 的点评…", incoming)
                except Exception:
                    pass
                return
        except Exception as exc:
            logger.warning("a_share_ai feedback route skip: %s", exc)

        # 多 Agent 编排优先（与旧评分并存；AGENT_ORCH_ENABLED=0 可回滚）
        if should_route_to_agent(user_text):
            from backpack_quant_trading.agents.dingtalk_bridge import is_steward_command

            threading.Thread(
                target=self._agent_work,
                args=(incoming, raw, user_text),
                daemon=True,
                name="dingtalk-agent-orch",
            ).start()
            try:
                host = (os.getenv("HOSTNAME") or "")[:12] or "ecs"
                if is_steward_command(user_text):
                    ack = f"收到，小管家处理中…〔{host}〕"
                else:
                    from backpack_quant_trading.agents.intent_router import classify_intent

                    intent = classify_intent(user_text)
                    if intent in ("meta", "chat"):
                        ack = f"收到，正在理解你的问题…〔{host}〕"
                    else:
                        ack = f"收到，分析师 Agent 处理中…〔{host}〕"
                self._handler.reply_text(ack, incoming)
            except Exception:
                pass
            return

        if is_feedback_command(user_text):
            threading.Thread(
                target=self._feedback_work,
                args=(incoming, raw, user_text),
                daemon=True,
                name="dingtalk-score-feedback",
            ).start()
            try:
                self._handler.reply_text("收到，正在记录你的评分纠正…", incoming)
            except Exception:
                pass
            return

        if not _legacy_manual_score_allowed(stream_mode):
            try:
                self._handler.reply_text(
                    usage_hint()
                    + "\n\n（本机器人专用于 Agent；旧「信号评分」请 @OpenClaw小钉）",
                    incoming,
                )
            except Exception:
                pass
            return

        if not is_manual_score_command(user_text):
            try:
                self._handler.reply_text(usage_hint(), incoming)
            except Exception:
                pass
            return

        parsed, hint = resolve_signal_for_scoring(user_text, raw)
        if not parsed or not parsed.get("symbol"):
            from backpack_quant_trading.core.dingtalk_signal_cache import (
                cache_signal_count,
                get_latest_cached_signal,
            )

            latest = get_latest_cached_signal(max_age_sec=7200)
            cache_n = cache_signal_count(max_age_sec=7200)
            quoted_body = ""
            text_block = raw.get("text")
            if isinstance(text_block, dict) and text_block.get("repliedMsg"):
                quoted_body = (_summarize_replied_msg(text_block["repliedMsg"]) or "")[:200]
            logger.warning(
                "[钉钉手动评分] 解析失败 text=%s hint=%s cache_n=%s latest=%s quoted=%s raw=%s",
                user_text,
                hint,
                cache_n,
                (latest or {}).get("symbol"),
                quoted_body,
                json.dumps(raw.get("text"), ensure_ascii=False)[:800],
            )
            try:
                if hint.startswith("ambiguous:"):
                    syms = hint.split(":", 1)[1].replace(",", "、")
                    tip = (
                        f"最近有多条相同策略的信号（{syms}），无法确定评哪条。\n"
                        f"请直接写品种，例如：@我 对 TAO 2h 买入 评分\n"
                        f"或带触发时间：@我 对 TAO 2026-07-06 10:00 评分"
                    )
                elif cache_n > 1:
                    tip = (
                        "最近有多条信号缓存，不能自动用「最新一条」。\n"
                        "请回复要评的那条信号，或写：@我 对 BTC 8h 卖出 评分"
                    )
                elif latest and latest.get("symbol"):
                    tip = (
                        "钉钉未传回信号正文（界面上能看到，API 里往往只有标题）。\n"
                        "请直接写：@我 对 BTC 8h 卖出 评分"
                    )
                else:
                    tip = (
                        "钉钉未传回信号正文，且服务器缓存里没有最近推送（需 tradingview_bot 推成功）。\n"
                        "请直接写：@我 对 BTC 8h 卖出 评分"
                    )
                self._handler.reply_text(tip, incoming)
            except Exception:
                pass
            return

        threading.Thread(
            target=self._work,
            args=(incoming, raw, parsed, user_text),
            daemon=True,
            name="dingtalk-manual-score",
        ).start()

        sym = parsed.get("symbol") or "?"
        tf = parsed.get("timeframe") or "默认周期"
        role = parsed.get("signal_role") or (
            "做多开仓" if (parsed.get("action") or "buy") == "buy" else "做空开仓"
        )
        src = parsed.get("resolve_source") or "?"
        logger.info("[钉钉手动评分] 开始评分 symbol=%s tf=%s role=%s via=%s", sym, tf, role, src)
        try:
            self._handler.reply_text(
                f"好的，正在评 {sym} {tf} {role}，请稍候…",
                incoming,
            )
        except Exception as exc:
            logger.warning("即时确认回复失败: %s", exc)


def _build_handler(logger_obj: logging.Logger):
    import dingtalk_stream
    from dingtalk_stream import AckMessage

    class _Handler(dingtalk_stream.ChatbotHandler):
        def __init__(self):
            super().__init__()
            self.logger = logger_obj
            self._manual = ManualScoreBotHandler(self)

        def _dispatch(self, callback: dingtalk_stream.CallbackMessage):
            raw = callback.data
            if isinstance(raw, str):
                raw = json.loads(raw)
            incoming = dingtalk_stream.ChatbotMessage.from_dict(raw)
            if not incoming.is_in_at_list:
                return AckMessage.STATUS_OK, "not_at"
            self._manual.handle(incoming, raw)
            return AckMessage.STATUS_OK, "OK"

        async def process(self, callback: dingtalk_stream.CallbackMessage):
            return self._dispatch(callback)

    return _Handler()


def _stream_credentials() -> tuple[str, str, str]:
    """优先用独立 Agent 机器人；未配置则回退旧评分机器人（同 Client 会抢 Stream）。"""
    agent_id = os.getenv("DINGTALK_AGENT_BOT_CLIENT_ID", "").strip()
    agent_sec = os.getenv("DINGTALK_AGENT_BOT_CLIENT_SECRET", "").strip()
    if agent_id and agent_sec:
        return agent_id, agent_sec, "agent"
    score_id = os.getenv("DINGTALK_SCORE_BOT_CLIENT_ID", "").strip()
    score_sec = os.getenv("DINGTALK_SCORE_BOT_CLIENT_SECRET", "").strip()
    return score_id, score_sec, "score"


def _legacy_manual_score_allowed(stream_mode: str) -> bool:
    """独立 Agent 机器人默认不走旧「AI 信号评分」，避免和 OpenClaw 小钉抢活。"""
    from backpack_quant_trading.core.dingtalk_manual_score import manual_dingtalk_score_enabled

    if not manual_dingtalk_score_enabled():
        return False
    if stream_mode == "agent":
        return os.getenv("DINGTALK_AGENT_ALLOW_LEGACY_SCORE", "0").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
    return True


def main() -> None:
    client_id, client_secret, stream_mode = _stream_credentials()
    if not client_id or not client_secret:
        logger.error(
            "缺少钉钉 Stream 凭证：请配置 DINGTALK_AGENT_BOT_CLIENT_ID/SECRET "
            "（推荐，独立 Agent 机器人）或 DINGTALK_SCORE_BOT_CLIENT_ID/SECRET"
        )
        sys.exit(1)

    # 旧评分机器人未开手动评分且也不是 Agent 专用凭证时才退出
    if stream_mode != "agent":
        from backpack_quant_trading.core.dingtalk_manual_score import manual_dingtalk_score_enabled

        if not manual_dingtalk_score_enabled():
            logger.error("DINGTALK_MANUAL_SCORE_ENABLED=0，已退出")
            sys.exit(1)

    try:
        import dingtalk_stream
    except ImportError:
        logger.error("请安装 dingtalk-stream: pip install dingtalk-stream")
        sys.exit(1)

    try:
        import logging as _log
        from backpack_quant_trading.config.settings import config
        from backpack_quant_trading.utils.logger import setup_logger
        from backpack_quant_trading.core.crypto_signal_scorer import log_score_runtime_config

        setup_logger(log_dir=config.log_dir, level=_log.INFO)
        log_score_runtime_config()
    except Exception as exc:
        logger.warning("评分日志初始化失败(继续): %s", exc)

    os.environ["_DINGTALK_STREAM_MODE"] = stream_mode
    credential = dingtalk_stream.Credential(client_id, client_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    client.register_callback_handler(
        dingtalk_stream.chatbot.ChatbotMessage.TOPIC,
        _build_handler(logger),
    )
    logger.info(
        "钉钉 Stream 启动 mode=%s client_id=%s… legacy_score=%s",
        stream_mode,
        client_id[:8],
        _legacy_manual_score_allowed(stream_mode),
    )
    client.start_forever()


if __name__ == "__main__":
    main()
