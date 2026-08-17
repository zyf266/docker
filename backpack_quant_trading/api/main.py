"""
FastAPI 量化交易后端
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backpack_quant_trading.core.env_loader import load_project_env

load_project_env()

# 尽早固定日志为北京时间（覆盖 Formatter.formatTime）
from backpack_quant_trading.utils.logger import setup_logger  # noqa: E402
from backpack_quant_trading.config.settings import config as _app_config  # noqa: E402

setup_logger(log_dir=_app_config.log_dir, level=__import__("logging").INFO)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="沐龙量化交易平台 API",
    description="实盘交易、策略回测、AI 实验室、OKX Agent 集成、网格与监控",
    version="1.0.0",
)

# CORS - 允许 Vue 前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:3000", "http://localhost:8050", "http://localhost:8051",
        "http://127.0.0.1:8050", "http://127.0.0.1:8051",
        "http://0.0.0.0:8050", "http://0.0.0.0:8051",
        "http://47.110.57.118:8050", "http://47.110.57.118:8051",
        "http://172.26.30.20:8050", "http://172.26.30.20:8051",
        "http://39.106.143.222:8100", "http://39.106.143.222:8050",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（显式导入 router，避免模块对象缺少 router 属性导致启动失败）
from backpack_quant_trading.api.routers.auth import router as auth_router
from backpack_quant_trading.api.routers.trading import router as trading_router
from backpack_quant_trading.api.routers.grid import router as grid_router
from backpack_quant_trading.api.routers.currency_monitor import router as currency_monitor_router
from backpack_quant_trading.api.routers.macd_pattern_monitor import router as macd_pattern_monitor_router
from backpack_quant_trading.api.routers.dashboard import router as dashboard_router
from backpack_quant_trading.api.routers.ai_lab import router as ai_lab_router
from backpack_quant_trading.api.routers.stock_ai import router as stock_ai_router
from backpack_quant_trading.api.routers.strategy import router as strategy_router
from backpack_quant_trading.api.routers.okx_agent import router as okx_agent_router
from backpack_quant_trading.api.routers.okx_console import router as okx_console_router
from backpack_quant_trading.api.routers.us_weekly_report import router as us_weekly_report_router
from backpack_quant_trading.api.routers.stock_news_alert import router as stock_news_alert_router
from backpack_quant_trading.api.routers.polymarket_alert import router as polymarket_alert_router
from backpack_quant_trading.api.routers.ai_stock_hub import router as ai_stock_hub_router
from backpack_quant_trading.api.routers.crypto_signal_hub import router as crypto_signal_hub_router
from backpack_quant_trading.api.routers.quiz import router as quiz_router

try:
    from backpack_quant_trading.api.routers.avatar import router as avatar_router
except Exception:  # pragma: no cover
    avatar_router = None

app.include_router(auth_router, prefix="/api/auth", tags=["认证"])
app.include_router(trading_router, prefix="/api/trading", tags=["实盘交易"])
app.include_router(grid_router, prefix="/api/grid", tags=["网格交易"])
app.include_router(currency_monitor_router, prefix="/api/currency-monitor", tags=["币种监视"])
app.include_router(macd_pattern_monitor_router, prefix="/api/macd-pattern-monitor", tags=["MACD形态监控"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["数据大屏"])
app.include_router(ai_lab_router, prefix="/api/ai-lab", tags=["AI实验室"])
app.include_router(stock_ai_router, prefix="/api/stock-ai", tags=["A股AI选股"])
app.include_router(strategy_router, prefix="/api/strategy", tags=["量化策略"])
app.include_router(okx_agent_router, prefix="/api/okx-agent", tags=["OKX AI 交易"])
app.include_router(okx_console_router, prefix="/api/okx-console", tags=["OKX 控制台"])
app.include_router(us_weekly_report_router, prefix="/api/us-weekly-report", tags=["泡沫周报"])
app.include_router(stock_news_alert_router, prefix="/api/stock-news-alert", tags=["自选快讯"])
app.include_router(polymarket_alert_router, prefix="/api/polymarket-alert", tags=["Polymarket概率"])
app.include_router(ai_stock_hub_router, prefix="/api/ai-stock-hub", tags=["AI选股卡片"])
app.include_router(crypto_signal_hub_router, prefix="/api/crypto-signal-hub", tags=["加密信号评分"])
app.include_router(quiz_router, prefix="/api/quiz", tags=["AI Agent 考试"])
if avatar_router is not None:
    app.include_router(avatar_router, prefix="/api/avatar", tags=["小沫数字人"])

# 可选：旧镜像可能缺这些文件，不能拖垮整站
try:
    from backpack_quant_trading.api.routers.steward import router as steward_router
    app.include_router(steward_router, prefix="/api/steward", tags=["小管家"])
except Exception as _exc:
    import logging as _logging
    _logging.getLogger(__name__).warning("steward router 未加载: %s", _exc)

try:
    from backpack_quant_trading.api.routers.agent_memory import router as agent_memory_router
    app.include_router(agent_memory_router, prefix="/api/agent-memory", tags=["Agent记忆"])
except Exception as _exc:
    import logging as _logging
    _logging.getLogger(__name__).warning("agent_memory router 未加载: %s", _exc)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "backpack-quant-api"}


# ──────────────────────────────────────────────────────────
# 每日凌晨2点 自动同步 HYPE 4H / ETH 2H K 线
# ──────────────────────────────────────────────────────────
import asyncio as _asyncio
import logging as _sched_logging
from datetime import datetime as _dt, timedelta as _td
from zoneinfo import ZoneInfo

_sched_logger = _sched_logging.getLogger("kline_scheduler")
_CN_TZ = ZoneInfo("Asia/Shanghai")
_PRICE_SYNC_HOUR = 5
# 多 worker 时仅持锁进程跑定时任务，避免外部 API / 内存翻倍
_SCHEDULER_LOCK_FD = None


def _try_acquire_scheduler_lock() -> bool:
    """非阻塞文件锁；Windows 开发环境无 fcntl 时默认允许启动调度。"""
    global _SCHEDULER_LOCK_FD
    if os.getenv("DISABLE_BACKGROUND_SCHEDULER", "").strip().lower() in ("1", "true", "yes"):
        return False
    lock_path = os.getenv("SCHEDULER_LOCK_PATH", "/tmp/backpack-api-scheduler.lock")
    try:
        import fcntl
    except ImportError:
        return True
    try:
        fd = open(lock_path, "a+", encoding="utf-8")
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.seek(0)
        fd.truncate()
        fd.write(f"pid={os.getpid()}\n")
        fd.flush()
        _SCHEDULER_LOCK_FD = fd
        return True
    except (BlockingIOError, OSError) as exc:
        _sched_logger.info("[调度] 本进程不持锁，跳过后台任务: %s", exc)
        return False


def _cn_now() -> _dt:
    return _dt.now(_CN_TZ)


def _today_cn_price_sync_at() -> _dt:
    now = _cn_now()
    return now.replace(hour=_PRICE_SYNC_HOUR, minute=0, second=0, microsecond=0)


def _parse_cache_updated_at(raw) -> _dt | None:
    if not raw:
        return None
    try:
        return _dt.strptime(str(raw), "%Y-%m-%d %H:%M:%S").replace(tzinfo=_CN_TZ)
    except Exception:
        return None


def _research_price_cache_stale_hours(cache: dict, *, max_age_hours: float = 20.0) -> bool:
    """缓存缺失或超过 max_age_hours 视为过期，需重新拉价。"""
    updated = _parse_cache_updated_at(cache.get("updated_at"))
    if not updated:
        return True
    return (_cn_now() - updated).total_seconds() > max_age_hours * 3600


def _missed_today_cn_price_sync(cache: dict) -> bool:
    """北京时间已过今日 5:00，但缓存更新时间仍早于今日 5:00 → 今日定时任务未成功。"""
    now = _cn_now()
    today_5 = _today_cn_price_sync_at()
    if now < today_5:
        return False
    updated = _parse_cache_updated_at(cache.get("updated_at"))
    if not updated:
        return True
    return updated < today_5


async def _run_research_price_sync(reason: str) -> None:
    from backpack_quant_trading.core.research_card_prices import refresh_research_prices_task

    try:
        res = await _asyncio.to_thread(refresh_research_prices_task)
        _sched_logger.info(
            "[研究卡片价格] %s: ok=%s 成功=%s/%s updated=%s",
            reason,
            res.get("ok"),
            res.get("ok_count"),
            res.get("count"),
            res.get("updated_at"),
        )
    except Exception as exc:
        _sched_logger.error("[研究卡片价格] %s 失败: %s", reason, exc)


@app.on_event("startup")
async def start_kline_scheduler():
    from backpack_quant_trading.core.stock_news_alert import try_restore_from_disk
    from backpack_quant_trading.core.polymarket_alert import try_restore_from_disk as try_restore_polymarket

    # 磁盘状态恢复：每个 worker 都需要（内存内状态）
    try_restore_from_disk()
    try_restore_polymarket()
    try:
        from backpack_quant_trading.core.binance_monitor import (
            restore_currency_monitor_from_db_if_needed,
        )

        restore_currency_monitor_from_db_if_needed()
    except Exception as exc:
        _sched_logger.warning("[币种监视] 启动恢复失败: %s", exc)

    try:
        from backpack_quant_trading.core.spot_net_inflow_monitor import (
            restore_spot_net_inflow_from_db_if_needed,
        )

        restore_spot_net_inflow_from_db_if_needed()
    except Exception as exc:
        _sched_logger.warning("[现货净流入] 启动恢复失败: %s", exc)

    try:
        from backpack_quant_trading.core.a_share_monitor import (
            restore_a_share_monitor_from_db_if_needed,
        )

        restore_a_share_monitor_from_db_if_needed()
    except Exception as exc:
        _sched_logger.warning("[A股监控] 启动恢复失败: %s", exc)

    # 轻量自愈（启动一次）
    try:
        from backpack_quant_trading.agents.self_heal import check_and_heal_monitors

        heal = check_and_heal_monitors()
        _sched_logger.info("[自愈] startup: %s", heal)
    except Exception as exc:
        _sched_logger.warning("[自愈] startup 失败: %s", exc)

    # 实盘策略 ERROR → 钉钉运维群
    try:
        from backpack_quant_trading.core.live_trade_dingtalk_alert import (
            install_live_trade_error_handlers,
        )

        install_live_trade_error_handlers()
    except Exception as exc:
        _sched_logger.warning("[实盘报错钉钉] 安装失败: %s", exc)

    if not _try_acquire_scheduler_lock():
        _sched_logger.info("[调度] 跳过后台定时任务（由其他 worker 负责）")
        return

    _sched_logger.info("[调度] 本进程持锁，启动后台定时任务")
    # 恢复 DB 中 running 的实盘策略实例（RSA 解密密钥）
    try:
        from backpack_quant_trading.api.routers.trading import resume_running_live_instances
        stats = await _asyncio.to_thread(resume_running_live_instances)
        _sched_logger.info("[实例恢复] %s", stats)
    except Exception as exc:
        _sched_logger.error("[实例恢复] 失败: %s", exc)

    _asyncio.create_task(_kline_sync_loop())
    _asyncio.create_task(_weekly_bubble_analyze_loop())
    _asyncio.create_task(_bootstrap_research_prices())
    _asyncio.create_task(_daily_research_price_sync_loop())
    _asyncio.create_task(_hourly_uptrend_scan_loop())
    _asyncio.create_task(_bootstrap_a_share_mtm())
    _asyncio.create_task(_daily_a_share_mtm_loop())
    _asyncio.create_task(_daily_agent_patrol_loop())
    _asyncio.create_task(_auto_review_loop())


async def _secs_until_next_hour(hour: int) -> float:
    now = _dt.now()
    target = now.replace(hour=int(hour) % 24, minute=0, second=0, microsecond=0)
    if target <= now:
        target += _td(days=1)
    return max(1.0, (target - now).total_seconds())


async def _daily_agent_patrol_loop():
    """每天 AGENT_PATROL_HOUR（默认 9）北京时间跑日巡检并钉钉推送。"""
    import os as _os

    while True:
        try:
            hour = int(_os.getenv("AGENT_PATROL_HOUR", "9") or 9)
        except Exception:
            hour = 9
        wait = await _secs_until_next_hour(hour)
        _sched_logger.info("[Agent巡检] 下次约 %.1fh 后（%02d:00）", wait / 3600, hour)
        await _asyncio.sleep(wait)
        try:
            from backpack_quant_trading.agents.patrol_agent import run_daily_patrol

            res = await _asyncio.to_thread(run_daily_patrol, push=True)
            _sched_logger.info(
                "[Agent巡检] ok=%s pushed=%s skipped=%s",
                res.get("ok"),
                res.get("pushed"),
                res.get("skipped"),
            )
        except Exception as exc:
            _sched_logger.error("[Agent巡检] 失败: %s", exc)


async def _auto_review_loop():
    """每天 20:00 自动复盘到期报告并钉钉推送。"""
    import os as _os

    while True:
        wait = await _secs_until_next_hour(20)
        _sched_logger.info("[自动复盘] 下次约 %.1fh 后（20:00）", wait / 3600)
        await _asyncio.sleep(wait)
        enabled = _os.getenv("AGENT_AUTO_REVIEW_ENABLED", "1").strip().lower() not in (
            "0",
            "false",
            "no",
            "off",
        )
        if not enabled:
            _sched_logger.info("[自动复盘] 已关闭 AGENT_AUTO_REVIEW_ENABLED=0")
            continue
        try:
            from backpack_quant_trading.agents.review_agent import auto_review_due_reports
            from backpack_quant_trading.agents.dingtalk_push import push_dingtalk_markdown

            res = await _asyncio.to_thread(auto_review_due_reports)
            md = res.get("markdown") or ""
            n = int(res.get("reviewed") or 0)
            _sched_logger.info("[自动复盘] reviewed=%s", n)
            if n > 0 and md:
                ok, msg = await _asyncio.to_thread(
                    lambda: push_dingtalk_markdown(
                        "Agent 自动复盘", md, use_ops_webhook=True
                    )
                )
                _sched_logger.info("[自动复盘] 钉钉 pushed=%s %s", ok, msg)
        except Exception as exc:
            _sched_logger.error("[自动复盘] 失败: %s", exc)


async def _weekly_bubble_analyze_loop():
    """每周六 10:00（中国时间）自动生成美股 + A股泡沫阶段周报。"""
    import os as _os
    from backpack_quant_trading.api.routers.us_weekly_report import run_weekly_analyze_task
    # 服务进程用本机时间作为「中国时间」近似（你的服务器若已是 Asia/Shanghai 即可）
    while True:
        now = _dt.now()
        # 计算下一个周六 10:00：weekday() 周一=0、周六=5
        days_ahead = (5 - now.weekday()) % 7
        target = now.replace(hour=10, minute=0, second=0, microsecond=0) + _td(days=days_ahead)
        if target <= now:
            target += _td(days=7)
        wait_secs = (target - now).total_seconds()
        _sched_logger.info(
            f"[泡沫监测] 下次自动分析：{target.strftime('%Y-%m-%d %H:%M:%S')}（{wait_secs/3600:.1f}h 后）"
        )
        await _asyncio.sleep(wait_secs)
        ding_on = _os.getenv("AGENT_WEEKLY_DINGTALK", "1").strip().lower() not in (
            "0",
            "false",
            "no",
            "off",
        )
        for mkt in ("us", "a_share"):
            try:
                res = await _asyncio.to_thread(run_weekly_analyze_task, mkt)
                ok = res.get("ok") if isinstance(res, dict) else False
                _sched_logger.info(f"[泡沫监测] 周六自动分析完成 market={mkt}: ok={ok}")
                if ok and ding_on:
                    label = "美股" if mkt == "us" else "A股"
                    body = (
                        (res.get("markdown") or res.get("summary") or "")
                        if isinstance(res, dict)
                        else ""
                    )
                    if not body and isinstance(res, dict):
                        report = res.get("report") or {}
                        if isinstance(report, dict):
                            body = report.get("summary") or report.get("one_liner") or ""
                    body = (body or f"{label}泡沫周报已生成，请打开网页查看。")[:3500]
                    from backpack_quant_trading.agents.dingtalk_push import push_dingtalk_markdown

                    pok, pmsg = await _asyncio.to_thread(
                        push_dingtalk_markdown,
                        f"{label}泡沫周报",
                        f"## 提醒 · {label}/泡沫周报\n\n{body}",
                    )
                    _sched_logger.info(
                        "[泡沫监测] 钉钉推送 market=%s ok=%s %s", mkt, pok, pmsg
                    )
            except Exception as exc:
                _sched_logger.error(f"[泡沫监测] 周六自动分析失败 market={mkt}: {exc}")


async def _hourly_uptrend_scan_loop():
    """上涨趋势扫描：每 1 小时自动刷新 HL 成交额 Top50 扫描缓存。"""
    from backpack_quant_trading.api.routers.crypto_signal_hub import (
        UPTREND_SCAN_INTERVAL_SEC,
        run_scheduled_uptrend_scan_sync,
    )

    interval = max(300, int(UPTREND_SCAN_INTERVAL_SEC or 3600))
    # 启动后稍等，避免与其它初始化任务抢网络
    await _asyncio.sleep(90)
    while True:
        try:
            res = await _asyncio.to_thread(run_scheduled_uptrend_scan_sync)
            if res.get("skipped"):
                _sched_logger.info("[上涨扫描] 跳过：%s", res.get("message"))
            elif res.get("ok"):
                _sched_logger.info(
                    "[上涨扫描] 定时完成: %s · 通过 %s 个 · 耗时 %ss",
                    res.get("scanned_at"),
                    res.get("uptrend_count"),
                    res.get("duration_sec"),
                )
            else:
                _sched_logger.warning("[上涨扫描] 定时失败: %s", res.get("error") or res)
        except Exception as exc:
            _sched_logger.error("[上涨扫描] 定时异常: %s", exc)
        _sched_logger.info(f"[上涨扫描] 下次扫描约 {interval/3600:.1f}h 后")
        await _asyncio.sleep(interval)


async def _kline_sync_loop():
    """每 4 小时 + 启动时立即同步：加密 HL + 美股 Massive K 线。"""
    from backpack_quant_trading.api.routers.strategy import run_scheduled_kline_sync

    interval = 4 * 3600
    while True:
        try:
            res = await _asyncio.to_thread(run_scheduled_kline_sync)
            _sched_logger.info("[K线定时] 同步完成: %s", res)
        except Exception as exc:
            _sched_logger.error("[K线定时] 同步失败: %s", exc)
        _sched_logger.info(f"[K线定时] 下次同步约 {interval/3600:.0f}h 后")
        await _asyncio.sleep(interval)


async def _bootstrap_research_prices():
    """启动时：缓存过期或错过今日 5:00 定时更新则立即补拉。"""
    from backpack_quant_trading.core.research_card_prices import load_price_cache

    cache = load_price_cache()
    if _missed_today_cn_price_sync(cache):
        _sched_logger.info(
            "[研究卡片价格] 启动补拉: 今日 %02d:00 定时更新尚未完成（缓存 %s）",
            _PRICE_SYNC_HOUR,
            cache.get("updated_at"),
        )
        await _run_research_price_sync("启动补拉")
        return
    if _research_price_cache_stale_hours(cache):
        _sched_logger.info("[研究卡片价格] 启动补拉: 缓存过期(%s)", cache.get("updated_at"))
        await _run_research_price_sync("启动补拉(过期)")
        return
    _sched_logger.info("[研究卡片价格] 使用有效缓存: %s", cache.get("updated_at"))


async def _daily_research_price_sync_loop():
    """每天北京时间 5:00 更新 AI 选股卡片现价；若启动时已错过当日 5:00 会先补跑。"""
    from backpack_quant_trading.core.research_card_prices import load_price_cache

    while True:
        cache = load_price_cache()
        if _missed_today_cn_price_sync(cache):
            await _run_research_price_sync("今日定时补跑")

        now = _cn_now()
        target = _today_cn_price_sync_at()
        if target <= now:
            target += _td(days=1)
        wait_secs = (target - now).total_seconds()
        _sched_logger.info(
            "[研究卡片价格] 下次更新(北京时间)：%s（%.1fh 后）",
            target.strftime("%Y-%m-%d %H:%M:%S"),
            wait_secs / 3600,
        )
        await _asyncio.sleep(wait_secs)
        await _run_research_price_sync("每日定时")


_A_SHARE_MTM_HOUR = 15
_A_SHARE_MTM_MINUTE = 35


def _today_cn_a_share_mtm_at() -> _dt:
    now = _cn_now()
    return now.replace(hour=_A_SHARE_MTM_HOUR, minute=_A_SHARE_MTM_MINUTE, second=0, microsecond=0)


async def _run_a_share_mtm_sync(reason: str) -> None:
    from backpack_quant_trading.core.a_share_strategy_mtm import refresh_mtm_close_prices

    try:
        res = await _asyncio.to_thread(refresh_mtm_close_prices)
        _sched_logger.info(
            "[A股盯市收盘] %s: 更新=%s quotes=%s",
            reason,
            res.get("updated_at"),
            list((res.get("quotes") or {}).keys()),
        )
    except Exception as exc:
        _sched_logger.error("[A股盯市收盘] %s 失败: %s", reason, exc)


async def _bootstrap_a_share_mtm() -> None:
    from backpack_quant_trading.core.a_share_strategy_mtm import load_close_cache

    cache = load_close_cache()
    if _research_price_cache_stale_hours(cache, max_age_hours=20.0):
        _sched_logger.info("[A股盯市收盘] 启动补拉: 缓存 %s", cache.get("updated_at"))
        await _run_a_share_mtm_sync("启动补拉")


async def _daily_a_share_mtm_loop() -> None:
    """每个交易日收盘后（北京时间 15:35）刷新 A 股盯市收盘价。"""
    while True:
        now = _cn_now()
        target = _today_cn_a_share_mtm_at()
        if target <= now:
            target += _td(days=1)
        wait_secs = (target - now).total_seconds()
        _sched_logger.info(
            "[A股盯市收盘] 下次更新(北京时间)：%s（%.1fh 后）",
            target.strftime("%Y-%m-%d %H:%M:%S"),
            wait_secs / 3600,
        )
        await _asyncio.sleep(wait_secs)
        await _run_a_share_mtm_sync("每日收盘后")


# ── HYPE 策略 Webhook 快捷入口（无需 /api/trading 前缀，供 TradingView 直接调用）──
from fastapi import Request as _Request
from fastapi.responses import JSONResponse as _JSONResponse
from backpack_quant_trading.api.routers.trading import HYPE_STRATEGY_INSTANCES, WebhookSignal


@app.post("/hype/webhook", tags=["HYPE Webhook"])
async def hype_webhook_shortcut(request: _Request):
    """TradingView Webhook 快捷入口，策略启动后立即可用。

    开空: POST /hype/webhook  {"交易品种":"ETH","操作":"sell","先前仓位大小":"0"}
    平空: POST /hype/webhook  {"交易品种":"ETH","操作":"buy","先前仓位大小":"0.5"}
    """
    try:
        data = await request.json()

        # 找到第一个运行中的 HYPE 实例
        target_id = None
        for iid, strategy in HYPE_STRATEGY_INSTANCES.items():
            if strategy.is_enabled:
                target_id = iid
                break

        if not target_id:
            return _JSONResponse(
                {"status": "error", "message": "没有运行中的 HYPE 策略，请先从前端启动"},
                status_code=404,
            )

        strategy = HYPE_STRATEGY_INSTANCES[target_id]

        # 直接从 dict 读取，避免中文字段名 Pydantic 解析失败
        action = (data.get("方向") or data.get("操作") or data.get("signal") or "").lower().strip()
        price_raw = data.get("成交价格") or data.get("价格") or data.get("price")
        try:
            price = float(price_raw) if price_raw is not None else None
        except (ValueError, TypeError):
            price = None
        symbol_raw = str(data.get("交易品种") or data.get("symbol") or "ETH")
        for suffix in ["USDT", "USD", "PERP", "/USDT", "/USD"]:
            if symbol_raw.upper().endswith(suffix.upper()):
                symbol_raw = symbol_raw[: -len(suffix)]
                break
        symbol = symbol_raw.upper().strip() or "ETH"
        prev_size = str(data.get("先前仓位大小") or "")
        if not prev_size:
            prev_size = "1" if strategy.position == "SHORT" else "0"

        import asyncio as _asyncio
        from backpack_quant_trading.strategy.hype_adaptive_short import TVSignal
        signal = TVSignal(
            交易品种=symbol,
            价格=price,
            操作=action,
            仓位方向=data.get("仓位方向"),
            先前仓位大小=prev_size,
        )

        from backpack_quant_trading.api.routers.trading import HYPE_STRATEGY_TASKS
        loop = HYPE_STRATEGY_TASKS.get(target_id)
        if loop:
            future = _asyncio.run_coroutine_threadsafe(
                strategy.execute_signal(signal, data), loop
            )
            future.result(timeout=5)
        else:
            _asyncio.ensure_future(strategy.execute_signal(signal, data))

        return {"status": "ok", "signal": action, "instance_id": target_id}

    except Exception as e:
        return _JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/hype/position", tags=["HYPE Webhook"])
def hype_position_shortcut():
    """查询 HYPE 策略当前持仓"""
    result = {}
    for iid, strategy in HYPE_STRATEGY_INSTANCES.items():
        result[iid] = strategy.get_status()
    return result if result else {"position": None, "message": "无运行中实例"}


# 生产构建后挂载 Vue 静态文件
# 尝试多个可能路径（兼容不同启动方式）
_pkg_dir = Path(__file__).resolve().parents[1]
_cwd_dir = Path.cwd()
for base in (_pkg_dir, _cwd_dir, _cwd_dir / "backpack_quant_trading"):
    frontend_dist = base / "frontend" / "dist"
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="frontend-assets")
        # SPA 根及子路由：返回 index.html
        from fastapi.responses import FileResponse
        _dist = str(frontend_dist)
        @app.get("/")
        def _index():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/login")
        def _login():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/trading")
        def _trading():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/dashboard")
        def _dashboard():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/ai-lab")
        def _ai_lab():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/grid-trading")
        def _grid():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/currency-monitor")
        def _monitor():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/stock-ai")
        def _stock_ai():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/okx-agent")
        def _okx_agent():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/okx-console")
        def _okx_console():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/us-weekly-report")
        def _us_weekly_report():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/ai-stock")
        def _ai_stock():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/ai-stock/{full_path:path}")
        def _ai_stock_nested(full_path: str):
            return FileResponse(frontend_dist / "index.html")
        @app.get("/crypto-signal-hub")
        def _crypto_signal_hub():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/agent-memory")
        def _agent_memory():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/study-center")
        def _study_center():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/study-center/{full_path:path}")
        def _study_center_nested(full_path: str):
            return FileResponse(frontend_dist / "index.html")
        @app.get("/ai-agent-quiz")
        def _ai_agent_quiz():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/strategies")
        def _strategies():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/strategies/{full_path:path}")
        def _strategies_nested(full_path: str):
            return FileResponse(frontend_dist / "index.html")
        @app.get("/stock-news-alert")
        def _stock_news_alert():
            return FileResponse(frontend_dist / "index.html")
        @app.get("/polymarket-alert")
        def _polymarket_alert():
            return FileResponse(frontend_dist / "index.html")
        break
