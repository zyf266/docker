"""现货 24h 资金净流入监控（币种监视页）。

口径对齐币安「24小时资金净流入(BASE)」：
  5m K 线 net = 2 * taker_buy_base_volume - volume（标的币数量，非 USDT）
滚动 24h = 最近 288 根之和；自然日按北京时间切日并求和。
"""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from backpack_quant_trading.core.binance_monitor import (
    fetch_binance_klines,
    send_dingtalk_alert,
)

logger = logging.getLogger(__name__)

BJ = timezone(timedelta(hours=8))
INTERVAL_MS = 5 * 60 * 1000
BARS_24H = 24 * 60 // 5  # 288
POLL_SEC = 300
ALERT_MULT = 1.5

_QUOTE_SUFFIXES = (
    "USDT", "FDUSD", "TUSD", "USDC", "BUSD", "BTC", "ETH", "BNB",
    "TRY", "EUR", "JPY", "BRL", "DAI", "USD1", "AEUR",
)


def base_asset_of_symbol(symbol: str) -> str:
    u = str(symbol or "").upper()
    for q in _QUOTE_SUFFIXES:
        if u.endswith(q) and len(u) > len(q):
            return u[: -len(q)]
    return u


def _bar_net(bar: Dict[str, Any]) -> float:
    """币安同款：净流入 = 主动买入量 - 主动卖出量（base 数量）。"""
    vol = float(bar.get("volume") or 0)
    tb = float(bar.get("taker_buy_base_volume") or 0)
    return 2.0 * tb - vol


def _bj_day_key(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=BJ).strftime("%Y-%m-%d")


def _now_bj() -> datetime:
    return datetime.now(tz=BJ)


@dataclass
class SymbolSnapshot:
    symbol: str
    base_asset: str = ""
    net_24h: float = 0.0
    yesterday_max: float = 0.0
    threshold_1_5x: float = 0.0
    daily_nets: Dict[str, float] = field(default_factory=dict)
    chart_times: List[str] = field(default_factory=list)
    chart_cumulative: List[float] = field(default_factory=list)
    last_error: str = ""
    last_alerts: List[str] = field(default_factory=list)
    updated_at: str = ""


def compute_snapshot_from_klines(symbol: str, klines: List[Dict[str, Any]]) -> SymbolSnapshot:
    """纯计算：供服务与单测使用。"""
    sym = symbol.upper()
    snap = SymbolSnapshot(symbol=sym, base_asset=base_asset_of_symbol(sym))
    if not klines:
        snap.last_error = "无K线"
        return snap

    points: List[Tuple[int, float]] = []
    for bar in klines:
        try:
            ts = int(bar["open_time"])
            points.append((ts, _bar_net(bar)))
        except Exception:
            continue
    if not points:
        snap.last_error = "K线解析失败"
        return snap

    points.sort(key=lambda x: x[0])
    last_ts = points[-1][0]
    window_start = last_ts - (BARS_24H - 1) * INTERVAL_MS
    window = [(t, n) for t, n in points if t >= window_start]
    snap.net_24h = sum(n for _, n in window)

    # 累计曲线（对齐币安页面观感）
    cum = 0.0
    for t, n in window:
        cum += n
        dt = datetime.fromtimestamp(t / 1000.0, tz=BJ)
        snap.chart_times.append(dt.strftime("%m-%d %H:%M"))
        snap.chart_cumulative.append(round(cum, 4))

    # 自然日汇总
    daily: Dict[str, float] = {}
    for t, n in points:
        k = _bj_day_key(t)
        daily[k] = daily.get(k, 0.0) + n
    snap.daily_nets = {k: round(v, 4) for k, v in sorted(daily.items())}

    yesterday = (_now_bj() - timedelta(days=1)).strftime("%Y-%m-%d")
    y_points = [n for t, n in points if _bj_day_key(t) == yesterday]
    if y_points:
        snap.yesterday_max = max(y_points)
    else:
        snap.yesterday_max = 0.0
    snap.threshold_1_5x = abs(snap.yesterday_max) * ALERT_MULT
    snap.updated_at = _now_bj().strftime("%Y-%m-%d %H:%M:%S")
    return snap


def evaluate_alert_conditions(snap: SymbolSnapshot) -> List[str]:
    """返回触发的条件文案列表。"""
    hits: List[str] = []
    if snap.threshold_1_5x > 0 and snap.net_24h > snap.threshold_1_5x:
        hits.append(
            f"条件1: 滚动24h净流入 {snap.net_24h:.2f} > 昨天最大值绝对值×1.5 "
            f"(|{snap.yesterday_max:.2f}|×1.5={snap.threshold_1_5x:.2f})"
        )

    today = _now_bj().date()
    d0 = today.strftime("%Y-%m-%d")
    d1 = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    d2 = (today - timedelta(days=2)).strftime("%Y-%m-%d")
    n0 = snap.daily_nets.get(d0)
    n1 = snap.daily_nets.get(d1)
    n2 = snap.daily_nets.get(d2)

    if n0 is not None and n1 is not None and n0 > 0 and n1 > 0 and n0 > n1:
        hits.append(f"条件2: 连续2日净流入为正且递增 ({d1}={n1:.2f} → {d0}={n0:.2f})")

    if (
        n0 is not None
        and n1 is not None
        and n2 is not None
        and n0 > 0
        and n1 > 0
        and n2 > 0
        and n1 > n2
        and n0 > n1
    ):
        hits.append(
            f"条件3: 连续3日净流入为正且递增 ({d2}={n2:.2f} → {d1}={n1:.2f} → {d0}={n0:.2f})"
        )
    return hits


