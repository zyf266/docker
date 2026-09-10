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


def test_calc_round_pnl_and_closed_rounds():
    from backpack_quant_trading.core.a_share_ai_agent_t0 import (
        build_closed_rounds_from_rows,
        calc_round_pnl,
    )

    pnl = calc_round_pnl(10.0, 11.0)
    assert pnl["pnl_abs"] == 1.0
    assert abs(pnl["pnl_pct"] - 10.0) < 1e-6

    rows = [
        {"id": 1, "code": "000716", "name": "黑芝麻", "interval": "30", "side": "buy",
         "status": "executed", "price": 5.52, "trade_date": "2026-09-04", "pair_id": None},
        {"id": 2, "code": "000716", "name": "黑芝麻", "interval": "30", "side": "sell",
         "status": "executed", "price": 5.67, "trade_date": "2026-09-07", "pair_id": 1},
        {"id": 3, "code": "002262", "name": "恩华药业", "interval": "30", "side": "buy",
         "status": "executed", "price": 22.0, "trade_date": "2026-09-04", "pair_id": None},
        {"id": 4, "code": "002262", "name": "恩华药业", "interval": "30", "side": "sell",
         "status": "executed", "price": 22.73, "trade_date": "2026-09-04", "pair_id": 3},
        {"id": 5, "code": "000716", "name": "黑芝麻", "interval": "60", "side": "buy",
         "status": "executed", "price": 5.67, "trade_date": "2026-09-07", "pair_id": None},
    ]
    rounds = build_closed_rounds_from_rows(rows)
    assert len(rounds) == 2
    by_code = {r["code"]: r for r in rounds}
    assert abs(by_code["000716"]["pnl_pct"] - ((5.67 / 5.52 - 1) * 100)) < 1e-3
    assert abs(by_code["002262"]["pnl_pct"] - ((22.73 / 22.0 - 1) * 100)) < 1e-3


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


def test_quality_gate_blocks_shrink_buy():
    from backpack_quant_trading.core.a_share_ai_agent import apply_quality_buy_gates

    d = apply_quality_buy_gates(
        {
            "action": "buy",
            "confidence": 0.8,
            "thesis": "想买",
            "volume_structure": {"state": "shrink", "trap_risk": "none"},
        }
    )
    assert d["action"] == "hold"
    assert d["quality_gate"] == "shrink"
    assert d["valid"] is False


def test_quality_gate_blocks_bull_trap_buy():
    from backpack_quant_trading.core.a_share_ai_agent import apply_quality_buy_gates

    d = apply_quality_buy_gates(
        {
            "action": "buy",
            "confidence": 0.9,
            "thesis": "突破",
            "volume_structure": {"state": "neutral", "trap_risk": "bull_trap"},
        }
    )
    assert d["action"] == "hold"
    assert d["quality_gate"] == "bull_trap"


def test_quality_gate_blocks_low_confidence_buy():
    from backpack_quant_trading.core.a_share_ai_agent import apply_quality_buy_gates

    d = apply_quality_buy_gates(
        {
            "action": "buy",
            "confidence": 0.4,
            "thesis": "勉强",
            "volume_structure": {"state": "expand", "trap_risk": "none"},
        }
    )
    assert d["action"] == "hold"
    assert d["quality_gate"] == "low_confidence"


def test_quality_gate_allows_expand_buy():
    from backpack_quant_trading.core.a_share_ai_agent import apply_quality_buy_gates

    d = apply_quality_buy_gates(
        {
            "action": "buy",
            "confidence": 0.7,
            "thesis": "放量突破",
            "volume_structure": {"state": "expand", "trap_risk": "none"},
        }
    )
    assert d["action"] == "buy"


def test_t0_pnl_exit_take_profit():
    from datetime import datetime

    from backpack_quant_trading.core.a_share_ai_agent_t0 import apply_t0_pnl_exits

    d = apply_t0_pnl_exits(
        {"action": "hold", "thesis": "再等等"},
        interval="30",
        open_buy={"id": 1, "price": 10.0},
        last_price=10.09,  # +0.9%
        now=datetime(2026, 9, 10, 11, 0, 0),
    )
    assert d["action"] == "sell"
    assert d["t0_exit_override"] == "t0_tp"


def test_t0_pnl_exit_stop_loss():
    from datetime import datetime

    from backpack_quant_trading.core.a_share_ai_agent_t0 import apply_t0_pnl_exits

    d = apply_t0_pnl_exits(
        {"action": "hold", "thesis": "扛住"},
        interval="30",
        open_buy={"id": 1, "price": 10.0},
        last_price=9.95,  # -0.5%
        now=datetime(2026, 9, 10, 11, 0, 0),
    )
    assert d["action"] == "sell"
    assert d["t0_exit_override"] == "t0_sl"


def test_t0_pnl_exit_afternoon_flat():
    from datetime import datetime

    from backpack_quant_trading.core.a_share_ai_agent_t0 import apply_t0_pnl_exits

    d = apply_t0_pnl_exits(
        {"action": "hold", "thesis": "拖到尾盘"},
        interval="30",
        open_buy={"id": 1, "price": 10.0},
        last_price=10.01,  # +0.1% < 0.15%
        now=datetime(2026, 9, 10, 14, 35, 0),
    )
    assert d["action"] == "sell"
    assert d["t0_exit_override"] == "t0_time"


def test_t0_pnl_exit_no_open_keeps_buy():
    from datetime import datetime

    from backpack_quant_trading.core.a_share_ai_agent_t0 import apply_t0_pnl_exits

    d = apply_t0_pnl_exits(
        {"action": "buy", "thesis": "开仓"},
        interval="30",
        open_buy=None,
        last_price=10.0,
        now=datetime(2026, 9, 10, 14, 40, 0),
    )
    assert d["action"] == "buy"
    assert not d.get("t0_exit_override")


def test_t0_pnl_exit_ignores_non_30():
    from datetime import datetime

    from backpack_quant_trading.core.a_share_ai_agent_t0 import apply_t0_pnl_exits

    d = apply_t0_pnl_exits(
        {"action": "hold", "thesis": "波段"},
        interval="60",
        open_buy={"id": 1, "price": 10.0},
        last_price=10.2,
        now=datetime(2026, 9, 10, 14, 40, 0),
    )
    assert d["action"] == "hold"
    assert not d.get("t0_exit_override")
