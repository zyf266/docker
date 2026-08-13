"""A股标的监控：MACD金叉 / RSI上穿 / K线涨幅，对齐收盘检测并钉钉推送。"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from backpack_quant_trading.core.binance_monitor import macd
from backpack_quant_trading.core.stockapi_client import (
    StockApiError,
    fetch_a_share_pool,
    fetch_day_klines,
    try_fetch_stockapi_minute_klines,
)

logger = logging.getLogger(__name__)

BJ = timezone(timedelta(hours=8))
STRATEGIES = {
    "macd": "MACD策略",
    "rsi": "RSI策略",
    "gain": "涨幅策略",
}
INTERVALS = ("1", "5", "15", "30", "60", "120", "240", "D")
INTERVAL_LABEL = {
    "1": "1分钟",
    "5": "5分钟",
    "15": "15分钟",
    "30": "30分钟",
    "60": "60分钟",
    "120": "120分钟",
    "240": "240分钟",
    "D": "日线",
}
DAILY_ALERT_LIMIT = 5
CLOSE_SETTLE_SEC = 8   # 收盘后等待行情落库
SCAN_GRACE_SEC = 25    # 收盘后仍视为刚收盘的宽限
MAX_SLEEP_SEC = 120

_instance: Optional["AShareMonitorService"] = None
_user_stopped = False


def get_a_share_monitor_instance() -> Optional["AShareMonitorService"]:
    return _instance


def set_a_share_monitor_instance(svc: Optional["AShareMonitorService"]) -> None:
    global _instance
    _instance = svc


def mark_a_share_monitor_user_stopped(v: bool = True) -> None:
    global _user_stopped
    _user_stopped = bool(v)


def a_share_monitor_webhook() -> str:
    """仅从环境变量读取；未配置则空串（调用方应失败而不是用硬编码兜底）。"""
    return (os.getenv("A_SHARE_MONITOR_WEBHOOK") or "").strip()


def a_share_monitor_dingtalk_keyword() -> str:
    """该机器人自定义关键词（当前群为「信号」）；可用环境变量覆盖。"""
    return (
        (os.getenv("A_SHARE_MONITOR_DINGTALK_KEYWORD") or "").strip()
        or "信号"
    )


def _ensure_a_share_dingtalk_keyword(content: str) -> str:
    text = (content or "").strip()
    kw = a_share_monitor_dingtalk_keyword()
    if kw and kw not in text:
        text = f"【{kw}】\n{text}"
    return text


def _bj_localize_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ)


def _bj_ts_ms(dt: datetime) -> int:
    return int(_bj_localize_naive(dt).timestamp() * 1000)


def _parse_cn_bar_time(label: str) -> datetime:
    s = (label or "").strip()
    for fmt, n in (
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d %H:%M", 16),
        ("%Y/%m/%d %H:%M:%S", 19),
        ("%Y-%m-%d", 10),
    ):
        try:
            return _bj_localize_naive(datetime.strptime(s[:n], fmt))
        except Exception:
            continue
    raise ValueError(f"无法解析时间: {label}")


def _in_a_share_session(dt: datetime) -> bool:
    if dt.weekday() >= 5:
        return False
    hm = dt.hour * 60 + dt.minute
    return (9 * 60 + 30 <= hm <= 11 * 60 + 30) or (13 * 60 <= hm <= 15 * 60)


def _in_a_share_scan_window(dt: datetime) -> bool:
    """允许拉 K / 推送的时间窗：交易时段 + 午盘/收盘后 settle+grace。"""
    now = _bj_localize_naive(dt)
    if now.weekday() >= 5:
        return False
    if _in_a_share_session(now):
        return True
    # 11:30 / 15:00 收盘后短暂宽限（秒级），避免刚出 session 分钟边界就漏扫
    for hh, mm in ((11, 30), (15, 0)):
        close = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        elapsed = (now - close).total_seconds()
        if CLOSE_SETTLE_SEC <= elapsed <= CLOSE_SETTLE_SEC + SCAN_GRACE_SEC:
            return True
    return False


def _session_boundaries(interval: str, day: datetime) -> List[datetime]:
    """A 股会话内该级别的收盘时刻列表（北京时间）。"""
    iv = str(interval)
    base = day.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=BJ)
    if iv == "D" or iv == "240":
        # 全天约 240 分钟交易；日线/240 以 15:00 收盘
        return [base.replace(hour=15, minute=0)]
    minutes = int(iv) if iv.isdigit() else 0
    if minutes <= 0:
        return []
    if minutes >= 120:
        # 上午 9:30-11:30、下午 13:00-15:00 各一根 120 分钟
        return [base.replace(hour=11, minute=30), base.replace(hour=15, minute=0)]
    out: List[datetime] = []
    for start_h, start_m, end_h, end_m in ((9, 30, 11, 30), (13, 0, 15, 0)):
        t = base.replace(hour=start_h, minute=start_m) + timedelta(minutes=minutes)
        end = base.replace(hour=end_h, minute=end_m)
        while t <= end:
            out.append(t)
            t += timedelta(minutes=minutes)
    return out


def _next_close_plus_settle(interval: str, now: datetime) -> Optional[datetime]:
    """下一根该级别 K 线收盘时刻 + CLOSE_SETTLE_SEC。"""
    now = _bj_localize_naive(now)
    iv = str(interval)
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    for _ in range(10):
        if day.weekday() < 5:
            for close in _session_boundaries(iv, day):
                wake = close.replace(second=CLOSE_SETTLE_SEC, microsecond=0)
                if wake > now:
                    return wake
        day = day + timedelta(days=1)
    return None


def _intervals_due_now(intervals: List[str], now: datetime) -> List[str]:
    now = _bj_localize_naive(now)
    due: List[str] = []
    for iv0 in intervals:
        iv = str(iv0)
        for close in _session_boundaries(iv, now):
            elapsed = (now - close).total_seconds()
            if CLOSE_SETTLE_SEC <= elapsed <= CLOSE_SETTLE_SEC + SCAN_GRACE_SEC:
                due.append(iv)
                break
    return due


def _seconds_until_next_wake(intervals: List[str], now: Optional[datetime] = None) -> Tuple[float, List[str]]:
    now = _bj_localize_naive(now or datetime.now(tz=BJ))
    if not intervals:
        return 15.0, []
    wakes: Dict[datetime, List[str]] = {}
    for iv in intervals:
        w = _next_close_plus_settle(str(iv), now)
        if w is None:
            continue
        wakes.setdefault(w, []).append(str(iv))
    if not wakes:
        return 30.0, []
    soonest = min(wakes.keys())
    return max(0.5, min(MAX_SLEEP_SEC, (soonest - now).total_seconds())), list(wakes[soonest])


def _rma(values: List[float], length: int) -> List[float]:
    """Wilder RMA（与 TradingView ta.rma 一致）。"""
    out: List[float] = []
    alpha = 1.0 / length
    prev = None
    for i, v in enumerate(values):
        if prev is None:
            if i + 1 < length:
                out.append(float("nan"))
                continue
            prev = sum(values[i + 1 - length : i + 1]) / length
            out.append(prev)
        else:
            prev = alpha * v + (1 - alpha) * prev
            out.append(prev)
    return out


def calc_rsi(closes: List[float], length: int = 14) -> List[float]:
    if len(closes) < length + 2:
        return [float("nan")] * len(closes)
    changes = [0.0] + [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    ups = [max(c, 0.0) for c in changes]
    downs = [-min(c, 0.0) for c in changes]
    avg_up = _rma(ups, length)
    avg_down = _rma(downs, length)
    out: List[float] = []
    for u, d in zip(avg_up, avg_down):
        if u != u or d != d:  # nan
            out.append(float("nan"))
        elif d == 0:
            out.append(100.0)
        elif u == 0:
            out.append(0.0)
        else:
            out.append(100.0 - (100.0 / (1.0 + u / d)))
    return out


def _eastmoney_secid(code: str) -> Optional[str]:
    c = str(code or "").strip()
    if not c.isdigit() or len(c) != 6:
        return None
    market = "1" if c.startswith(("5", "6", "9")) else "0"
    return f"{market}.{c}"


def fetch_eastmoney_klines(code: str, interval: str, limit: int = 200) -> List[Dict[str, Any]]:
    """东财分钟/日 K（klt）。240 按交易日合成一根（上午+下午）。"""
    secid = _eastmoney_secid(code)
    if not secid:
        return []
    iv = str(interval)
    if iv == "240":
        raw60 = fetch_eastmoney_klines(code, "60", limit=limit * 8 + 20)
        return _aggregate_session_240(raw60)[-limit:]
    klt_map = {
        "1": "1",
        "5": "5",
        "15": "15",
        "30": "30",
        "60": "60",
        "120": "120",
        "D": "101",
    }
    klt = klt_map.get(iv)
    if not klt:
        return []
    try:
        sess = requests.Session()
        sess.trust_env = False
        r = sess.get(
            "https://push2his.eastmoney.com/api/qt/stock/kline/get",
            params={
                "secid": secid,
                "klt": klt,
                "fqt": "1",
                "lmt": str(limit),
                "end": "20500101",
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            },
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"},
            timeout=25,
        )
        r.raise_for_status()
        lines = ((r.json() or {}).get("data") or {}).get("klines") or []
    except Exception as e:
        logger.warning("东财K线失败 %s %s: %s", code, iv, e)
        return []
    bars: List[Dict[str, Any]] = []
    for line in lines:
        parts = str(line).split(",")
        if len(parts) < 5:
            continue
        try:
            label = parts[0]
            dt = _parse_cn_bar_time(label)
            ts = _bj_ts_ms(dt)
            # 东财: 日期,开,收,高,低,...
            o, c, h, l_ = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            bars.append({
                "open_time": ts,
                "open": o,
                "close": c,
                "high": h,
                "low": l_,
                "volume": float(parts[5]) if len(parts) > 5 else 0,
                "close_time": ts,
                "time_label": label,
            })
        except Exception:
            continue
    return bars


def _aggregate_session_240(klines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将 60 分钟 K 按北京交易日合成一根 240 分钟（全天）K。"""
    by_day: Dict[str, Dict[str, Any]] = {}
    for bar in klines:
        dt = datetime.fromtimestamp(int(bar["open_time"]) / 1000.0, tz=BJ)
        day = dt.strftime("%Y-%m-%d")
        if day not in by_day:
            by_day[day] = {
                "open_time": int(bar["open_time"]),
                "open": float(bar["open"]),
                "high": float(bar["high"]),
                "low": float(bar["low"]),
                "close": float(bar["close"]),
                "volume": float(bar.get("volume") or 0),
                "close_time": int(bar.get("close_time") or bar["open_time"]),
                "time_label": f"{day} 15:00",
            }
        else:
            b = by_day[day]
            b["high"] = max(b["high"], float(bar["high"]))
            b["low"] = min(b["low"], float(bar["low"]))
            b["close"] = float(bar["close"])
            b["volume"] += float(bar.get("volume") or 0)
            b["close_time"] = int(bar.get("close_time") or bar["open_time"])
    return [by_day[k] for k in sorted(by_day.keys())]