class SpotNetInflowMonitorService:
    def __init__(self, symbols: List[str]):
        self.symbols = sorted({str(s).upper().strip() for s in symbols if str(s).strip()})
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._snapshots: Dict[str, SymbolSnapshot] = {}

    @property
    def running(self) -> bool:
        return self._running

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            snaps = {
                s: {
                    "symbol": sn.symbol,
                    "base_asset": sn.base_asset or base_asset_of_symbol(s),
                    "net_24h": round(sn.net_24h, 4),
                    "yesterday_max": round(sn.yesterday_max, 4),
                    "threshold_1_5x": round(sn.threshold_1_5x, 4),
                    "daily_nets": sn.daily_nets,
                    "last_error": sn.last_error,
                    "last_alerts": sn.last_alerts,
                    "updated_at": sn.updated_at,
                }
                for s, sn in self._snapshots.items()
            }
        return {
            "running": self._running,
            "symbols": list(self.symbols),
            "poll_sec": POLL_SEC,
            "unit": "base",
            "snapshots": snaps,
        }

    def get_series(self, symbol: str) -> Dict[str, Any]:
        sym = symbol.upper().strip()
        with self._lock:
            sn = self._snapshots.get(sym)
            if not sn:
                return {
                    "symbol": sym,
                    "base_asset": base_asset_of_symbol(sym),
                    "unit": "base",
                    "times": [],
                    "values": [],
                    "net_24h": 0,
                }
            return {
                "symbol": sym,
                "base_asset": sn.base_asset or base_asset_of_symbol(sym),
                "unit": "base",
                "times": list(sn.chart_times),
                "values": list(sn.chart_cumulative),
                "net_24h": round(sn.net_24h, 4),
                "updated_at": sn.updated_at,
                "last_error": sn.last_error,
            }

    def start(self):
        if self._running:
            return
        if not self.symbols:
            raise ValueError("请选择至少一个现货币种")
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="spot-net-inflow", daemon=True)
        self._thread.start()
        logger.info("[现货净流入] 已启动 symbols=%s", self.symbols)

    def stop(self):
        self._running = False
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=5)
        self._thread = None
        logger.info("[现货净流入] 已停止")

    def _loop(self):
        while self._running:
            try:
                self._tick_all()
            except Exception as e:
                logger.exception("[现货净流入] tick 异常: %s", e)
            for _ in range(POLL_SEC):
                if not self._running:
                    break
                time.sleep(1)

    def _tick_all(self):
        for sym in list(self.symbols):
            if not self._running:
                break
            try:
                self._tick_one(sym)
            except Exception as e:
                logger.warning("[现货净流入] %s 失败: %s", sym, e)
                with self._lock:
                    sn = self._snapshots.get(sym) or SymbolSnapshot(symbol=sym)
                    sn.last_error = str(e)
                    sn.updated_at = _now_bj().strftime("%Y-%m-%d %H:%M:%S")
                    self._snapshots[sym] = sn
            time.sleep(0.2)  # 轻微限速

    def _fetch_klines(self, symbol: str) -> List[Dict[str, Any]]:
        # 约 4 天 5m ≈ 1152，分两批 limit=1000
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - 4 * 24 * 60 * 60 * 1000
        batch1 = fetch_binance_klines(
            symbol, "5m", limit=1000, market="spot", start_time=start_ms, end_time=end_ms
        ) or []
        if len(batch1) < 900:
            return batch1
        # 若被截断，再向前补一截
        earliest = int(batch1[0]["open_time"])
        batch0 = fetch_binance_klines(
            symbol,
            "5m",
            limit=1000,
            market="spot",
            start_time=start_ms,
            end_time=earliest - 1,
        ) or []
        merged = {int(b["open_time"]): b for b in batch0 + batch1}
        return [merged[k] for k in sorted(merged.keys())]

    def _tick_one(self, symbol: str):
        kl = self._fetch_klines(symbol)
        snap = compute_snapshot_from_klines(symbol, kl)
        hits = evaluate_alert_conditions(snap) if not snap.last_error else []
        snap.last_alerts = hits
        with self._lock:
            self._snapshots[symbol] = snap
        for msg in hits:
            base = snap.base_asset or base_asset_of_symbol(symbol)
            title = f"{symbol} 现货24h资金净流入"
            body = (
                f"{msg}\n"
                f"当前滚动24h净流入: {snap.net_24h:.4f} {base}\n"
                f"更新: {snap.updated_at}"
            )
            ok = send_dingtalk_alert(symbol, "5m净流入", f"{title}\n{body}")
            logger.info("[现货净流入] 钉钉 %s ok=%s | %s", symbol, ok, msg)


_instance: Optional[SpotNetInflowMonitorService] = None
_instance_lock = threading.Lock()


def get_spot_net_inflow_instance() -> Optional[SpotNetInflowMonitorService]:
    return _instance


def set_spot_net_inflow_instance(inst: Optional[SpotNetInflowMonitorService]):
    global _instance
    with _instance_lock:
        _instance = inst


def restore_spot_net_inflow_from_db_if_needed() -> Optional[SpotNetInflowMonitorService]:
    inst = get_spot_net_inflow_instance()
    if inst and inst.running:
        return inst
    try:
        from backpack_quant_trading.database.models import DatabaseManager

        cfg = DatabaseManager().get_spot_net_inflow_config()
        if not cfg:
            return None
        _, data = cfg
        d = json.loads(data) if isinstance(data, str) else data
        symbols = d.get("symbols") or []
        if not symbols:
            return None
        if inst:
            try:
                inst.stop()
            except Exception:
                pass
        service = SpotNetInflowMonitorService(symbols=symbols)
        set_spot_net_inflow_instance(service)
        service.start()
        logger.info("[现货净流入] 已从 DB 恢复 %s 个币种", len(symbols))
        return service
    except Exception as e:
        logger.warning("[现货净流入] DB 恢复失败: %s", e)
        return None
