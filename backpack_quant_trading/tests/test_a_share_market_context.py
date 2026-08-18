"""A股 AI 自适应：大盘相对强弱（不依赖实盘 LLM）。"""
from __future__ import annotations

from backpack_quant_trading.core.a_share_ai_agent import (
    apply_market_vs_stock,
    build_market_context,
    index_keys_for_code,
    _alignment_from_rs,
    _close_pct,
)
from backpack_quant_trading.core.a_share_ai_agent_dingtalk import build_action_card_markdown


def _bars(n: int, start: float, step: float) -> list:
    out = []
    px = start
    for i in range(n):
        out.append(
            {
                "open_time": 1_700_000_000_000 + i * 30 * 60 * 1000,
                "open": px,
                "high": px,
                "low": px,
                "close": px,
                "volume": 1000,
                "time_label": str(i),
            }
        )
        px += step
    return out


def test_index_keys_by_board():
    assert index_keys_for_code("603629")[0] == "sh_composite"
    assert "csi300" in index_keys_for_code("603629")
    assert index_keys_for_code("300750")[0] == "chinext"
    assert index_keys_for_code("688256")[0] == "star50"
    assert index_keys_for_code("000001")[0] == "sz_component"


def test_close_pct_and_alignment():
    stock = _bars(30, 100.0, 1.0)
    last = 100.0 + 29 * 1.0
    prev = 100.0 + 28 * 1.0
    assert _close_pct(stock, 1) == round((last - prev) / prev * 100.0, 3)
    assert _alignment_from_rs(2.0, "30") == "lead"
    assert _alignment_from_rs(-2.0, "30") == "lag"
    assert _alignment_from_rs(0.1, "30") == "sync"


def test_market_context_lead_without_network():
    stock = _bars(40, 100.0, 0.8)
    index = _bars(40, 3000.0, 0.0)
    csi = _bars(40, 4000.0, 0.0)
    market = build_market_context(
        "603629",
        "30",
        stock,
        index_bars_by_key={
            "sh_composite": (index, "mock"),
            "csi300": (csi, "mock"),
        },
    )
    assert market["ok"] is True
    assert market["alignment_hint"] == "lead"
    assert market["vs_primary"]["rs_5"] is not None
    assert market["vs_primary"]["rs_5"] > 0


def test_apply_overrides_missing_market_claim():
    market = {
        "ok": True,
        "alignment_hint": "lag",
        "note": "对照上证指数：近1根个股-0.5% / 指数1.2%，超额-1.7pct。",
    }
    d = apply_market_vs_stock(
        {"action": "hold", "market_vs_stock": {"alignment": "unclear", "note": "无大盘数据，无法判断个股相对强弱"}},
        market,
    )
    mvs = d["market_vs_stock"]
    assert mvs["alignment"] == "lag"
    assert "无大盘" not in mvs["note"]
    title, text = build_action_card_markdown(
        {
            "code": "603629",
            "name": "利通电子",
            "interval_label": "30分钟",
            "as_of": "2026-08-18 10:28:38",
            "decision": d,
        }
    )
    assert "无大盘" not in text
    assert "lag" in text
    assert title


if __name__ == "__main__":
    test_index_keys_by_board()
    test_close_pct_and_alignment()
    test_market_context_lead_without_network()
    test_apply_overrides_missing_market_claim()
    print("ok")
