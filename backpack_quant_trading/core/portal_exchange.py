"""普通用户交易所连接：本期支持 Hyperliquid 私钥 + OKX API Key。"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, Optional

import requests

from backpack_quant_trading.core import portal_store as store
from backpack_quant_trading.core.live_instance_store import (
    load_secrets_from_config,
    sanitize_and_encrypt_config,
    strip_secrets_for_api,
)
from backpack_quant_trading.utils.instance_crypto import decrypt_field, encrypt_field

logger = logging.getLogger(__name__)

SUPPORTED = ("okx", "hyperliquid")
PLATFORM_LABEL = {
    "okx": "欧意 OKX",
    "hyperliquid": "Hyperliquid",
    "binance": "币安",
    store.BOOK_PLATFORM_CRYPTO: store.BOOK_PLATFORM_LABELS[store.BOOK_PLATFORM_CRYPTO],
    store.BOOK_PLATFORM_US: store.BOOK_PLATFORM_LABELS[store.BOOK_PLATFORM_US],
}


def _normalize_platform(raw: str) -> str:
    key = (raw or "").strip().lower()
    aliases = {
        "okx": "okx",
        "欧意": "okx",
        "ouyi": "okx",
        "hyperliquid": "hyperliquid",
        "hype": "hyperliquid",
        "hl": "hyperliquid",
        "binance": "binance",
        "币安": "binance",
    }
    return aliases.get(key, key)


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
        # 余额页不能被交易所卡住两分钟，否则前端整页超时
        return pool.submit(_in_thread).result(timeout=12)


def _verify_hyperliquid(private_key: str) -> Dict[str, Any]:
    from backpack_quant_trading.core.hyperliquid_client import HyperliquidAPIClient

    client = HyperliquidAPIClient(private_key=private_key)

    async def _run():
        try:
            state = await client.post_info({
                "type": "clearinghouseState",
                "user": client.address,
                "dex": "",
            }) or {}
            summary = state.get("marginSummary") or {}
            equity = float(summary.get("accountValue") or state.get("withdrawable") or 0)
            available = float(state.get("withdrawable") or 0)
            positions = []
            for p in state.get("assetPositions") or []:
                pos = (p or {}).get("position") or {}
                coin = pos.get("coin") or ""
                szi = float(pos.get("szi") or 0)
                if not coin or abs(szi) < 1e-12:
                    continue
                upnl = float(pos.get("unrealizedPnl") or 0)
                positions.append({
                    "symbol": coin,
                    "side": "Long" if szi > 0 else "Short",
                    "size": abs(szi),
                    "pnl": upnl,
                    "pnl_pct": None,
                })
            return {
                "ok": True,
                "address": client.address,
                "balance": available,
                "equity": equity,
                "currency": "USDC",
                "positions": positions,
            }
        finally:
            await client.close()

    return _run_async(_run())


def _okx_sign(secret: str, timestamp: str, method: str, path: str, body: str = "") -> str:
    msg = f"{timestamp}{method.upper()}{path}{body}"
    dig = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(dig).decode("ascii")


def _verify_okx(api_key: str, api_secret: str, passphrase: str, *, demo: bool = False) -> Dict[str, Any]:
    host = "https://www.okx.com"
    path = "/api/v5/account/balance"
    ts = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    sign = _okx_sign(api_secret, ts, "GET", path)
    headers = {
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json",
    }
    if demo:
        headers["x-simulated-trading"] = "1"
    resp = requests.get(f"{host}{path}", headers=headers, timeout=8)
    data = {}
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text[:200]}
    code = str(data.get("code", ""))
    if resp.status_code != 200 or code not in ("0", "0.0"):
        msg = data.get("msg") or data.get("detail") or resp.text[:160] or f"HTTP {resp.status_code}"
        raise ValueError(f"OKX 校验失败: {msg}")
    details = (data.get("data") or [{}])[0]
    total_raw = details.get("totalEq") or details.get("adjEq") or "0"
    try:
        equity = float(total_raw)
    except (TypeError, ValueError):
        equity = 0.0
    available = 0.0
    for d in details.get("details") or []:
        if (d.get("ccy") or "").upper() == "USDT":
            try:
                available = float(d.get("availBal") or d.get("cashBal") or 0)
            except (TypeError, ValueError):
                available = 0.0
            break
    positions = _okx_positions(api_key, api_secret, passphrase, demo=demo)
    return {
        "ok": True,
        "total_eq": equity,
        "equity": equity,
        "balance": available if available else equity,
        "currency": "USDT",
        "demo": bool(demo),
        "positions": positions,
    }


def _okx_positions(api_key: str, api_secret: str, passphrase: str, *, demo: bool = False) -> List[Dict[str, Any]]:
    host = "https://www.okx.com"
    path = "/api/v5/account/positions"
    ts = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    sign = _okx_sign(api_secret, ts, "GET", path)
    headers = {
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json",
    }
    if demo:
        headers["x-simulated-trading"] = "1"
    try:
        resp = requests.get(f"{host}{path}", headers=headers, timeout=8)
        data = resp.json()
    except Exception as exc:
        logger.warning("OKX positions 失败: %s", exc)
        return []
    if str(data.get("code", "")) not in ("0", "0.0"):
        return []
    out: List[Dict[str, Any]] = []
    for row in data.get("data") or []:
        try:
            pos = float(row.get("pos") or 0)
        except (TypeError, ValueError):
            pos = 0.0
        if abs(pos) < 1e-12:
            continue
        inst = (row.get("instId") or "").replace("-SWAP", "").replace("-USDT", "")
        side = (row.get("posSide") or "").lower()
        if side in ("long", "short"):
            side_label = "Long" if side == "long" else "Short"
        else:
            side_label = "Long" if pos > 0 else "Short"
        try:
            upnl = float(row.get("upl") or 0)
        except (TypeError, ValueError):
            upnl = 0.0
        try:
            upl_ratio = float(row.get("uplRatio") or 0) * 100
        except (TypeError, ValueError):
            upl_ratio = None
        out.append({
            "symbol": inst or row.get("instId") or "?",
            "side": side_label,
            "size": abs(pos),
            "pnl": upnl,
            "pnl_pct": upl_ratio,
        })
    return out


def _secrets_from_binding(cfg: Dict[str, Any]) -> Dict[str, str]:
    secrets = load_secrets_from_config(cfg)
    if cfg.get("api_key_enc") and "api_key" not in secrets:
        try:
            secrets["api_key"] = decrypt_field(str(cfg["api_key_enc"]))
        except Exception as exc:
            logger.error("解密 api_key_enc 失败: %s", exc)
            raise
    return secrets


def _fetch_one_exchange_binding(r: Dict[str, Any]) -> tuple:
    """单交易所余额；返回 (account_item, positions_list, equity_ok)。"""
    plat = (r.get("platform") or "").lower()
    cfg = r.get("config") or {}
    item: Dict[str, Any] = {
        "platform": plat,
        "platform_label": PLATFORM_LABEL.get(plat, plat),
        "label": (cfg.get("label") or "").strip(),
        "status": "error",
        "equity": None,
        "balance": None,
        "currency": "USD",
        "address_mask": cfg.get("address_mask") or "",
        "api_key_mask": cfg.get("api_key_mask") or "",
        "account_id": cfg.get("address_mask") or cfg.get("api_key_mask") or plat,
        "demo": bool(cfg.get("demo")),
        "error": "",
    }
    pos_out: List[Dict[str, Any]] = []
    equity_ok = 0.0
    try:
        secrets = _secrets_from_binding(cfg)
        if plat == "hyperliquid":
            pk = secrets.get("private_key") or ""
            if not pk:
                raise ValueError("缺少 Hyperliquid 私钥")
            meta = _verify_hyperliquid(pk)
            equity = float(meta.get("equity") or meta.get("balance") or 0)
            mask = _mask_addr(meta.get("address") or cfg.get("address") or "")
            item.update({
                "status": "ok",
                "equity": equity,
                "balance": float(meta.get("balance") or 0),
                "currency": meta.get("currency") or "USDC",
                "address_mask": mask,
                "account_id": mask or plat,
            })
            equity_ok = equity
            for p in meta.get("positions") or []:
                pos_out.append({**p, "platform": plat})
        elif plat == "okx":
            key = secrets.get("api_key") or ""
            sec = secrets.get("api_secret") or ""
            pwd = secrets.get("api_passphrase") or ""
            if not key or not sec or not pwd:
                raise ValueError("缺少 OKX 凭证")
            meta = _verify_okx(key, sec, pwd, demo=bool(cfg.get("demo")))
            equity = float(meta.get("equity") or 0)
            key_mask = cfg.get("api_key_mask") or _mask_key(key)
            item.update({
                "status": "ok",
                "equity": equity,
                "balance": float(meta.get("balance") or equity),
                "currency": meta.get("currency") or "USDT",
                "api_key_mask": key_mask,
                "account_id": key_mask or plat,
            })
            equity_ok = equity
            for p in meta.get("positions") or []:
                pos_out.append({**p, "platform": plat})
        else:
            item["error"] = "暂不支持查询该平台余额"
    except Exception as exc:
        logger.warning("拉取余额失败 platform=%s: %s", plat, exc)
        item["error"] = str(exc)[:200]
    if not item.get("account_id"):
        item["account_id"] = item.get("address_mask") or item.get("api_key_mask") or plat
    return item, pos_out, equity_ok


def _build_book_accounts(user_id: int) -> tuple:
    """本地账面账户（快路径，不访问交易所）。"""
    book_accounts: List[Dict[str, Any]] = []
    positions: List[Dict[str, Any]] = []
    total = 0.0
    try:
        store.maybe_restore_scaled_legacy_books()
    except Exception as exc:
        logger.warning("legacy 账面恢复检查失败: %s", exc)
    try:
        store.ensure_empty_dynamic_book_trades_cloned()
    except Exception as exc:
        logger.warning("动态账面成交补齐失败: %s", exc)
    for book_plat, market in (
        (store.BOOK_PLATFORM_CRYPTO, "crypto"),
        (store.BOOK_PLATFORM_US, "us"),
    ):
        init_cap = store.get_book_initial_capital(book_plat)
        eq = store.book_account_equity(user_id, book_plat)
        book_accounts.append(
            {
                "platform": book_plat,
                "platform_label": store.BOOK_PLATFORM_LABELS.get(book_plat, book_plat),
                "title": store.BOOK_MARKET_TITLES.get(market, book_plat),
                "market": market,
                "label": "账面账户",
                "status": "ok",
                "equity": eq,
                "balance": eq,
                "currency": "USD",
                "address_mask": "",
                "api_key_mask": "",
                "account_id": _book_display_id(book_plat),
                "demo": False,
                "book": True,
                "initial_capital": init_cap,
                "error": "",
            }
        )
        total += float(eq or 0)
    try:
        for dyn in store.list_portal_book_accounts():
            book_accounts.append(
                {
                    "platform": dyn["platform"],
                    "platform_label": dyn.get("platform_label") or dyn["platform"],
                    "title": dyn.get("title") or dyn["platform"],
                    "market": dyn.get("market") or "crypto",
                    "book_account_id": dyn.get("id"),
                    "label": dyn.get("label") or "账面账户",
                    "status": "ok",
                    "equity": dyn.get("equity"),
                    "balance": dyn.get("equity"),
                    "currency": "USD",
                    "address_mask": "",
                    "api_key_mask": "",
                    "account_id": dyn.get("account_no") or dyn["platform"],
                    "demo": False,
                    "book": True,
                    "initial_capital": dyn.get("initial_capital"),
                    "error": "",
                }
            )
            total += float(dyn.get("equity") or 0)
    except Exception as exc:
        logger.warning("动态账面账户列表失败: %s", exc)
    try:
        positions.extend(store.list_book_open_positions(""))
    except Exception as exc:
        logger.warning("账面持仓还原失败: %s", exc)
    return book_accounts, positions, total


def fetch_balances(user_id: int, *, include_book: bool = False) -> Dict[str, Any]:
    """登录后拉已绑定交易所余额/持仓；账面加密/美股仅管理员可见。

    账面先算（本地秒回）；交易所并行拉取且单平台限时，避免拖垮整页。
    """
    if include_book:
        try:
            store.ensure_book_account_csv_trades(user_id)
        except Exception as exc:
            logger.warning("ensure book csv trades failed: %s", exc)

    accounts: List[Dict[str, Any]] = []
    positions: List[Dict[str, Any]] = []
    total_equity = 0.0
    exchange_equity = 0.0

    # 1) 账面优先：本地库，不依赖外网
    if include_book:
        book_accounts, book_pos, book_eq = _build_book_accounts(user_id)
        accounts.extend(book_accounts)
        positions.extend(book_pos)
        total_equity += book_eq

    # 2) 交易所并行（单平台最多 ~12s，整体不串行叠加）
    rows = store.list_exchange_bindings(user_id)
    if rows:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        from concurrent.futures import TimeoutError as FuturesTimeout

        with ThreadPoolExecutor(max_workers=min(4, len(rows))) as pool:
            futs = {pool.submit(_fetch_one_exchange_binding, r): r for r in rows}
            pending = set(futs.keys())
            try:
                for fut in as_completed(futs, timeout=16):
                    pending.discard(fut)
                    r = futs[fut]
                    plat = (r.get("platform") or "").lower()
                    try:
                        item, pos_out, eq = fut.result(timeout=1)
                    except Exception as exc:
                        logger.warning("交易所余额失败 platform=%s: %s", plat, exc)
                        item = {
                            "platform": plat,
                            "platform_label": PLATFORM_LABEL.get(plat, plat),
                            "label": "",
                            "status": "error",
                            "equity": None,
                            "balance": None,
                            "currency": "USD",
                            "address_mask": "",
                            "api_key_mask": "",
                            "account_id": plat,
                            "demo": False,
                            "error": str(exc)[:200] or "拉取失败",
                        }
                        pos_out, eq = [], 0.0
                    accounts.append(item)
                    positions.extend(pos_out)
                    total_equity += float(eq or 0)
                    exchange_equity += float(eq or 0)
            except FuturesTimeout:
                logger.warning("交易所余额整体超时，剩余 %s 个平台跳过", len(pending))
            for fut in pending:
                r = futs[fut]
                plat = (r.get("platform") or "").lower()
                accounts.append({
                    "platform": plat,
                    "platform_label": PLATFORM_LABEL.get(plat, plat),
                    "label": "",
                    "status": "error",
                    "equity": None,
                    "balance": None,
                    "currency": "USD",
                    "address_mask": "",
                    "api_key_mask": "",
                    "account_id": plat,
                    "demo": False,
                    "error": "拉取超时",
                })

    # 持仓挂上观察库策略名（connected 配置）；账面仓已自带 strategy_name
    try:
        cfgs = store.list_connected_watch_configs(user_id)
        for p in positions:
            if p.get("book") and p.get("strategy_name"):
                continue
            name = store.match_strategy_for_position(
                cfgs,
                symbol=str(p.get("symbol") or ""),
                platform=str(p.get("platform") or ""),
            )
            p["strategy_name"] = name
    except Exception as exc:
        logger.warning("持仓匹配策略名失败: %s", exc)
        for p in positions:
            p.setdefault("strategy_name", "")

    exchange_ok = any(
        a.get("status") == "ok" and not a.get("book")
        for a in accounts
    )
    return {
        "connected": exchange_ok,
        "accounts": accounts,
        "positions": positions,
        "total_equity": round(total_equity, 4),
        "exchange_equity": round(exchange_equity, 4),
        "currency": "USD",
    }


def connect_exchange(
    user_id: int,
    platform: str,
    *,
    private_key: str = "",
    api_key: str = "",
    api_secret: str = "",
    passphrase: str = "",
    label: str = "",
    demo: bool = False,
    symbols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    plat = _normalize_platform(platform)
    if plat == "binance":
        raise ValueError("币安连接即将支持，本次请先用 Hyperliquid 或欧意 OKX")
    if plat not in SUPPORTED:
        raise ValueError("不支持的交易平台")

    verify_meta: Dict[str, Any] = {}
    secrets: Dict[str, Any] = {}
    public: Dict[str, Any] = {
        "platform": plat,
        "label": (label or "").strip(),
        "demo": bool(demo) if plat == "okx" else False,
    }

    if plat == "hyperliquid":
        pk = (private_key or "").strip()
        if not pk:
            raise ValueError("请输入 Hyperliquid 私钥")
        verify_meta = _verify_hyperliquid(pk)
        secrets["private_key"] = pk
        public["address"] = verify_meta.get("address") or ""
        public["address_mask"] = _mask_addr(public["address"])
    else:
        key = (api_key or "").strip()
        sec = (api_secret or "").strip()
        pwd = (passphrase or "").strip()
        if not key or not sec or not pwd:
            raise ValueError("OKX 需要填写 API Key、Secret、Passphrase")
        verify_meta = _verify_okx(key, sec, pwd, demo=demo)
        secrets["api_secret"] = sec
        secrets["api_passphrase"] = pwd
        public["api_key_mask"] = _mask_key(key)

    cleaned = sanitize_and_encrypt_config(public, secrets)
    if plat == "okx":
        cleaned["api_key_enc"] = encrypt_field((api_key or "").strip())
        cleaned.pop("api_key", None)

    row = store.upsert_exchange_binding(user_id, plat, cleaned)
    linked = []
    if symbols:
        linked = store.mark_watch_connected(user_id, symbols, plat)

    return {
        "binding": strip_secrets_for_api({**row, **{k: v for k, v in cleaned.items() if not str(k).endswith("_enc")}}),
        "verify": {k: v for k, v in verify_meta.items() if k != "ok"},
        "linked": linked,
        "platform_label": PLATFORM_LABEL.get(plat, plat),
    }


def disconnect_exchange(user_id: int, platform: str) -> Dict[str, Any]:
    plat = _normalize_platform(platform)
    if plat in (store.BOOK_PLATFORM_CRYPTO, store.BOOK_PLATFORM_US):
        raise ValueError("账面账户不可断开，请在平台筛选中切换查看")
    if plat not in SUPPORTED and plat != "binance":
        raise ValueError("不支持的交易平台")
    ok = store.delete_exchange_binding(user_id, plat)
    if not ok:
        raise ValueError(f"未找到已连接的 {PLATFORM_LABEL.get(plat, plat)}")
    return {"platform": plat, "platform_label": PLATFORM_LABEL.get(plat, plat), "disconnected": True}


def list_bindings(user_id: int) -> List[Dict[str, Any]]:
    rows = store.list_exchange_bindings(user_id)
    out = []
    for r in rows:
        cfg = r.get("config") or {}
        safe = strip_secrets_for_api(cfg)
        out.append({
            "id": r["id"],
            "platform": r["platform"],
            "platform_label": PLATFORM_LABEL.get(r["platform"], r["platform"]),
            "label": safe.get("label") or "",
            "address_mask": safe.get("address_mask") or "",
            "api_key_mask": safe.get("api_key_mask") or "",
            "demo": bool(safe.get("demo")),
            "status": r.get("status") or "connected",
            "updated_at": r.get("updated_at") or "",
            "has_secrets": bool(
                cfg.get("private_key_enc")
                or cfg.get("api_secret_enc")
                or cfg.get("api_key_enc")
            ),
        })
    return out


def _book_display_id(book_plat: str) -> str:
    """账面账户展示用 id：与 Hype 地址掩码同风格，按平台稳定生成。"""
    dig = hashlib.sha256(f"portal-book-id:{book_plat}".encode("utf-8")).hexdigest()
    return f"0x{dig[:4]}…{dig[-4:]}"


def _mask_addr(addr: str) -> str:
    a = (addr or "").strip()
    if len(a) < 10:
        return a
    return f"{a[:6]}…{a[-4:]}"


def _mask_key(key: str) -> str:
    k = (key or "").strip()
    if len(k) < 8:
        return "****"
    return f"{k[:4]}…{k[-4:]}"
