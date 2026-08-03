from backpack_quant_trading.core.stock_news_alert import (
    load_config,
    is_material_news,
    _impact_keyword_list,
    matches_watch,
)
from backpack_quant_trading.core.stock_news_keyword_i18n import text_matches_any_term

c = load_config()
kw = _impact_keyword_list(c)
t = "report earnings as chip"
print("mat", is_material_news(t, 0, kw, True))
print("any", text_matches_any_term(t, kw))
print("earn_in", [x for x in kw if "earn" in x.lower()][:8])
print("extra", c.get("only_extra_impact_keywords"), c.get("extra_impact_keywords"))
print("only_material", c.get("only_material"))
# real yahoo-like
t2 = "[Yahoo Finance] Tech stocks today: Microsoft, Meta, Qualcomm report earnings as chip stocks struggle (NVIDIA NVDA MICRON MU)"
print("mat2", is_material_news(t2, 0, kw, True))
print("watch2", matches_watch(t2, c.get("watch_names") or [], {"text": t2, "related_tickers": ["NVIDIA", "NVDA", "MICRON", "MU"]}))
