# 小沫数字人助手 — 一期执行计划（2026-08-14）

## 目标（一期 MVP）✅

网页后台浮动助手「小沫」：点麦克风说话 → ASR → 后端编排 → 字幕 + 浏览器 TTS。  
半身 CSS 形象；支持打开页面；行情/策略/模块介绍不依赖云端也能答。

## 非目标（二期）

- 授权后热词「小沫」  
- 钉钉 Agent 深对接（已有 `agent_handoff` 占位）  
- 云端 TTS / 真 3D / 私有化 ASR  

## 已完成

| ID | 内容 | 状态 |
|----|------|------|
| T1 | 计划文档 | ✅ |
| T2 | `/api/avatar/chat` 菜单/模块/策略/行情/打开页/Agent预留/LLM | ✅ |
| T3 | 前端小沫：麦、TTS、半身、跳转、建议 chips | ✅ |
| T4 | 冒烟断言 | ✅（见下方命令） |

## 关键文件

- `backpack_quant_trading/core/avatar_agent.py`
- `backpack_quant_trading/api/routers/avatar.py`
- `backpack_quant_trading/frontend/src/components/ChatBot.jsx`
- `backpack_quant_trading/frontend/src/api/avatar.js`

## 验收

1. 「后台有哪些功能」→ menu  
2. 「介绍币种监视」→ feature_monitor  
3. 「打开泡沫检测」→ navigate `/us-weekly-report`  
4. 「讲讲 159570」→ strategy 数字  
5. 「ETH 多少钱」→ market（网络可用时）  
6. 麦克风：Chrome 授权后能识别并自动发送  
