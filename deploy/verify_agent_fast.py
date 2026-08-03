import time
from backpack_quant_trading.agents.coordinator import extract_symbols
from backpack_quant_trading.agents.analysts.crypto_analyst import _agent_fast_enabled

t0 = time.time()
syms = extract_symbols("分析一下ETH 2h")
print("syms", syms, "parse_ms", int((time.time() - t0) * 1000))
print("agent_fast", _agent_fast_enabled())
