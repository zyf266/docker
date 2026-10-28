"""普通用户产品站 API。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backpack_quant_trading.api.deps import require_user
from backpack_quant_trading.core import portal_exchange as exchange
from backpack_quant_trading.core import portal_store as store
from backpack_quant_trading.core import portal_watchlist as watchlist
from backpack_quant_trading.core import portal_webhook_trade as webhook_trade

router = APIRouter()


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
    require_short: bool = True
    require_mid: bool = True
    require_long: bool = False
    strategy_name: str = ""
    timeframe: str = "2h"
    size_mode: str = "percent"  # fixed | percent
    size_value: str = "10"
    leverage: int = 5  # 开仓杠杆，默认 5x
    take_profit: str = ""  # 止盈 %
    stop_loss: str = ""  # 止损 %
    exchanges: List[str] = Field(default_factory=list)  # 下单平台多选：hyperliquid / okx


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
        raw_symbols = []
        for s in body.symbols:
            s = (s or "").strip().upper()
            if not s:
                continue
            # 带 USDT 当加密，否则原样（美股代码）
            raw_symbols.append(watchlist.normalize_crypto_pair(s) if s.endswith("USDT") or len(s) > 5 else s)
        items = store.upsert_watch_configs(
            user["id"],
            raw_symbols,
            require_short=body.require_short,
            require_mid=body.require_mid,
            require_long=body.require_long,
            strategy_name=body.strategy_name,
            timeframe=body.timeframe,
            size_mode=body.size_mode,
            size_value=body.size_value,
            leverage=body.leverage,
            take_profit=body.take_profit,
            stop_loss=body.stop_loss,
            exchanges=body.exchanges,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "items": items}


@router.get("/exchange/bindings")
def get_exchange_bindings(user: dict = Depends(require_user)):
    return {"ok": True, "items": exchange.list_bindings(user["id"])}


@router.get("/exchange/balances")
def get_exchange_balances(user: dict = Depends(require_user)):
    """已连接交易所的真实账户权益 / 可用余额 / 持仓。"""
    try:
        snap = exchange.fetch_balances(user["id"])
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
            result["balances"] = exchange.fetch_balances(user["id"])
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
            result["balances"] = exchange.fetch_balances(user["id"])
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


@router.get("/tv-webhook/hint")
def portal_tv_webhook_hint(user: dict = Depends(require_user)):
    """前端展示用：webhook URL 与字段示例。"""
    return {
        "ok": True,
        "path": "/api/portal/tv-webhook",
        "method": "POST",
        "example": {
            "strategy_name": "test",
            "symbol": "BTC",
            "timeframe": "2h",
            "signal": "buy",
        },
    }


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
    try:
        store.ensure_crypto_account_csv_trades(user["id"])
    except Exception:
        pass
    items = store.list_trades(
        user["id"], platform=platform, symbol=symbol, strategy=strategy, limit=limit
    )
    stats = store.trade_stats(
        user["id"], platform=platform, symbol=symbol, strategy=strategy
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
    days: int = Query(30, ge=7, le=365),
    user: dict = Depends(require_user),
):
    """净值曲线（按已实现盈亏重建；默认不含 BTC 基准）。"""
    plat = (platform or "").strip().lower()
    try:
        store.ensure_crypto_account_csv_trades(user["id"])
    except Exception:
        pass
    current_equity = None
    initial_capital = None
    try:
        snap = exchange.fetch_balances(user["id"])
        accounts = snap.get("accounts") or []
        if plat and plat not in ("all", "全部"):
            for a in accounts:
                if (a.get("platform") or "").lower() == plat and a.get("status") == "ok":
                    current_equity = a.get("equity")
                    if a.get("book"):
                        initial_capital = a.get("initial_capital")
                    break
            if plat == store.BOOK_PLATFORM_CRYPTO and initial_capital is None:
                initial_capital = store.CRYPTO_ACCOUNT_INITIAL_USD
            elif plat == store.BOOK_PLATFORM_US and initial_capital is None:
                initial_capital = store.US_ACCOUNT_INITIAL_USD
        else:
            current_equity = snap.get("total_equity")
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
