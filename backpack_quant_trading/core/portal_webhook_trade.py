"""观察库配置 → TradingView webhook 自动下单（Hyperliquid / OKX）。"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from backpack_quant_trading.core import portal_store as store
from backpack_quant_trading.core.portal_exchange import (
    _okx_sign,
    _secrets_from_binding,
    _verify_hyperliquid,
    _verify_okx,
)
from backpack_quant_trading.core.portal_store import _norm_tf, _symbol_bases

logger = logging.getLogger(__name__)

# 与观察库下拉、原交易册三策略对齐的标准名
STRATEGY_LONG = "自适应做多策略"
STRATEGY_SHORT = "自适应做空策略"
STRATEGY_CLOSE = "自适应平仓策略"
PORTAL_STRATEGY_OPTIONS = (STRATEGY_LONG, STRATEGY_SHORT, STRATEGY_CLOSE)


def _dry_run() -> bool:
    return (os.getenv("PORTAL_WEBHOOK_DRY_RUN") or "").strip().lower() in ("1", "true", "yes", "on")


def _skip_equity_check() -> bool:
    """测试用：权益为 0 时仍用固定保证金继续向交易所发单（看请求是否到达）。"""
    return (os.getenv("PORTAL_SKIP_EQUITY_CHECK") or "").strip().lower() in ("1", "true", "yes", "on")


def _skip_ma_gate() -> bool:
    return (os.getenv("PORTAL_SKIP_MA_GATE") or "").strip().lower() in ("1", "true", "yes", "on")


def _test_margin_usdt() -> float:
    try:
        v = float(os.getenv("PORTAL_TEST_MARGIN") or "5")
    except (TypeError, ValueError):
        v = 5.0
    return max(v, 1.0)


def extract_tv_fields(payload: dict) -> Tuple[str, str, str, str]:
    """返回 (symbol, action, timeframe, strategy_name)。"""
    action = str(
        payload.get("方向")
        or payload.get("操作")
        or payload.get("action")
        or payload.get("signal")
        or ""
    ).lower().strip()
    symbol = str(
        payload.get("交易品种") or payload.get("symbol") or payload.get("coin") or ""
    ).strip()
    tf = str(
        payload.get("周期")
        or payload.get("K线级别")
        or payload.get("timeframe")
        or payload.get("interval")
        or payload.get("tf")
        or ""
    ).strip()
    strategy_name = str(
        payload.get("策略名称")
        or payload.get("策略名")
        or payload.get("strategy_name")
        or payload.get("strategyName")
        or payload.get("strategy")
        or payload.get("strategy_label")
        or ""
    ).strip()
    return symbol, action, tf, strategy_name


def _normalize_side(action: str) -> Optional[str]:
    a = (action or "").lower().strip()
    if a in ("buy", "long", "开多", "做多", "多"):
        return "BUY"
    if a in ("sell", "short", "开空", "做空", "空"):
        return "SELL"
    if a in ("close", "平仓", "flat"):
        return "CLOSE"
    return None


def strategy_family(strategy_name: str) -> str:
    """long | short | close | unknown — 对齐原自适应多/空/自动平仓。"""
    n = (strategy_name or "").strip().lower().replace(" ", "")
    if not n:
        return "unknown"
    if "平仓" in n or "autoclose" in n or "auto_close" in n or "auto-close" in n:
        return "close"
    if "做空" in n or "short" in n:
        return "short"
    if "做多" in n or "long" in n:
        return "long"
    return "unknown"


def parse_exchanges(raw: Any) -> List[str]:
    """配置里 exchange 支持单值或逗号分隔多平台。"""
    if isinstance(raw, (list, tuple)):
        items = [str(x or "").strip().lower() for x in raw]
    else:
        items = [p.strip().lower() for p in str(raw or "").replace(";", ",").split(",")]
    out: List[str] = []
    for p in items:
        if p in ("hyperliquid", "okx", "binance") and p not in out:
            out.append(p)
    return out


def resolve_trade_intent(strategy_name: str, side: str) -> Tuple[str, Optional[str], str]:
    """按策略族解析意图。

    返回 (op, open_side_or_expect_pos, detail)
    - op=open 时第二项为 BUY/SELL
    - op=close 时第二项为 long/short/None（None=任意仓）
    - op=skip 时忽略信号
    """
    fam = strategy_family(strategy_name)
    side_u = (side or "").upper()

    # 自适应做多：buy 开多，sell/close 平多（对齐 adaptive_long_strategy）
    if fam == "long":
        if side_u == "BUY":
            return "open", "BUY", "自适应做多·开多"
        if side_u in ("SELL", "CLOSE"):
            return "close", "long", "自适应做多·平多"
        return "skip", None, f"自适应做多忽略信号 {side_u}"

    # 自适应做空：sell 开空，buy/close 平空（对齐 adaptive_short_strategy）
    if fam == "short":
        if side_u == "SELL":
            return "open", "SELL", "自适应做空·开空"
        if side_u in ("BUY", "CLOSE"):
            return "close", "short", "自适应做空·平空"
        return "skip", None, f"自适应做空忽略信号 {side_u}"

    # 自动平仓：多仓仅 sell 平；空仓仅 buy 平（对齐 auto_close_strategy）
    if fam == "close":
        if side_u == "SELL":
            return "close", "long", "自动平仓·平多"
        if side_u == "BUY":
            return "close", "short", "自动平仓·平空"
        if side_u == "CLOSE":
            return "close", None, "自动平仓·平任意"
        return "skip", None, f"自动平仓忽略信号 {side_u}"

    # 未知策略名：保持旧行为（buy 开多 / sell 开空 / close 平仓）
    if side_u == "CLOSE":
        return "close", None, "平仓"
    if side_u in ("BUY", "SELL"):
        return "open", side_u, "开仓"
    return "skip", None, f"未知信号 {side_u}"


def _base_coin(symbol: str) -> str:
    bases = _symbol_bases(symbol)
    # 优先最短非 USDT 形式
    bare = [b for b in bases if not b.endswith(("USDT", "USDC", "USD"))]
    if bare:
        return sorted(bare, key=len)[0]
    return (symbol or "").strip().upper() or "BTC"


def _parse_pct(raw: str) -> Optional[float]:
    s = str(raw or "").strip().replace("%", "")
    if not s:
        return None
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def _leverage_from_cfg(cfg: Dict[str, Any], default: int = 5) -> int:
    try:
        lev = int(cfg.get("leverage") if cfg.get("leverage") is not None else default)
    except (TypeError, ValueError):
        lev = default
    return max(1, min(lev, 125))


def _check_ma_gate(cfg: Dict[str, Any], side: str) -> Tuple[bool, str]:
    """买入前检查是否满足配置勾选的「站上 MA5/30/200」。卖出/平仓不校验。"""
    if side != "BUY":
        return True, ""
    need_short = bool(cfg.get("require_short"))
    need_mid = bool(cfg.get("require_mid"))
    need_long = bool(cfg.get("require_long"))
    if not (need_short or need_mid or need_long):
        return True, ""

    from backpack_quant_trading.core.portal_watchlist import compute_symbol_metrics

    symbol = str(cfg.get("symbol") or "")
    try:
        metrics = compute_symbol_metrics(symbol, market="crypto", force=False)
    except Exception as exc:
        return False, f"均线状态拉取失败: {exc}"

    if metrics.get("error") and metrics.get("ma5") is None and metrics.get("ma30") is None:
        return False, f"均线数据不足: {metrics.get('error')}"

    missing = []
    if need_short and not metrics.get("short_on"):
        missing.append("MA5")
    if need_mid and not metrics.get("mid_on"):
        missing.append("MA30")
    if need_long and not metrics.get("long_on"):
        missing.append("MA200")
    if missing:
        return False, (
            f"未站上 {','.join(missing)}（price={metrics.get('price')}, "
            f"MA5={metrics.get('ma5')}, MA30={metrics.get('ma30')}, MA200={metrics.get('ma200')}），拒绝开多"
        )
    return True, ""


def _record_from_result(
    cfg: Dict[str, Any],
    *,
    side: str,
    action: str,
    out: Dict[str, Any],
    dry: bool,
) -> None:
    if out.get("status") not in ("ok", "skipped", "error"):
        return
    status = str(out.get("status") or "ok")
    if dry and status == "ok":
        status = "dry-run"
    order = out.get("order") if isinstance(out.get("order"), dict) else {}
    try:
        margin_val = out.get("margin")
        if margin_val in (None, "") and order.get("margin") not in (None, ""):
            margin_val = order.get("margin")
        store.record_trade(
            int(cfg.get("user_id")),
            platform=str(cfg.get("exchange") or ""),
            symbol=str(cfg.get("symbol") or out.get("coin") or ""),
            side=side,
            action=action,
            strategy_name=str(cfg.get("strategy_name") or ""),
            timeframe=str(cfg.get("timeframe") or ""),
            price=float(out["entry"]) if out.get("entry") not in (None, "") else None,
            quantity=float(out["size"]) if out.get("size") not in (None, "") else None,
            margin=float(margin_val) if margin_val not in (None, "") else None,
            leverage=_leverage_from_cfg(cfg),
            pnl=float(out.get("pnl") or 0),
            status=status,
            detail=str(out.get("detail") or "")[:240],
            order_id=str(order.get("orderId") or order.get("ordId") or ""),
        )
    except Exception:
        logger.exception("写入 portal_trades 失败 cfg=%s", cfg.get("id"))


def _margin_usdt(cfg: Dict[str, Any], equity: float) -> float:
    mode = (cfg.get("size_mode") or "percent").lower()
    try:
        val = float(str(cfg.get("size_value") or "0").strip())
    except (TypeError, ValueError):
        val = 0.0
    if mode == "fixed":
        return max(val, 0.0)
    # percent：权益 × 比例
    if equity <= 0:
        return 0.0
    return max(equity * (val / 100.0), 0.0)


def execute_portal_signal(payload: dict) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload 必须是 JSON 对象", "matched": 0, "executed": 0, "results": []}

    symbol, action, tf, strategy_name = extract_tv_fields(payload)
    side = _normalize_side(action)
    dry = _dry_run()

    if not strategy_name or not symbol or not tf:
        return {
            "ok": False,
            "error": "缺少 strategy_name / symbol / timeframe",
            "matched": 0,
            "executed": 0,
            "parsed": {"symbol": symbol, "action": action, "timeframe": tf, "strategy_name": strategy_name},
            "results": [],
            "dry_run": dry,
        }
    if not side:
        return {
            "ok": False,
            "error": f"无法识别方向: {action!r}（需 buy/long/sell/short/close）",
            "matched": 0,
            "executed": 0,
            "parsed": {"symbol": symbol, "action": action, "timeframe": tf, "strategy_name": strategy_name},
            "results": [],
            "dry_run": dry,
        }

    configs = store.find_connected_configs(strategy_name, symbol, tf)
    op, intent_side, intent_detail = resolve_trade_intent(strategy_name, side)
    results: List[Dict[str, Any]] = []
    executed = 0

    for cfg in configs:
        uid = cfg.get("user_id")
        platforms = parse_exchanges(cfg.get("exchange"))
        if not platforms:
            results.append({
                "config_id": cfg.get("id"),
                "user_id": uid,
                "symbol": cfg.get("symbol"),
                "strategy_name": cfg.get("strategy_name"),
                "status": "skipped",
                "detail": "配置未选择下单平台",
            })
            continue

        for exchange in platforms:
            item: Dict[str, Any] = {
                "config_id": cfg.get("id"),
                "user_id": uid,
                "symbol": cfg.get("symbol"),
                "strategy_name": cfg.get("strategy_name"),
                "timeframe": cfg.get("timeframe"),
                "exchange": exchange,
                "intent": intent_detail,
                "status": "skipped",
                "detail": "",
            }
            if not uid:
                item["detail"] = "配置缺少 user_id"
                results.append(item)
                continue
            if exchange not in ("hyperliquid", "okx"):
                item["detail"] = f"交易所未支持或未绑定: {exchange}"
                results.append(item)
                continue
            if op == "skip":
                item["detail"] = intent_detail
                results.append(item)
                continue

            binding = store.get_exchange_binding(int(uid), exchange)
            if not binding:
                item["detail"] = f"用户未绑定 {exchange}"
                results.append(item)
                continue

            run_cfg = {**cfg, "exchange": exchange}

            # 仅「开多」校验站上 MA（开空/平仓不挡）
            if op == "open" and intent_side == "BUY" and not _skip_ma_gate():
                ok_gate, gate_msg = _check_ma_gate(run_cfg, "BUY")
                if not ok_gate:
                    item["status"] = "rejected"
                    item["detail"] = gate_msg
                    results.append(item)
                    try:
                        store.record_trade(
                            int(uid),
                            platform=exchange,
                            symbol=str(cfg.get("symbol") or ""),
                            side="BUY",
                            action="open",
                            strategy_name=str(cfg.get("strategy_name") or ""),
                            timeframe=str(cfg.get("timeframe") or ""),
                            leverage=_leverage_from_cfg(cfg),
                            status="rejected",
                            detail=gate_msg[:240],
                        )
                    except Exception:
                        logger.exception("写入拒绝记录失败")
                    continue

            try:
                secrets = _secrets_from_binding(binding.get("config") or {})
                demo = bool((binding.get("config") or {}).get("demo"))
                if op == "close":
                    out = _exec_close(
                        run_cfg, exchange, secrets, dry=dry, expect_side=intent_side, demo=demo
                    )
                    trade_action = "close"
                    record_side = "SELL" if intent_side != "short" else "BUY"
                elif exchange == "hyperliquid":
                    out = _exec_hyperliquid(run_cfg, intent_side or side, secrets, dry=dry)
                    trade_action = "open"
                    record_side = intent_side or side
                else:
                    out = _exec_okx(
                        run_cfg, intent_side or side, secrets, dry=dry, demo=demo
                    )
                    trade_action = "open"
                    record_side = intent_side or side
                item.update(out)
                if out.get("status") == "ok":
                    executed += 1
                _record_from_result(
                    run_cfg,
                    side=record_side,
                    action=trade_action,
                    out=out,
                    dry=dry,
                )
            except Exception as exc:
                logger.exception("portal webhook 执行失败 cfg=%s exchange=%s", cfg.get("id"), exchange)
                item["status"] = "error"
                item["detail"] = str(exc)[:240]
            results.append(item)

    return {
        "ok": True,
        "matched": len(configs),
        "executed": executed,
        "dry_run": dry,
        "parsed": {
            "symbol": symbol,
            "action": action,
            "side": side,
            "intent": intent_detail,
            "op": op,
            "timeframe": _norm_tf(tf),
            "strategy_name": strategy_name,
            "strategy_family": strategy_family(strategy_name),
        },
        "results": results,
    }


def _run_async(coro):
    """在已有事件循环（如 FastAPI）内也能跑协程。"""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    def _in_thread():
        return asyncio.run(coro)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_in_thread).result(timeout=120)


def _exec_hyperliquid(cfg: Dict[str, Any], side: str, secrets: Dict[str, str], *, dry: bool) -> Dict[str, Any]:
    from backpack_quant_trading.core.hyperliquid_client import HyperliquidAPIClient

    pk = secrets.get("private_key") or ""
    if not pk:
        return {"status": "error", "detail": "缺少 Hyperliquid 私钥"}

    coin = _base_coin(cfg.get("symbol") or "")
    meta = _verify_hyperliquid(pk)
    equity = float(meta.get("equity") or meta.get("balance") or 0)
    margin = _margin_usdt(cfg, equity)
    skipped_equity = False
    if margin <= 0 and _skip_equity_check():
        margin = _test_margin_usdt()
        skipped_equity = True
    if margin <= 0:
        return {"status": "error", "detail": f"仓位金额无效 equity={equity} margin={margin}"}

    tp_pct = _parse_pct(cfg.get("take_profit") or "")
    sl_pct = _parse_pct(cfg.get("stop_loss") or "")
    leverage = _leverage_from_cfg(cfg)

    if dry:
        return {
            "status": "ok",
            "detail": "dry-run",
            "margin": round(margin, 4),
            "equity": round(equity, 4),
            "coin": coin,
            "side": side,
            "leverage": leverage,
            "tp_pct": tp_pct,
            "sl_pct": sl_pct,
            "skipped_equity": skipped_equity,
        }

    client = HyperliquidAPIClient(private_key=pk)

    async def _run():
        try:
            # 同向已有仓 → 跳过
            positions = await client.get_positions(symbol=coin)
            target = "long" if side == "BUY" else "short"
            for p in positions or []:
                psym = str(p.get("symbol") or "").split(":")[-1].upper()
                if psym == coin and (p.get("side") or "").lower() == target:
                    return {"status": "skipped", "detail": f"已有 {target} 仓位，跳过"}

            price = await client.get_price(coin)
            # 与原实盘策略相同：HyperliquidAPIClient.place_order（保证金→×杠杆→市价 IOC）
            res = await client.place_order(
                symbol=coin,
                side=side,
                quantity=margin,
                order_type="MARKET",
                leverage=leverage,
            )
            close_side = "SELL" if side == "BUY" else "BUY"
            if res.get("status") != "FILLED":
                # 无余额联通测试：开仓被拒时仍向交易所发 TP/SL 触发单请求，确认接口可达
                tpsl_probe: Dict[str, Any] = {}
                if _skip_equity_check() and (tp_pct or sl_pct) and price and price > 0:
                    probe_sz = max(float(f"{(margin * leverage / price):.4f}"), 0.001)
                    if tp_pct:
                        tp_px = price * (1 + tp_pct / 100.0) if side == "BUY" else price * (1 - tp_pct / 100.0)
                        tpsl_probe["tp"] = await client.place_tpsl_order(coin, close_side, probe_sz, tp_px, "tp")
                    if sl_pct:
                        sl_px = price * (1 - sl_pct / 100.0) if side == "BUY" else price * (1 + sl_pct / 100.0)
                        tpsl_probe["sl"] = await client.place_tpsl_order(coin, close_side, probe_sz, sl_px, "sl")
                return {
                    "status": "error",
                    "detail": f"开仓失败(交易所已收到请求): {res.get('error') or res}",
                    "exchange_response": res,
                    "margin": margin,
                    "leverage": leverage,
                    "skipped_equity": skipped_equity,
                    "tpsl_probe": tpsl_probe or None,
                }

            positions = await client.get_positions(symbol=coin)
            pos = next(
                (
                    p for p in (positions or [])
                    if str(p.get("symbol") or "").split(":")[-1].upper() == coin
                ),
                None,
            )
            sz = abs(float((pos or {}).get("size") or 0))
            entry = float(
                (pos or {}).get("entry_price")
                or (pos or {}).get("entryPx")
                or (pos or {}).get("avg_entry")
                or price
                or 0
            )
            tpsl = {}
            if sz > 0 and entry > 0:
                # 与原自适应多相同：place_tpsl_order 挂交易所触发单
                if tp_pct:
                    tp_px = entry * (1 + tp_pct / 100.0) if side == "BUY" else entry * (1 - tp_pct / 100.0)
                    tpsl["tp"] = await client.place_tpsl_order(coin, close_side, sz, tp_px, "tp")
                if sl_pct:
                    sl_px = entry * (1 - sl_pct / 100.0) if side == "BUY" else entry * (1 + sl_pct / 100.0)
                    tpsl["sl"] = await client.place_tpsl_order(coin, close_side, sz, sl_px, "sl")
            return {
                "status": "ok",
                "detail": "hyperliquid filled",
                "order": {
                    "orderId": res.get("orderId"),
                    "margin": margin,
                    "coin": coin,
                    "leverage": leverage,
                },
                "entry": entry,
                "size": sz,
                "tpsl": tpsl,
                "skipped_equity": skipped_equity,
            }
        finally:
            await client.close()

    return _run_async(_run())


def _exec_okx(
    cfg: Dict[str, Any],
    side: str,
    secrets: Dict[str, str],
    *,
    dry: bool,
    demo: bool = False,
) -> Dict[str, Any]:
    key = secrets.get("api_key") or ""
    sec = secrets.get("api_secret") or ""
    pwd = secrets.get("api_passphrase") or ""
    if not key or not sec or not pwd:
        return {"status": "error", "detail": "缺少 OKX 凭证"}

    coin = _base_coin(cfg.get("symbol") or "")
    inst_id = f"{coin}-USDT-SWAP"
    meta = _verify_okx(key, sec, pwd, demo=demo)
    equity = float(meta.get("equity") or 0)
    margin = _margin_usdt(cfg, equity)
    skipped_equity = False
    if margin <= 0 and _skip_equity_check():
        margin = _test_margin_usdt()
        skipped_equity = True
    if margin <= 0:
        return {"status": "error", "detail": f"仓位金额无效 equity={equity} margin={margin}"}

    tp_pct = _parse_pct(cfg.get("take_profit") or "")
    sl_pct = _parse_pct(cfg.get("stop_loss") or "")
    leverage = _leverage_from_cfg(cfg)
    okx_side = "buy" if side == "BUY" else "sell"
    pos_mode = _okx_pos_mode(key, sec, pwd, demo=demo)  # net_mode | long_short_mode
    # 净仓用 net；双向用 long/short（与 OKX 控制台 / okx_console 兜底一致）
    if pos_mode == "long_short_mode":
        pos_side = "long" if side == "BUY" else "short"
    else:
        pos_side = "net"

    if dry:
        return {
            "status": "ok",
            "detail": "dry-run",
            "margin": round(margin, 4),
            "equity": round(equity, 4),
            "instId": inst_id,
            "side": okx_side,
            "posSide": pos_side,
            "posMode": pos_mode,
            "leverage": leverage,
            "tp_pct": tp_pct,
            "sl_pct": sl_pct,
            "demo": demo,
            "skipped_equity": skipped_equity,
        }

    # 同向持仓跳过
    want_side = "Long" if side == "BUY" else "Short"
    for p in meta.get("positions") or []:
        if coin in str(p.get("symbol") or "").upper() and (p.get("side") or "") == want_side:
            return {"status": "skipped", "detail": f"已有 {want_side} 仓位，跳过"}

    # 模拟盘/实盘同一套：先设杠杆，再市价开仓；demo 仅多 x-simulated-trading 头
    lev_body: Dict[str, Any] = {
        "instId": inst_id,
        "lever": str(leverage),
        "mgnMode": "cross",
    }
    if pos_mode == "long_short_mode":
        lev_body["posSide"] = pos_side
    lev_res = _okx_private(
        "POST",
        "/api/v5/account/set-leverage",
        key,
        sec,
        pwd,
        body=lev_body,
        demo=demo,
    )

    # 名义≈保证金×杠杆，再换算张数
    notional = margin * leverage
    sz = _okx_size_from_margin(key, sec, pwd, inst_id, notional, demo=demo)
    if sz <= 0:
        return {"status": "error", "detail": "OKX 下单张数过小", "leverage_set": lev_res}

    body: Dict[str, Any] = {
        "instId": inst_id,
        "tdMode": "cross",
        "side": okx_side,
        "ordType": "market",
        "sz": str(sz),
    }
    if pos_mode == "long_short_mode":
        body["posSide"] = pos_side
    else:
        body["posSide"] = "net"
    mark = _okx_mark_price(inst_id, demo=demo) or 0.0
    if mark > 0 and (tp_pct or sl_pct):
        algo: Dict[str, Any] = {}
        if tp_pct:
            tp_px = mark * (1 + tp_pct / 100.0) if side == "BUY" else mark * (1 - tp_pct / 100.0)
            algo["tpTriggerPx"] = str(round(tp_px, 2))
            algo["tpOrdPx"] = "-1"
        if sl_pct:
            sl_px = mark * (1 - sl_pct / 100.0) if side == "BUY" else mark * (1 + sl_pct / 100.0)
            algo["slTriggerPx"] = str(round(sl_px, 2))
            algo["slOrdPx"] = "-1"
        if algo:
            body["attachAlgoOrds"] = [algo]

    order_res = _okx_private("POST", "/api/v5/trade/order", key, sec, pwd, body=body, demo=demo)
    if str(order_res.get("code")) not in ("0", "0.0"):
        return {
            "status": "error",
            "detail": f"OKX 开仓失败(交易所已收到请求, demo={demo}): {order_res.get('msg') or order_res}",
            "exchange_response": order_res,
            "leverage_set": lev_res,
            "request_body": body,
            "skipped_equity": skipped_equity,
        }

    return {
        "status": "ok",
        "detail": f"okx filled (demo={demo})",
        "order": order_res.get("data"),
        "margin": margin,
        "sz": sz,
        "instId": inst_id,
        "mark": mark,
        "leverage": leverage,
        "leverage_set": lev_res,
        "demo": demo,
        "posMode": pos_mode,
        "posSide": body.get("posSide"),
        "skipped_equity": skipped_equity,
        "tpsl_attached": bool(body.get("attachAlgoOrds")),
        "request_body": body,
    }


def _exec_close(
    cfg: Dict[str, Any],
    exchange: str,
    secrets: Dict[str, str],
    *,
    dry: bool,
    expect_side: Optional[str] = None,
    demo: bool = False,
) -> Dict[str, Any]:
    """平仓。expect_side=long|short|None：限制只平对应方向（对齐三策略）。"""
    expect = (expect_side or "").strip().lower() or None
    if dry:
        return {
            "status": "ok",
            "detail": f"dry-run close expect={expect or 'any'}",
            "exchange": exchange,
        }
    coin = _base_coin(cfg.get("symbol") or "")
    if exchange == "hyperliquid":
        from backpack_quant_trading.core.hyperliquid_client import HyperliquidAPIClient

        pk = secrets.get("private_key") or ""
        client = HyperliquidAPIClient(private_key=pk)

        async def _run():
            try:
                positions = await client.get_positions(symbol=coin)
                pos = None
                for p in positions or []:
                    psym = str(p.get("symbol") or "").split(":")[-1].upper()
                    if psym != coin:
                        continue
                    ps = (p.get("side") or "").lower()
                    if expect and ps and ps != expect:
                        continue
                    pos = p
                    break
                if not pos:
                    tip = f"无{expect}仓" if expect else "无持仓"
                    return {"status": "skipped", "detail": tip}
                close_side = "SELL" if (pos.get("side") or "").lower() == "long" else "BUY"
                sz = abs(float(pos.get("size") or 0))
                if sz <= 0:
                    return {"status": "skipped", "detail": "持仓数量为 0"}
                res = await client.place_order(coin, close_side, sz, order_type="MARKET", reduce_only=True)
                if res.get("status") != "FILLED":
                    return {"status": "error", "detail": str(res.get("error") or res)}
                return {"status": "ok", "detail": f"hyperliquid closed ({pos.get('side')})", "order": res}
            finally:
                await client.close()

        return _run_async(_run())

    # OKX close
    key = secrets.get("api_key") or ""
    sec = secrets.get("api_secret") or ""
    pwd = secrets.get("api_passphrase") or ""
    inst_id = f"{coin}-USDT-SWAP"
    meta = _verify_okx(key, sec, pwd, demo=demo)
    target = None
    for p in meta.get("positions") or []:
        if coin not in str(p.get("symbol") or "").upper():
            continue
        ps = "long" if (p.get("side") or "") in ("Long", "long") else "short"
        if expect and ps != expect:
            continue
        if abs(float(p.get("size") or 0)) > 0:
            target = p
            break
    if not target:
        tip = f"无{expect}仓" if expect else "无持仓"
        return {"status": "skipped", "detail": tip}
    pos_side = "long" if target.get("side") in ("Long", "long") else "short"
    okx_side = "sell" if pos_side == "long" else "buy"
    sz = abs(float(target.get("size") or 0))
    pos_mode = _okx_pos_mode(key, sec, pwd, demo=demo)
    body: Dict[str, Any] = {
        "instId": inst_id,
        "tdMode": "cross",
        "side": okx_side,
        "ordType": "market",
        "sz": str(sz),
        "reduceOnly": True,
    }
    if pos_mode == "long_short_mode":
        body["posSide"] = pos_side
    else:
        body["posSide"] = "net"
    order_res = _okx_private("POST", "/api/v5/trade/order", key, sec, pwd, body=body, demo=demo)
    if str(order_res.get("code")) not in ("0", "0.0"):
        return {"status": "error", "detail": f"OKX 平仓失败: {order_res.get('msg') or order_res}"}
    return {"status": "ok", "detail": f"okx closed ({pos_side})", "order": order_res.get("data")}


def _okx_pos_mode(api_key: str, api_secret: str, passphrase: str, *, demo: bool = False) -> str:
    """返回 net_mode 或 long_short_mode；失败时默认 net_mode（OKX 模拟盘常见）。"""
    try:
        res = _okx_private("GET", "/api/v5/account/config", api_key, api_secret, passphrase, demo=demo)
        rows = res.get("data") or []
        if rows:
            mode = str(rows[0].get("posMode") or "").strip()
            if mode in ("net_mode", "long_short_mode"):
                return mode
    except Exception as exc:
        logger.warning("OKX 读取 posMode 失败: %s", exc)
    return "net_mode"


def _okx_private(
    method: str,
    path: str,
    api_key: str,
    api_secret: str,
    passphrase: str,
    *,
    body: Optional[Dict[str, Any]] = None,
    demo: bool = False,
) -> Dict[str, Any]:
    import json as _json

    host = "https://www.okx.com"
    body_str = _json.dumps(body) if body is not None else ""
    ts = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    sign = _okx_sign(api_secret, ts, method, path, body_str)
    headers = {
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json",
    }
    if demo:
        headers["x-simulated-trading"] = "1"
    if method.upper() == "GET":
        resp = requests.get(f"{host}{path}", headers=headers, timeout=20)
    else:
        resp = requests.post(f"{host}{path}", headers=headers, data=body_str, timeout=20)
    try:
        return resp.json()
    except Exception:
        return {"code": str(resp.status_code), "msg": resp.text[:200]}


def _okx_mark_price(inst_id: str, *, demo: bool = False) -> Optional[float]:
    try:
        resp = requests.get(
            "https://www.okx.com/api/v5/public/mark-price",
            params={"instType": "SWAP", "instId": inst_id},
            timeout=15,
        )
        data = resp.json()
        rows = data.get("data") or []
        if rows:
            return float(rows[0].get("markPx") or 0)
    except Exception as exc:
        logger.warning("OKX mark price 失败: %s", exc)
    return None


def _okx_size_from_margin(
    api_key: str,
    api_secret: str,
    passphrase: str,
    inst_id: str,
    margin_usdt: float,
    *,
    demo: bool = False,
) -> float:
    """按保证金估算合约张数（简化：sz ≈ margin / markPx / ctVal，杠杆默认视为 1x 名义≈保证金）。"""
    mark = _okx_mark_price(inst_id, demo=demo) or 0.0
    if mark <= 0 or margin_usdt <= 0:
        return 0.0
    ct_val = 0.01  # BTC-USDT-SWAP 常见面值；ETH 等可能不同，尽量从 instruments 读
    try:
        resp = requests.get(
            "https://www.okx.com/api/v5/public/instruments",
            params={"instType": "SWAP", "instId": inst_id},
            timeout=15,
        )
        rows = (resp.json().get("data") or [])
        if rows and rows[0].get("ctVal"):
            ct_val = float(rows[0]["ctVal"])
    except Exception:
        pass
    # 名义价值 = margin（简化，不乘杠杆）；张数 = 名义 / (mark * ctVal)
    notional = margin_usdt
    raw = notional / (mark * ct_val) if mark * ct_val > 0 else 0
    # OKX SWAP sz 多为整数张或小数，保留 2 位
    return max(round(raw, 2), 0.0)