def _resample_minutes(klines: List[Dict[str, Any]], minutes: int) -> List[Dict[str, Any]]:
    if not klines or minutes <= 0:
        return []
    bucket_ms = minutes * 60 * 1000
    buckets: Dict[int, Dict[str, Any]] = {}
    for bar in klines:
        ts = int(bar["open_time"])
        key = ts - (ts % bucket_ms)
        if key not in buckets:
            buckets[key] = {
                "open_time": key,
                "open": float(bar["open"]),
                "high": float(bar["high"]),
                "low": float(bar["low"]),
                "close": float(bar["close"]),
                "volume": float(bar.get("volume") or 0),
                "close_time": key + bucket_ms - 1,
                "time_label": bar.get("time_label") or "",
            }
        else:
            b = buckets[key]
            b["high"] = max(b["high"], float(bar["high"]))
            b["low"] = min(b["low"], float(bar["low"]))
            b["close"] = float(bar["close"])
            b["volume"] += float(bar.get("volume") or 0)
            b["close_time"] = key + bucket_ms - 1
    return [buckets[k] for k in sorted(buckets.keys())]


def fetch_klines_for_interval(code: str, interval: str, limit: int = 200) -> Tuple[List[Dict[str, Any]], str]:
    """返回 (bars, source)。source=stockapi|eastmoney|mixed。"""
    iv = str(interval)
    if iv == "D":
        try:
            bars = fetch_day_klines(code, days=max(limit, 120))
            if bars:
                return bars[-limit:], "stockapi"
        except Exception as e:
            logger.warning("stockapi 日线失败 %s: %s", code, e)
        bars = fetch_eastmoney_klines(code, "D", limit=limit)
        return bars, "eastmoney"

    if iv == "240":
        bars60, src = fetch_klines_for_interval(code, "60", limit=limit * 4 + 20)
        return _resample_minutes(bars60, 240)[-limit:], src

    bars, err = try_fetch_stockapi_minute_klines(code, iv)
    if bars:
        return bars[-limit:], "stockapi"
    if err:
        logger.info("stockapi 分钟线不可用 %s %s: %s → 东财兜底", code, iv, err)
    bars = fetch_eastmoney_klines(code, iv, limit=limit)
    return bars, "eastmoney"


