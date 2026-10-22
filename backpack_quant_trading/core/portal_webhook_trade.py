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


def _dry_run() -> bool:
    return (os.getenv("PORTAL_WEBHOOK_DRY_RUN") or "").strip().lower() in ("1", "true", "yes", "on")


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
    results: List[Dict[str, Any]] = []
    executed = 0

    for cfg in configs:
        uid = cfg.get("user_id")
        exchange = (cfg.get("exchange") or "").strip().lower()
        item: Dict[str, Any] = {
            "config_id": cfg.get("id"),
            "user_id": uid,
            "symbol": cfg.get("symbol"),
            "strategy_name": cfg.get("strategy_name"),
            "timeframe": cfg.get("timeframe"),
            "exchange": exchange,
            "status": "skipped",
            "detail": "",
        }
        if not uid:
            item["detail"] = "配置缺少 user_id"
            results.append(item)
            continue
        if exchange not in ("hyperliquid", "okx"):
            item["detail"] = f"交易所未支持或未绑定: {exchange or '(空)'}"
            results.append(item)
            continue
        binding = store.get_exchange_binding(int(uid), exchange)
        if not binding:
            item["detail"] = f"用户未绑定 {exchange}"
            results.append(item)
            continue
        try:
            secrets = _secrets_from_binding(binding.get("config") or {})
            if side == "CLOSE":
                out = _exec_close(cfg, exchange, secrets, dry=dry)
            elif exchange == "hyperliquid":
                out = _exec_hyperliquid(cfg, side, secrets, dry=dry)
            else:
                out = _exec_okx(cfg, side, secrets, dry=dry, demo=bool((binding.get("config") or {}).get("demo")))
            item.update(out)
            if out.get("status") == "ok":
                executed += 1
        except Exception as exc:
            logger.exception("portal webhook 执行失败 cfg=%s", cfg.get("id"))
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
            "timeframe": _norm_tf(tf),
            "strategy_name": strategy_name,
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
    if margin <= 0:
        return {"status": "error", "detail": f"仓位金额无效 equity={equity} margin={margin}"}

    tp_pct = _parse_pct(cfg.get("take_profit") or "")
    sl_pct = _parse_pct(cfg.get("stop_loss") or "")

    if dry:
        return {
            "status": "ok",
            "detail": "dry-run",
            "margin": round(margin, 4),
            "equity": round(equity, 4),
            "coin": coin,
            "side": side,
            "tp_pct": tp_pct,
            "sl_pct": sl_pct,
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
            res = await client.place_order(
                symbol=coin,
                side=side,
                quantity=margin,
                order_type="MARKET",
                leverage=5,
            )
            if res.get("status") != "FILLED":
                return {"status": "error", "detail": f"开仓失败: {res.get('error') or res}"}

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
                close_side = "SELL" if side == "BUY" else "BUY"
                if tp_pct:
                    tp_px = entry * (1 + tp_pct / 100.0) if side == "BUY" else entry * (1 - tp_pct / 100.0)
                    tpsl["tp"] = await client.place_tpsl_order(coin, close_side, sz, tp_px, "tp")
                if sl_pct:
                    sl_px = entry * (1 - sl_pct / 100.0) if side == "BUY" else entry * (1 + sl_pct / 100.0)
                    tpsl["sl"] = await client.place_tpsl_order(coin, close_side, sz, sl_px, "sl")
            return {
                "status": "ok",
                "detail": "hyperliquid filled",
                "order": {"orderId": res.get("orderId"), "margin": margin, "coin": coin},
                "entry": entry,
                "size": sz,
                "tpsl": tpsl,
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
    if margin <= 0:
        return {"status": "error", "detail": f"仓位金额无效 equity={equity} margin={margin}"}

    tp_pct = _parse_pct(cfg.get("take_profit") or "")
    sl_pct = _parse_pct(cfg.get("stop_loss") or "")
    pos_side = "long" if side == "BUY" else "short"
    okx_side = "buy" if side == "BUY" else "sell"

    if dry:
        return {
            "status": "ok",
            "detail": "dry-run",
            "margin": round(margin, 4),
            "equity": round(equity, 4),
            "instId": inst_id,
            "side": okx_side,
            "posSide": pos_side,
            "tp_pct": tp_pct,
            "sl_pct": sl_pct,
        }

    # 同向持仓跳过
    for p in meta.get("positions") or []:
        if coin in str(p.get("symbol") or "").upper() and (p.get("side") or "") == ("Long" if pos_side == "long" else "Short"):
            return {"status": "skipped", "detail": f"已有 {pos_side} 仓位，跳过"}

    # 张数：用 USDT 保证金 / (标记价 * ctVal) 近似；简化：sz = margin（合约面值需查 instruments）
    sz = _okx_size_from_margin(key, sec, pwd, inst_id, margin, demo=demo)
    if sz <= 0:
        return {"status": "error", "detail": "OKX 下单张数过小"}

    body: Dict[str, Any] = {
        "instId": inst_id,
        "tdMode": "cross",
        "side": okx_side,
        "posSide": pos_side,
        "ordType": "market",
        "sz": str(sz),
    }
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
        return {"status": "error", "detail": f"OKX 开仓失败: {order_res.get('msg') or order_res}"}

    return {
        "status": "ok",
        "detail": "okx filled",
        "order": order_res.get("data"),
        "margin": margin,
        "sz": sz,
        "instId": inst_id,
        "mark": mark,
    }


def _exec_close(cfg: Dict[str, Any], exchange: str, secrets: Dict[str, str], *, dry: bool) -> Dict[str, Any]:
    if dry:
        return {"status": "ok", "detail": "dry-run close", "exchange": exchange}
    coin = _base_coin(cfg.get("symbol") or "")
    if exchange == "hyperliquid":
        from backpack_quant_trading.core.hyperliquid_client import HyperliquidAPIClient

        pk = secrets.get("private_key") or ""
        client = HyperliquidAPIClient(private_key=pk)

        async def _run():
            try:
                positions = await client.get_positions(symbol=coin)
                pos = next((p for p in (positions or []) if (p.get("symbol") or "").upper() == coin), None)
                if not pos:
                    return {"status": "skipped", "detail": "无持仓"}
                close_side = "SELL" if (pos.get("side") or "").lower() == "long" else "BUY"
                sz = abs(float(pos.get("size") or 0))
                res = await client.place_order(coin, close_side, sz, order_type="MARKET", reduce_only=True)
                if res.get("status") != "FILLED":
                    return {"status": "error", "detail": str(res.get("error") or res)}
                return {"status": "ok", "detail": "hyperliquid closed", "order": res}
            finally:
                await client.close()

        return _run_async(_run())

    # OKX close
    key = secrets.get("api_key") or ""
    sec = secrets.get("api_secret") or ""
    pwd = secrets.get("api_passphrase") or ""
    inst_id = f"{coin}-USDT-SWAP"
    meta = _verify_okx(key, sec, pwd, demo=False)
    target = None
    for p in meta.get("positions") or []:
        if coin in str(p.get("symbol") or "").upper():
            target = p
            break
    if not target:
        return {"status": "skipped", "detail": "无持仓"}
    pos_side = "long" if target.get("side") == "Long" else "short"
    okx_side = "sell" if pos_side == "long" else "buy"
    sz = float(target.get("size") or 0)
    body = {
        "instId": inst_id,
        "tdMode": "cross",
        "side": okx_side,
        "posSide": pos_side,
        "ordType": "market",
        "sz": str(sz),
        "reduceOnly": True,
    }
    order_res = _okx_private("POST", "/api/v5/trade/order", key, sec, pwd, body=body, demo=False)
    if str(order_res.get("code")) not in ("0", "0.0"):
        return {"status": "error", "detail": f"OKX 平仓失败: {order_res.get('msg') or order_res}"}
    return {"status": "ok", "detail": "okx closed", "order": order_res.get("data")}


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
