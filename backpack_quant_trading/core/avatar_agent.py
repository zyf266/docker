"""小沫数字人：一期对话编排（菜单 / 模块 / 策略 / 行情 / 打开页面 / Agent 预留 / LLM）。"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

MENU_SCRIPT = """我是小沫，沐龙量化后台的数字助手。当前网页后台主要模块有：

1. AI量化实盘：各策略卡片、回测曲线与交易明细
2. AI选股：选股相关能力
3. 策略交易：实盘实例与下单相关
4. 币种监视：加密与 A 股标的监控、钉钉提醒
5. 加密信号AI评分：信号评分与复盘
6. Agent 记忆：智能体记忆检索
7. 自选多源快讯：新闻监控推送
8. 泡沫检测：美股/泡沫周报

你可以说「介绍币种监视」「打开币种监视」「看看 159570」「ETH 现在多少钱」，我来帮你。"""

# (pattern, intent, script, navigate_path|None)
FEATURE_SCRIPTS: List[Tuple[re.Pattern, str, str, Optional[str]]] = [
    (
        re.compile(r"币种监视|标的监控|a股.*监控|监控.*钉钉", re.I),
        "feature_monitor",
        "「币种监视」用来盯盘和推送提醒：可配置加密涨跌/形态监视，也可配 A 股 MACD 金叉、RSI、涨幅等，"
        "选好多周期 K 线后启动，触发走钉钉。A 股建议只在交易时段扫盘。",
        "/currency-monitor",
    ),
    (
        re.compile(r"泡沫|周报|美股周报", re.I),
        "feature_weekly",
        "「泡沫检测」是美股/泡沫周报：生成结构化周报卡片，可看最新与历史。",
        "/us-weekly-report",
    ),
    (
        re.compile(r"agent\s*记忆|记忆检索|chroma", re.I),
        "feature_memory",
        "「Agent 记忆」可查看智能体向量记忆与检索结果，方便排查分析上下文。",
        "/agent-memory",
    ),
    (
        re.compile(r"快讯|新闻监控|自选.*新闻", re.I),
        "feature_news",
        "「自选多源快讯」聚合多源财经快讯，按关键词命中后推钉钉。",
        "/stock-news-alert",
    ),
    (
        re.compile(r"信号评分|加密信号", re.I),
        "feature_score",
        "「加密信号AI评分」对买卖信号做 AI 评分与复盘。",
        "/crypto-signal-hub",
    ),
    (
        re.compile(r"策略交易|实盘交易|下单", re.I),
        "feature_trading",
        "「策略交易」管理实盘实例：启停策略、持仓与下单。请注意实盘风险与风控。",
        "/trading",
    ),
    (
        re.compile(r"量化实盘|策略卡片|回测", re.I),
        "feature_strategies",
        "「AI量化实盘」展示策略卡片：K 线、权益曲线、成交明细。也可直接问我「讲讲 159570」。",
        "/strategies",
    ),
    (
        re.compile(r"选股", re.I),
        "feature_stock_ai",
        "「AI选股」提供选股相关能力。",
        "/ai-stock",
    ),
]

OPEN_PAGE_RE = re.compile(
    r"(打开|进入|跳转|去|带我去)\s*(币种监视|标的监控|泡沫|周报|agent\s*记忆|记忆|"
    r"快讯|信号评分|策略交易|量化实盘|策略卡片|选股|交易)",
    re.I,
)

OPEN_PATH = {
    "币种监视": "/currency-monitor",
    "标的监控": "/currency-monitor",
    "泡沫": "/us-weekly-report",
    "周报": "/us-weekly-report",
    "agent记忆": "/agent-memory",
    "记忆": "/agent-memory",
    "快讯": "/stock-news-alert",
    "信号评分": "/crypto-signal-hub",
    "策略交易": "/trading",
    "量化实盘": "/strategies",
    "策略卡片": "/strategies",
    "选股": "/ai-stock",
    "交易": "/trading",
}

STRATEGY_NAV = {
    "159570": "/strategies/a-share-159570",
    "300308": "/strategies/a-share-300308",
    "603986": "/strategies/a-share-603986",
    "688146": "/strategies/a-share-688146",
    "002837": "/strategies/a-share-002837",
    "nvda": "/strategies/us-momentum-nvda",
    "eth": "/strategies/eth-trend",
    "paxg": "/strategies/paxg-trend",
    "510210": "/strategies/sse-510210",
    "mnq": "/strategies/mnq-dip",
}

STRATEGY_CODE_RE = re.compile(
    r"(159570|300308|603986|688146|002837|nvda|eth|btc|paxg|hype|crcl|510210|mnq)",
    re.I,
)
MENU_RE = re.compile(
    r"(后台|菜单|功能|模块|有哪些|能做什么|你是谁|介绍一下.*(系统|平台|后台)|小沫.*(介绍|你好))",
    re.I,
)
MARKET_RE = re.compile(
    r"(价格|行情|多少钱|现价|报价|涨跌|看看)\s*(eth|btc|比特币|以太|以太坊)|"
    r"(eth|btc|比特币|以太|以太坊)\s*(价格|行情|多少钱|现价|报价|怎样|怎么样)|"
    r"(分析一下|分析)\s*(eth|btc).*(分钟|小时|趋势|k线)?",
    re.I,
)
AGENT_RE = re.compile(
    r"(@?\s*(美股|A股|加密)?分析师|@?\s*信息检索|@?\s*复盘|@?\s*风控|@?\s*协调|"
    r"深度分析|分析一下|帮我分析|给我.*报告|策略A|策略B|这周.*(周报|美股|A股))",
    re.I,
)
WAKE_STRIP_RE = re.compile(
    r"^\s*(小沫|小默|小魔)[,，.。!！？?\s]*(你在吗)?[,，.。!！？?\s]*",
    re.I,
)


def strip_wake_prefix(text: str) -> str:
    t = (text or "").strip()
    t2 = WAKE_STRIP_RE.sub("", t).strip()
    return t2 or t


def _deepseek_key() -> str:
    return (os.getenv("DEEPSEEK_API_KEY") or "").strip()


def _http_session_direct() -> requests.Session:
    sess = requests.Session()
    use_proxy = (os.getenv("AVATAR_LLM_USE_PROXY") or "").strip().lower() in ("1", "true", "yes")
    sess.trust_env = use_proxy
    return sess


def _ok(reply: str, intent: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"reply": reply, "intent": intent, "speak": True}
    out.update(extra)
    return out


def _strategy_slug_for_token(token: str) -> Optional[str]:
    t = token.strip().lower()
    mapping = {
        "159570": "159570-2h",
        "300308": "300308-2h",
        "603986": "603986-2h",
        "688146": "688146-2h",
        "002837": "002837-2h",
        "nvda": "nvda-2h",
        "eth": "eth-2h",
        "btc": None,
        "paxg": "paxg-2h",
        "hype": "hype-2h",
        "crcl": "crcl-2h",
        "510210": "510210-4h",
        "mnq": "mnq-4h",
    }
    return mapping.get(t)


def _fetch_strategy_overview(slug: str) -> Optional[Dict[str, Any]]:
    try:
        from fastapi import HTTPException
        from backpack_quant_trading.api.routers import strategy as strat

        slug = (slug or "").strip().lower()
        fn = None
        if slug.endswith("-2h") and slug.split("-")[0].isdigit():
            code = slug.split("-")[0]
            from backpack_quant_trading.core.a_share_strategy_import import get_spec_by_code

            spec = get_spec_by_code(code)
            label = f"A股·{(spec.name if spec else code)}"
            fn = lambda: strat._a_share_overview(code, label)
        else:
            table = {
                "eth-2h": getattr(strat, "get_eth_2h_overview", None),
                "nvda-2h": getattr(strat, "get_nvda_2h_overview", None),
                "paxg-2h": getattr(strat, "get_paxg_2h_overview", None),
                "crcl-2h": getattr(strat, "get_crcl_1h_overview", None),
                "510210-4h": getattr(strat, "get_sse_510210_4h_overview", None),
                "mnq-4h": getattr(strat, "get_mnq_dip_4h_overview", None),
            }
            fn = table.get(slug)
        if not callable(fn):
            return None
        out = fn()
        if hasattr(out, "model_dump"):
            return out.model_dump()
        if isinstance(out, dict):
            return out
        return dict(out)
    except Exception as e:
        try:
            from fastapi import HTTPException

            if isinstance(e, HTTPException):
                logger.info("小沫策略 overview 不可用 %s: %s", slug, e.detail)
                return None
        except Exception:
            pass
        logger.warning("小沫拉策略 overview 失败 %s: %s", slug, e)
        return None


def _format_strategy_overview(slug: str, data: Dict[str, Any], token: str) -> Dict[str, Any]:
    name = data.get("strategy_name") or slug
    symbol = data.get("symbol") or ""
    tr = data.get("total_return_pct")
    mdd = data.get("max_drawdown_pct")
    wr = data.get("win_rate_pct")
    pf = data.get("profit_factor")
    lines = [
        f"好的，我来讲一下策略卡片「{name}」{f'（{symbol}）' if symbol else ''}：",
        f"- 总收益率：{tr}%" if tr is not None else "",
        f"- 最大回撤：{mdd}%" if mdd is not None else "",
        f"- 胜率：{wr}%" if wr is not None else "",
        f"- 盈亏比：{pf}" if pf is not None else "",
        "需要的话我可以帮你打开对应策略页。",
    ]
    nav = STRATEGY_NAV.get(token.lower())
    return _ok(
        "\n".join([x for x in lines if x]),
        "strategy",
        navigate=nav,
        suggestions=["打开该策略页", "后台有哪些功能", "介绍币种监视"],
    )


def _try_open_page(text: str) -> Optional[Dict[str, Any]]:
    m = OPEN_PAGE_RE.search(text or "")
    if not m:
        # 「打开 159570」
        m2 = re.search(r"(打开|进入|跳转|去)\s*(159570|300308|603986|688146|002837|nvda|eth)", text or "", re.I)
        if m2:
            tok = m2.group(2).lower()
            path = STRATEGY_NAV.get(tok)
            if path:
                return _ok(f"好的，正在打开「{tok}」策略页。", "navigate", navigate=path)
        return None
    raw = re.sub(r"\s+", "", m.group(2).lower())
    # normalize agent记忆
    key = raw.replace("agent", "agent")
    path = None
    for k, p in OPEN_PATH.items():
        if k.replace(" ", "").lower() in key or key in k.replace(" ", "").lower():
            path = p
            break
    if not path:
        path = OPEN_PATH.get(m.group(2).strip())
    if not path:
        return None
    label = m.group(2).strip()
    return _ok(f"好的，正在打开「{label}」。", "navigate", navigate=path)


def _try_menu(text: str) -> Optional[Dict[str, Any]]:
    t = text or ""
    if any(p.search(t) for p, _, _, _ in FEATURE_SCRIPTS) and not re.search(r"后台|菜单|有哪些|能做什么", t):
        return None
    if MENU_RE.search(t) or re.search(r"介绍.*(后台|功能|菜单|模块)|后台.*(介绍|功能)", t):
        return _ok(
            MENU_SCRIPT,
            "menu",
            suggestions=["介绍币种监视", "打开泡沫检测", "讲讲 159570"],
        )
    return None


def _try_feature(text: str) -> Optional[Dict[str, Any]]:
    t = text or ""
    if re.search(r"^(打开|进入|跳转|去)\b", t):
        return None
    for pattern, intent, script, nav in FEATURE_SCRIPTS:
        if pattern.search(t):
            tips = []
            if nav:
                tips.append("打开该页面")
            tips.extend(["后台有哪些功能", "讲讲 159570"])
            return _ok(script, intent, navigate=nav if re.search(r"打开|进入|跳转|带我", t) else None, suggestions=tips)
    return None


def _try_strategy(text: str) -> Optional[Dict[str, Any]]:
    m = STRATEGY_CODE_RE.search(text or "")
    if not m:
        m2 = re.search(r"\b(\d{6})\b", text or "")
        if not m2:
            return None
        token = m2.group(1)
    else:
        token = m.group(1)
    t = text or ""
    if not re.search(r"(策略|表现|收益|回撤|卡片|讲讲|看看|overview|\d{6})", t, re.I):
        if not re.fullmatch(r"\s*\d{6}\s*", t):
            if token.lower() in ("eth", "btc", "nvda", "paxg", "hype", "crcl", "mnq"):
                if not re.search(r"策略|卡片|回测|表现", t):
                    return None
    slug = _strategy_slug_for_token(token)
    if not slug:
        return _ok(
            f"我暂时没有绑定「{token}」的策略卡片路由，你可以在「AI量化实盘」里手动点开查看。",
            "strategy",
            navigate="/strategies",
        )
    data = _fetch_strategy_overview(slug)
    if not data:
        return _ok(
            f"策略「{slug}」暂时读不到概览（可能未导入）。请到「AI量化实盘」确认。",
            "strategy",
            navigate=STRATEGY_NAV.get(token.lower()) or "/strategies",
        )
    return _format_strategy_overview(slug, data, token)


def _try_market(text: str) -> Optional[Dict[str, Any]]:
    t = text or ""
    if not MARKET_RE.search(t) and not re.search(r"\b(eth|btc)\b.*(价|行情|涨|跌)", t, re.I):
        return None
    sym = "ETHUSDT"
    name = "ETH"
    if re.search(r"btc|比特币", t, re.I):
        sym = "BTCUSDT"
        name = "BTC"
    try:
        from backpack_quant_trading.core.binance_monitor import fetch_binance_klines

        rows = fetch_binance_klines(symbol=sym, interval="15m", limit=3) or []
        if not rows:
            return _ok(
                f"暂时拉不到币安 {name} 行情（网络或代理问题）。你可以稍后再问，或打开策略页查看。",
                "market",
            )
        last = rows[-1]
        close = float(last.get("close") or last.get("c") or 0)
        open_ = float(last.get("open") or last.get("o") or close)
        chg = ((close - open_) / open_ * 100.0) if open_ else 0.0
        return _ok(
            f"币安永续 {name} 最近 15 分钟参考价约 {close:.2f} USDT，"
            f"该根 K 相对开盘约 {chg:+.2f}%。这是短周期参考，不构成投资建议。",
            "market",
            suggestions=[f"讲讲 {name.lower()} 策略", "打开量化实盘", "后台有哪些功能"],
        )
    except Exception as e:
        logger.warning("小沫行情失败 %s: %s", sym, e)
        return _ok(f"行情接口暂时不可用：{e}。请稍后再试。", "market")


def _try_agent(text: str) -> Optional[Dict[str, Any]]:
    t = text or ""
    # 明确 Agent / 分析师；避免「分析一下后台」误进
    if not AGENT_RE.search(t):
        return None
    if re.search(r"分析一下.*(后台|功能|菜单|监视)", t):
        return None
    try:
        from backpack_quant_trading.agents.dingtalk_bridge import handle_agent_text

        # 网页侧固定 staff，便于待确认列表隔离；不静默改执行策略
        result = handle_agent_text(t, staff_id="avatar_web")
        md = (result.get("markdown") or "").strip()
        if not md:
            md = "Agent 没有返回内容，请换个说法，例如「@美股分析师 NVDA」。"
        # 语音播报截断，完整内容仍在字幕
        speak_md = re.sub(r"[#>*`]", " ", md)
        speak_md = re.sub(r"\s+", " ", speak_md).strip()[:400]
        return _ok(
            md if len(md) < 2500 else md[:2400] + "\n…（已截断）",
            "agent",
            speak_text=speak_md,
            suggestions=["@美股分析师 NVDA", "介绍币种监视", "后台有哪些功能"],
            agent_ok=bool(result.get("ok", True)),
        )
    except Exception as e:
        logger.exception("小沫 Agent 调用失败: %s", e)
        return _ok(
            f"Agent 暂时不可用：{e}。你仍可问后台功能或策略卡片。",
            "agent",
            suggestions=["后台有哪些功能", "讲讲 159570"],
        )


def _llm_reply(user_text: str, history: List[Dict[str, str]]) -> str:
    api_key = _deepseek_key()
    if not api_key:
        return (
            "云端模型未配置。我仍可介绍后台、打开页面、讲策略卡片、报 ETH/BTC 参考价。"
            "试试：「介绍币种监视」「打开泡沫检测」「讲讲 159570」「ETH 多少钱」。"
        )
    system = (
        "你是「小沫」，沐龙量化网页后台数字人助手。语气亲切、短句、适合语音播报。"
        "可介绍后台、策略与行情；不要编造成交数字；没有数据就老实说。"
    )
    messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
    for h in (history or [])[-8:]:
        role = h.get("role")
        content = (h.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_text})
    try:
        sess = _http_session_direct()
        kwargs: Dict[str, Any] = {
            "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            "json": {"model": "deepseek-chat", "messages": messages, "temperature": 0.4},
            "timeout": 60,
        }
        if not sess.trust_env:
            kwargs["proxies"] = {"http": None, "https": None}
        resp = sess.post("https://api.deepseek.com/v1/chat/completions", **kwargs)
        resp.raise_for_status()
        data = resp.json()
        return (
            ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
            or "我这边暂时没组织好语言，请再说一次。"
        ).strip()
    except Exception as e:
        logger.warning("小沫 LLM 失败: %s", e)
        return (
            "云端模型暂时连不上。你仍可问：「后台有哪些功能」「介绍币种监视」"
            "「打开泡沫检测」「讲讲 159570」「ETH 多少钱」。"
        )


def handle_avatar_chat(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    raw = (message or "").strip()
    if not raw:
        return _ok("我在听，可以问后台功能、打开某个页面、策略表现或 ETH/BTC 行情。", "empty")

    # 仅唤醒词
    if re.fullmatch(r"\s*(小沫|小默|小魔)([,，.。!！？?\s]*(你在吗)?)?\s*", raw, re.I):
        return _ok(
            "我在，请说。可以介绍功能、打开页面、讲策略，或说「@美股分析师 NVDA」。",
            "wake",
            suggestions=["介绍币种监视", "@美股分析师 NVDA", "打开泡沫检测"],
        )

    text = strip_wake_prefix(raw)

    if re.fullmatch(r"打开该(页面|策略页)?", text):
        return _ok("请直接说「打开币种监视」或「打开 159570」。", "clarify")

    nav = _try_open_page(text)
    if nav:
        return nav

    # Agent 优先于笼统「分析」行情（避免抢走 @分析师）
    agent = _try_agent(text)
    if agent:
        return agent

    feat = _try_feature(text)
    if feat:
        return feat

    menu = _try_menu(text)
    if menu:
        return menu

    market = _try_market(text)
    if market:
        return market

    strat = _try_strategy(text)
    if strat:
        return strat

    reply = _llm_reply(text, history or [])
    return _ok(reply, "llm", suggestions=["后台有哪些功能", "介绍币种监视", "@美股分析师 NVDA"])
