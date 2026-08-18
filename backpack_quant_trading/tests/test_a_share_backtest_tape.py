from backpack_quant_trading.core.a_share_ai_agent import (
    backtest_fundamentals_payload,
    compute_tape_stats,
)
from backpack_quant_trading.core.a_share_ai_agent_prompts import BACKTEST_SYSTEM_ADDENDUM, BACKTEST_USER_HINT


def test_tape_stats_buy_bias_on_crash():
    bars = [{"close": 200 - i * 4} for i in range(30)]  # 200 -> 84
    t = compute_tape_stats(bars)
    assert t["ok"] is True
    assert t["drawdown_from_high_pct"] < -18
    assert t["buy_bias"] is True


def test_tape_stats_no_bias_chop():
    bars = [{"close": 100 + (i % 3)} for i in range(30)]
    t = compute_tape_stats(bars)
    assert t["buy_bias"] is False


def test_backtest_fund_strips_lookahead_pe():
    p = backtest_fundamentals_payload(
        {"pe": 98.0, "pb": 23.0, "roe": 12.0, "name": "利扬芯片", "industry": "半导体"}
    )
    assert "pe" not in p
    assert "pb" not in p
    assert p["mode"] == "backtest_no_lookahead"
    assert "前视" in p["note"]
    assert p["industry"] == "半导体"


def test_backtest_prompt_forbids_all_hold():
    assert "前视" in BACKTEST_USER_HINT
    assert "PE/PB" in BACKTEST_USER_HINT
    assert "全部写成 hold" in BACKTEST_SYSTEM_ADDENDUM


if __name__ == "__main__":
    test_tape_stats_buy_bias_on_crash()
    test_tape_stats_no_bias_chop()
    test_backtest_fund_strips_lookahead_pe()
    test_backtest_prompt_forbids_all_hold()
    print("ok")
