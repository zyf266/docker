from backpack_quant_trading.agents.intent_router import handle_meta_intent, detect_scoring_market

q = "现在美股的评分权重是怎样的"
r = handle_meta_intent(q)
md = r.get("markdown") or ""
print("market", detect_scoring_market(q), "intent", r.get("intent"))
print("is_us_title", "美股评分权重" in md)
print("not_crypto_title", "加密「买入信号」" not in md[:120])
print("has_us_formula", "0.50×动能" in md and "新闻" in md)
