# -*- coding: utf-8 -*-
"""冒烟：半点缓存桶 / 钱包备注绑定键 / 默认逐仓 / 中文键值开仓价。"""
from __future__ import annotations

from datetime import datetime

from backpack_quant_trading.core.portal_store import (
    _norm_book_trade_action,
    _normalize_exchanges,
    binding_account_key,
    exchange_base_platform,
    parse_book_webhook_body,
)
from backpack_quant_trading.core.portal_watchlist import _half_hour_bucket
from backpack_quant_trading.core.portal_webhook_trade import _margin_mode_from_cfg


def main() -> None:
    t415 = datetime.now().replace(hour=16, minute=15, second=0, microsecond=0).timestamp()
    t430 = datetime.now().replace(hour=16, minute=30, second=0, microsecond=0).timestamp()
    t500 = datetime.now().replace(hour=17, minute=0, second=0, microsecond=0).timestamp()
    assert _half_hour_bucket(t415) != _half_hour_bucket(t430)
    assert _half_hour_bucket(t430) != _half_hour_bucket(t500)

    label_a = "\u94b1\u5305A"  # 钱包A
    key = binding_account_key("okx", label_a)
    assert key.startswith("okx:") and key.endswith("a"), key
    assert exchange_base_platform(key) == "okx"
    assert key in _normalize_exchanges([key, "hyperliquid"])
    assert "hyperliquid" in _normalize_exchanges([key, "hyperliquid"])
    assert _normalize_exchanges(["okx:wallet_a", "hyperliquid"]) == ["okx:wallet_a", "hyperliquid"]
    assert _margin_mode_from_cfg({}) == "isolated"
    assert _margin_mode_from_cfg({"margin_mode": "\u5168\u4ed3"}) == "cross"  # 全仓

    p = parse_book_webhook_body(
        "\u7b56\u7565\u540d\uff1ax\n"
        "\u4ea4\u6613\u54c1\u79cd\uff1aETHUSDT\n"
        "\u4ef7\u683c\uff1a2420.4\n"
        "\u64cd\u4f5c\uff1asell\n"
        "\u4ed3\u4f4d\u65b9\u5411\uff1ashort"
    )
    assert float(p["\u4ef7\u683c"]) == 2420.4
    assert _norm_book_trade_action(p) == "open"
    print("OK")


if __name__ == "__main__":
    main()
