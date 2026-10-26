import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getPortalTrades } from '../../api/portal'

const fmtMoney = (n, digits = 2) => {
  const v = Number(n)
  if (!Number.isFinite(v)) return '—'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`
}

const fmtNum = (n, digits = 4) => {
  const v = Number(n)
  if (!Number.isFinite(v)) return '—'
  return v.toLocaleString('en-US', { maximumFractionDigits: digits })
}

const fmtRatio = (bucket) => {
  if (!bucket) return '—'
  if (bucket.pnl_ratio_infinite) return '∞'
  const r = Number(bucket.pnl_ratio)
  if (!Number.isFinite(r) || r <= 0) return '—'
  return r.toFixed(2)
}

const PortalTrades = () => {
  const [platform, setPlatform] = useState('all')
  const [symbol, setSymbol] = useState('all')
  const [strategy, setStrategy] = useState('all')
  const [items, setItems] = useState([])
  const [stats, setStats] = useState(null)
  const [optPlatforms, setOptPlatforms] = useState([])
  const [optSymbols, setOptSymbols] = useState([])
  const [optStrategies, setOptStrategies] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await getPortalTrades({
        platform: platform === 'all' ? '' : platform,
        symbol: symbol === 'all' ? '' : symbol,
        strategy: strategy === 'all' ? '' : strategy,
      })
      setItems(res?.items || [])
      setStats(res?.stats || null)
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [platform, symbol, strategy])

  useEffect(() => {
    getPortalTrades({})
      .then((res) => {
        const rows = res?.items || []
        setOptPlatforms(Array.from(new Set(rows.map((r) => r.platform).filter(Boolean))))
        setOptSymbols(Array.from(new Set(rows.map((r) => r.symbol).filter(Boolean))))
        setOptStrategies(Array.from(new Set(rows.map((r) => r.strategy_name).filter(Boolean))))
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const s7 = stats?.['7d'] || {}
  const s30 = stats?.['30d'] || {}
  const s180 = stats?.['180d'] || {}

  return (
    <div>
      <div className="qt-hero">
        <div>
          <p className="qt-kicker">LIVE TRADES</p>
          <h1 className="qt-title">实盘账户 · 交易记录</h1>
          <p className="qt-sub">Webhook 跟单成交入库；可按平台 / 币种 / 策略筛选，并查看收益与盈亏比。</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link className="portal-btn portal-btn-ghost" to="/portal">返回实盘</Link>
          <button type="button" className="portal-btn portal-btn-ghost" onClick={load}>刷新</button>
        </div>
      </div>

      <div className="qt-grid-4" style={{ marginBottom: 16 }}>
        <section className="qt-card">
          <p className="qt-stat-label">7 天</p>
          <p className={`qt-stat-value ${(s7.pnl || 0) >= 0 ? 'qt-up' : 'qt-down'}`}>
            {fmtMoney(s7.pnl || 0)}
          </p>
          <p className="qt-sub" style={{ margin: '4px 0 0' }}>{s7.orders || 0} 笔 · 盈亏比 {fmtRatio(s7)}</p>
        </section>
        <section className="qt-card">
          <p className="qt-stat-label">30 天</p>
          <p className={`qt-stat-value ${(s30.pnl || 0) >= 0 ? 'qt-up' : 'qt-down'}`}>
            {fmtMoney(s30.pnl || 0)}
          </p>
          <p className="qt-sub" style={{ margin: '4px 0 0' }}>{s30.orders || 0} 笔 · 盈亏比 {fmtRatio(s30)}</p>
        </section>
        <section className="qt-card">
          <p className="qt-stat-label">180 天</p>
          <p className={`qt-stat-value ${(s180.pnl || 0) >= 0 ? 'qt-up' : 'qt-down'}`}>
            {fmtMoney(s180.pnl || 0)}
          </p>
          <p className="qt-sub" style={{ margin: '4px 0 0' }}>{s180.orders || 0} 笔 · 盈亏比 {fmtRatio(s180)}</p>
        </section>
        <section className="qt-card">
          <p className="qt-stat-label">筛选内累计</p>
          <p className={`qt-stat-value ${(stats?.total_pnl || 0) >= 0 ? 'qt-up' : 'qt-down'}`}>
            {fmtMoney(stats?.total_pnl || 0)}
          </p>
          <p className="qt-sub" style={{ margin: '4px 0 0' }}>
            {stats?.total_orders || 0} 笔 · 盈亏比 {fmtRatio(stats)}
          </p>
        </section>
      </div>

      <section className="qt-card">
        <div className="qt-toolbar">
          <select className="qt-select" value={platform} onChange={(e) => setPlatform(e.target.value)}>
            <option value="all">平台: 全部</option>
            <option value="hyperliquid">Hyperliquid</option>
            <option value="okx">OKX</option>
            {optPlatforms.filter((p) => !['hyperliquid', 'okx'].includes(p)).map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <select className="qt-select" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            <option value="all">币种: 全部</option>
            {optSymbols.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select className="qt-select" value={strategy} onChange={(e) => setStrategy(e.target.value)}>
            <option value="all">策略: 全部</option>
            {optStrategies.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
            {['自适应做多策略', '自适应做空策略', '自适应平仓策略']
              .filter((s) => !optStrategies.includes(s))
              .map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
          </select>
        </div>
        {error ? <p className="qt-down">{error}</p> : null}
        {loading ? <p className="qt-sub">加载中…</p> : null}
        <div className="qt-table-wrap">
          <table className="qt-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>平台</th>
                <th>币种</th>
                <th>方向</th>
                <th>动作</th>
                <th>数量</th>
                <th>价格</th>
                <th>盈亏</th>
                <th>策略</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr><td colSpan={10}>暂无记录</td></tr>
              ) : (
                items.map((row) => (
                  <tr key={row.id}>
                    <td>{row.created_at}</td>
                    <td>{row.platform === 'hyperliquid' ? 'Hype' : (row.platform || '—').toUpperCase()}</td>
                    <td>{row.symbol}</td>
                    <td>{row.side}</td>
                    <td>{row.action}</td>
                    <td>{fmtNum(row.quantity)}</td>
                    <td>{fmtNum(row.price)}</td>
                    <td className={Number(row.pnl) >= 0 ? 'qt-up' : 'qt-down'}>{fmtMoney(row.pnl)}</td>
                    <td>{row.strategy_name || '—'}</td>
                    <td>{row.status}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

export default PortalTrades
