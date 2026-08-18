"""基本面纠偏 + 量能中文。"""
from __future__ import annotations

from backpack_quant_trading.core.a_share_ai_agent import (
    compute_volume_structure,
    format_volume_cn,
    fundamentals_brief,
    scrub_false_missing_fundamentals,
)
from backpack_quant_trading.core.a_share_ai_agent_dingtalk import build_action_card_markdown


def test_volume_cn_and_compute():
    bars = []
    for i in range(25):
        bars.append({"close": 100 + i, "volume": 1000 if i < 22 else 120})
    vol = compute_volume_structure(bars)
    assert vol["divergence"] == "price_up_vol_down"
    text = format_volume_cn(vol)
    assert "价涨量缩" in text
    assert "expand" not in text
    assert "price_up_vol_down" not in text


def test_scrub_pe_pb_missing_claim():
    fund = {"pe": 93.3, "pb": 23.2, "roe": 12.9, "revenue_growth": 41.6}
    d = scrub_false_missing_fundamentals(
        {
            "thesis": "基本面方面，最新期净利2.7亿但PE/PB/增速/ROE等关键数据缺失，无法评估估值。",
            "risk_notes": ["基本面关键数据缺失，无法进行有效估值", "诱多"],
        },
        fund,
    )
    assert "缺失" not in d["thesis"]
    assert "估值可用" in d["thesis"]
    assert "无法评估" not in d["thesis"]
    assert "无法进行有效估值" not in str(d["risk_notes"])


def test_card_shows_cn_volume_and_fund():
    title, text = build_action_card_markdown(
        {
            "code": "603629",
            "name": "利通电子",
            "interval_label": "30分钟",
            "as_of": "2026-08-18 11:05:32",
            "fundamentals": {"brief": "PE(TTM) 93.3 · PB 23.21 · ROE 12.93%"},
            "decision": {
                "action": "hold",
                "confidence": 0.65,
                "thesis": "估值可用（PE(TTM) 93.3），量价背离，观望。",
                "volume_structure": {
                    "state": "expand",
                    "divergence": "price_up_vol_down",
                    "trap_risk": "bull_trap",
                    "note": "近1根是均量 1.30 倍",
                },
                "market_vs_stock": {"alignment": "lag", "note": "弱于上证"},
                "risk_notes": ["高位震荡"],
                "valid": True,
            },
        }
    )
    assert "放量" in text
    assert "价涨量缩" in text
    assert "诱多" in text
    assert "price_up_vol_down" not in text
    assert "PE(TTM) 93.3" in text
    assert "弱于大盘" in text
    assert title


def test_fundamentals_brief():
    s = fundamentals_brief({"pe": 98.02, "pb": 23.33, "roe": 12.93, "revenue_growth": 41.6, "missing": ["industry"]})
    assert "PE(TTM)" in s
    assert "ROE" in s
    assert "industry" in s


if __name__ == "__main__":
    test_volume_cn_and_compute()
    test_scrub_pe_pb_missing_claim()
    test_card_shows_cn_volume_and_fund()
    test_fundamentals_brief()
    print("ok")
