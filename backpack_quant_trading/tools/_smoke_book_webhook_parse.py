"""本地冒烟：账面 webhook 中文键值 / 宽松 JSON 解析。"""
from __future__ import annotations

from backpack_quant_trading.core.portal_store import (
    _norm_book_trade_action,
    _norm_book_trade_side,
    normalize_book_strategy_symbol,
    parse_book_webhook_body,
)


def main() -> None:
    raw = """策略名：ETH  2H空15分钟离场
交易品种：BINANCE:ETHUSDT.P
价格：3500.5
操作：sell
仓位方向：short"""
    p = parse_book_webhook_body(raw)
    assert p["策略名"].startswith("ETH"), p
    assert p["操作"] == "sell"
    sym = normalize_book_strategy_symbol(p["交易品种"])
    assert sym == "ETHUSDT", sym
    act = _norm_book_trade_action(p)
    side = _norm_book_trade_side(p, action=act)
    assert act == "open" and side == "SELL", (act, side)

    p2 = parse_book_webhook_body(
        """策略名：ETH  2H空15分钟离场
交易品种：ETHUSDT
价格：3400
操作：buy
仓位方向：flat"""
    )
    assert _norm_book_trade_action(p2) == "close"
    assert _norm_book_trade_side(p2, action="close") == "BUY"

    try:
        parse_book_webhook_body("")
        raise SystemExit("empty should fail")
    except ValueError as e:
        assert "空" in str(e)

    p3 = parse_book_webhook_body(
        '{\n  "strategy_name": "x",\n  "symbol": "BTC",\n  "action": "open",\n}'
    )
    assert p3["symbol"] == "BTC"

    print("OK", sym, act, side)


if __name__ == "__main__":
    main()