def drop_forming_bar(bars: List[Dict[str, Any]], interval: str) -> List[Dict[str, Any]]:
    """去掉可能未收盘的最后一根（对齐收盘）。"""
    if len(bars) < 3:
        return bars
    iv = str(interval)
    now_ms = int(datetime.now().timestamp() * 1000)
    last = bars[-1]
    if iv == "D":
        # 日线：若今天尚未收盘（15:00 前）且最后一根是今天，则丢掉
        now_bj = datetime.now(tz=BJ)
        label = str(last.get("time_label") or "")[:10]
        today = now_bj.strftime("%Y-%m-%d")
        if label == today and now_bj.hour * 60 + now_bj.minute < 15 * 60:
            return bars[:-1]
        return bars
    minutes = int(iv) if iv.isdigit() else 0
    if minutes <= 0:
        return bars
    # 若当前仍落在最后一根的开盘桶内，视为未收盘
    ot = int(last["open_time"])
    if now_ms < ot + minutes * 60 * 1000:
        return bars[:-1]
    return bars


def detect_macd_golden(closes: List[float]) -> Tuple[bool, Dict[str, Any]]:
    if len(closes) < 40:
        return False, {}
    dif, dea = macd(closes, 12, 26, 9)
    i = len(closes) - 1
    if i < 1:
        return False, {}
    prev_ok = dif[i - 1] <= dea[i - 1]
    curr_ok = dif[i] > dea[i]
    hit = prev_ok and curr_ok
    return hit, {"dif": round(dif[i], 4), "dea": round(dea[i], 4), "prev_dif": round(dif[i - 1], 4), "prev_dea": round(dea[i - 1], 4)}


