import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import * as echarts from 'echarts'
import {
  disconnectExchange,
  getEquityCurve,
  getExchangeBalances,
  getPortalTrades,
} from '../../api/portal'
import PortalConnectModal from './PortalConnectModal'
import PortalWatchlist from './PortalWatchlist'

const fmtMoney = (n, digits = 2) => {
  const v = Number(n)
  if (!Number.isFinite(v)) return '—'
  return v.toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

const fmtPnl = (row) => {
  const pnl = Number(row?.pnl)
  if (!Number.isFinite(pnl)) return '—'
  const sign = pnl > 0 ? '+' : ''
  if (row?.pnl_pct != null && Number.isFinite(Number(row.pnl_pct))) {
    return `${sign}${Number(row.pnl_pct).toFixed(2)}%`
  }
  return `${sign}${fmtMoney(pnl)}`
}

const fmtSigned = (n) => {
  const v = Number(n)
  if (!Number.isFinite(v)) return '—'
  const sign = v > 0 ? '+' : ''
  return `${sign}${fmtMoney(v)}`
}

const fmtRatio = (bucket) => {
  if (!bucket) return '—'
  if (bucket.pnl_ratio_infinite) return '∞'
  const r = Number(bucket.pnl_ratio)
  if (!Number.isFinite(r) || r <= 0) return '—'
  return r.toFixed(2)
}

const platShort = (p) => {
  if (p === 'hyperliquid') return 'Hype'
  if (p === 'okx') return 'OKX'
  return (p || '').toUpperCase() || '—'
}

const PortalAccount = () => {
  const [connectOpen, setConnectOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [disconnectBusy, setDisconnectBusy] = useState('')
  const [snap, setSnap] = useState({
    connected: false,
    accounts: [],
    positions: [],
    total_equity: null,
  })
  /** 多平台时左上角筛选：all | hyperliquid | okx … */
  const [viewPlatform, setViewPlatform] = useState('all')
  const [tradeSymbol, setTradeSymbol] = useState('all')
  const [tradeStrategy, setTradeStrategy] = useState('all')
  const [trades, setTrades] = useState([])
  const [tradeStats, setTradeStats] = useState(null)
  const [tradeOpts, setTradeOpts] = useState({ symbols: [], strategies: [] })
  const [tradeErr, setTradeErr] = useState('')
  const [curve, setCurve] = useState(null)
  const [curveErr, setCurveErr] = useState('')
  const [curveLoading, setCurveLoading] = useState(false)
  const chartRef = useRef(null)
  const chartInst = useRef(null)

  const applySnap = (res) => {
    setSnap({
      connected: !!res?.connected,
      accounts: res?.accounts || [],
      positions: res?.positions || [],
      total_equity: res?.total_equity,
    })
  }

  const loadBalances = useCallback(async () => {
    setError('')
    try {
      const res = await getExchangeBalances()
      applySnap(res)
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '余额加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadTrades = useCallback(async () => {
    setTradeErr('')
    try {
      const res = await getPortalTrades({
        platform: viewPlatform === 'all' ? '' : viewPlatform,
        symbol: tradeSymbol === 'all' ? '' : tradeSymbol,
        strategy: tradeStrategy === 'all' ? '' : tradeStrategy,
      })
      setTrades(res?.items || [])
      setTradeStats(res?.stats || null)
    } catch (e) {
      setTradeErr(e?.response?.data?.detail || e?.message || '交易记录加载失败')
    }
  }, [viewPlatform, tradeSymbol, tradeStrategy])

  useEffect(() => {
    loadBalances()
    getPortalTrades({})
      .then((res) => {
        const items = res?.items || []
        setTradeOpts({
          symbols: Array.from(new Set(items.map((r) => r.symbol).filter(Boolean))),
          strategies: Array.from(new Set(items.map((r) => r.strategy_name).filter(Boolean))),
        })
      })
      .catch(() => {})
  }, [loadBalances])

  useEffect(() => {
    if (window.location.hash === '#portal-watchlist') {
      const t = window.setTimeout(() => {
        document.getElementById('portal-watchlist')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 300)
      return () => window.clearTimeout(t)
    }
    return undefined
  }, [])

  useEffect(() => {
    loadTrades()
  }, [loadTrades])

  const loadCurve = useCallback(async () => {
    setCurveLoading(true)
    setCurveErr('')
    try {
      const res = await getEquityCurve({
        platform: viewPlatform === 'all' ? '' : viewPlatform,
        days: 90,
      })
      setCurve(res)
    } catch (e) {
      setCurve(null)
      setCurveErr(e?.response?.data?.detail || e?.message || '净值曲线加载失败')
    } finally {
      setCurveLoading(false)
    }
  }, [viewPlatform])

  useEffect(() => {
    loadCurve()
  }, [loadCurve])

  useEffect(() => {
    const el = chartRef.current
    if (!el) return undefined
    if (!chartInst.current) chartInst.current = echarts.init(el)
    const ch = chartInst.current
    const dates = curve?.dates || []
    const liveIdx = curve?.live_index || []
    const btcIdx = curve?.btc_index || []
    if (!dates.length || !liveIdx.length) {
      ch.clear()
      ch.setOption({
        title: {
          text: curveLoading ? '净值加载中…' : (curveErr || '暂无净值数据（成交后自动生成）'),
          left: 'center',
          top: 'middle',
          textStyle: { color: '#94a3b8', fontSize: 13, fontWeight: 'normal' },
        },
      })
    } else {
      ch.setOption({
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          valueFormatter: (v) => (v == null || Number.isNaN(Number(v)) ? '—' : `${(Number(v) * 100 - 100).toFixed(2)}%`),
        },
        legend: {
          data: ['AI 实盘', '基准 BTC'],
          top: 0,
          textStyle: { color: '#94a3b8' },
        },
        grid: { left: 48, right: 16, top: 36, bottom: 28 },
        xAxis: {
          type: 'category',
          data: dates.map((d) => String(d).slice(5)),
          axisLabel: { color: '#64748b' },
          axisLine: { lineStyle: { color: '#334155' } },
        },
        yAxis: {
          type: 'value',
          scale: true,
          axisLabel: {
            color: '#64748b',
            formatter: (v) => `${((Number(v) - 1) * 100).toFixed(0)}%`,
          },
          splitLine: { lineStyle: { color: 'rgba(148,163,184,0.12)' } },
        },
        series: [
          {
            name: 'AI 实盘',
            type: 'line',
            smooth: true,
            showSymbol: false,
            data: liveIdx,
            lineStyle: { color: '#4ade80', width: 2.5 },
            itemStyle: { color: '#4ade80' },
            areaStyle: { color: 'rgba(74, 222, 128, 0.12)' },
          },
          {
            name: '基准 BTC',
            type: 'line',
            smooth: true,
            showSymbol: false,
            data: btcIdx,
            lineStyle: { color: '#38bdf8', width: 2, type: 'dashed' },
            itemStyle: { color: '#38bdf8' },
          },
        ],
      }, true)
    }
    const onResize = () => ch.resize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [curve, curveLoading, curveErr])

  useEffect(() => () => {
    chartInst.current?.dispose()
    chartInst.current = null
  }, [])

  const allOkAccounts = useMemo(
    () => (snap.accounts || []).filter((a) => a.status === 'ok'),
    [snap.accounts],
  )

  const multiPlatform = allOkAccounts.length > 1

  useEffect(() => {
    if (!multiPlatform && viewPlatform !== 'all') {
      setViewPlatform('all')
    }
  }, [multiPlatform, viewPlatform])

  const okAccounts = useMemo(() => {
    if (viewPlatform === 'all') return allOkAccounts
    return allOkAccounts.filter((a) => a.platform === viewPlatform)
  }, [allOkAccounts, viewPlatform])

  const positions = useMemo(() => {
    const all = snap.positions || []
    if (viewPlatform === 'all') return all
    return all.filter((p) => (p.platform || '') === viewPlatform)
  }, [snap.positions, viewPlatform])

  const filteredEquity = useMemo(() => {
    if (!snap.connected) return null
    if (viewPlatform === 'all') return snap.total_equity
    const acc = okAccounts[0]
    return acc?.equity ?? null
  }, [snap.connected, snap.total_equity, viewPlatform, okAccounts])

  const platforms = allOkAccounts.map((a) => a.platform)
  const s7 = tradeStats?.['7d'] || {}
  const s30 = tradeStats?.['30d'] || {}
  const s180 = tradeStats?.['180d'] || {}

  const onDisconnect = async (platform) => {
    if (!platform) return
    if (!window.confirm(`确定断开 ${platShort(platform)}？将删除本站保存的 API/私钥绑定。`)) return
    setDisconnectBusy(platform)
    setError('')
    try {
      const res = await disconnectExchange(platform)
      if (res?.balances) applySnap(res.balances)
      else await loadBalances()
      if (viewPlatform === platform) setViewPlatform('all')
      await loadTrades()
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '断开失败')
    } finally {
      setDisconnectBusy('')
    }
  }

  const StatPeriod = ({ label, bucket }) => (
    <div>
      <p className="qt-stat-label">{label}</p>
      <p className={`qt-stat-value ${(bucket.pnl || 0) >= 0 ? 'qt-up' : 'qt-down'}`}>
        {fmtSigned(bucket.pnl || 0)}
      </p>
      <p className="qt-sub" style={{ margin: 0 }}>
        {bucket.orders || 0} 笔 · 盈亏比 {fmtRatio(bucket)}
      </p>
    </div>
  )

  return (
    <div>
      <div className="qt-hero">
        <div>
          <p className="qt-kicker">LIVE ACCOUNT</p>
          <h1 className="qt-title">AI 实盘主账户</h1>
          <p className="qt-sub" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
            {multiPlatform ? (
              <select
                className="qt-select"
                style={{ width: 'auto', minWidth: 140 }}
                value={viewPlatform}
                onChange={(e) => setViewPlatform(e.target.value)}
                aria-label="选择平台"
              >
                <option value="all">平台: 全部</option>
                {allOkAccounts.map((a) => (
                  <option key={a.platform} value={a.platform}>
                    {a.platform_label || platShort(a.platform)}
                  </option>
                ))}
              </select>
            ) : null}
            {snap.connected ? '已连接交易所 · 余额实时拉取' : '连接交易所后显示真实账户余额'}
            <span className={`qt-pill ${snap.connected ? 'qt-pill-live' : 'qt-pill-off'}`}>
              {snap.connected ? '在线' : '未连接'}
            </span>
            {platforms.includes('okx') ? <span className="qt-pill qt-pill-crypto">OKX</span> : null}
            {platforms.includes('hyperliquid') ? <span className="qt-pill qt-pill-us">Hyperliquid</span> : null}
            {platforms.includes('binance') ? <span className="qt-pill qt-pill-crypto">Binance</span> : null}
            {viewPlatform !== 'all' ? (
              <span className="qt-pill qt-pill-live">筛选 · {platShort(viewPlatform)}</span>
            ) : null}
          </p>
        </div>
        <Link className="portal-btn portal-btn-cyan" to="/portal/trades">查看交易记录</Link>
      </div>

      <div className="qt-grid-2" style={{ marginBottom: 16 }}>
        <section className="qt-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, gap: 8, flexWrap: 'wrap' }}>
            <strong>净值曲线 · AI 实盘 vs 基准 BTC</strong>
            <span style={{ color: 'var(--qt-muted)', fontSize: 12 }}>
              {curveLoading
                ? '加载中…'
                : curve
                  ? `近 ${curve.days || 90} 日 · 实盘 ${fmtSigned(curve.live_return_pct || 0)}%`
                    + (curve.btc_return_pct != null ? ` · BTC ${fmtSigned(curve.btc_return_pct)}%` : '')
                  : (curveErr || '—')}
            </span>
          </div>
          <div ref={chartRef} className="qt-chart-live" />
          <div className="qt-grid-4" style={{ marginTop: 14 }}>
            <div>
              <p className="qt-stat-label">账户权益</p>
              <p className="qt-stat-value qt-up">
                {snap.connected && filteredEquity != null ? `$ ${fmtMoney(filteredEquity)}` : '—'}
              </p>
            </div>
            <div>
              <p className="qt-stat-label">已连接平台</p>
              <p className="qt-stat-value qt-blue">{viewPlatform === 'all' ? allOkAccounts.length : okAccounts.length}</p>
            </div>
            <div>
              <p className="qt-stat-label">持仓数</p>
              <p className="qt-stat-value">{positions.length}</p>
            </div>
            <div>
              <p className="qt-stat-label">状态</p>
              <p className="qt-stat-value">{loading ? '…' : (okAccounts.length || snap.connected ? 'LIVE' : 'IDLE')}</p>
            </div>
          </div>
        </section>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <section className="qt-card">
            <strong>一键连接</strong>
            {loading ? (
              <p className="qt-sub">正在读取交易所余额…</p>
            ) : okAccounts.length || allOkAccounts.length ? (
              <div className="qt-balance-list">
                {(viewPlatform === 'all' ? allOkAccounts : okAccounts).map((acc) => (
                  <div className="qt-balance-row" key={acc.platform}>
                    <div>
                      <strong>{acc.platform_label}</strong>
                      {acc.label ? (
                        <span style={{ color: 'var(--qt-muted)', marginLeft: 8, fontSize: 12 }}>{acc.label}</span>
                      ) : null}
                      {acc.address_mask || acc.api_key_mask ? (
                        <div style={{ color: 'var(--qt-muted)', fontSize: 12, marginTop: 2 }}>
                          {acc.address_mask || acc.api_key_mask}
                          {acc.demo ? ' · 模拟盘' : ''}
                        </div>
                      ) : null}
                      <button
                        type="button"
                        className="portal-btn portal-btn-ghost"
                        style={{ marginTop: 6, padding: '2px 8px', fontSize: 12 }}
                        disabled={disconnectBusy === acc.platform}
                        onClick={() => onDisconnect(acc.platform)}
                      >
                        {disconnectBusy === acc.platform ? '断开中…' : '断开连接'}
                      </button>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div className="qt-up" style={{ fontWeight: 700, fontSize: 18 }}>
                        {fmtMoney(acc.equity)} {acc.currency || ''}
                      </div>
                      <div style={{ color: 'var(--qt-muted)', fontSize: 12 }}>
                        可用 {fmtMoney(acc.balance)}
                      </div>
                    </div>
                  </div>
                ))}
                {(snap.accounts || []).filter((a) => a.status !== 'ok').map((acc) => (
                  <p key={acc.platform} className="qt-down" style={{ margin: '8px 0 0', fontSize: 13 }}>
                    {acc.platform_label}: {acc.error || '查询失败'}
                    {' · '}
                    <button
                      type="button"
                      className="portal-btn portal-btn-ghost"
                      style={{ padding: '0 6px', fontSize: 12 }}
                      onClick={() => onDisconnect(acc.platform)}
                    >
                      断开
                    </button>
                  </p>
                ))}
              </div>
            ) : (
              <div className="qt-steps">
                <div>1. 一键连接 Hyperliquid / 欧意 OKX</div>
                <div>2. 在观察库配置策略与下单平台</div>
                <div>3. TradingView Webhook 自动跟单</div>
              </div>
            )}
            {error ? <p className="qt-down" style={{ marginTop: 8 }}>{error}</p> : null}
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <button
                type="button"
                className="portal-btn portal-btn-primary"
                style={{ flex: 1 }}
                onClick={() => setConnectOpen(true)}
              >
                一键连接
              </button>
              {snap.connected || allOkAccounts.length ? (
                <button
                  type="button"
                  className="portal-btn portal-btn-ghost"
                  onClick={() => { setLoading(true); loadBalances() }}
                >
                  刷新
                </button>
              ) : null}
            </div>
          </section>
          <section className="qt-card">
            <strong>当前持仓 ({positions.length})</strong>
            <div className="qt-pos-list">
              {positions.length === 0 ? (
                <p className="qt-empty" style={{ margin: '12px 0' }}>
                  {snap.connected ? '暂无持仓' : '连接后显示交易所持仓'}
                </p>
              ) : (
                positions.map((row) => (
                  <div className="qt-pos-row" key={`${row.platform}-${row.symbol}-${row.side}`}>
                    <div>
                      <strong>{row.symbol}</strong>
                      {' '}
                      <span className={`qt-pill ${row.side === 'Long' ? 'qt-pill-long' : 'qt-pill-short'}`}>
                        {row.side}
                      </span>
                      {row.platform ? (
                        <span style={{ color: 'var(--qt-muted)', fontSize: 11, marginLeft: 6 }}>
                          {platShort(row.platform)}
                        </span>
                      ) : null}
                      {row.strategy_name ? (
                        <div style={{ color: 'var(--qt-muted)', fontSize: 12, marginTop: 2 }}>
                          策略 · {row.strategy_name}
                        </div>
                      ) : null}
                    </div>
                    <span className={String(fmtPnl(row)).startsWith('-') ? 'qt-down' : 'qt-up'}>
                      {fmtPnl(row)}
                    </span>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      </div>

      <div className="qt-grid-4">
        <section className="qt-card">
          <p className="qt-stat-label">账户总权益</p>
          <p className="qt-stat-value">
            {snap.connected && filteredEquity != null ? `$ ${fmtMoney(filteredEquity)}` : '—'}
          </p>
        </section>
        <section className="qt-card">
          <p className="qt-stat-label">可用余额合计</p>
          <p className="qt-stat-value qt-up">
            {okAccounts.length
              ? `$ ${fmtMoney(okAccounts.reduce((s, a) => s + (Number(a.balance) || 0), 0))}`
              : '—'}
          </p>
        </section>
        <section className="qt-card">
          <p className="qt-stat-label">持仓未实现盈亏</p>
          <p className={`qt-stat-value ${positions.reduce((s, p) => s + (Number(p.pnl) || 0), 0) >= 0 ? 'qt-up' : 'qt-down'}`}>
            {snap.connected
              ? (() => {
                const v = positions.reduce((s, p) => s + (Number(p.pnl) || 0), 0)
                return `${v >= 0 ? '+' : ''}$ ${fmtMoney(v)}`
              })()
              : '—'}
          </p>
        </section>
        <section className="qt-card">
          <p className="qt-stat-label">筛选盈亏比</p>
          <p className="qt-stat-value qt-blue">
            {tradeStats?.pnl_ratio_infinite ? '∞' : (fmtRatio(tradeStats) === '—' ? '—' : fmtRatio(tradeStats))}
          </p>
          <p className="qt-sub" style={{ margin: '4px 0 0' }}>
            盈利合计 / |亏损合计|
          </p>
        </section>
      </div>

      <section className="qt-card" style={{ marginTop: 16 }}>
        <PortalWatchlist embedded />
      </section>

      <section className="qt-card" style={{ marginTop: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <strong>交易记录清单</strong>
          <Link className="portal-btn portal-btn-ghost" to="/portal/trades">完整列表</Link>
        </div>
        <div className="qt-toolbar" style={{ marginTop: 12 }}>
          <select className="qt-select" value={tradeSymbol} onChange={(e) => setTradeSymbol(e.target.value)}>
            <option value="all">币种: 全部</option>
            {tradeOpts.symbols.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select className="qt-select" value={tradeStrategy} onChange={(e) => setTradeStrategy(e.target.value)}>
            <option value="all">策略: 全部</option>
            {tradeOpts.strategies.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
            {['自适应做多策略', '自适应做空策略', '自适应平仓策略']
              .filter((s) => !tradeOpts.strategies.includes(s))
              .map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
          </select>
          <button type="button" className="portal-btn portal-btn-ghost" onClick={loadTrades}>刷新</button>
        </div>
        <div className="qt-grid-4" style={{ margin: '12px 0' }}>
          <StatPeriod label="7 天收益 / 订单" bucket={s7} />
          <StatPeriod label="30 天收益 / 订单" bucket={s30} />
          <StatPeriod label="180 天收益 / 订单" bucket={s180} />
          <div>
            <p className="qt-stat-label">筛选内累计</p>
            <p className={`qt-stat-value ${(tradeStats?.total_pnl || 0) >= 0 ? 'qt-up' : 'qt-down'}`}>
              {fmtSigned(tradeStats?.total_pnl || 0)}
            </p>
            <p className="qt-sub" style={{ margin: 0 }}>
              {tradeStats?.total_orders || 0} 笔 · 盈亏比 {fmtRatio(tradeStats)}
            </p>
          </div>
        </div>
        {tradeErr ? <p className="qt-down">{tradeErr}</p> : null}
        <div className="qt-table-wrap">
          <table className="qt-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>平台</th>
                <th>币种</th>
                <th>方向</th>
                <th>动作</th>
                <th>盈亏</th>
                <th>策略</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {trades.length === 0 ? (
                <tr><td colSpan={8}>暂无交易记录（Webhook 跟单成功后写入）</td></tr>
              ) : (
                trades.slice(0, 30).map((row) => (
                  <tr key={row.id}>
                    <td>{row.created_at}</td>
                    <td>{platShort(row.platform)}</td>
                    <td>{row.symbol}</td>
                    <td>{row.side === 'BUY' ? '多' : row.side === 'SELL' ? '空' : row.side}</td>
                    <td>{row.action === 'open' ? '开仓' : row.action === 'close' ? '平仓' : row.action}</td>
                    <td className={Number(row.pnl) >= 0 ? 'qt-up' : 'qt-down'}>{fmtSigned(row.pnl)}</td>
                    <td>{row.strategy_name || '—'}</td>
                    <td>{row.status}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <PortalConnectModal
        open={connectOpen}
        symbols={[]}
        onClose={() => setConnectOpen(false)}
        onDone={(res) => {
          if (res?.balances) {
            applySnap(res.balances)
            setLoading(false)
          } else {
            setLoading(true)
            loadBalances()
          }
          loadCurve()
        }}
      />
    </div>
  )
}

export default PortalAccount
