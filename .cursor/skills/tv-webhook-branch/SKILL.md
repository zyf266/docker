---
name: tv-webhook-branch
description: >-
  Adds a TradingView alert ID → DingTalk webhook branch in tradingview_bot.py.
  Use when the user asks to add a strategy branch, TV webhook route, id_webhook_map
  entry, 山寨趋进-style ID routing, or new DingTalk group for TradingView signals.
---

# TV Webhook 策略分支（Harness SOP）

## 何时使用

用户给出类似：

```json
{ "id": "山寨趋进", "symbol": "{{ticker}}", "action": "{{strategy.order.action}}", "price": "..." }
```

以及钉钉 webhook URL 时，按本 SOP 落地，禁止只改一半。

## 步骤

1. **改配置** `tradingview_bot.py` → `CONFIG["id_webhook_map"]` 增加 `"<ID>": "<完整 webhook URL>"`
2. **解析兜底**：`_parse_json_alert` 在 `策略名称` 为空时用 `id` 作 `strategy` 展示名（已有则勿重复破坏）
3. **策略名兜底**（可选）：`send_to_dingtalk` 里当 id 未命中 map 时，用策略名关键字回退到同一 webhook
4. **本地验证**（必做，贴输出）：

```python
from tradingview_bot import TradingViewBot, CONFIG
bot = TradingViewBot(CONFIG)
p = bot.parse_tradingview_message({"id":"<ID>","symbol":"DOGEUSDT","action":"buy","price":"0.12"})
assert p["id"] == "<ID>"
assert "<ID>" in CONFIG["id_webhook_map"]
print("ok", p["strategy"], p["signal"])
```

5. **正式服**：用户明确要求后才 commit/push；提醒重启 `tradingview_bot`（`:5001`），**禁止** `docker cp` / hotfix 热更本文件到生产
6. **自测命令**（服务器上优先本机，避免 SSL）：

```bash
curl -sf http://127.0.0.1:5001/health
curl -X POST "http://127.0.0.1:5001/webhook" \
  -H "Content-Type: application/json" \
  -d '{"id":"<ID>","symbol":"DOGEUSDT","action":"buy","price":"0.12"}'
```

公网 HTTPS 自签证书用 `curl -k`。

## 完成定义

- map 命中正确 webhook
- 解析出 id / signal / strategy
- 贴出本地 assert 或 curl 成功 JSON（`status: success`）
- 钉钉群收到卡片（或说明尚未 Deploy/重启）

## 禁止

- 把 token 写进 docs / 面试题库
- 正式机 `scp tradingview_bot.py` 热更
