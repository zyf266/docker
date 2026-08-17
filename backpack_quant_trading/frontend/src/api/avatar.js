import request from './request'

export const getAvatarMeta = () => request.get('/avatar/meta')

export const sendAvatarChat = (data) =>
  request.post('/avatar/chat', data, { timeout: 90000 })

/** 云端 TTS → audio/mpeg Blob；失败由调用方回退浏览器 TTS */
export const fetchAvatarTts = (text, voice) =>
  request.post(
    '/avatar/tts',
    { text, voice },
    { responseType: 'blob', timeout: 60000 }
  )

/** D-ID 口型视频；未配置 Key 时 503 */
export const fetchAvatarTalk = (text, voice) =>
  request.post('/avatar/talk', { text, voice }, { timeout: 120000 })
