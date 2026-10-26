import React, { useCallback, useEffect, useMemo, useState } from 'react'
import AisPageShell from '../components/AisPageShell'
import {
  addMaLabelSymbol,
  getMaLabelBoard,
  getMaLabelWebhookHint,
  removeMaLabelSymbol,
} from '../api/maLabelBoard'
import './MaLabelBoard.css'

const TF_COLUMNS = [
  { id: '30m', label: '30分钟' },
  { id: '60m', label: '1h' },
  { id: '120m', label: '2h' },
  { id: '4h', label: '4h' },
  { id: '1d', label: '日线' },
]

const trendTone = (stateCn) => {
  if (stateCn === '极强多头') return 'strong-bull'
  if (stateCn === '极强空头') return 'strong-bear'
  if (String(stateCn || '').includes('多')) return 'bull'
  if (String(stateCn || '').includes('空')) return 'bear'
  return 'neutral'
}

const Cell = ({ frame }) => {
  if (!frame || frame.error) {
    return <span className="mlb-cell-empty">—</span>
  }
  const state = frame.state_cn || '—'
  const pct = Math.abs(Number(frame.sug_pos) || 0)
  const tone = trendTone(state)
  return (
    <div className={`mlb-cell ${tone}`}>
      <strong>{state}</strong>
      <em>{pct}%</em>
    </div>
  )
}

const displayCode = (symbol) => {
  const s = String(symbol || '')
  return s.endsWith('USDT') ? s.slice(0, -4) : s
}

const MaLabelBoard = () => {
  const [data, setData] = useState(null)
  const [hint, setHint] = useState(null)
  const [error, setError] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [addValue, setAddValue] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setError('')
    try {
      const res = await getMaLabelBoard('')
      setData(res)
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '加载失败')
    }
  }, [])

  useEffect(() => {
    load()
    getMaLabelWebhookHint()
      .then(setHint)
      .catch(() => setHint(null))
  }, [load])

  useEffect(() => {
    const timer = setInterval(() => {
      load()
    }, 20000)
    return () => clearInterval(timer)
  }, [load])

  const rows = useMemo(() => {
    return (data?.items || []).map((item) => ({
      symbol: item.symbol,
      frames: item.frames || {},
    }))
  }, [data])

  const webhookUrl = useMemo(() => {
    const path = hint?.path || data?.webhook_path || '/api/ma-label-board/tv-webhook'
    const origin = typeof window !== 'undefined' ? window.location.origin : ''
    return `${origin}${path}`
  }, [hint, data])

  const onAdd = async () => {
    const raw = addValue.trim()
    if (!raw) return
    setBusy(true)
    setError('')
    try {
      await addMaLabelSymbol(raw)
      setAddValue('')
      setAddOpen(false)
      await load()
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '添加失败')
    } finally {
      setBusy(false)
    }
  }

  const onRemove = async (symbol) => {
    if (!window.confirm(`从看板移除 ${displayCode(symbol)}？`)) return
    setBusy(true)
    try {
      await removeMaLabelSymbol(symbol)
      await load()
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '移除失败')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AisPageShell title="标签看板" className="mlb-page">
      <div className="mlb-toolbar">
        <button type="button" className="mlb-btn" onClick={() => setAddOpen(true)} disabled={busy}>
          + 增加币种
        </button>
        <button type="button" className="mlb-btn mlb-btn-ghost" onClick={load} disabled={busy}>
          刷新
        </button>
      </div>

      <section className="mlb-webhook">
        <strong>TradingView Webhook · 标签看板</strong>
        <p className="mlb-webhook-url">POST {webhookUrl}</p>
        <pre className="mlb-webhook-pre">
          {JSON.stringify(
            hint?.example || {
              symbol: 'BTCUSDT',
              interval: '30m',
              state_cn: '极强多头',
              sug_pos: 100,
              score: 5,
            },
            null,
            2,
          )}
        </pre>
      </section>

      {error ? <p className="mlb-error">{error}</p> : null}
      <div className="mlb-table-wrap">
        <table className="mlb-table">
          <thead>
            <tr>
              <th>币种</th>
              {TF_COLUMNS.map((tf) => (
                <th key={tf.id}>{tf.label}</th>
              ))}
              <th className="mlb-actions-col">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={TF_COLUMNS.length + 2} className="mlb-empty-row">
                  暂无币种记录
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.symbol}>
                  <td className="mlb-symbol">
                    <strong>{displayCode(row.symbol)}</strong>
                    <span>{row.symbol}</span>
                  </td>
                  {TF_COLUMNS.map((tf) => (
                    <td key={tf.id}>
                      <Cell frame={row.frames[tf.id]} />
                    </td>
                  ))}
                  <td>
                    <button
                      type="button"
                      className="mlb-link-btn"
                      disabled={busy}
                      onClick={() => onRemove(row.symbol)}
                    >
                      移除
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {addOpen ? (
        <div className="mlb-modal-mask" role="dialog" aria-modal="true">
          <div className="mlb-modal">
            <h4>增加币种</h4>
            <input
              className="mlb-input"
              value={addValue}
              onChange={(e) => setAddValue(e.target.value)}
              placeholder="例如 BTC 或 BTCUSDT"
              onKeyDown={(e) => {
                if (e.key === 'Enter') onAdd()
              }}
              autoFocus
            />
            <div className="mlb-modal-actions">
              <button type="button" className="mlb-btn mlb-btn-ghost" onClick={() => setAddOpen(false)}>
                取消
              </button>
              <button type="button" className="mlb-btn" disabled={busy || !addValue.trim()} onClick={onAdd}>
                {busy ? '添加中…' : '确认添加'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </AisPageShell>
  )
}

export default MaLabelBoard
