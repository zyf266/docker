#!/usr/bin/env python
"""联通测试：跳过余额/均线门槛，真实向 Hyperliquid / OKX 发开仓+TP/SL 请求。

环境变量：
  PORTAL_SKIP_EQUITY_CHECK=1
  PORTAL_SKIP_MA_GATE=1
  PORTAL_TEST_MARGIN=5
  PORTAL_WEBHOOK_DRY_RUN=0

OKX 凭证优先级：
  1) 用户 Portal 绑定
  2) 环境变量 OKX_API_KEY / OKX_SECRET_KEY / OKX_PASSPHRASE（OKX_DEMO=1 模拟盘）
  3) ~/.okx/config.toml 的 profiles.demo（或 OKX_PROFILE=live）

用法：
  python -m backpack_quant_trading.tools.e2e_portal_exchange_orders --user-id 7
  python -m backpack_quant_trading.tools.e2e_portal_exchange_orders --user-id 7 --exchange okx
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("PORTAL_SKIP_EQUITY_CHECK", "1")
os.environ.setdefault("PORTAL_SKIP_MA_GATE", "1")
os.environ.setdefault("PORTAL_TEST_MARGIN", "5")
os.environ["PORTAL_WEBHOOK_DRY_RUN"] = "0"

from backpack_quant_trading.core.env_loader import load_project_env


def _parse_okx_toml(path: Path, profile: str) -> Optional[Tuple[str, str, str, bool]]:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    # 极简 TOML 段解析，避免引入依赖
    sections = re.split(r"\n(?=\[)", text)
    wanted = f"[profiles.{profile}]"
    block = next((s for s in sections if s.strip().startswith(wanted)), "")
    if not block:
        return None

    def _val(key: str) -> str:
        m = re.search(rf'^\s*{re.escape(key)}\s*=\s*"([^"]*)"', block, re.M)
        return (m.group(1) if m else "").strip()

    key = _val("api_key")
    sec = _val("secret_key")
    pwd = _val("passphrase")
    demo_m = re.search(r"^\s*demo\s*=\s*(true|false)", block, re.M | re.I)
    demo = (demo_m.group(1).lower() == "true") if demo_m else (profile == "demo")
    if not key or not sec or not pwd:
        return None
    return key, sec, pwd, demo


def _resolve_okx_secrets() -> Optional[Dict[str, Any]]:
    env_key = (os.getenv("OKX_API_KEY") or "").strip()
    env_sec = (os.getenv("OKX_SECRET_KEY") or os.getenv("OKX_API_SECRET") or "").strip()
    env_pwd = (os.getenv("OKX_PASSPHRASE") or "").strip()
    if env_key and env_sec and env_pwd:
        demo = (os.getenv("OKX_DEMO") or "1").strip().lower() in ("1", "true", "yes", "on")
        return {"api_key": env_key, "api_secret": env_sec, "api_passphrase": env_pwd, "demo": demo, "source": "env"}

    profile = (os.getenv("OKX_PROFILE") or "demo").strip() or "demo"
    parsed = _parse_okx_toml(Path.home() / ".okx" / "config.toml", profile)
    if not parsed:
        return None
    key, sec, pwd, demo = parsed
    return {"api_key": key, "api_secret": sec, "api_passphrase": pwd, "demo": demo, "source": f"~/.okx:{profile}"}


def main() -> int:
    load_project_env()
    os.environ["PORTAL_SKIP_EQUITY_CHECK"] = "1"
    os.environ["PORTAL_SKIP_MA_GATE"] = "1"
    os.environ["PORTAL_WEBHOOK_DRY_RUN"] = "0"

    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--exchange", default="all", choices=("all", "hyperliquid", "okx"))
    parser.add_argument("--symbol", default="ETHUSDT", help="用 ETH 张数不易过小")
    parser.add_argument("--side", default="BUY", choices=("BUY", "SELL"))
    parser.add_argument("--tp", default="5")
    parser.add_argument("--sl", default="3")
    parser.add_argument("--leverage", type=int, default=5)
    args = parser.parse_args()

    from backpack_quant_trading.core import portal_store as store
    from backpack_quant_trading.core.portal_exchange import _secrets_from_binding
    from backpack_quant_trading.core import portal_webhook_trade as wh

    uid = args.user_id
    targets = []
    if args.exchange in ("all", "hyperliquid"):
        targets.append("hyperliquid")
    if args.exchange in ("all", "okx"):
        targets.append("okx")

    summary = []
    for plat in targets:
        secrets: Dict[str, str] = {}
        demo = False
        source = "binding"
        binding = store.get_exchange_binding(uid, plat)
        if binding:
            secrets = _secrets_from_binding(binding.get("config") or {})
            demo = bool((binding.get("config") or {}).get("demo"))
        elif plat == "okx":
            resolved = _resolve_okx_secrets()
            if not resolved:
                print(f"[{plat}] 无绑定且无 ~/.okx / 环境变量，跳过")
                summary.append({"exchange": plat, "status": "no_binding"})
                continue
            secrets = {
                "api_key": resolved["api_key"],
                "api_secret": resolved["api_secret"],
                "api_passphrase": resolved["api_passphrase"],
            }
            demo = bool(resolved["demo"])
            source = str(resolved["source"])
        else:
            print(f"[{plat}] 无绑定，跳过")
            summary.append({"exchange": plat, "status": "no_binding"})
            continue

        cfg = {
            "user_id": uid,
            "symbol": args.symbol,
            "exchange": plat,
            "strategy_name": "e2e-probe",
            "timeframe": "2h",
            "size_mode": "fixed",
            "size_value": os.getenv("PORTAL_TEST_MARGIN") or "5",
            "leverage": args.leverage,
            "take_profit": args.tp,
            "stop_loss": args.sl,
            "require_short": False,
            "require_mid": False,
            "require_long": False,
        }
        print(f"\n=== {plat} demo={demo} source={source} symbol={args.symbol} side={args.side} ===")
        if plat == "hyperliquid":
            out = wh._exec_hyperliquid(cfg, args.side, secrets, dry=False)
        else:
            out = wh._exec_okx(cfg, args.side, secrets, dry=False, demo=demo)
        # 脱敏：不打印密钥
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        summary.append(
            {
                "exchange": plat,
                "demo": demo,
                "source": source,
                "status": out.get("status"),
                "detail": out.get("detail"),
                "tpsl_attached": out.get("tpsl_attached"),
                "tpsl": out.get("tpsl") or out.get("tpsl_probe"),
                "exchange_code": (out.get("exchange_response") or {}).get("code")
                if isinstance(out.get("exchange_response"), dict)
                else None,
            }
        )

        try:
            store.record_trade(
                uid,
                platform=plat,
                symbol=args.symbol,
                side=args.side,
                action="open",
                strategy_name="e2e-probe",
                timeframe="2h",
                price=out.get("entry") or out.get("mark"),
                quantity=out.get("size") or out.get("sz"),
                margin=out.get("margin"),
                leverage=args.leverage,
                status="ok" if out.get("status") == "ok" else str(out.get("status")),
                detail=str(out.get("detail") or "")[:240],
            )
        except Exception as exc:
            print("record_trade err", exc)

    print("\n=== SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    reached = [
        s
        for s in summary
        if s.get("status") in ("ok", "error", "skipped") and s.get("status") != "no_binding"
    ]
    return 0 if reached else 1


if __name__ == "__main__":
    raise SystemExit(main())
