import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchAvatarTalk, fetchAvatarTts, sendAvatarChat } from '../api/avatar'
import './ChatBot.css'

const suggestQuestions = [
  '介绍一下后台有哪些功能',
  '介绍币种监视',
  '打开泡沫检测',
  '@美股分析师 NVDA',
  '讲讲 159570 策略表现',
]

const WAKE_RE = /小沫|小默|小魔/

const formatContent = (text) => {
  if (!text) return ''
  return text
    .replace(/\n/g, '<br/>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
}

const micErrorHint = (code) => {
  const map = {
    'not-allowed': '麦克风权限被拒绝。请在浏览器地址栏允许麦克风后重试。',
    'service-not-allowed': '当前页面不允许语音识别（需 HTTPS 或 localhost）。',
    'no-speech': '没听清，请靠近麦克风再说一次，或改用打字。',
    aborted: '已取消听写。',
    network: '浏览器语音服务网络异常。可用 Chrome 并检查网络，或改用打字。',
    'audio-capture': '找不到麦克风设备。',
    'language-not-supported': '当前浏览器不支持中文听写，请换 Chrome。',
  }
  return map[code] || `语音识别失败（${code || 'unknown'}）。请用 Chrome，或直接打字。`
}

const ChatBot = () => {
  const navigate = useNavigate()
  const [panelOpen, setPanelOpen] = useState(false)
  const [inputText, setInputText] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [listening, setListening] = useState(false)
  const [wakeEnabled, setWakeEnabled] = useState(() => localStorage.getItem('xiaomo_wake') === '1')
  const [wakeArmed, setWakeArmed] = useState(false)
  const [interim, setInterim] = useState('')
  const [speaking, setSpeaking] = useState(false)
  const [micHint, setMicHint] = useState('')
  const [chips, setChips] = useState(suggestQuestions)
  const [pos, setPos] = useState({ left: null, top: null })
  const [dragging, setDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0, left: 0, top: 0 })
  const [didDrag, setDidDrag] = useState(false)

  const [didVideoUrl, setDidVideoUrl] = useState(null)
  const [didEnabled, setDidEnabled] = useState(false)

  const messagesRef = useRef(null)
  const wrapperRef = useRef(null)
  const recogRef = useRef(null)
  const wakeRecogRef = useRef(null)
  const messagesStateRef = useRef([])
  const lastNavigateRef = useRef(null)
  const wakeEnabledRef = useRef(wakeEnabled)
  const commandBusyRef = useRef(false)
  const sendRef = useRef(null)
  const speakRef = useRef(null)
  const restartWakeTimer = useRef(null)
  const audioObjUrlRef = useRef(null)
  const audioElRef = useRef(null)

  useEffect(() => {
    messagesStateRef.current = messages
  }, [messages])

  useEffect(() => {
    wakeEnabledRef.current = wakeEnabled
    localStorage.setItem('xiaomo_wake', wakeEnabled ? '1' : '0')
  }, [wakeEnabled])

  const wrapperStyle = useMemo(() => {
    if (pos.left != null && pos.top != null) {
      return { left: `${pos.left}px`, top: `${pos.top}px`, right: 'auto', bottom: 'auto' }
    }
    return { right: '28px', bottom: '28px' }
  }, [pos.left, pos.top])

  const panelOnLeft = useMemo(() => {
    if (pos.left == null) return false
    return pos.left < window.innerWidth / 2
  }, [pos.left])

  const ensurePosition = useCallback(() => {
    if (pos.left != null) return true
    if (!wrapperRef.current) return false
    const rect = wrapperRef.current.getBoundingClientRect()
    setPos({ left: rect.left, top: rect.top })
    return true
  }, [pos.left])

  const scrollToBottom = useCallback(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight
    }
  }, [])

  useEffect(() => {
    if (panelOpen) scrollToBottom()
  }, [panelOpen, messages, interim, scrollToBottom])

  const speakBrowser = useCallback((plain) => {
    try {
      if (!window.speechSynthesis) return
      window.speechSynthesis.cancel()
      const u = new SpeechSynthesisUtterance(plain)
      u.lang = 'zh-CN'
      u.rate = 1.02
      u.pitch = 1.12
      const pickFemale = () => {
        const voices = window.speechSynthesis.getVoices() || []
        const zh = voices.filter((v) => /^zh/i.test(v.lang) || /chinese|中文/i.test(v.name))
        const prefer =
          zh.find((v) => /xiaoyi|xiaoxiao|huihui|yaoyao|female|女|tingting|meijia/i.test(v.name)) ||
          zh.find((v) => /google.*中文|microsoft.*xia|zh-cn/i.test(`${v.name} ${v.lang}`)) ||
          zh[0]
        if (prefer) u.voice = prefer
      }
      pickFemale()
      // Chrome 常异步加载 voices
      if (!u.voice) {
        window.speechSynthesis.onvoiceschanged = () => {
          pickFemale()
        }
      }
      u.onstart = () => setSpeaking(true)
      u.onend = () => setSpeaking(false)
      u.onerror = () => setSpeaking(false)
      window.speechSynthesis.speak(u)
    } catch {
      setSpeaking(false)
    }
  }, [])

  const stopCloudAudio = useCallback(() => {
    try {
      audioElRef.current?.pause?.()
    } catch {
      /* ignore */
    }
    if (audioObjUrlRef.current) {
      URL.revokeObjectURL(audioObjUrlRef.current)
      audioObjUrlRef.current = null
    }
    audioElRef.current = null
  }, [])

  const speakWithTts = useCallback(
    async (plain) => {
      try {
        const blob = await fetchAvatarTts(plain)
        if (!(blob instanceof Blob) || blob.size < 64) {
          throw new Error('bad tts blob')
        }
        if (blob.type && /json|text/i.test(blob.type)) {
          const errText = await blob.text()
          throw new Error(errText || 'tts json error')
        }
        const url = URL.createObjectURL(blob)
        audioObjUrlRef.current = url
        const audio = new Audio(url)
        audioElRef.current = audio
        audio.onplay = () => {
          setSpeaking(true)
          setMicHint('小沫女声播报中')
        }
        audio.onended = () => {
          setSpeaking(false)
          setMicHint('')
          stopCloudAudio()
        }
        audio.onerror = () => {
          setSpeaking(false)
          stopCloudAudio()
          setMicHint('云端女声播放失败，已改用浏览器女声')
          speakBrowser(plain)
        }
        await audio.play()
      } catch (e) {
        console.warn('[xiaomo] cloud tts fallback', e)
        setMicHint('云端女声暂不可用，已用浏览器女声（请确认 API 已重启且装了 edge-tts）')
        speakBrowser(plain)
      }
    },
    [speakBrowser, stopCloudAudio]
  )

  const speakText = useCallback(
    async (text) => {
      const plain = String(text || '')
        .replace(/[#>*_`]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
        .slice(0, 500)
      if (!plain) return
      try {
        window.speechSynthesis?.cancel?.()
      } catch {
        /* ignore */
      }
      stopCloudAudio()
      setDidVideoUrl(null)

      // 短句 + 已配置 D-ID：尝试口型视频（可能较慢）；失败立刻回退 TTS
      const tryDid = didEnabled && plain.length <= 120
      if (tryDid) {
        setMicHint('正在生成口型视频…（首次可能较慢）')
        try {
          const res = await fetchAvatarTalk(plain)
          const videoUrl = res?.video_url
          if (videoUrl) {
            setDidVideoUrl(videoUrl)
            setSpeaking(true)
            setMicHint('小沫口型播报中')
            return
          }
        } catch (e) {
          console.warn('[xiaomo] did talk fallback', e)
        }
      }
      await speakWithTts(plain)
    },
    [didEnabled, speakWithTts, stopCloudAudio]
  )

  useEffect(() => {
    speakRef.current = speakText
  }, [speakText])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const { getAvatarMeta } = await import('../api/avatar')
        const meta = await getAvatarMeta()
        if (!cancelled && meta?.did_enabled) setDidEnabled(true)
      } catch {
        /* ignore */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!didVideoUrl) return undefined
    const v = document.getElementById('xiaomo-did-video')
    if (!v) return undefined
    v.onended = () => {
      setSpeaking(false)
      setDidVideoUrl(null)
      setMicHint('')
    }
    v.onerror = () => {
      setSpeaking(false)
      setDidVideoUrl(null)
      setMicHint('口型视频播放失败，已回退女声')
    }
    void v.play().catch(() => {
      setSpeaking(false)
      setDidVideoUrl(null)
    })
    return undefined
  }, [didVideoUrl])

  const stopWakeLoop = useCallback(() => {
    if (restartWakeTimer.current) {
      clearTimeout(restartWakeTimer.current)
      restartWakeTimer.current = null
    }
    try {
      wakeRecogRef.current?.abort?.()
    } catch {
      /* ignore */
    }
    wakeRecogRef.current = null
    setWakeArmed(false)
  }, [])

  const onWakeHeard = useCallback((utterance) => {
    const raw = String(utterance || '').trim()
    setPanelOpen(true)
    // 「小沫，介绍币种监视」→ 整句交给后端清洗
    const onlyWake = /^\s*(小沫|小默|小魔)([,，.。!！？?\s]*(你在吗)?)?\s*$/i.test(raw)
    if (onlyWake) {
      const hello = '我在，请说。'
      setMessages((prev) => {
        const next = prev.length ? prev : [{ role: 'assistant', content: hello }]
        if (prev.length) {
          const n2 = [...prev, { role: 'assistant', content: hello }]
          messagesStateRef.current = n2
          return n2
        }
        messagesStateRef.current = next
        return next
      })
      speakRef.current?.(hello)
      setMicHint('已唤醒，可点麦克风继续说指令')
      return
    }
    void sendRef.current?.(raw)
  }, [])

  const startWakeLoop = useCallback(async () => {
    if (!wakeEnabledRef.current) return
    if (commandBusyRef.current) return
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) {
      setMicHint('当前浏览器不支持唤醒听写，请用 Chrome')
      return
    }
    try {
      if (navigator.mediaDevices?.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        stream.getTracks().forEach((t) => t.stop())
      }
    } catch {
      setWakeEnabled(false)
      setMicHint(micErrorHint('not-allowed'))
      return
    }

    stopWakeLoop()
    const recog = new SR()
    wakeRecogRef.current = recog
    recog.lang = 'zh-CN'
    recog.continuous = true
    recog.interimResults = true
    recog.maxAlternatives = 1

    let fired = false
    recog.onstart = () => setWakeArmed(true)
    recog.onerror = (ev) => {
      const code = ev?.error
      if (code === 'aborted' || code === 'no-speech') return
      setWakeArmed(false)
      if (code === 'not-allowed') {
        setWakeEnabled(false)
        setMicHint(micErrorHint(code))
      }
    }
    recog.onresult = (ev) => {
      if (fired || commandBusyRef.current) return
      let buf = ''
      for (let i = ev.resultIndex; i < ev.results.length; i += 1) {
        buf += ev.results[i][0]?.transcript || ''
        if (ev.results[i].isFinal && WAKE_RE.test(buf)) {
          fired = true
          try {
            recog.stop()
          } catch {
            /* ignore */
          }
          onWakeHeard(buf)
          return
        }
      }
      if (WAKE_RE.test(buf) && buf.replace(WAKE_RE, '').replace(/[,，.。!！？?\s你在吗]/g, '').length >= 2) {
        // 热词后已跟指令（interim）
        fired = true
        try {
          recog.stop()
        } catch {
          /* ignore */
        }
        onWakeHeard(buf)
      }
    }
    recog.onend = () => {
      setWakeArmed(false)
      wakeRecogRef.current = null
      if (!wakeEnabledRef.current || commandBusyRef.current) return
      restartWakeTimer.current = setTimeout(() => {
        if (wakeEnabledRef.current && !commandBusyRef.current) void startWakeLoop()
      }, 600)
    }
    try {
      recog.start()
      setMicHint('已开启：说「小沫」唤醒')
    } catch {
      setWakeArmed(false)
      restartWakeTimer.current = setTimeout(() => {
        if (wakeEnabledRef.current) void startWakeLoop()
      }, 1200)
    }
  }, [onWakeHeard, stopWakeLoop])

  useEffect(() => {
    if (wakeEnabled) {
      void startWakeLoop()
    } else {
      stopWakeLoop()
      setMicHint('')
    }
    return () => stopWakeLoop()
  }, [wakeEnabled, startWakeLoop, stopWakeLoop])

  useEffect(() => {
    return () => {
      try {
        recogRef.current?.abort?.()
      } catch {
        /* ignore */
      }
      stopWakeLoop()
      try {
        window.speechSynthesis?.cancel?.()
      } catch {
        /* ignore */
      }
    }
  }, [stopWakeLoop])

  const handleMouseMove = useCallback(
    (e) => {
      if (!dragging) return
      const dx = e.clientX - dragStart.x
      const dy = e.clientY - dragStart.y
      if (Math.abs(dx) > 4 || Math.abs(dy) > 4) setDidDrag(true)
      const sz = 88
      let left = dragStart.left + dx
      let top = dragStart.top + dy
      left = Math.max(0, Math.min(window.innerWidth - sz, left))
      top = Math.max(0, Math.min(window.innerHeight - sz, top))
      setPos({ left, top })
    },
    [dragStart.left, dragStart.top, dragStart.x, dragStart.y, dragging]
  )

  const handleMouseUp = useCallback(() => {
    setDragging(false)
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
  }, [handleMouseMove])

  const onAvatarMouseDown = (e) => {
    if (e.button !== 0) return
    if (!ensurePosition()) return
    setDragging(true)
    setDidDrag(false)
    setDragStart({
      x: e.clientX,
      y: e.clientY,
      left: pos.left ?? 0,
      top: pos.top ?? 0,
    })
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }

  const onAvatarClick = () => {
    if (didDrag) return
    setPanelOpen((v) => {
      const next = !v
      if (next && messagesStateRef.current.length === 0) {
        const hello =
          '你好，我是小沫。可开「听小沫」唤醒；或点麦克风；也可打字。试试「@美股分析师 NVDA」。'
        setMessages([{ role: 'assistant', content: hello }])
        speakText(hello)
      }
      return next
    })
  }

  const applyNavigate = (path) => {
    if (!path || typeof path !== 'string' || !path.startsWith('/')) return
    try {
      navigate(path)
    } catch {
      /* ignore */
    }
  }

  const send = async (overrideText) => {
    const text = (overrideText ?? inputText)?.trim()
    if (!text || loading) return

    let q = text
    if (text === '打开该页面' || text === '打开该策略页') {
      if (lastNavigateRef.current) {
        applyNavigate(lastNavigateRef.current)
        const tip = '好的，已打开页面。'
        setMessages((prev) => {
          const next = [...prev, { role: 'user', content: text }, { role: 'assistant', content: tip }]
          messagesStateRef.current = next
          return next
        })
        speakText(tip)
        setInputText('')
        return
      }
      const lastChip = (chips || []).find((c) => String(c).startsWith('打开'))
      if (lastChip) q = lastChip
    }

    commandBusyRef.current = true
    stopWakeLoop()

    const userMsg = { role: 'user', content: q }
    const base = messagesStateRef.current
    const newMessages = [...base, userMsg]
    setMessages(newMessages)
    messagesStateRef.current = newMessages
    setInputText('')
    setInterim('')
    setMicHint('')
    setLoading(true)
    setPanelOpen(true)

    try {
      const history = newMessages.map((m) => ({ role: m.role, content: m.content }))
      const res = await sendAvatarChat({ message: q, history })
      const reply = res.reply || '暂无回复'
      setMessages((prev) => {
        const next = [...prev, { role: 'assistant', content: reply }]
        messagesStateRef.current = next
        return next
      })
      if (Array.isArray(res.suggestions) && res.suggestions.length) {
        setChips(res.suggestions)
      }
      if (res.navigate) {
        lastNavigateRef.current = res.navigate
        if (res.intent === 'navigate' || /打开|进入|跳转|带我/.test(q)) {
          applyNavigate(res.navigate)
        } else {
          setChips((prev) => {
            const extra = ['打开该页面', ...(res.suggestions || prev || [])]
            return [...new Set(extra)].slice(0, 6)
          })
        }
      }
      if (res.speak !== false) speakText(res.speak_text || reply)
    } catch (e) {
      const errMsg =
        e?.response?.data?.detail || e?.response?.data?.reply || e?.message || '请求失败，请稍后重试。'
      const content = typeof errMsg === 'string' ? errMsg : '请求失败，请稍后重试。'
      setMessages((prev) => {
        const next = [...prev, { role: 'assistant', content }]
        messagesStateRef.current = next
        return next
      })
    } finally {
      setLoading(false)
      commandBusyRef.current = false
      scrollToBottom()
      if (wakeEnabledRef.current) {
        restartWakeTimer.current = setTimeout(() => void startWakeLoop(), 800)
      }
    }
  }

  sendRef.current = send

  const askQuestion = (q) => {
    void send(q)
  }

  const ensureMicPermission = async () => {
    if (!navigator.mediaDevices?.getUserMedia) return true
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream.getTracks().forEach((t) => t.stop())
      return true
    } catch {
      const tip = micErrorHint('not-allowed')
      setMicHint(tip)
      setMessages((prev) => [...prev, { role: 'assistant', content: tip }])
      return false
    }
  }

  const startMic = async () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) {
      const tip = '当前浏览器不支持语音识别，请用最新版 Chrome，或直接打字。'
      setMicHint(tip)
      setMessages((prev) => [...prev, { role: 'assistant', content: tip }])
      return
    }
    if (listening) {
      try {
        recogRef.current?.stop?.()
      } catch {
        /* ignore */
      }
      setListening(false)
      return
    }
    const ok = await ensureMicPermission()
    if (!ok) return

    commandBusyRef.current = true
    stopWakeLoop()
    try {
      window.speechSynthesis?.cancel?.()
    } catch {
      /* ignore */
    }
    setSpeaking(false)

    const recog = new SR()
    recogRef.current = recog
    recog.lang = 'zh-CN'
    recog.continuous = false
    recog.interimResults = true
    recog.maxAlternatives = 3

    let finalText = ''
    recog.onstart = () => {
      setListening(true)
      setMicHint('正在听指令…')
      setInterim('')
    }
    recog.onerror = (ev) => {
      const code = ev?.error || 'unknown'
      setListening(false)
      setInterim('')
      if (code === 'aborted') return
      const tip = micErrorHint(code)
      setMicHint(tip)
      if (code !== 'no-speech') {
        setMessages((prev) => [...prev, { role: 'assistant', content: tip }])
      }
    }
    recog.onresult = (ev) => {
      let interimBuf = ''
      for (let i = ev.resultIndex; i < ev.results.length; i += 1) {
        const piece = ev.results[i][0]?.transcript || ''
        if (ev.results[i].isFinal) finalText += piece
        else interimBuf += piece
      }
      setInterim(interimBuf || finalText)
      if (finalText.trim()) setInputText(finalText.trim())
    }
    recog.onend = () => {
      setListening(false)
      const said = (finalText || '').trim()
      setInterim('')
      commandBusyRef.current = false
      if (said) {
        setMicHint(`识别到：${said}`)
        void send(said)
      } else {
        setMicHint('没有识别到有效语句')
        if (wakeEnabledRef.current) void startWakeLoop()
      }
    }
    try {
      recog.start()
    } catch {
      setListening(false)
      commandBusyRef.current = false
      setMicHint('无法启动听写')
      if (wakeEnabledRef.current) void startWakeLoop()
    }
  }

  const toggleWake = async () => {
    if (wakeEnabled) {
      setWakeEnabled(false)
      stopWakeLoop()
      setMicHint('已关闭热词唤醒')
      return
    }
    const ok = await ensureMicPermission()
    if (!ok) return
    setWakeEnabled(true)
    setPanelOpen(true)
    setMicHint('已开启：请说「小沫」')
    speakText('已开启小沫唤醒，请叫我小沫。')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void send()
    }
  }

  return (
    <div className="chatbot-wrapper" style={wrapperStyle} ref={wrapperRef}>
      <div
        className={`chatbot-avatar xiaomo${panelOpen ? ' open' : ''}${dragging ? ' dragging' : ''}${speaking ? ' talking' : ''}${listening || wakeArmed ? ' listening' : ''}`}
        onMouseDown={onAvatarMouseDown}
        onClick={onAvatarClick}
        title="小沫 · 拖拽移动 · 点击打开"
      >
        <div className="avatar-visual">
          {didVideoUrl ? (
            <video
              id="xiaomo-did-video"
              className="avatar-portrait-video"
              src={didVideoUrl}
              autoPlay
              playsInline
              muted={false}
            />
          ) : (
            <>
              <img
                className={`avatar-portrait${speaking || listening ? ' talking' : ''}`}
                src="/xiaomo-avatar.png"
                alt="小沫"
                draggable={false}
                onError={(e) => {
                  e.currentTarget.style.display = 'none'
                  const fallback = e.currentTarget.parentElement?.querySelector('.avatar-fallback')
                  if (fallback) fallback.style.display = 'flex'
                }}
              />
              <div className="avatar-fallback" style={{ display: 'none' }} aria-hidden>
                沫
              </div>
            </>
          )}
        </div>
        {!panelOpen && <span className="avatar-pulse" />}
        <span className="avatar-badge">{wakeArmed ? '听…' : '小沫'}</span>
      </div>

      {panelOpen && (
        <div className={`chatbot-panel${panelOnLeft ? ' panel-left' : ''}`}>
          <div className="panel-header">
            <span className="panel-title">小沫</span>
            <span className="panel-desc">{didEnabled ? '口型可选 · 女声' : '科幻形象 · 女声'}</span>
            <button
              type="button"
              className={`wake-toggle${wakeEnabled ? ' on' : ''}`}
              onClick={() => void toggleWake()}
              title="授权后说「小沫」唤醒"
            >
              {wakeEnabled ? (wakeArmed ? '听小沫中' : '唤醒已开') : '听小沫'}
            </button>
            <button className="panel-close" onClick={() => setPanelOpen(false)} aria-label="关闭" type="button">
              ×
            </button>
          </div>

          <div className="panel-body">
            <div className="messages-area" ref={messagesRef}>
              {messages.length === 0 && (
                <div className="welcome-area">
                  <p className="welcome-text">你好，我是小沫。开启「听小沫」后可喊我名字。</p>
                </div>
              )}
              {messages.map((m, i) => (
                <div key={i} className={`msg-row ${m.role === 'user' ? 'user' : 'assistant'}`}>
                  {m.role === 'assistant' && <div className="msg-avatar xiaomo-mini">沫</div>}
                  <div className="msg-bubble">
                    <div className="msg-content" dangerouslySetInnerHTML={{ __html: formatContent(m.content) }} />
                  </div>
                  {m.role === 'user' && <div className="msg-avatar user-avatar">我</div>}
                </div>
              ))}
              {listening && interim && (
                <div className="msg-row user">
                  <div className="msg-bubble interim">
                    <div className="msg-content">{interim}</div>
                  </div>
                  <div className="msg-avatar user-avatar">…</div>
                </div>
              )}
              {loading && (
                <div className="msg-row assistant">
                  <div className="msg-avatar xiaomo-mini">沫</div>
                  <div className="msg-bubble typing">
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                  </div>
                </div>
              )}
            </div>
            <div className="guess-list chips">
              {(chips || suggestQuestions).slice(0, 6).map((q, i) => (
                <button key={`${q}-${i}`} className="guess-item" type="button" onClick={() => askQuestion(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>

          {(micHint || listening || wakeArmed) && (
            <div className={`mic-status${listening || wakeArmed ? ' on' : ''}`}>
              {micHint || (wakeArmed ? '正在听「小沫」…' : '聆听中…')}
            </div>
          )}

          <div className="panel-footer xiaomo-footer">
            <button
              type="button"
              className={`mic-btn${listening ? ' on' : ''}`}
              onClick={() => void startMic()}
              disabled={loading}
              title="点击说指令"
            >
              {listening ? '停止' : '麦克风'}
            </button>
            <textarea
              className="chat-input-textarea"
              rows={1}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="说话或输入…"
            />
            <button
              className="el-button el-button--primary send-btn"
              type="button"
              disabled={loading}
              onClick={() => send()}
            >
              {loading ? '…' : '发送'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default ChatBot
