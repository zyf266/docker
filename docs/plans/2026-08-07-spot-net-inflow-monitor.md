# 现货 24h 资金净流入监控（币种监视）

## 背景

在币种监视页增加现货「24小时资金净流入」监控：手动启动币种后每 5 分钟计算；旁侧曲线图；满足 3 条规则则钉钉推送到币种监视同群。

## 口径

- 现货 5m K 线：`net = 2 * takerBuyQuoteVolume - quoteVolume`
- 滚动 24h 净流入 = 最近 288 根 5m 的 net 之和
- 自然日 = 北京时间；日净流入 = 当日所有 5m net 之和
- 告警满足即推（不去重）

## 任务

### T1：K 线字段 + 全量现货交易对

- **文件**: `core/binance_monitor.py`
- **改动**: `fetch_binance_klines` 增加 `quote_volume` / `taker_buy_quote_volume`；新增 `fetch_binance_spot_symbols_all`
- **验证**: `python -c` 拉 ETHUSDT 5m 含新字段
- **完成标准**: 字段非空；全量现货列表长度 > USDT-only

### T2：净流入计算与告警服务

- **文件**: `core/spot_net_inflow_monitor.py`（新）
- **改动**: 服务类：启停、5 分钟循环、算 24h/日序列、三条件、`send_dingtalk_alert`、图表序列
- **验证**: 单元式调用 `evaluate_alerts` 用假数据
- **完成标准**: 三条件逻辑可单测；钉钉走币种监视 webhook

### T3：DB 持久化 + API

- **文件**: `database/models.py`, `api/routers/currency_monitor.py`, 启动恢复钩子
- **改动**: `spot_net_inflow` singleton 配置；`/spot-net-inflow/{start,stop,status,series}`；API 启动恢复
- **验证**: OpenAPI 有路由；start→status.running
- **完成标准**: 重启后可从 DB 恢复

### T4：前端币种监视页

- **文件**: `frontend/src/api/currencyMonitor.js`, `views/CurrencyMonitor.jsx/.css`
- **改动**: 选币启停；旁侧面积图（24h 累计或分时净流入曲线）
- **验证**: 页面可选全部现货、启动后有图数据接口
- **完成标准**: 与现有监视区风格一致

## 执行顺序

- [x] T1
- [x] T2
- [x] T3
- [x] T4

## 风险

- 全量现货下拉列表很大，需搜索/多选组件已有则复用
- 多币种并发拉 K 线注意限频（仅手动启动集合）

## 建议下一 skill

`executing-plans` / 直接实现（用户已确认开始执行）
