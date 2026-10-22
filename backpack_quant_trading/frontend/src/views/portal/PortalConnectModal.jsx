import React, { useState } from 'react'
import { connectExchange } from '../../api/portal'

const PLATFORMS = [
  { id: 'hyperliquid', label: 'Hyperliquid', ready: true },
  { id: 'okx', label: '欧意 OKX', ready: true },
  { id: 'binance', label: '币安', ready: false },
]

/**
 * 交易所连接弹窗：本期 Hyperliquid 私钥 / OKX API Key。
 * symbols 可选，连接成功后把对应观察库标的标成 connected。
 */
const PortalConnectModal = ({ open, symbols = [], onClose, onDone }) => {
  const [platform, setPlatform] = useState('hyperliquid')
  const [label, setLabel] = useState('')
  const [privateKey, setPrivateKey] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [passphrase, setPassphrase] = useState('')
  const [demo, setDemo] = useState(false)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  if (!open) return null

  const meta = PLATFORMS.find((p) => p.id === platform) || PLATFORMS[0]
  const symHint = symbols.length
    ? symbols.map((s) => String(s).replace(/USDT$/, '')).join('、')
    : ''

  const onSubmit = async () => {
    if (!meta.ready) {
      setMsg('币安连接即将支持，请先选 Hyperliquid 或欧意')
      return
    }
    setBusy(true)
    setMsg('')
    try {
      const res = await connectExchange({
        platform,
        private_key: privateKey,
        api_key: apiKey,
        api_secret: apiSecret,
        passphrase,
        label,
        demo,
        symbols,
      })
      const tip = res?.platform_label || platform
      setMsg(`已连接 ${tip}`)
      onDone?.(res)
      setTimeout(() => onClose?.(), 500)
    } catch (e) {
      setMsg(e?.response?.data?.detail || e?.message || '连接失败')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="qt-modal-mask" role="dialog" aria-modal="true">
      <div className="qt-modal" style={{ maxWidth: 480 }}>
        <div className="qt-modal-head">
          <strong>
            立即连接
            {symHint ? (
              <span style={{ color: 'var(--qt-muted)', fontWeight: 500, marginLeft: 8 }}>{symHint}</span>
            ) : null}
          </strong>
          <button type="button" className="portal-btn portal-btn-ghost" onClick={onClose}>关闭</button>
        </div>

        <label className="qt-field">
          交易平台
          <select
            className="qt-select"
            value={platform}
            onChange={(e) => {
              setPlatform(e.target.value)
              setMsg('')
            }}
          >
            {PLATFORMS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}{p.ready ? '' : '（即将支持）'}
              </option>
            ))}
          </select>
        </label>

        {platform === 'hyperliquid' ? (
          <div className="qt-connect-panel">
            <strong>私钥配置</strong>
            <p className="qt-sub" style={{ margin: '6px 0 12px' }}>该平台使用链上钱包，请输入私钥</p>
            <label className="qt-field">
              钱包备注（可选）
              <input
                className="qt-input"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="例如：主钱包/测试钱包/服务器A"
              />
            </label>
            <label className="qt-field">
              Private Key
              <input
                className="qt-input"
                type="password"
                autoComplete="off"
                value={privateKey}
                onChange={(e) => setPrivateKey(e.target.value)}
                placeholder="输入 0x 开头的私钥"
              />
            </label>
          </div>
        ) : null}

        {platform === 'okx' ? (
          <div className="qt-connect-panel">
            <strong>API 配置</strong>
            <p className="qt-sub" style={{ margin: '6px 0 12px' }}>填写欧意 API Key / Secret / Passphrase，连接前会校验账户</p>
            <label className="qt-field">
              备注（可选）
              <input
                className="qt-input"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="例如：实盘主账户"
              />
            </label>
            <label className="qt-field">
              API Key
              <input
                className="qt-input"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="OKX API Key"
                autoComplete="off"
              />
            </label>
            <label className="qt-field">
              Secret Key
              <input
                className="qt-input"
                type="password"
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
                placeholder="OKX Secret"
                autoComplete="off"
              />
            </label>
            <label className="qt-field">
              Passphrase
              <input
                className="qt-input"
                type="password"
                value={passphrase}
                onChange={(e) => setPassphrase(e.target.value)}
                placeholder="创建 Key 时设置的口令"
                autoComplete="off"
              />
            </label>
            <label className="qt-check">
              <input type="checkbox" checked={demo} onChange={(e) => setDemo(e.target.checked)} />
              模拟盘（demo）
            </label>
          </div>
        ) : null}

        {platform === 'binance' ? (
          <p className="qt-sub">币安连接下一期开放，本次请先用 Hyperliquid 或欧意。</p>
        ) : null}

        {msg ? (
          <p className={msg.startsWith('已连接') ? 'qt-up' : 'qt-down'} style={{ marginTop: 10 }}>
            {msg}
          </p>
        ) : null}

        <div className="qt-modal-actions">
          <button type="button" className="portal-btn portal-btn-ghost" onClick={onClose}>取消</button>
          <button
            type="button"
            className="portal-btn portal-btn-primary"
            disabled={busy || !meta.ready}
            onClick={onSubmit}
          >
            {busy ? '连接中…' : '确认连接'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default PortalConnectModal
