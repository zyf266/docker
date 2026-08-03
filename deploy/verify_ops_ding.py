from backpack_quant_trading.agents.dingtalk_push import resolve_ops_dingtalk_webhook, push_dingtalk_markdown
from backpack_quant_trading.core.stock_news_alert import matches_watch

wh = resolve_ops_dingtalk_webhook()
print("ops_tail", (wh or "")[-12:])
item = {
    "related_tickers": ["INTC"],
    "text": "Why Goldman is cautious on outperforming Intel stock (NVDA)",
}
print("nvda_false", matches_watch(item["text"], ["NVDA"], item))
print("intc_true", matches_watch(item["text"], ["INTC"], item))
ok, msg = push_dingtalk_markdown(
    "Agent 日巡检",
    "## 提醒 · Agent 日巡检\n\n配置验证：复盘/巡检已切到本群",
    use_ops_webhook=True,
)
print("push", ok, msg)
