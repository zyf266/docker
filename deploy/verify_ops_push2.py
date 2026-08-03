import os
from backpack_quant_trading.core.stock_news_alert import send_dingtalk_markdown

wh = os.environ.get("AGENT_OPS_DINGTALK_WEBHOOK", "")
print("wh_ok", bool(wh))
print(send_dingtalk_markdown(
    wh,
    "提醒",
    "【提醒】Agent 日巡检/自动复盘 配置验证：后续将推送到本群",
))