def detect_rsi_cross(closes: List[float], threshold: float, length: int = 14) -> Tuple[bool, Dict[str, Any]]:
    rsi = calc_rsi(closes, length)
    i = len(rsi) - 1
    if i < 1 or rsi[i] != rsi[i] or rsi[i - 1] != rsi[i - 1]:
        return False, {}
    hit = rsi[i - 1] <= threshold < rsi[i]
    return hit, {"rsi": round(rsi[i], 2), "prev_rsi": round(rsi[i - 1], 2), "threshold": threshold}


def detect_gain(
    closes: List[float],
    threshold_pct: float,
    opens: Optional[List[float]] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """本根 K 线涨幅：(收-开)/开；无开盘价时退化为相对上一根收盘。"""
    if len(closes) < 1:
        return False, {}
    curr = closes[-1]
    if opens and len(opens) >= len(closes) and opens[-1]:
        base = float(opens[-1])
        if base == 0:
            return False, {}
        pct = (curr - base) / base * 100.0
        mode = "bar_oc"
    else:
        if len(closes) < 2 or closes[-2] == 0:
            return False, {}
        base = closes[-2]
        pct = (curr - base) / base * 100.0
        mode = "prev_close"
    hit = pct >= threshold_pct
    return hit, {
        "gain_pct": round(pct, 2),
        "threshold": threshold_pct,
        "close": curr,
        "base": base,
        "mode": mode,
    }


def send_a_share_dingtalk(title: str, body: str) -> Tuple[bool, str]:
    url = a_share_monitor_webhook()
    if not url:
        msg = "未配置 A_SHARE_MONITOR_WEBHOOK"
        logger.warning("A股监控钉钉跳过：%s", msg)
        return False, msg
    try:
        content = _ensure_a_share_dingtalk_keyword(f"{title}\n{body}")
        resp = requests.post(url, json={"msgtype": "text", "text": {"content": content}}, timeout=8)
        if resp.status_code != 200:
            msg = f"HTTP {resp.status_code} {resp.text[:200]}"
            logger.error("A股监控钉钉失败 %s", msg)
            return False, msg
        try:
            j = resp.json()
        except Exception:
            return True, "ok"
        if isinstance(j, dict):
            try:
                errcode = int(j.get("errcode", -1))
            except (TypeError, ValueError):
                errcode = -1
            if errcode == 0:
                return True, "ok"
            msg = str(j.get("errmsg") or j)
            logger.error("A股监控钉钉失败: %s", j)
            return False, msg
        return True, "ok"
    except Exception as e:
        logger.error("A股监控钉钉异常: %s", e)
        return False, str(e)


def format_alert_message(
    code: str,
    name: str,
    strategy: str,
    interval: str,
    trigger: str,
    extra: str = "",
) -> str:
    now = datetime.now(tz=BJ).strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "【A股标的监控提醒】",
        f"标的：{code} {name or ''}".strip(),
        f"策略：{STRATEGIES.get(strategy, strategy)}",
        f"K线：{INTERVAL_LABEL.get(interval, interval)}",
        f"触发：{trigger}",
    ]
    if extra:
        lines.append(extra)
    lines.append(f"时间：{now}")
    return "\n".join(lines)


