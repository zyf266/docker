"""30分钟默认底仓 + 硬规则日内可卖。"""
from __future__ import annotations

from backpack_quant_trading.core.a_share_ai_agent import (
    apply_hard_rules,
    default_position_for_interval,
)


def test_default_position_30_has_base_intraday():
    p = default_position_for_interval("30")
    assert p["holding"] is True
    assert p["has_base_position"] is True
    assert p["sellable"] is True
    assert p["bought_today"] is False
    assert p["intraday_ok"] is True


def test_default_position_60_empty():
    p = default_position_for_interval("60")
    assert p["holding"] is False
    assert p["sellable"] is False
    assert p["intraday_ok"] is False


def test_hard_rules_allow_sell_base_position_same_day():
    d = apply_hard_rules(
        {"action": "sell", "thesis": "破位减仓"},
        limit_status="normal",
        position=default_position_for_interval("30"),
    )
    assert d["action"] == "sell"
    assert d["valid"] is True
    assert d.get("t1_blocked") is False


def test_hard_rules_block_sell_bought_today_not_sellable():
    d = apply_hard_rules(
        {"action": "sell", "thesis": "想卖"},
        limit_status="normal",
        position={"holding": True, "bought_today": True, "sellable": False},
    )
    assert d["action"] == "hold"
    assert d["t1_blocked"] is True


def test_hard_rules_block_sell_when_empty():
    d = apply_hard_rules(
        {"action": "sell", "thesis": "空仓卖"},
        limit_status="normal",
        position=default_position_for_interval("D"),
    )
    assert d["action"] == "hold"
    assert "无持仓" in str(d.get("invalid_reason") or "")
