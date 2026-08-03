from backpack_quant_trading.agents.intent_router import try_handle_intent, classify_intent
from backpack_quant_trading.core.dingtalk_manual_score import is_manual_score_command
from backpack_quant_trading.agents.dingtalk_bridge import should_route_to_agent

q = "现在评分权重是怎样的"
print("intent", classify_intent(q))
print("manual", is_manual_score_command(q))
print("route", should_route_to_agent(q))
r = try_handle_intent(q)
print("handled", (r or {}).get("intent"), "has_formula", "0.48" in ((r or {}).get("markdown") or ""))
