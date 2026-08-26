"""A股 AI Agent T0 规则与台账。"""
from __future__ import annotations

from backpack_quant_trading.core.a_share_ai_agent import apply_hard_rules, default_position_for_interval
from backpack_quant_trading.core.a_share_ai_agent_t0 import apply_t0_rules


def test_default_position_30_t0_base_not_sellable():
    p = default_position_for_interval("30")
    assert p["holding"] is True
    assert p["has_base_position"] is True
    assert p["sellable"] is False
    assert p["intraday_open"] is False
    assert p["can_buy"] is True
    assert p["intraday_ok"] is True


def test_default_position_60_empty():
    p = default_position_for_interval("60")
    assert p["holding"] is False
    assert p["sellable"] is False
    assert p["intraday_ok"] is False


def test_t0_ignore_first_sell_without_open():
    d = apply_t0_rules({"action": "sell", "thesis": "想卖底仓"}, interval="30", intraday_open=False)
    assert d["action"] == "hold"
    assert d["t0_ignored"] is True
    assert d["t0_raw_action"] == "sell"
    assert "底仓" in str(d.get("invalid_reason") or "")


def test_t0_block_second_buy_while_open():
    d = apply_t0_rules({"action": "buy", "thesis": "再买"}, interval="30", intraday_open=True)
    assert d["action"] == "hold"
    assert d["t0_ignored"] is True
    assert d["t0_raw_action"] == "buy"


def test_t0_allow_sell_when_open():
    d = apply_t0_rules({"action": "sell", "thesis": "平仓"}, interval="30", intraday_open=True)
    assert d["action"] == "sell"
    assert not d.get("t0_ignored")


def test_t0_allow_buy_when_flat():
    d = apply_t0_rules({"action": "buy", "thesis": "开仓"}, interval="30", intraday_open=False)
    assert d["action"] == "buy"


def test_hard_rules_block_sell_when_empty_swing():
    d = apply_hard_rules(
        {"action": "sell", "thesis": "空仓卖"},
        limit_status="normal",
        position=default_position_for_interval("D"),
    )
    assert d["action"] == "hold"
    assert "无持仓" in str(d.get("invalid_reason") or "")


def test_hard_rules_block_sell_bought_today_not_sellable_swing():
    d = apply_hard_rules(
        {"action": "sell", "thesis": "想卖"},
        limit_status="normal",
        position={"holding": True, "bought_today": True, "sellable": False, "intraday_ok": False},
    )
    assert d["action"] == "hold"
    assert d["t1_blocked"] is True


def test_hard_rules_allow_sell_when_t0_open():
    d = apply_hard_rules(
        {"action": "sell", "thesis": "平日内仓"},
        limit_status="normal",
        position={
            "holding": True,
            "has_base_position": True,
            "sellable": True,
            "bought_today": True,
            "intraday_ok": True,
            "intraday_open": True,
        },
    )
    assert d["action"] == "sell"
    assert d["valid"] is True
