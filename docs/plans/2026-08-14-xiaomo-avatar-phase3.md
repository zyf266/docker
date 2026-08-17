# 小沫数字人 — 三期计划（2026-08-14）

## 已确认

| 项 | 决定 |
|----|------|
| 范围 | **A 云端 TTS + B 半身 3D** 必做；**C Porcupine** 仅在有有效 AccessKey + 自定义「小沫」模型时启用，否则回退二期 Web Speech |
| TTS | 免费：`edge-tts`（微软神经女声 `zh-CN-XiaoxiaoNeural`），失败回退浏览器 TTS |
| 3D | 免费 CDN GLB（Three.js 示例半身/可表情模型），音量驱动口型 |
| 验收 | 本地 Chrome：能听到云端女声 + 半身模型随播报动嘴 |

## 关于 Picovoice / Porcupine（回答「要钱吗」）

- **2026-06-30 起**：Picovoice **已取消长期 Free Tier**，旧免费 AccessKey 会失效；现以 **企业试用 / 商务合同** 为主。
- 个人验证：可注册看是否还有 **Free Trial**，但试用到期后要企业方案；**中文「小沫」还需 Console 训练自定义 `.ppn`**，内置词表没有「小沫」。
- **结论**：三期不把 Porcupine 当硬依赖；默认继续用二期「听小沫」Web Speech；若你日后提供 `PICOVOICE_ACCESS_KEY` + `xiaomo.ppn`，再打开 Porcupine 路径。

## 非目标（四期）

- 私有化 ASR（Whisper 等）
- 真写实定制建模 / 商业数字人 SaaS
- 付费云 TTS（Azure 正式版、火山等）

## 任务

### T1：计划（本文件）
- **完成标准**: 范围与 C 降级写清

### T2：后端 `/api/avatar/tts`
- **文件**: `core/avatar_tts.py`, `api/routers/avatar.py`, `requirements.txt`
- **改动**: `edge-tts` 合成 MP3；无依赖或失败返回明确错误；`meta.tts` 更新
- **验证**: `python -c` 调合成或 curl `/api/avatar/tts`
- **完成标准**: 返回 `audio/mpeg` 且时长 > 0

### T3：前端播云端 TTS
- **文件**: `frontend/src/api/avatar.js`, `ChatBot.jsx`
- **改动**: `speakText` 优先拉 TTS blob → `Audio` 播放；失败回退 `speechSynthesis`
- **完成标准**: 对话回复用女声播放（网络可用时）

### T4：半身 3D + 口型
- **文件**: `XiaomoAvatar3D.jsx`, `ChatBot.jsx/css`, `package.json`（`three`）
- **改动**: 默认**程序化女半身**（不依赖外网机器人 GLB）；可选 `VITE_XIAOMO_MODEL_URL`；音量张嘴
- **完成标准**: 播报时模型 visibly 动；形象为女半身而非机器人

### T5：Porcupine 可选（软）
- **文件**: 计划说明 + `meta.wake_engine`；无 Key 不装必选依赖
- **改动**: 文档与 meta 标明 `web_speech | porcupine_optional`
- **完成标准**: 无 Key 时行为与二期一致

### T6：冒烟
- **验证**: TTS 合成脚本 + meta 字段；前端需本机 Chrome 听感验收

## 执行顺序
- [x] T1
- [x] T2
- [x] T3
- [x] T4
- [x] T5（meta + 文档；无 Key 保持 web_speech）
- [x] T6（后端 TTS 冒烟已过；Chrome 听感/3D 需本机点一次）

## 风险与回滚
- `edge-tts` 依赖外网；挂了自动回退浏览器 TTS
- GLB CDN 不可达时回退 CSS 半身
- Porcupine 无免费长期方案 → 不强绑

## 建议下一 skill
- 本计划确认后按 T2→T6 执行（用户已确认验收标准，直接开工）