class AShareMonitorService:
    """后台线程：按任务列表在对应 K 线收盘后检测三策略。"""

    def __init__(self, tasks: Optional[List[Dict[str, Any]]] = None):
        self.tasks: List[Dict[str, Any]] = list(tasks or [])
        self.running = False
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        # (code, strategy, interval) -> last closed bar open_time
        self._last_bar: Dict[str, int] = {}
        # (code, strategy, date) -> count
        self._daily_counts: Dict[str, int] = {}
        self.signals: List[Dict[str, Any]] = []
        self.last_error: str = ""
        self.last_scan_at: str = ""
        self.data_source_note: str = ""

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self.running,
                "tasks": list(self.tasks),
                "task_count": len(self.tasks),
                "signals": list(self.signals)[:50],
                "last_error": self.last_error,
                "last_scan_at": self.last_scan_at,
                "data_source_note": self.data_source_note,
                "daily_counts": dict(self._daily_counts),
            }

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="a-share-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.running = False
        self._stop.set()
        th = self._thread
        if th and th.is_alive() and th is not threading.current_thread():
            th.join(timeout=3.0)
        self._thread = None

    def _loop(self) -> None:
        """按各任务 K 线收盘时刻 + CLOSE_SETTLE_SEC 唤醒；非交易时段不扫描。"""
        while not self._stop.is_set():
            with self._lock:
                intervals = list({str(t.get("interval") or "5") for t in self.tasks})
            sleep_sec, planned = _seconds_until_next_wake(intervals)
            now = datetime.now(tz=BJ)
            if not _in_a_share_scan_window(now):
                # 休市：最多睡到下次唤醒点，且至少 60s，绝不扫盘
                sleep_sec = max(min(sleep_sec, MAX_SLEEP_SEC), 60.0)
                if self._stop.wait(sleep_sec):
                    break
                continue
            if self._stop.wait(sleep_sec):
                break
            try:
                now2 = datetime.now(tz=BJ)
                if not _in_a_share_scan_window(now2):
                    continue
                due = _intervals_due_now(intervals, now2)
                # 仅当刚睡到计划点附近时才用 planned，避免 MAX_SLEEP 截断后休市误扫
                if not due and planned:
                    remain, _ = _seconds_until_next_wake(planned, now2)
                    if remain <= 2.0:
                        due = list(planned)
                if not due:
                    continue
                self._scan_once(due_intervals=due)
            except Exception as e:
                self.last_error = str(e)
                logger.exception("A股监控扫描异常: %s", e)
                self._notify_datasource_error(str(e))

    def _notify_datasource_error(self, msg: str) -> None:
        if not _in_a_share_scan_window(datetime.now(tz=BJ)):
            logger.info("A股监控休市忽略数据源告警: %s", msg[:200])
            return
        day = datetime.now(tz=BJ).strftime("%Y-%m-%d")
        key = f"__datasource__|{day}"
        with self._lock:
            n = int(self._daily_counts.get(key, 0))
            if n >= 3:
                return
            self._daily_counts[key] = n + 1
        send_a_share_dingtalk(
            "【A股标的监控提醒】数据源异常",
            f"数据源异常\n详情：{msg[:300]}\n时间：{datetime.now(tz=BJ).strftime('%Y-%m-%d %H:%M:%S')}",
        )

    def _scan_once(self, due_intervals: Optional[List[str]] = None) -> None:
        now = datetime.now(tz=BJ)
        if not _in_a_share_scan_window(now):
            return
        self.last_scan_at = now.strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            tasks = list(self.tasks)
        if not tasks:
            return

        due_set = set(str(x) for x in (due_intervals or [])) if due_intervals is not None else None
        if due_set is not None and not due_set:
            return

        groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for t in tasks:
            iv = str(t.get("interval") or "5")
            if due_set is not None and iv not in due_set:
                continue
            if due_set is None and iv not in _intervals_due_now([iv], now):
                continue
            key = (str(t.get("code")), iv)
            groups.setdefault(key, []).append(t)

        for (code, interval), group in groups.items():
            if self._stop.is_set():
                return
            try:
                bars, src = fetch_klines_for_interval(code, interval)
                bars = drop_forming_bar(bars, interval)
                if bars and interval not in ("D", "240"):
                    minutes = int(interval) if str(interval).isdigit() else 0
                    if minutes > 0:
                        expect_close = int(bars[-1]["open_time"]) + minutes * 60 * 1000
                        if expect_close > int(now.timestamp() * 1000) - CLOSE_SETTLE_SEC * 1000:
                            time.sleep(3)
                            bars2, src2 = fetch_klines_for_interval(code, interval)
                            bars2 = drop_forming_bar(bars2, interval)
                            if bars2 and int(bars2[-1]["open_time"]) >= int(bars[-1]["open_time"]):
                                bars, src = bars2, src2
                self.data_source_note = src
                need = 3 if str(group[0].get("strategy")) == "gain" else 30
                if len(bars) < need:
                    self.last_error = f"{code}/{interval}: K线不足({len(bars)})"
                    self._notify_datasource_error(self.last_error)
                    continue
                closes = [float(b["close"]) for b in bars]
                opens = [float(b["open"]) for b in bars]
                bar_ts = int(bars[-1]["open_time"])
                name = group[0].get("name") or ""
                for t in group:
                    self._eval_task(t, code, name, interval, closes, bar_ts, src, opens=opens)
            except Exception as e:
                self.last_error = f"{code}/{interval}: {e}"
                logger.warning("A股监控任务失败 %s: %s", code, e)
                self._notify_datasource_error(f"{code} {interval}: {e}")

    def _eval_task(
        self,
        task: Dict[str, Any],
        code: str,
        name: str,
        interval: str,
        closes: List[float],
        bar_ts: int,
        src: str,
        opens: Optional[List[float]] = None,
    ) -> None:
        strategy = str(task.get("strategy") or "")
        key_bar = f"{code}|{strategy}|{interval}"
        with self._lock:
            if self._last_bar.get(key_bar) == bar_ts:
                return

        hit = False
        meta: Dict[str, Any] = {}
        trigger = ""
        if strategy == "macd":
            hit, meta = detect_macd_golden(closes)
            if hit:
                trigger = f"MACD金叉 DIF={meta.get('dif')} DEA={meta.get('dea')}"
        elif strategy == "rsi":
            thr = float(task.get("rsi_threshold") or 70)
            hit, meta = detect_rsi_cross(closes, thr, 14)
            if hit:
                trigger = f"RSI={meta.get('rsi')} 上穿 {thr}"
        elif strategy == "gain":
            thr = float(task.get("gain_pct") or 5.0)
            hit, meta = detect_gain(closes, thr, opens=opens)
            if hit:
                trigger = f"涨幅={meta.get('gain_pct')}% ≥ {thr}%"
        else:
            return

        if not hit:
            with self._lock:
                self._last_bar[key_bar] = bar_ts
            return

        day = datetime.now(tz=BJ).strftime("%Y-%m-%d")
        day_key = f"{code}|{strategy}|{day}"
        with self._lock:
            cnt = int(self._daily_counts.get(day_key, 0))
            if cnt >= DAILY_ALERT_LIMIT:
                logger.info("A股监控达日限额 %s", day_key)
                self._last_bar[key_bar] = bar_ts
                return

        msg = format_alert_message(code, name, strategy, interval, trigger, extra=f"数据源：{src}")
        ok, _ = send_a_share_dingtalk("【A股标的监控提醒】", msg)
        # 仅成功推送才占日限额；失败不锁 bar，允许宽限内重试
        with self._lock:
            if ok:
                self._daily_counts[day_key] = cnt + 1
                self._last_bar[key_bar] = bar_ts
            elif datetime.now(tz=BJ).second > CLOSE_SETTLE_SEC + SCAN_GRACE_SEC - 3:
                self._last_bar[key_bar] = bar_ts
        sig = {
            "ts": datetime.now(tz=BJ).strftime("%Y-%m-%d %H:%M:%S"),
            "code": code,
            "name": name,
            "strategy": strategy,
            "strategy_label": STRATEGIES.get(strategy, strategy),
            "interval": interval,
            "interval_label": INTERVAL_LABEL.get(interval, interval),
            "trigger": trigger,
            "meta": meta,
            "dingtalk_ok": ok,
            "source": src,
        }
        with self._lock:
            self.signals.insert(0, sig)
            self.signals = self.signals[:100]
        self._persist_signal(sig)

    def _persist_signal(self, sig: Dict[str, Any]) -> None:
        try:
            from backpack_quant_trading.config.settings import config

            path = Path(config.data_dir) / "a_share_monitor_signals.json"
            items: List[Dict[str, Any]] = []
            if path.exists():
                items = json.loads(path.read_text(encoding="utf-8") or "[]")
            if not isinstance(items, list):
                items = []
            items.insert(0, sig)
            path.write_text(json.dumps(items[:200], ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("写入信号历史失败: %s", e)


def load_signal_history(limit: int = 50) -> List[Dict[str, Any]]:
    try:
        from backpack_quant_trading.config.settings import config

        path = Path(config.data_dir) / "a_share_monitor_signals.json"
        if not path.exists():
            return []
        items = json.loads(path.read_text(encoding="utf-8") or "[]")
        if not isinstance(items, list):
            return []
        return items[:limit]
    except Exception:
        return []


def restore_a_share_monitor_from_db_if_needed() -> Optional[AShareMonitorService]:
    global _user_stopped
    if _user_stopped:
        return get_a_share_monitor_instance()
    inst = get_a_share_monitor_instance()
    if inst and inst.running:
        return inst
    try:
        from backpack_quant_trading.database.models import DatabaseManager

        row = DatabaseManager().get_a_share_monitor_config()
        if not row:
            return None
        _, cfg_json = row
        cfg = json.loads(cfg_json or "{}")
        tasks = cfg.get("tasks") or []
        if not tasks:
            return None
        svc = AShareMonitorService(tasks=tasks)
        set_a_share_monitor_instance(svc)
        svc.start()
        logger.info("A股监控已从 DB 恢复 tasks=%s", len(tasks))
        return svc
    except Exception as e:
        logger.warning("A股监控恢复失败: %s", e)
        return None
