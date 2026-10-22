# 普通用户产品站 — 执行计划（2026-10-19）

## 目标

- 页面注册 → 角色 `user`，登录进深色产品站（首页/策略/跟踪库/介绍/FAQ/联系）
- 已有账号视为管理端（`superuser`）；管理账号仅云端 CLI 创建
- 改现有登录：未登录访问产品站 → `/login`；按角色分流
- 一期：六页 UI + 接口壳；自选、搜索结果页、站内信、邮件口子、咨询落库、净值对比占位、分析全屏空壳

## 非目标

- 真实 SMTP 发信、钉钉推送、咨询管理后台、真实行情/净值数据

## 任务

1. 计划本文档
2. 注册恒为 `user`；CLI 创建 `superuser`；`require_admin` 保护管理 API（可选前端门禁）
3. Portal Layout + 六页 + 搜索/站内信/全屏
4. API：favorites / search / inbox / email stub / contact / equity mock
5. App 路由分流 + SPA 刷新路径
6. 冒烟 + `npm run build`

## 验收

- 新注册用户登录 → `/portal`
- superuser 登录 → 原后台
- 未登录打开 `/portal` → 登录页
- 自选增删、搜索跳结果页、咨询落库、站内信列表可读、邮件接口返回 stub
