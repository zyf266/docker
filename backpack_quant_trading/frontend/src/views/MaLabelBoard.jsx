import React, { useCallback, useEffect, useState } from 'react'
import AisPageShell from '../components/AisPageShell'
import { getMaLabelBoard } from '../api/maLabelBoard'
import './MaLabelBoard.css'

const fmt = (n) => {
  const v = Number(n)
  if (!Number.isFinite(v)) return '—'
  const abs = Math.abs(v)
  const digits = abs >= 1000 ? 2 : abs >= 1 ? 3 : 5
  return v.toFixed(digits)
}

const tone = (above) => (above ? 'up-text' : 'down-text')

const FrameCard = ({ symbol, tfLabel, frame }) => {
  if (!frame || frame.error) {
    return (
      <section className="mlb-board">
        <p className="mlb-miss">{frame?.error || '这个周期还没有记录'}</p>
      </section>
    )
  }
  const bull = frame.sug_pos > 0
  const bear = frame.sug_pos < 0
  const toneName = bull ? 'up' : bear ? 'down' : ''
  const mas = [
    ['短均线 MA5', frame.ma5, frame.dev_short],
    ['中均线 MA30', frame.ma30, frame.dev_mid],
    ['长均线 MA200', frame.ma200, frame.dev_long],
  ]
  return (
    <section className={`mlb-board ${toneName}`}>
      <div className="mlb-hero">
        <div>
          <p className="mlb-kicker">{symbol} · {tfLabel}</p>
          <p className="mlb-price">{fmt(frame.price)}</p>
          <p className="mlb-time">{frame.captured_at || '—'}</p>
          {frame.unresolved_symbol || frame.unresolved_tf ? (
            <p className="mlb-time">品种或周期仍是 TradingView 占位符，暂按策略名归档。</p>
          ) : null}
        </div>
        <span className={`mlb-pill ${toneName}`}>{frame.state_cn}</span>
      </div>
      <div className="mlb-stats">
        <div>
          <span>强弱总分</span>
          <strong className={frame.total > 0 ? 'up-text' : frame.total < 0 ? 'down-text' : ''}>{frame.total} / 5</strong>
          <em>价格分 {frame.pos_score}</em>
        </div>
        <div>
          <span>当前趋势</span>
          <strong className={toneName ? `${toneName}-text` : ''}>{frame.state_cn}</strong>
          <em>趋势档</em>
        </div>
        <div>
          <span>参考仓位</span>
          <strong className={toneName ? `${toneName}-text` : ''}>{Math.abs(frame.sug_pos)}%</strong>
          <em>{frame.side_cn}</em>
        </div>
      </div>
      <div className="mlb-mas">
        {mas.map(([name, value, dev]) => (
          <div key={name} className="mlb-ma">
            <span>{name}</span>
            <strong>{fmt(value)}</strong>
            <em className={tone(dev?.above)}>{dev ? `${dev.pct}% ${dev.side}` : '—'}</em>
          </div>
        ))}
      </div>
    </section>
  )
}

const TF_OPTIONS = [
  { id: '30m', label: '30分钟' },
  { id: '60m', label: '60分钟' },
  { id: '120m', label: '120分钟' },
  { id: '1d', label: '日线' },
]

const MaLabelBoard = () => {
  const [data, setData] = useState(null)
  const [symbol, setSymbol] = useState('')
  const [timeframe, setTimeframe] = useState('30m')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await getMaLabelBoard('')
      const items = res?.items || []
      setData(res)
      setSymbol((current) => current || items[0]?.symbol || '')
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const symbols = (data?.items || []).map((item) => item.symbol)
  const current = (data?.items || []).find((item) => item.symbol === symbol)
  const tfLabel = TF_OPTIONS.find((item) => item.id === timeframe)?.label || timeframe
  const frame = current?.frames?.[timeframe]

  return (
    <AisPageShell title="标签看板" className="mlb-page">
      <div className="mlb-toolbar">
        <label>
          币种
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {symbols.length === 0 ? <option value="">暂无币种</option> : null}
            {symbols.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          K线级别
          <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
            {TF_OPTIONS.map((item) => (
              <option key={item.id} value={item.id}>{item.label}</option>
            ))}
          </select>
        </label>
        <button className="mlb-btn" type="button" onClick={load} disabled={loading}>
          {loading ? '刷新中…' : '刷新'}
        </button>
      </div>
      {error ? <p className="mlb-error">{error}</p> : null}
      <FrameCard symbol={symbol || '—'} tfLabel={tfLabel} frame={frame} />
    </AisPageShell>
  )
}

export default MaLabelBoard
