"""小管家：把钉钉自然语言落到后台监视创建（币种/合约分钟/MACD/新闻）。"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class StewardIntent:
    action: str  # currency_add | minute_add | macd_add | news_add | status | help | unknown
    params: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""
    note: str = ""


_TF_CURRENCY = {
    "1h": "1小时",
    "1小时": "1小时",
    "2h": "2小时",
    "2小时": "2小时",
    "4h": "4小时",
    "4小时": "4小时",
    "1d": "天",
    "天": "天",
    "日线": "天",
    "1w": "周",
    "周": "周",
    "周线": "周",
}

_TF_MACD = {
    "1h": "60",
    "1小时": "60",
    "2h": "120",
    "2小时": "120",
    "4h": "240",
    "4小时": "240",
    "640": "640",
    "640分钟": "640",
    "1d": "D",
    "日线": "D",
    "天": "D",
}

_TF_MINUTE = {
    "1m": "1m",
    "1分钟": "1m",
    "一分钟": "1m",
    "3m": "3m",
    "3分钟": "3m",
    "5m": "5m",
    "5分钟": "5m",
    "15m": "15m",
    "15分钟": "15m",
}

_PATTERN_ALIASES = {
    # 后台四选项（必须全覆盖）
    "水上金叉转死叉": "above_golden_to_death",
    "水下金叉转死叉": "below_golden_to_death",
    "死叉转水下金叉": "death_to_below_golden",
    "死叉转水上金叉": "death_to_above_golden",
    "死叉→水上金叉": "death_to_above_golden",
    "死叉→水下金叉": "death_to_below_golden",
    "死叉到水上金叉": "death_to_above_golden",
    "死叉到水下金叉": "death_to_below_golden",
    "水上金叉→死叉": "above_golden_to_death",
    "水下金叉→死叉": "below_golden_to_death",
    "水上金叉到死叉": "above_golden_to_death",
    "水下金叉到死叉": "below_golden_to_death",
    "水下死叉转水上金叉": "death_to_above_golden",
    "水下死叉到水上金叉": "death_to_above_golden",
    "水下死叉→水上金叉": "death_to_above_golden",
}


def _norm_coin(text: str) -> Optional[str]:
    t = (text or "").upper()
    m = re.search(r"\b([A-Z]{2,10})USDT\b", t)
    if m:
        return m.group(1) + "USDT"
    # 常见币
    for coin in ("BTC", "ETH", "SOL", "BNB", "DOGE", "XRP", "HYPE", "TAO", "PEPE", "WIF", "ZEC", "APT", "SUI", "ARB", "OP"):
        if re.search(rf"(?<![A-Z0-9]){coin}(?![A-Z0-9])", t):
            return coin + "USDT"
    return None


def _norm_us_ticker(text: str) -> Optional[str]:
    t = (text or "").upper()
    # 先排除加密
    if _norm_coin(text):
        # 若同时有 NVDA 等仍可取美股
        pass
    for tick in ("NVDA", "TSLA", "AAPL", "MSFT", "META", "GOOGL", "AMZN", "AMD", "MU", "INTC", "TSM"):
        if re.search(rf"(?<![A-Z0-9]){tick}(?![A-Z0-9])", t):
            return tick
    m = re.search(r"(?<![A-Z0-9])([A-Z]{1,5})(?![A-Z0-9])", t)
    if m and m.group(1) not in ("USDT", "USD", "MACD", "ETH", "BTC", "SOL", "BNB"):
        # 仅当上下文像新闻/美股时
        if any(k in (text or "") for k in ("新闻", "评级", "美股", "上调", "下调")):
            return m.group(1)
    return None


def _pick_currency_tf(text: str) -> str:
    t = text or ""
    for k, v in sorted(_TF_CURRENCY.items(), key=lambda x: -len(x[0])):
        if k.lower() in t.lower() or k in t:
            return v
    return "1小时"


def _pick_macd_tf(text: str) -> str:
    t = text or ""
    for k, v in sorted(_TF_MACD.items(), key=lambda x: -len(x[0])):
        if k.lower() in t.lower() or k in t:
            return v
    return "60"


def _pick_minute_tf(text: str) -> str:
    t = text or ""
    for k, v in sorted(_TF_MINUTE.items(), key=lambda x: -len(x[0])):
        if k in t or k.lower() in t.lower():
            return v
    return "1m"


def _pick_pattern(text: str) -> Optional[str]:
    """识别后台四种 MACD 形态；按「金叉/死叉出现顺序 + 水上/水下」推断。"""
    t = text or ""
    for k, v in sorted(_PATTERN_ALIASES.items(), key=lambda x: -len(x[0])):
        if k in t:
            return v

    idx_death = t.find("死叉")
    idx_golden = t.find("金叉")
    if idx_death < 0 or idx_golden < 0:
        if "MACD金叉" in t or "金叉形态" in t:
            return "death_to_above_golden"
        return None

    turn = any(x in t for x in ("转", "到", "→", "变成", "变为", "变"))
    if not turn and "形态" not in t:
        if "新增" in t or "增加" in t or "添加" in t:
            return "death_to_above_golden"
        return None

    golden_below = ("水下金叉" in t) or ("转水下" in t) or ("到水下" in t) or ("→水下" in t)
    golden_above = ("水上金叉" in t) or ("转水上" in t) or ("到水上" in t) or ("→水上" in t)
    if golden_below and golden_above:
        for mark in ("转水下", "到水下", "→水下", "转水上", "到水上", "→水上"):
            if mark in t:
                golden_below = "水下" in mark
                golden_above = "水上" in mark
                break

    if idx_death < idx_golden:
        if golden_below and not golden_above:
            return "death_to_below_golden"
        return "death_to_above_golden"
    if golden_below and not golden_above:
        return "below_golden_to_death"
    return "above_golden_to_death"


def _parse_ob_notional(text: str) -> Optional[float]:
    """订单簿/订单薄 名义金额。"""
    t = text or ""
    m = re.search(
        r"(?:订单[簿薄]|大单墙|ob)[^\d]{0,12}(\d+(?:\.\d+)?)\s*([万万kKmM]?)",
        t,
        re.I,
    )
    if not m:
        m = re.search(r"订单[簿薄].{0,8}改成\s*(\d+(?:\.\d+)?)\s*([万万kKmM]?)", t)
    if not m:
        return None
    val = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if unit in ("万",):
        val *= 10000
    elif unit in ("k",):
        val *= 1000
    elif unit in ("m",):
        val *= 1_000_000
    return val


_STOP_KEYS = ("停止", "删除", "移除", "取消", "关掉", "关闭", "去掉", "别监视", "不要监视", "给停")


def _is_stop_command(text: str) -> bool:
    t = text or ""
    return any(k in t for k in _STOP_KEYS)


def _looks_macd(text: str) -> bool:
    t = text or ""
    return (
        "MACD" in t.upper()
        or "金叉形态" in t
        or "形态监控" in t
        or "形态监视" in t
        or "金叉" in t
        or "死叉" in t
    )


def _looks_minute(text: str) -> bool:
    t = text or ""
    return any(
        k in t
        for k in (
            "合约监视",
            "合约监控",
            "分钟监视",
            "分钟监控",
            "分钟预警",
            "合约预警",
            "订单薄",
            "订单簿",
        )
    ) or (("合约" in t) and ("监视" in t or "监控" in t or "预警" in t))


def _looks_currency(text: str) -> bool:
    t = text or ""
    return any(k in t for k in ("币种监视", "币种监控", "特别K", "K倍数")) or (
        ("监视" in t or "监控" in t) and ("合约" not in t) and not _looks_macd(t)
    )


def parse_steward_intent(text: str) -> StewardIntent:
    raw = (text or "").strip()
    t = re.sub(r"^@?小管家\s*", "", raw).strip()
    if not t or t in ("帮助", "help", "?", "怎么用"):
        return StewardIntent(action="help", raw=raw)

    # --- 策略实例（须在通用「停止」之前，避免误删监视）---
    inst = _parse_instance_intent(t, raw)
    if inst is not None:
        return inst

    if any(
        k in t
        for k in (
            "现在有哪些",
            "当前监视",
            "当前监控",
            "监视列表",
            "监控列表",
            "看看监视",
            "看看监控",
            "监视状态",
            "监控状态",
            "status",
        )
    ) or t in ("状态",):
        return StewardIntent(action="status", raw=raw)

    # --- 停止 / 删除（优先于新增）---
    if _is_stop_command(t):
        sym = _norm_coin(t)
        if _looks_macd(t):
            if not sym:
                return StewardIntent(action="unknown", raw=raw, note="停止 MACD 请带币种，如 ETH")
            pattern = _pick_pattern(t)
            params: Dict[str, Any] = {"symbols": [sym]}
            # 有明确周期词才限定 TF；否则删该币全部形态任务
            if any(k in t.lower() for k in ("1h", "2h", "4h", "1小时", "2小时", "4小时", "日线", "640")):
                params["timeframes"] = [_pick_macd_tf(t)]
            if pattern:
                params["patterns"] = [pattern]
            return StewardIntent(action="macd_remove", params=params, raw=raw)
        if _looks_minute(t):
            if not sym:
                return StewardIntent(
                    action="minute_remove",
                    params={"symbols": [], "stop_all": True},
                    raw=raw,
                    note="未指定币种，将停止全部合约分钟监视",
                )
            return StewardIntent(action="minute_remove", params={"symbols": [sym]}, raw=raw)
        if _looks_currency(t) or (sym and ("监视" in t or "监控" in t)):
            if not sym:
                return StewardIntent(action="unknown", raw=raw, note="停止币种监视请带币种，如 ZEC")
            params = {"symbols": [sym]}
            if any(
                k in t.lower()
                for k in ("1h", "2h", "4h", "1小时", "2小时", "4小时", "日线", "周", "天")
            ):
                params["timeframes"] = [_pick_currency_tf(t)]
            return StewardIntent(action="currency_remove", params=params, raw=raw)
        if sym:
            # 默认按币种监视停
            params = {"symbols": [sym]}
            if any(k in t.lower() for k in ("1h", "2h", "4h", "1小时", "2小时", "4小时")):
                params["timeframes"] = [_pick_currency_tf(t)]
            return StewardIntent(action="currency_remove", params=params, raw=raw)
        return StewardIntent(
            action="unknown",
            raw=raw,
            note="停止请说明类型，如：停止 ZEC 1h 币种监视 / 停止 ETH 死叉转水下金叉 / 停止 BTC 合约预警",
        )

    # --- 新闻监控 ---
    if any(
        k in t
        for k in (
            "新闻监控",
            "新闻监视",
            "快讯监控",
            "评级",
            "上调评级",
            "下调评级",
            "财报",
            "earnings",
            "新闻",
        )
    ) and (
        _norm_us_ticker(t)
        or any(k in t for k in ("评级", "上调", "下调", "财报", "监控", "监视"))
    ):
        tick = _norm_us_ticker(t) or ""
        extras: List[str] = []
        if "上调评级" in t or "机构上调" in t:
            extras.extend(["上调评级", "机构上调评级", "upgrade", "raised rating"])
        if "下调评级" in t:
            extras.extend(["下调评级", "downgrade"])
        if "财报" in t or "earnings" in t.lower():
            extras.extend(["财报", "earnings", "季报", "年报", "业绩"])
        if not tick and not extras:
            return StewardIntent(action="unknown", raw=raw, note="新闻监控请带标的，如 NVDA")
        params: Dict[str, Any] = {}
        if tick:
            params["watch_names"] = [tick]
        if extras:
            params["extra_impact_keywords"] = extras
            params["only_extra_impact_keywords"] = False
        return StewardIntent(action="news_add", params=params, raw=raw)

    # --- MACD 形态（可不写「MACD」，口语如「水下死叉转水上金叉」）---
    if (
        "MACD" in t.upper()
        or "金叉形态" in t
        or "死叉转" in t
        or "形态监控" in t
        or "形态监视" in t
        or (("金叉" in t or "死叉" in t) and _norm_coin(t))
    ):
        sym = _norm_coin(t)
        pattern = _pick_pattern(t)
        tf = _pick_macd_tf(t)
        if not sym:
            return StewardIntent(action="unknown", raw=raw, note="MACD 形态请带币种，如 ETH")
        if not pattern:
            pattern = "death_to_above_golden"
            note = "未识别形态，默认「死叉转水上金叉」"
        else:
            note = ""
        return StewardIntent(
            action="macd_add",
            params={"symbols": [sym], "timeframes": [tf], "patterns": [pattern]},
            raw=raw,
            note=note,
        )

    # --- 合约/分钟监视（订单簿）——须在「币种监视」之前，避免「合约监控」误判成币种 ---
    if any(
        k in t
        for k in (
            "合约监视",
            "合约监控",
            "分钟监视",
            "分钟监控",
            "分钟预警",
            "订单薄",
            "订单簿",
            "1分钟合约",
            "合约预警",
        )
    ) or (
        ("合约" in t)
        and ("监视" in t or "监控" in t)
        and ("币种" not in t)
    ):
        sym = _norm_coin(t)
        if not sym:
            return StewardIntent(action="unknown", raw=raw, note="合约监视请带币种，如 BTC")
        params = {
            "symbols": [sym],
            "interval": _pick_minute_tf(t),
        }
        ob = _parse_ob_notional(t)
        if ob is not None:
            params["ob_notional_threshold"] = ob
        return StewardIntent(action="minute_add", params=params, raw=raw)

    # --- 币种监视 ---
    if any(k in t for k in ("币种监视", "币种监控", "特别K", "K倍数")) or (
        ("新增" in t or "增加" in t or "添加" in t)
        and _norm_coin(t)
        and ("监视" in t or "监控" in t)
        and ("合约" not in t)
        and ("分钟" not in t)
    ):
        sym = _norm_coin(t)
        if not sym:
            return StewardIntent(action="unknown", raw=raw, note="币种监视请带币种，如 ETH")
        return StewardIntent(
            action="currency_add",
            params={"symbols": [sym], "timeframes": [_pick_currency_tf(t)]},
            raw=raw,
        )

    # 兜底：新增/增加 + 币 + 监视
    if (("新增" in t) or ("增加" in t) or ("添加" in t) or ("帮我" in t)) and ("监视" in t or "监控" in t):
        sym = _norm_coin(t)
        if sym and any(x in t for x in ("分钟", "合约", "订单")):
            return StewardIntent(
                action="minute_add",
                params={
                    "symbols": [sym],
                    "interval": _pick_minute_tf(t),
                    **(
                        {"ob_notional_threshold": _parse_ob_notional(t)}
                        if _parse_ob_notional(t) is not None
                        else {}
                    ),
                },
                raw=raw,
            )
        if sym:
            return StewardIntent(
                action="currency_add",
                params={"symbols": [sym], "timeframes": [_pick_currency_tf(t)]},
                raw=raw,
            )

    return StewardIntent(action="unknown", raw=raw, note="未识别指令")


def steward_help_markdown() -> str:
    return (
        "## 提醒 · 小管家用法\n\n"
        "点名 `@小管家` 后可直接配置后台监视（无需进网页）：\n\n"
        "1. **币种监视**\n"
        "   - `新增 ETH 2h 币种监视`\n"
        "2. **合约分钟/订单簿监视**\n"
        "   - `新增 BTC 1分钟合约监视，订单薄改成 2000000`\n"
        "3. **MACD 形态**（与后台四选项一致，口语即可）\n"
        "   - `ETH 1h 水上金叉转死叉`\n"
        "   - `ETH 1h 水下金叉转死叉`\n"
        "   - `ETH 1h 死叉转水下金叉`\n"
        "   - `ETH 1h 死叉转水上金叉` / `水下死叉转水上金叉`\n"
        "4. **新闻监控**\n"
        "   - `增加 NVDA 上调评级的新闻监控`\n"
        "5. **停止/删除**\n"
        "   - `把 ZEC 1h 币种监视停止`\n"
        "   - `停止 ETH 1h 死叉转水下金叉`\n"
        "   - `删除 BTC 合约预警`\n"
        "6. **查看状态**：`当前监视状态`\n"
        "7. **策略实例**\n"
        "   - `查看策略实例` / `实例状态 <id>`\n"
        "   - `确认停止实例 <id>` / `确认启动实例 <id>`\n"
        "   - `实例日志` / `把实例 <id> 改成逐仓`\n"
    )


def _parse_instance_intent(t: str, raw: str) -> Optional[StewardIntent]:
    """解析实例相关口令；无关则返回 None。"""
    if any(k in t for k in ("查看策略实例", "策略实例列表", "实例列表", "有哪些实例")):
        return StewardIntent(action="instance_list", raw=raw)
    if "实例日志" in t or t.strip() in ("日志", "策略日志"):
        return StewardIntent(action="instance_logs", raw=raw)

    m_st = re.search(r"实例状态\s*[：:]?\s*([A-Za-z0-9_\-]+)", t)
    if m_st:
        return StewardIntent(
            action="instance_status", params={"instance_id": m_st.group(1)}, raw=raw
        )

    m_stop = re.search(r"确认停止实例\s*[：:]?\s*([A-Za-z0-9_\-]+)", t)
    if m_stop:
        return StewardIntent(
            action="instance_stop", params={"instance_id": m_stop.group(1)}, raw=raw
        )
    m_start = re.search(r"确认启动实例\s*[：:]?\s*([A-Za-z0-9_\-]+)", t)
    if m_start:
        return StewardIntent(
            action="instance_start", params={"instance_id": m_start.group(1)}, raw=raw
        )

    if "停止实例" in t or "启动实例" in t:
        return StewardIntent(
            action="unknown",
            raw=raw,
            note="启停须二次确认：确认停止实例 <id> / 确认启动实例 <id>",
        )

    m_margin = re.search(
        r"实例\s*([A-Za-z0-9_\-]+).{0,12}(逐仓|全仓|ISOLATED|CROSSED)", t, re.I
    )
    if not m_margin:
        m_margin = re.search(
            r"把实例\s*([A-Za-z0-9_\-]+)\s*改成\s*(逐仓|全仓|ISOLATED|CROSSED)", t, re.I
        )
    if m_margin:
        mt = m_margin.group(2)
        if mt in ("逐仓",) or mt.upper() == "ISOLATED":
            margin = "ISOLATED"
        else:
            margin = "CROSSED"
        return StewardIntent(
            action="instance_margin",
            params={"instance_id": m_margin.group(1), "margin_type": margin},
            raw=raw,
        )
    return None


def _exec_instance_list() -> Dict[str, Any]:
    from backpack_quant_trading.agents.steward_trading import list_instances_brief

    try:
        data = list_instances_brief()
    except Exception as exc:
        return {"ok": False, "markdown": f"### 小管家\n列出实例失败：{exc}"}
    rows = data.get("instances") or []
    lines = [
        "## 提醒 · 小管家 · 策略实例",
        "",
        f"绑定用户 id=`{data.get('user_id')}` · 共 **{len(rows)}** 个",
        "",
    ]
    if not rows:
        lines.append("（暂无实例。可在网页「策略交易」创建。）")
    for r in rows[:30]:
        lines.append(
            f"- `{r.get('id')}` · {r.get('strategy') or '—'} · {r.get('symbol') or '—'} · "
            f"{r.get('margin_type') or '—'} · **{r.get('status') or '—'}**"
        )
    lines.append("\n启停请发：`确认停止实例 <id>` / `确认启动实例 <id>`")
    return {"ok": True, "markdown": "\n".join(lines)}


def _exec_instance_status(params: Dict[str, Any]) -> Dict[str, Any]:
    from backpack_quant_trading.agents.steward_trading import instance_brief

    iid = str(params.get("instance_id") or "")
    data = instance_brief(iid)
    if not data.get("ok"):
        return {"ok": False, "markdown": f"### 小管家\n{data.get('error')}"}
    r = data["instance"]
    md = (
        f"## 提醒 · 小管家 · 实例 `{iid}`\n\n"
        f"- 策略：{r.get('strategy') or '—'}\n"
        f"- 品种：{r.get('symbol') or '—'}\n"
        f"- 交易所：{r.get('exchange') or '—'}\n"
        f"- 保证金：{r.get('margin_type') or '—'}\n"
        f"- 状态：**{r.get('status') or '—'}**\n"
    )
    return {"ok": True, "markdown": md}


def _exec_instance_start(params: Dict[str, Any]) -> Dict[str, Any]:
    from backpack_quant_trading.agents.steward_trading import start_instance

    iid = str(params.get("instance_id") or "")
    try:
        res = start_instance(iid)
        return {
            "ok": True,
            "markdown": f"## 提醒 · 小管家\n已请求**启动**实例 `{iid}`\n\n```\n{res}\n```",
        }
    except Exception as exc:
        return {"ok": False, "markdown": f"### 小管家\n启动失败：{exc}"}


def _exec_instance_stop(params: Dict[str, Any]) -> Dict[str, Any]:
    from backpack_quant_trading.agents.steward_trading import stop_instance

    iid = str(params.get("instance_id") or "")
    try:
        res = stop_instance(iid, keep_card=True)
        return {
            "ok": True,
            "markdown": f"## 提醒 · 小管家\n已请求**停止**实例 `{iid}`（保留卡片）\n\n```\n{res}\n```",
        }
    except Exception as exc:
        return {"ok": False, "markdown": f"### 小管家\n停止失败：{exc}"}


def _exec_instance_margin(params: Dict[str, Any]) -> Dict[str, Any]:
    from backpack_quant_trading.agents.steward_trading import set_margin

    iid = str(params.get("instance_id") or "")
    mt = str(params.get("margin_type") or "ISOLATED")
    try:
        res = set_margin(iid, mt)
        return {
            "ok": True,
            "markdown": f"## 提醒 · 小管家\n已请求实例 `{iid}` 保证金模式 → **{mt}**\n\n```\n{res}\n```",
        }
    except Exception as exc:
        return {"ok": False, "markdown": f"### 小管家\n改保证金失败：{exc}"}


def _exec_instance_logs() -> Dict[str, Any]:
    from backpack_quant_trading.agents.steward_trading import recent_logs_markdown

    try:
        return {"ok": True, "markdown": recent_logs_markdown(40)}
    except Exception as exc:
        return {"ok": False, "markdown": f"### 小管家\n读日志失败：{exc}"}


def execute_steward_intent(intent: StewardIntent) -> Dict[str, Any]:
    """在 API 进程内执行（会操作全局 monitor singleton）。"""
    if intent.action == "help":
        return {"ok": True, "markdown": steward_help_markdown()}
    if intent.action == "unknown":
        return {
            "ok": False,
            "markdown": f"### 小管家\n未能理解。{intent.note or ''}\n\n" + steward_help_markdown(),
        }
    if intent.action == "status":
        return {"ok": True, "markdown": _status_markdown()}
    if intent.action == "instance_list":
        return _exec_instance_list()
    if intent.action == "instance_status":
        return _exec_instance_status(intent.params)
    if intent.action == "instance_start":
        return _exec_instance_start(intent.params)
    if intent.action == "instance_stop":
        return _exec_instance_stop(intent.params)
    if intent.action == "instance_margin":
        return _exec_instance_margin(intent.params)
    if intent.action == "instance_logs":
        return _exec_instance_logs()
    if intent.action == "currency_add":
        return _exec_currency_add(intent.params, note=intent.note)
    if intent.action == "currency_remove":
        return _exec_currency_remove(intent.params, note=intent.note)
    if intent.action == "minute_add":
        return _exec_minute_add(intent.params, note=intent.note)
    if intent.action == "minute_remove":
        return _exec_minute_remove(intent.params, note=intent.note)
    if intent.action == "macd_add":
        return _exec_macd_add(intent.params, note=intent.note)
    if intent.action == "macd_remove":
        return _exec_macd_remove(intent.params, note=intent.note)
    if intent.action == "news_add":
        return _exec_news_add(intent.params, note=intent.note)
    return {"ok": False, "markdown": f"未实现动作：{intent.action}"}


def handle_steward(text: str, *, staff_id: str = "") -> Dict[str, Any]:
    intent = parse_steward_intent(text)
    logger.info("steward intent=%s params=%s staff=%s", intent.action, intent.params, staff_id)
    return execute_steward_intent(intent)


def _status_markdown() -> str:
    lines = ["## 提醒 · 小管家 · 当前监视", ""]
    try:
        from backpack_quant_trading.core.binance_monitor import (
            get_monitor_instance,
            get_minute_alert_instance,
        )
        from backpack_quant_trading.core.macd_pattern_monitor import get_macd_pattern_instance
        from backpack_quant_trading.core.stock_news_alert import load_config, get_stock_news_alert_instance

        cm = get_monitor_instance()
        if not (cm and getattr(cm, "_running", False)):
            try:
                from backpack_quant_trading.core.binance_monitor import (
                    restore_currency_monitor_from_db_if_needed,
                )
                cm = restore_currency_monitor_from_db_if_needed() or cm
            except Exception:
                pass
        pairs = list(getattr(cm, "_pairs", []) or []) if cm and getattr(cm, "_running", False) else []
        lines.append(f"- **币种监视**: {'运行中' if pairs else '未运行'} · {len(pairs)} 对")
        for s, tf in pairs[:12]:
            lines.append(f"  - {s} / {tf}")
        if len(pairs) > 12:
            lines.append(f"  - …共 {len(pairs)} 对")

        ma = get_minute_alert_instance()
        if ma and getattr(ma, "_running", False):
            lines.append(
                f"- **合约分钟监视**: 运行中 · {getattr(ma, 'symbols', [])} · "
                f"{getattr(ma, 'interval', '1m')} · 订单簿≥{getattr(ma, 'ob_notional_threshold', 0)}"
            )
        else:
            lines.append("- **合约分钟监视**: 未运行")

        mp = get_macd_pattern_instance()
        tasks = list(getattr(mp, "_tasks", []) or []) if mp and getattr(mp, "_running", False) else []
        lines.append(f"- **MACD 形态**: {'运行中' if tasks else '未运行'} · {len(tasks)} 条")
        for s, tf, p in tasks[:8]:
            lines.append(f"  - {s} / {tf} / {p}")

        cfg = load_config()
        sn = get_stock_news_alert_instance()
        running = bool(sn and getattr(sn, "_running", False)) or bool(cfg.get("running"))
        watches = cfg.get("watch_names") or []
        lines.append(f"- **新闻监控**: {'运行中' if running else '未运行'} · 词 {watches}")
    except Exception as exc:
        lines.append(f"- 读取状态失败：{exc}")
    return "\n".join(lines)


def _exec_currency_add(params: Dict[str, Any], note: str = "") -> Dict[str, Any]:
    import json
    from backpack_quant_trading.core.binance_monitor import (
        BinanceMonitorService,
        get_monitor_instance,
        set_monitor_instance,
        set_currency_monitor_user_stopped,
    )
    from backpack_quant_trading.database.models import DatabaseManager

    symbols = [str(s).upper() for s in (params.get("symbols") or [])]
    timeframes = [str(t) for t in (params.get("timeframes") or ["1小时"])]
    if not symbols:
        return {"ok": False, "markdown": "缺少币种"}
    set_currency_monitor_user_stopped(False)
    inst = get_monitor_instance()
    base_pairs: List[Tuple[str, str]] = []
    if inst and getattr(inst, "_pairs", []):
        base_pairs = list(inst._pairs)
    if not base_pairs:
        cfg = DatabaseManager().get_currency_monitor_config()
        if cfg:
            _, data = cfg
            try:
                d = json.loads(data) if isinstance(data, str) else data
                base_pairs = [(str(p[0]).upper(), str(p[1])) for p in d.get("pairs", [])]
            except Exception:
                pass
    new_pairs = [(s, t) for s in symbols for t in timeframes]
    seen = set()
    merged = []
    for p in base_pairs + new_pairs:
        if p not in seen:
            seen.add(p)
            merged.append(p)
    if inst and getattr(inst, "_running", False):
        inst.stop()
    service = BinanceMonitorService(pairs=merged, user_id=None)
    set_monitor_instance(service)
    service.start()
    DatabaseManager().save_currency_monitor_config(json.dumps({"pairs": merged}))
    added = ", ".join(f"{s}/{t}" for s, t in new_pairs)
    return {
        "ok": True,
        "markdown": (
            f"## 提醒 · 小管家\n\n已追加**币种监视**：{added}\n"
            f"当前共 **{len(merged)}** 对在跑。\n"
            + (f"\n> {note}\n" if note else "")
        ),
    }


def _exec_currency_remove(params: Dict[str, Any], note: str = "") -> Dict[str, Any]:
    import json
    from backpack_quant_trading.core.binance_monitor import (
        BinanceMonitorService,
        get_monitor_instance,
        set_monitor_instance,
        set_currency_monitor_user_stopped,
    )
    from backpack_quant_trading.database.models import DatabaseManager

    symbols = [str(s).upper() for s in (params.get("symbols") or [])]
    timeframes = [str(t) for t in (params.get("timeframes") or [])]
    if not symbols:
        return {"ok": False, "markdown": "缺少币种"}
    db = DatabaseManager()
    inst = get_monitor_instance()
    pairs: List[Tuple[str, str]] = []
    if inst and getattr(inst, "_pairs", None):
        pairs = list(inst._pairs)
    if not pairs:
        cfg = db.get_currency_monitor_config()
        if cfg:
            _, data = cfg
            try:
                d = json.loads(data) if isinstance(data, str) else data
                pairs = [(str(p[0]).upper(), str(p[1])) for p in d.get("pairs", [])]
            except Exception:
                pairs = []
    before = list(pairs)
    sym_set = set(symbols)
    if timeframes:
        tf_set = set(timeframes)
        pairs = [(s, t) for s, t in pairs if not (s in sym_set and t in tf_set)]
    else:
        pairs = [(s, t) for s, t in pairs if s not in sym_set]
    removed = [p for p in before if p not in pairs]
    if not removed:
        target = ", ".join(symbols) + (f"/{','.join(timeframes)}" if timeframes else "")
        return {
            "ok": False,
            "markdown": f"## 提醒 · 小管家\n\n未找到要停止的币种监视：{target}\n",
        }
    if inst and getattr(inst, "_running", False):
        inst.stop()
    if not pairs:
        set_monitor_instance(None)
        set_currency_monitor_user_stopped(True)
        db.delete_currency_monitor_config()
        left = 0
    else:
        set_currency_monitor_user_stopped(False)
        service = BinanceMonitorService(pairs=pairs, user_id=None)
        set_monitor_instance(service)
        service.start()
        db.save_currency_monitor_config(json.dumps({"pairs": pairs}))
        left = len(pairs)
    gone = ", ".join(f"{s}/{t}" for s, t in removed)
    return {
        "ok": True,
        "markdown": (
            f"## 提醒 · 小管家\n\n已停止**币种监视**：{gone}\n"
            f"剩余 **{left}** 对在跑。\n"
            + (f"\n> {note}\n" if note else "")
        ),
    }


def _exec_minute_add(params: Dict[str, Any], note: str = "") -> Dict[str, Any]:
    """合并 symbols，其它参数：用户指定覆盖，否则保留已有，再否则默认。"""
    import json
    from backpack_quant_trading.api.routers.currency_monitor import _build_minute_alert_service
    from backpack_quant_trading.core.binance_monitor import (
        get_minute_alert_instance,
        set_minute_alert_instance,
    )
    from backpack_quant_trading.database.models import DatabaseManager

    defaults = {
        "interval": "1m",
        "vol_pct_threshold": 5.0,
        "volume_mult_threshold": 20.0,
        "ob_notional_threshold": 200000.0,
        "ob_distance_pct": 0.003,
        "depth_levels": 50,
        "cooldown_sec": 300,
    }
    db = DatabaseManager()
    cur: Dict[str, Any] = {}
    inst = get_minute_alert_instance()
    if inst and getattr(inst, "_running", False):
        cur = {
            "symbols": list(getattr(inst, "symbols", []) or []),
            "interval": getattr(inst, "interval", "1m"),
            "vol_pct_threshold": getattr(inst, "vol_pct_threshold", 5.0),
            "volume_mult_threshold": getattr(inst, "volume_mult_threshold", 20.0),
            "ob_notional_threshold": getattr(inst, "ob_notional_threshold", 200000.0),
            "ob_distance_pct": getattr(inst, "ob_distance_pct", 0.003),
            "depth_levels": getattr(inst, "depth_levels", 50),
            "cooldown_sec": getattr(inst, "cooldown_sec", 300),
        }
    else:
        cfg = db.get_minute_alert_config()
        if cfg:
            _, data = cfg
            try:
                cur = json.loads(data) if isinstance(data, str) else dict(data)
            except Exception:
                cur = {}

    merged = dict(defaults)
    merged.update({k: v for k, v in cur.items() if v is not None})
    for k in (
        "interval",
        "vol_pct_threshold",
        "volume_mult_threshold",
        "ob_notional_threshold",
        "ob_distance_pct",
        "depth_levels",
        "cooldown_sec",
    ):
        if k in params and params[k] is not None:
            merged[k] = params[k]

    old_syms = [str(s).upper() for s in (merged.get("symbols") or [])]
    add_syms = [str(s).upper() for s in (params.get("symbols") or [])]
    syms = []
    seen = set()
    for s in old_syms + add_syms:
        if s and s not in seen:
            seen.add(s)
            syms.append(s)
    if not syms:
        return {"ok": False, "markdown": "缺少币种"}
    merged["symbols"] = syms

    if inst and getattr(inst, "_running", False):
        inst.stop()
    service = _build_minute_alert_service(merged, market="futures")
    set_minute_alert_instance(service)
    service.start()
    db.save_minute_alert_config(json.dumps(merged))
    return {
        "ok": True,
        "markdown": (
            "## 提醒 · 小管家\n\n已更新**合约分钟监视**：\n"
            f"- 币种：{', '.join(syms)}\n"
            f"- 周期：{merged.get('interval')}\n"
            f"- 订单簿名义阈值：{merged.get('ob_notional_threshold')}\n"
            f"- 波动%：{merged.get('vol_pct_threshold')} · 量能倍数：{merged.get('volume_mult_threshold')}\n"
            + (f"\n> {note}\n" if note else "")
        ),
    }


def _exec_minute_remove(params: Dict[str, Any], note: str = "") -> Dict[str, Any]:
    import json
    from backpack_quant_trading.api.routers.currency_monitor import _build_minute_alert_service
    from backpack_quant_trading.core.binance_monitor import (
        get_minute_alert_instance,
        set_minute_alert_instance,
    )
    from backpack_quant_trading.database.models import DatabaseManager

    db = DatabaseManager()
    inst = get_minute_alert_instance()
    cur: Dict[str, Any] = {}
    if inst and getattr(inst, "_running", False):
        cur = {
            "symbols": list(getattr(inst, "symbols", []) or []),
            "interval": getattr(inst, "interval", "1m"),
            "vol_pct_threshold": getattr(inst, "vol_pct_threshold", 5.0),
            "volume_mult_threshold": getattr(inst, "volume_mult_threshold", 20.0),
            "ob_notional_threshold": getattr(inst, "ob_notional_threshold", 200000.0),
            "ob_distance_pct": getattr(inst, "ob_distance_pct", 0.003),
            "depth_levels": getattr(inst, "depth_levels", 50),
            "cooldown_sec": getattr(inst, "cooldown_sec", 300),
        }
    else:
        cfg = db.get_minute_alert_config()
        if cfg:
            _, data = cfg
            try:
                cur = json.loads(data) if isinstance(data, str) else dict(data)
            except Exception:
                cur = {}

    if params.get("stop_all") or not (params.get("symbols") or []):
        if inst and getattr(inst, "_running", False):
            inst.stop()
        set_minute_alert_instance(None)
        db.delete_minute_alert_config()
        return {
            "ok": True,
            "markdown": "## 提醒 · 小管家\n\n已**全部停止**合约分钟/订单簿监视。\n"
            + (f"\n> {note}\n" if note else ""),
        }

    remove_syms = {str(s).upper() for s in (params.get("symbols") or [])}
    old = [str(s).upper() for s in (cur.get("symbols") or [])]
    kept = [s for s in old if s not in remove_syms]
    gone = [s for s in old if s in remove_syms]
    if not gone:
        return {
            "ok": False,
            "markdown": f"## 提醒 · 小管家\n\n合约监视中未找到：{', '.join(sorted(remove_syms))}\n",
        }
    if inst and getattr(inst, "_running", False):
        inst.stop()
    if not kept:
        set_minute_alert_instance(None)
        db.delete_minute_alert_config()
        return {
            "ok": True,
            "markdown": (
                f"## 提醒 · 小管家\n\n已移除 {', '.join(gone)}，合约分钟监视已无剩余币种，已全部停止。\n"
                + (f"\n> {note}\n" if note else "")
            ),
        }
    cur["symbols"] = kept
    service = _build_minute_alert_service(cur, market="futures")
    set_minute_alert_instance(service)
    service.start()
    db.save_minute_alert_config(json.dumps(cur))
    return {
        "ok": True,
        "markdown": (
            "## 提醒 · 小管家\n\n已从**合约分钟监视**移除：\n"
            f"- 删除：{', '.join(gone)}\n"
            f"- 剩余：{', '.join(kept)}\n"
            + (f"\n> {note}\n" if note else "")
        ),
    }


def _exec_macd_add(params: Dict[str, Any], note: str = "") -> Dict[str, Any]:
    import json
    from backpack_quant_trading.core.macd_pattern_monitor import (
        MACD_TF_OPTIONS,
        PATTERN_OPTIONS,
        MacdPatternMonitorService,
        get_macd_pattern_instance,
        set_macd_pattern_instance,
        set_macd_pattern_user_stopped,
    )
    from backpack_quant_trading.database.models import DatabaseManager

    symbols = [str(s).upper() for s in (params.get("symbols") or [])]
    timeframes = [str(t) for t in (params.get("timeframes") or [])]
    patterns = [str(p) for p in (params.get("patterns") or [])]
    for tf in timeframes:
        if tf not in MACD_TF_OPTIONS:
            return {"ok": False, "markdown": f"不支持的 MACD 周期：{tf}"}
    for p in patterns:
        if p not in PATTERN_OPTIONS:
            return {"ok": False, "markdown": f"不支持的形态：{p}"}
    set_macd_pattern_user_stopped(False)
    inst = get_macd_pattern_instance()
    base = []
    if inst and getattr(inst, "_tasks", []):
        base = list(inst._tasks)
    if not base:
        cfg = DatabaseManager().get_macd_pattern_monitor_config()
        if cfg:
            _, data = cfg
            try:
                d = json.loads(data) if isinstance(data, str) else data
                for t in d.get("tasks", []):
                    if len(t) >= 3:
                        base.append((str(t[0]).upper(), str(t[1]), str(t[2])))
            except Exception:
                pass
    new_tasks = [(s, tf, p) for s in symbols for tf in timeframes for p in patterns]
    seen = set()
    merged = []
    for t in base + new_tasks:
        if t not in seen:
            seen.add(t)
            merged.append(t)
    if inst and getattr(inst, "_running", False):
        inst.stop()
    service = MacdPatternMonitorService(tasks=merged)
    set_macd_pattern_instance(service)
    service.start()
    DatabaseManager().save_macd_pattern_monitor_config(json.dumps({"tasks": merged}))
    labels = [PATTERN_OPTIONS.get(p, p) for p in patterns]
    return {
        "ok": True,
        "markdown": (
            "## 提醒 · 小管家\n\n已追加 **MACD 形态**：\n"
            f"- {', '.join(symbols)} · TF={timeframes} · {labels}\n"
            f"- 当前任务数：**{len(merged)}**\n"
            + (f"\n> {note}\n" if note else "")
        ),
    }

def _exec_macd_remove(params: Dict[str, Any], note: str = "") -> Dict[str, Any]:
    import json
    from backpack_quant_trading.core.macd_pattern_monitor import (
        PATTERN_OPTIONS,
        MacdPatternMonitorService,
        get_macd_pattern_instance,
        set_macd_pattern_instance,
        set_macd_pattern_user_stopped,
    )
    from backpack_quant_trading.database.models import DatabaseManager

    symbols = [str(s).upper() for s in (params.get("symbols") or [])]
    timeframes = [str(t) for t in (params.get("timeframes") or [])]
    patterns = [str(p) for p in (params.get("patterns") or [])]
    if not symbols:
        return {"ok": False, "markdown": "缺少币种"}
    db = DatabaseManager()
    inst = get_macd_pattern_instance()
    tasks: List[Tuple[str, str, str]] = []
    if inst and getattr(inst, "_tasks", None):
        tasks = list(inst._tasks)
    if not tasks:
        cfg = db.get_macd_pattern_monitor_config()
        if cfg:
            _, data = cfg
            try:
                d = json.loads(data) if isinstance(data, str) else data
                for row in d.get("tasks", []):
                    if len(row) >= 3:
                        tasks.append((str(row[0]).upper(), str(row[1]), str(row[2])))
            except Exception:
                tasks = []
    before = list(tasks)
    sym_set = set(symbols)
    tf_set = set(timeframes) if timeframes else None
    pat_set = set(patterns) if patterns else None

    def _keep(row: Tuple[str, str, str]) -> bool:
        s, tf, p = row
        if s not in sym_set:
            return True
        if tf_set is not None and tf not in tf_set:
            return True
        if pat_set is not None and p not in pat_set:
            return True
        return False

    tasks = [row for row in before if _keep(row)]
    removed = [row for row in before if row not in tasks]
    if not removed:
        return {
            "ok": False,
            "markdown": (
                "## 提醒 · 小管家\n\n未找到匹配的 MACD 任务"
                f"（{symbols} / {timeframes or '任意周期'} / "
                f"{[PATTERN_OPTIONS.get(p, p) for p in patterns] or '任意形态'}）。\n"
            ),
        }
    if inst and getattr(inst, "_running", False):
        inst.stop()
    if not tasks:
        set_macd_pattern_instance(None)
        set_macd_pattern_user_stopped(True)
        db.delete_macd_pattern_monitor_config()
        left = 0
    else:
        set_macd_pattern_user_stopped(False)
        service = MacdPatternMonitorService(tasks=tasks)
        set_macd_pattern_instance(service)
        service.start()
        db.save_macd_pattern_monitor_config(json.dumps({"tasks": tasks}))
        left = len(tasks)
    lines = [
        f"- {s} / {tf} / {PATTERN_OPTIONS.get(p, p)}" for s, tf, p in removed
    ]
    return {
        "ok": True,
        "markdown": (
            "## 提醒 · 小管家\n\n已停止 **MACD 形态**：\n"
            + "\n".join(lines)
            + f"\n\n剩余任务数：**{left}**\n"
            + (f"\n> {note}\n" if note else "")
        ),
    }


def _exec_news_add(params: Dict[str, Any], note: str = "") -> Dict[str, Any]:
    from backpack_quant_trading.core.stock_news_alert import (
        StockNewsAlertService,
        get_stock_news_alert_instance,
        load_config,
        merge_watch_names,
        resolve_dingtalk_webhook,
        save_config,
        set_stock_news_alert_instance,
        set_stock_news_alert_user_stopped,
    )

    cfg = load_config()
    watches = list(params.get("watch_names") or [])
    if watches:
        cfg["watch_names"] = merge_watch_names(cfg.get("watch_names") or [], watches)
    extras = [str(x).strip() for x in (params.get("extra_impact_keywords") or []) if str(x).strip()]
    if extras:
        old = [str(x).strip() for x in (cfg.get("extra_impact_keywords") or []) if str(x).strip()]
        seen = set()
        merged_ex = []
        for x in old + extras:
            if x not in seen:
                seen.add(x)
                merged_ex.append(x)
        cfg["extra_impact_keywords"] = merged_ex
    if "only_extra_impact_keywords" in params:
        cfg["only_extra_impact_keywords"] = bool(params["only_extra_impact_keywords"])
    if not resolve_dingtalk_webhook(cfg):
        # 回退到币种监视同款 DINGTALK_TOKEN（免进后台单独配新闻 webhook）
        token = (os.environ.get("DINGTALK_TOKEN") or "").strip()
        if token:
            cfg["dingtalk_webhook"] = (
                f"https://oapi.dingtalk.com/robot/send?access_token={token}"
            )
    if not resolve_dingtalk_webhook(cfg):
        return {
            "ok": False,
            "markdown": (
                "## 提醒 · 小管家\n\n新闻监控需要先配置钉钉 Webhook"
                "（后台自选快讯页、环境变量 `STOCK_NEWS_DINGTALK_WEBHOOK`，"
                "或与币种监视共用的 `DINGTALK_TOKEN`）。"
            ),
        }
    if not (cfg.get("watch_names") or []):
        return {"ok": False, "markdown": "新闻监控缺少自选关键词"}
    save_config(cfg)
    set_stock_news_alert_user_stopped(False)
    inst = get_stock_news_alert_instance()
    if inst and getattr(inst, "_running", False):
        # 热更新：重启以加载新词
        try:
            inst.stop()
        except Exception:
            pass
    service = StockNewsAlertService()
    set_stock_news_alert_instance(service)
    service.start()
    cfg["running"] = True
    save_config(cfg)
    return {
        "ok": True,
        "markdown": (
            "## 提醒 · 小管家\n\n已更新**新闻监控**：\n"
            f"- 自选：{cfg.get('watch_names')}\n"
            f"- 额外影响词：{cfg.get('extra_impact_keywords') or '（内置）'}\n"
            + (f"\n> {note}\n" if note else "")
        ),
    }
