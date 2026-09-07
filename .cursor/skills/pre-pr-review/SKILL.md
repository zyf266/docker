---
name: pre-pr-review
description: >-
  Runs two-pass code review before claiming a PR is ready. Use when user asks
  for PR、开 PR、准备合并、code review、审查改动、/review after implementation.
---

# PR 前审查（Harness SOP）

## 强制顺序

1. 读 `~/.cursor/skills/code-review/SKILL.md`（若存在）并按两轮审查执行
2. **本轮禁止**「一边大改代码一边自评通过」
3. 对照 `verification-before-completion`：必须有测试/build 证据

## 本仓库检查点

- [ ] 无正式服热更脚本 / `docker cp` 说明写入文档当「正确路径」
- [ ] 前端改动：本地 `npm run build` 已通过
- [ ] A股 AI / T0：相关 pytest 已通过
- [ ] `tradingview_bot` 新 ID：map + 本地 parse 冒烟
- [ ] 无明文密钥提交（`.env`、长 access_token 勿进 docs）
- [ ] 实现与审查分离：审查结论单独一轮

## 输出

用简短 Markdown：

```markdown
## Review
### 需求符合性
- ...
### 质量/风险
- ...
### 合并建议
- 可以合并 / 需先修：...
```
