from backpack_quant_trading.agents.scheduler_hooks import build_agent_signal_text
from backpack_quant_trading.agents.coordinator import parse_route

t = build_agent_signal_text("CRCL", market="us_stock", timeframe="2h", action="buy")
h = parse_route(t)
print("text=", t)
print("symbols=", h.symbols)
print("ok=", bool(h.symbols))
