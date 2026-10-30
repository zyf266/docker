"""普通用户产品站 API。"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backpack_quant_trading.api.deps import is_admin_role, require_admin, require_user
from backpack_quant_trading.core import portal_exchange as exchange
from backpack_quant_trading.core import portal_store as store
from backpack_quant_trading.core import portal_watchlist as watchlist
from backpack_quant_trading.core import portal_webhook_trade as webhook_trade

router = APIRouter()


def _include_book(user: dict) -> bool:
    return is_admin_role((user or {}).get("role"))


class FavoriteIn(BaseModel):
    symbol: str
    market: str = "crypto"
    name: str = ""


class WatchAddIn(BaseModel):
    symbol: str
    name: str = ""
    market: str = "crypto"  # crypto | us


class WatchConfigIn(BaseModel):
    symbols: List[str] = Field(default_factory=list)
    require_short: bool = False  # MA5 已下线，默认不再要求
    require_mid: bool = True
    require_long: bool = False
    require_2h: bool = False
    require_4h: bool = False
    status_mode: str = "趋势"  # 兼容旧单配置
    # 三套状态：{"趋势":{require_2h..},"反弹":{...},"空头":{...}}
    status_profiles: Optional[Dict[str, Any]] = None
    strategy_name: str = ""
    timeframe: str = "2h"
    size_mode: str = "percent"  # fixed | percent
    size_value: str = "10"
    leverage: int = 5  # 开仓杠杆，默认 5x
    take_profit: str = ""  # 止盈 %
    stop_loss: str = ""  # 止损 %
    exchanges: List[str] = Field(default_factory=list)  # 下单平台多选：hyperliquid / okx
    gates_only: bool = False  # True=只保存第一步条件，可不填策略/仓位
    # crypto | us：批量应用到该市场全部标的，并记为该市场默认（新标的继承）
    market: str = ""
    # status=只状态；trade=只交易；空/full=按 gates_only
    config_kind: str = ""


class ExchangeConnectIn(BaseModel):
    platform: str  # okx | hyperliquid | binance
    private_key: str = ""
    api_key: str = ""
    api_secret: str = ""
    passphrase: str = ""
    label: str = ""
    demo: bool = False
    symbols: List[str] = Field(default_factory=list)


class InboxTestIn(BaseModel):
    title: str = "测试站内信"
    body: str = "这是一条产品站测试消息。"


class EmailStubIn(BaseModel):
    to_addr: str
    subject: str = "沐龙量化通知"
    body: str = ""


class ContactIn(BaseModel):
    name: str
    phone: str
    experience: str = ""
    interests: List[str] = Field(default_factory=list)
    message: str = ""


class EquityIn(BaseModel):
    strategy_ids: Optional[List[str]] = None


@router.get("/favorites")
def get_favorites(user: dict = Depends(require_user)):
    return {"ok": True, "items": store.list_favorites(user["id"])}


@router.post("/favorites")
def post_favorite(body: FavoriteIn, user: dict = Depends(require_user)):
    try:
        item = store.add_favorite(user["id"], body.symbol, body.market, body.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "item": item}


@router.delete("/favorites/{symbol}")
def delete_favorite(symbol: str, user: dict = Depends(require_user)):
    ok = store.remove_favorite(user["id"], symbol)
    return {"ok": ok}


@router.get("/watchlist")
def get_watchlist(
    metrics: int = Query(0, description="1=带指标（优先 30 分钟缓存）；0=只读库，仍回填未过期缓存"),
    force: int = Query(0, description="1=忽略缓存强制重拉 K 线（仅 metrics=1 时有效）"),
    user: dict = Depends(require_user),
):
    try:
        return {
            "ok": True,
            **watchlist.list_watchlist_board(
                user["id"],
                with_metrics=bool(metrics),
                force=bool(force) and bool(metrics),
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"观察库加载失败: {e}") from e


@router.get("/watchlist/binance-symbols")
def watchlist_binance_symbols(
    q: str = Query(""),
    market: str = Query("all"),
    user: dict = Depends(require_user),
):
    return {"ok": True, "items": watchlist.search_watch_symbols(q, market=market)}


@router.post("/watchlist")
def post_watchlist(body: WatchAddIn, user: dict = Depends(require_user)):
    try:
        item = watchlist.add_watch_symbol(user["id"], body.symbol, body.name, body.market)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "item": item}


@router.delete("/watchlist/{symbol}")
def delete_watchlist(symbol: str, user: dict = Depends(require_user)):
    # 兼容加密 BTCUSDT 与美股 NVDA
    ok = store.remove_favorite(user["id"], symbol)
    if not ok:
        ok = store.remove_favorite(user["id"], watchlist.normalize_crypto_pair(symbol))
    return {"ok": ok}


@router.post("/watchlist/config")
def post_watchlist_config(body: WatchConfigIn, user: dict = Depends(require_user)):
    try:
        kind = (body.config_kind or "").strip().lower()
        gates_only = bool(body.gates_only) or kind == "status"
        trade_only = kind == "trade"
        mkt = (body.market or "").strip().lower()
        raw_symbols = []
        for s in body.symbols:
            s = (s or "").strip().upper()
            if not s:
                continue
            # 带 USDT 当加密，否则原样（美股代码）
            raw_symbols.append(watchlist.normalize_crypto_pair(s) if s.endswith("USDT") or len(s) > 5 else s)
        if mkt in ("crypto", "us", "加密", "美股"):
            raw_symbols = store.list_favorite_symbols_by_market(user["id"], mkt)
            if not raw_symbols:
                raise ValueError("该市场暂无标的，请先添加后再批量配置")
            if gates_only or not trade_only:
                store.save_watch_market_default(
                    user["id"],
                    mkt,
                    gates={
                        "require_mid": body.require_mid,
                        "require_long": body.require_long,
                        "require_2h": body.require_2h,
                        "require_4h": body.require_4h,
                        "status_mode": body.status_mode,
                        "status_profiles": body.status_profiles,
                    },
                )
            if not gates_only:
                store.save_watch_market_default(
                    user["id"],
                    mkt,
                    trade={
                        "strategy_name": body.strategy_name,
                        "timeframe": body.timeframe,
                        "size_mode": body.size_mode,
                        "size_value": body.size_value,
                        "leverage": body.leverage,
                        "take_profit": body.take_profit,
                        "stop_loss": body.stop_loss,
                        "exchanges": body.exchanges,
                    },
                )
        if trade_only and not gates_only:
            # 只更新交易参数：先取已有 gates，避免覆盖状态条件
            existing = {c["symbol"]: c for c in store.list_watch_configs(user["id"])}
            items = []
            for sym in raw_symbols:
                seed = existing.get(sym) or {}
                items.extend(
                    store.upsert_watch_configs(
                        user["id"],
                        [sym],
                        require_short=False,
                        require_mid=bool(seed.get("require_mid", body.require_mid)),
                        require_long=bool(seed.get("require_long", body.require_long)),
                        require_2h=bool(seed.get("require_2h", body.require_2h)),
                        require_4h=bool(seed.get("require_4h", body.require_4h)),
                        status_mode=seed.get("status_mode") or body.status_mode,
                        strategy_name=body.strategy_name,
                        timeframe=body.timeframe,
                        size_mode=body.size_mode,
                        size_value=body.size_value,
                        leverage=body.leverage,
                        take_profit=body.take_profit,
                        stop_loss=body.stop_loss,
                        exchanges=body.exchanges,
                        gates_only=False,
                    )
                )
        else:
            items = store.upsert_watch_configs(
                user["id"],
                raw_symbols,
                require_short=False,
                require_mid=body.require_mid,
                require_long=body.require_long,
                require_2h=body.require_2h,
                require_4h=body.require_4h,
                status_mode=body.status_mode,
                status_profiles=body.status_profiles,
                strategy_name=body.strategy_name,
                timeframe=body.timeframe,
                size_mode=body.size_mode,
                size_value=body.size_value,
                leverage=body.leverage,
                take_profit=body.take_profit,
                stop_loss=body.stop_loss,
                exchanges=body.exchanges,
                gates_only=gates_only,
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "items": items}


@router.get("/exchange/bindings")
def get_exchange_bindings(user: dict = Depends(require_user)):
    return {"ok": True, "items": exchange.list_bindings(user["id"])}


@router.get("/exchange/balances")
def get_exchange_balances(user: dict = Depends(require_user)):
    """已连接交易所的真实账户权益 / 可用余额 / 持仓。账面账户仅管理员可见。"""
    try:
        snap = exchange.fetch_balances(user["id"], include_book=_include_book(user))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"余额查询失败: {e}") from e
    return {"ok": True, **snap}


@router.post("/exchange/connect")
def post_exchange_connect(body: ExchangeConnectIn, user: dict = Depends(require_user)):
    try:
        result = exchange.connect_exchange(
            user["id"],
            body.platform,
            private_key=body.private_key,
            api_key=body.api_key,
            api_secret=body.api_secret,
            passphrase=body.passphrase,
            label=body.label,
            demo=body.demo,
            symbols=body.symbols,
        )
        # 连接后立刻回填余额，方便前端刷新
        try:
            result["balances"] = exchange.fetch_balances(user["id"], include_book=_include_book(user))
        except Exception:
            result["balances"] = None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接失败: {e}") from e
    return {"ok": True, **result}


@router.delete("/exchange/bindings/{platform}")
def delete_exchange_binding(platform: str, user: dict = Depends(require_user)):
    """断开指定交易所连接（删除绑定密钥）。"""
    try:
        result = exchange.disconnect_exchange(user["id"], platform)
        try:
            result["balances"] = exchange.fetch_balances(user["id"], include_book=_include_book(user))
        except Exception:
            result["balances"] = None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"断开失败: {e}") from e
    return {"ok": True, **result}


@router.post("/tv-webhook")
async def portal_tv_webhook(request: Request):
    """TradingView → 观察库自动下单（无需登录）。

    匹配 portal_watch_configs：strategy_name + symbol + timeframe 且 status=connected，
    用用户绑定的 Hyperliquid/OKX 按仓位开仓并挂止盈止损。

    环境变量 PORTAL_WEBHOOK_DRY_RUN=1 时只匹配/算仓位，不真下单。
    """
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无效 JSON: {e}") from e
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体须为 JSON 对象")
    try:
        result = webhook_trade.execute_portal_signal(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"webhook 处理失败: {e}") from e
    return result


def _public_webhook_base() -> str:
    """TradingView 只允许 80/443：对外走 Nginx，不要带 :8100/:8005。

    与实盘策略一致，例如 http://47.110.57.118/adaptive-long/webhook
    → 账面记账：http://47.110.57.118/api/portal/book-trade-webhook
    """
    raw = (
        os.getenv("PORTAL_PUBLIC_BASE_URL")
        or os.getenv("PUBLIC_WEBHOOK_BASE")
        or os.getenv("PUBLIC_API_BASE")
        or "http://47.110.57.118"
    ).strip().rstrip("/")
    # 误配成 :8100/:8005 时剥掉，强制走默认 80/443
    for port in (":8100", ":8005", ":8050"):
        if port in raw:
            raw = raw.replace(port, "")
    return raw.rstrip("/")


@router.get("/tv-webhook/hint")
def portal_tv_webhook_hint(user: dict = Depends(require_user)):
    """前端展示用：webhook URL 与字段示例。"""
    token = (os.getenv("PORTAL_BOOK_WEBHOOK_TOKEN") or "").strip()
    book_path = "/api/portal/book-trade-webhook"
    if token:
        book_path = f"{book_path}?token={token}"
    base = _public_webhook_base()
    return {
        "ok": True,
        "path": "/api/portal/tv-webhook",
        "url": f"{base}/api/portal/tv-webhook",
        "method": "POST",
        "public_base": base,
        "example": {
            "strategy_name": "test",
            "symbol": "BTC",
            "timeframe": "2h",
            "signal": "buy",
        },
        "book_journal": {
            "path": book_path,
            "url": f"{base}{book_path}",
            "method": "POST",
            "note": "TV 请用 80 端口公网地址（经 Nginx /api → 8100）。只记账、不下真实单。",
            "example": {
                "market": "加密",
                "strategy_name": "加密追踪策略",
                "symbol": "{{ticker}}",
                "timeframe": "2h",
                "action": "open",
                "signal": "buy",
                "price": "{{close}}",
                "margin": 2000000,
                "pnl": 0,
            },
        },
    }


def _check_book_webhook_token(request: Request) -> None:
    expected = (os.getenv("PORTAL_BOOK_WEBHOOK_TOKEN") or "").strip()
    if not expected:
        return
    got = (request.query_params.get("token") or "").strip()
    if not got:
        got = (request.headers.get("X-Portal-Token") or "").strip()
    if got != expected:
        raise HTTPException(status_code=401, detail="webhook token 无效")


@router.post("/book-trade-webhook")
async def portal_book_trade_webhook(request: Request):
    """TradingView → 账面交易清单（crypto_account / us_account）。

    只落库，不真实下单。开仓会出现在管理员账面「当前持仓」。
    可选鉴权：环境变量 PORTAL_BOOK_WEBHOOK_TOKEN，URL ?token= 或头 X-Portal-Token。
    """
    _check_book_webhook_token(request)
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无效 JSON: {e}") from e
    try:
        result = store.record_book_trade_from_webhook(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记账失败: {e}") from e
    return result


@router.get("/search")
def search(q: str = Query(""), user: dict = Depends(require_user)):
    return {"ok": True, "q": q, "items": store.search_catalog(q)}


@router.get("/inbox")
def inbox(user: dict = Depends(require_user)):
    return {"ok": True, "items": store.list_inbox(user["id"])}


@router.post("/inbox/test")
def inbox_test(body: InboxTestIn, user: dict = Depends(require_user)):
    item = store.create_inbox(user["id"], body.title, body.body)
    return {"ok": True, "item": item}


@router.post("/inbox/{msg_id}/read")
def inbox_read(msg_id: int, user: dict = Depends(require_user)):
    ok = store.mark_inbox_read(user["id"], msg_id)
    if not ok:
        raise HTTPException(status_code=404, detail="消息不存在")
    return {"ok": True}


@router.post("/email/stub")
def email_stub(body: EmailStubIn, user: dict = Depends(require_user)):
    if not body.to_addr.strip():
        raise HTTPException(status_code=400, detail="收件人不能为空")
    result = store.enqueue_email(user["id"], body.to_addr, body.subject, body.body)
    # 同步写一条站内信，方便产品站可见
    store.create_inbox(user["id"], f"[邮件口子] {body.subject}", f"已记录待发至 {body.to_addr}\n{body.body}")
    return {"ok": True, **result}


@router.post("/contact")
def contact(body: ContactIn, user: dict = Depends(require_user)):
    if not body.name.strip() or not body.phone.strip():
        raise HTTPException(status_code=400, detail="姓名和电话必填")
    result = store.save_contact(
        body.name,
        body.phone,
        body.experience,
        body.interests,
        body.message,
        user_id=user["id"],
    )
    return {"ok": True, **result}


@router.get("/trades")
def get_portal_trades(
    platform: str = Query("", description="交易所过滤，空=全部"),
    symbol: str = Query("", description="币种过滤，空=全部"),
    strategy: str = Query("", description="策略名过滤，空=全部"),
    limit: int = Query(200, ge=1, le=500),
    user: dict = Depends(require_user),
):
    """交易记录清单 + 7/30/180 天收益、盈亏比与订单统计（按筛选条件）。"""
    plat = (platform or "").strip().lower()
    if store.is_book_platform(plat) and not _include_book(user):
        raise HTTPException(status_code=403, detail="普通用户无权查看账面账户")
    # 普通用户：空平台不过账面共享成交，只看自己连接账户
    view_plat = platform
    if not _include_book(user) and (not plat or plat in ("all", "全部")):
        view_plat = "connected"
    if _include_book(user):
        try:
            store.ensure_book_account_csv_trades(user["id"])
        except Exception:
            pass
    items = store.list_trades(
        user["id"], platform=view_plat, symbol=symbol, strategy=strategy, limit=limit
    )
    stats = store.trade_stats(
        user["id"], platform=view_plat, symbol=symbol, strategy=strategy
    )
    return {"ok": True, "items": items, "stats": stats}


@router.get("/equity-overlay")
def equity_overlay(ids: str = Query(""), user: dict = Depends(require_user)):
    strategy_ids = [x.strip() for x in (ids or "").split(",") if x.strip()] or None
    return {"ok": True, **store.equity_overlay_mock(strategy_ids)}


@router.post("/equity-overlay")
def equity_overlay_post(body: EquityIn, user: dict = Depends(require_user)):
    return {"ok": True, **store.equity_overlay_mock(body.strategy_ids)}


@router.get("/equity-curve")
def get_equity_curve(
    platform: str = Query("", description="平台过滤，空=全部（含账面账户）"),
    days: int = Query(0, ge=0, le=9000, description="0=全部历史；30/180/360 为窗口"),
    user: dict = Depends(require_user),
):
    """净值曲线（按已实现盈亏重建；默认不含 BTC 基准）。"""
    plat = (platform or "").strip().lower()
    if store.is_book_platform(plat) and not _include_book(user):
        raise HTTPException(status_code=403, detail="普通用户无权查看账面账户")
    if _include_book(user):
        try:
            store.ensure_book_account_csv_trades(user["id"])
        except Exception:
            pass
    current_equity = None
    initial_capital = None
    try:
        snap = exchange.fetch_balances(user["id"], include_book=_include_book(user))
        accounts = snap.get("accounts") or []
        if plat in ("connected", "self", "exchange", "自己连接", "自己连接的账户"):
            current_equity = 0.0
            for a in accounts:
                if a.get("status") != "ok" or a.get("book"):
                    continue
                if store.is_book_platform(a.get("platform") or ""):
                    continue
                current_equity += float(a.get("equity") or 0)
        elif plat and plat not in ("all", "全部"):
            for a in accounts:
                if (a.get("platform") or "").lower() == plat and a.get("status") == "ok":
                    current_equity = a.get("equity")
                    if a.get("book"):
                        initial_capital = a.get("initial_capital")
                    break
            if store.is_book_platform(plat) and initial_capital is None:
                if not _include_book(user):
                    raise HTTPException(status_code=403, detail="普通用户无权查看账面账户")
                initial_capital = store.get_book_initial_capital(plat)
        else:
            current_equity = snap.get("total_equity")
    except HTTPException:
        raise
    except Exception:
        current_equity = None
    curve = store.build_equity_curve(
        user["id"],
        platform=plat,
        days=days,
        current_equity=current_equity,
        initial_capital=initial_capital,
        include_btc=False,
    )
    return {"ok": True, **curve}


class BookCapitalIn(BaseModel):
    market: str = Field(..., description="加密 / 美股")
    capital: str = Field(..., description="本金，如 200w 或 2000000")


@router.post("/book-capital")
def post_book_capital(body: BookCapitalIn, user: dict = Depends(require_admin)):
    """管理员：新增一张账面账户卡（不改动已有账户）。"""
    try:
        result = store.create_book_account(body.market, body.capital)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"新增账面账户失败: {e}") from e
    return {"ok": True, **result}
