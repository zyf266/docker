"""钉钉 ↔ Agent 编排桥接（与旧手动评分并存）。"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict

from backpack_quant_trading.agents.coordinator import extract_symbols, parse_route, strip_prefix
from backpack_quant_trading.agents.execution_agent import parse_exec_command
from backpack_quant_trading.agents.memory import is_agent_preference_command

logger = logging.getLogger(__name__)

_AGENT_ROLE_RE = re.compile(
    r"(美股分析师|A股分析师|加密分析师|信息检索|风控|复盘|执行|协调|小管家)"
)
_STEWARD_RE = re.compile(r"^@?小管家\b", re.I)


def agent_orch_enabled() -> bool:
    return os.getenv("AGENT_ORCH_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")


def mentions_agent_role(user_text: str) -> bool:
    """是否点名了多 Agent 角色（优先级高于旧「信号评分」）。"""
    return bool(_AGENT_ROLE_RE.search(user_text or ""))


_STEWARD_OPS_KEYS = (
    "小管家",
    "币种监视",
    "币种监控",
    "合约监视",
    "合约监控",
    "分钟监视",
    "分钟监控",
    "分钟预警",
    "订单簿",
    "订单薄",
    "MACD",
    "金叉形态",
    "形态监控",
    "形态监视",
    "金叉",
    "死叉",
    "水上金叉",
    "水下金叉",
    "新闻监控",
    "新闻监视",
    "快讯监控",
    "财报",
    "当前监视",
    "当前监控",
    "监视状态",
    "监控状态",
    "监视列表",
    "策略实例",
    "查看策略实例",
    "实例列表",
    "实例状态",
    "实例日志",
    "确认停止实例",
    "确认启动实例",
    "停止实例",
    "启动实例",
    "改成逐仓",
    "改成全仓",
    "停止",
    "删除",
    "移除",
    "关掉",
    "关闭",
)


def is_exec_workflow_command(user_text: str) -> bool:
    """确认 / 取消 / 待确认列表 —— 优先于小管家（避免「取消」被监视口令抢走）。"""
    from backpack_quant_trading.agents.execution_agent import parse_exec_command

    ok, _pid = parse_exec_command(user_text or "")
    return bool(ok)


def is_steward_command(user_text: str) -> bool:
    """点名小管家，或明显是后台监视配置口令（@机器人/@小管家 常被钉钉剥掉）。"""
    t = (user_text or "").strip()
    if not t:
        return False
    # 执行确认工作流优先
    if is_exec_workflow_command(t):
        return False
    if _STEWARD_RE.search(t) or "小管家" in t:
        return True
    if any(k in t for k in _STEWARD_OPS_KEYS):
        return True
    # 增加/新增/给我/帮我/停止 + 监视类或 MACD 形态词
    if any(
        k in t
        for k in (
            "新增",
            "增加",
            "添加",
            "帮我",
            "给我",
            "监控一个",
            "监视一个",
            "停止",
            "删除",
            "移除",
            "取消",
            "关掉",
            "关闭",
        )
    ) and any(
        k in t
        for k in (
            "监视",
            "监控",
            "预警",
            "新闻",
            "财报",
            "评级",
            "金叉",
            "死叉",
            "MACD",
            "形态",
        )
    ):
        return True
    # 裸「新闻」+ 美股代码
    if "新闻" in t and any(
        x in t.upper() for x in ("NVDA", "TSLA", "AAPL", "MSFT", "META", "GOOGL", "AMZN", "AMD")
    ):
        return True
    return False

def should_route_to_agent(user_text: str) -> bool:
    """判断是否走多 Agent 编排（优先于旧「评分」路径）。"""
    if not agent_orch_enabled():
        return False
    t = (user_text or "").strip()
    if not t:
        return False

    # 元问题 / 闲聊疑问：走 Agent，避免误入旧「手动评分」
    try:
        from backpack_quant_trading.agents.intent_router import classify_intent, is_meta_question

        if is_meta_question(t) or classify_intent(t) in ("meta", "chat"):
            return True
    except Exception:
        pass

    kind, _ = parse_exec_command(t)
    if kind:
        return True

    if is_steward_command(t):
        return True

    # 点名角色：一律走 Agent（即使同时写了「信号评分」）
    if mentions_agent_role(t):
        return True

    hit, _ = strip_prefix(t)
    if hit is not None:
        return True

    kind2, _ = parse_exec_command(t)
    if kind2:
        return True

    if is_agent_preference_command(t):
        return True

    if t.startswith("复盘") or "复盘 " in t:
        return True

    syms = extract_symbols(t)
    if len(syms) >= 2:
        return True

    # 自然语言分析且带标的（无「评分」时走 Agent；带「评分/打分」留给旧路径）
    if any(k in t for k in ("看看", "分析一下", "帮我看", "怎么看")) and syms:
        if not any(k in t for k in ("评分", "打分", "score")):
            return True

    if t.startswith("信息检索") or t.startswith("风控") or t.startswith("执行"):
        return True

    # 策略A/B 个股报告：给我一份利通电子 策略A的报告 / NVDA 策略B
    if re.search(r"策略\s*[A-Za-z]", t) and any(
        k in t for k in ("报告", "分析", "深度", "周报")
    ):
        return True
    if ("报告" in t or "深度分析" in t) and any(
        k in t for k in ("给我", "帮我", "生成", "来一份", "出一份")
    ):
        try:
            from backpack_quant_trading.agents.a_share_resolve import extract_a_share_from_text

            if extract_a_share_from_text(t):
                return True
        except Exception:
            pass
        if re.search(r"(?<![A-Za-z0-9])([A-Z]{2,5})(?![A-Za-z0-9])", t.upper()):
            return True

    return False


def call_steward_api(user_text: str, *, staff_id: str = "") -> Dict[str, Any]:
    """监视 singleton 在 api 进程：钉钉侧必须 HTTP 转发到 /api/steward/command。"""
    import urllib.error
    import urllib.request
    import json

    base = (
        os.getenv("AGENT_API_BASE", "").strip()
        or os.getenv("API_BASE", "").strip()
        or "http://api:8100"
    ).rstrip("/")
    token = (
        os.getenv("AGENT_STEWARD_TOKEN", "").strip()
        or os.getenv("WEBHOOK_SECRET", "").strip()
    )
    if not token:
        return {
            "ok": False,
            "markdown": (
                "### 小管家\n未配置 `AGENT_STEWARD_TOKEN` / `WEBHOOK_SECRET`，"
                "无法调用后台监视接口。"
            ),
            "reports": [],
        }
    url = f"{base}/api/steward/command"
    body = json.dumps({"text": user_text, "staff_id": staff_id or ""}, ensure_ascii=False).encode(
        "utf-8"
    )
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        return {
            "ok": bool(data.get("ok")),
            "markdown": data.get("markdown") or "",
            "reports": [],
        }
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            pass
        logger.exception("steward api HTTP %s: %s", exc.code, detail)
        return {
            "ok": False,
            "markdown": f"### 小管家\n调用后台失败 HTTP {exc.code}\n```\n{detail}\n```",
            "reports": [],
        }
    except Exception as exc:
        logger.exception("steward api failed: %s", exc)
        return {"ok": False, "markdown": f"### 小管家\n调用后台失败：{exc}", "reports": []}


def handle_agent_text(user_text: str, *, staff_id: str = "") -> Dict[str, Any]:
    # 意图：元问题 / 闲聊先答，避免落到「请对 BTC 评分」
    try:
        from backpack_quant_trading.agents.intent_router import try_handle_intent

        early = try_handle_intent(user_text, staff_id=staff_id)
        if early is not None:
            return {
                "ok": bool(early.get("ok", True)),
                "markdown": early.get("markdown") or "",
                "intent": early.get("intent"),
                "reports": [],
            }
    except Exception as exc:
        logger.exception("intent router failed: %s", exc)

    # 确认/取消/待确认列表走 coordinator，不进小管家
    if is_exec_workflow_command(user_text):
        from backpack_quant_trading.agents.coordinator import handle

        try:
            return handle(user_text, staff_id=staff_id, propose_execution=True)
        except Exception as exc:
            logger.exception("agent exec workflow failed: %s", exc)
            return {"ok": False, "markdown": f"Agent 处理失败：{exc}", "reports": []}

    if is_steward_command(user_text):
        return call_steward_api(user_text, staff_id=staff_id)

    from backpack_quant_trading.agents.coordinator import handle

    try:
        return handle(user_text, staff_id=staff_id, propose_execution=True)
    except Exception as exc:
        logger.exception("agent handle failed: %s", exc)
        return {"ok": False, "markdown": f"Agent 处理失败：{exc}", "reports": []}


def usage_hint() -> str:
    return (
        "【Agent】@美股分析师 NVDA / @A股分析师 茅台 / @加密分析师 BTC\n"
        "【个股策略A】给我一份利通电子 策略A的报告 / 给我一份 NVDA 策略A的报告\n"
        "【个股策略B】给我一份利通电子 策略B的报告 / @美股分析师 TSLA 策略B\n"
        "【周报】@美股分析师 这周美股周报 / @A股分析师 这周A股周报\n"
        "【小管家】@小管家 新增 ETH 2h 币种监视 | 当前监视状态\n"
        "【实例】查看策略实例 | 确认停止实例 <id> | 确认启动实例 <id> | 实例日志\n"
        "【问答】现在评分权重是怎样的 / 怎么用 / 待确认列表\n"
        "拆单：看看茅台+BTC | 检索：@信息检索 NVDA | 复盘 NVDA\n"
        "纠正偏好：纠正偏好：更严止损 | 下单：确认 / 取消\n"
        "【旧评分】对 TSM 2h 买入 评分（不要问权重时带「评分」歧义句）"
    )
