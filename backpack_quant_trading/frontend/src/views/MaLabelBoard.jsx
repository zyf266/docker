import React, { useCallback, useEffect, useMemo, useState } from 'react'
import AisPageShell from '../components/AisPageShell'
import { getMaLabelBoard } from '../api/maLabelBoard'
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
  const [error, setError] = useState('')

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
  }, [load])

  const rows = useMemo(() => {
    return (data?.items || []).map((item) => ({
      symbol: item.symbol,
      frames: item.frames || {},
    }))
  }, [data])

  return (
    <AisPageShell title="标签看板" className="mlb-page">
      {error ? <p className="mlb-error">{error}</p> : null}
      <div className="mlb-table-wrap">
        <table className="mlb-table">
          <thead>
            <tr>
              <th>币种</th>
              {TF_COLUMNS.map((tf) => (
                <th key={tf.id}>{tf.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={TF_COLUMNS.length + 1} className="mlb-empty-row">
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
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </AisPageShell>
  )
}

export default MaLabelBoard
