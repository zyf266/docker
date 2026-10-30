import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import * as echarts from 'echarts'
import {
  disconnectExchange,
  getEquityCurve,
  getExchangeBalances,
  getPortalTrades,
  getTvWebhookHint,
} from '../../api/portal'
import { isAdminRole, readStoredUser } from '../../utils/authRole'
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

const CURVE_DAY_OPTIONS = [
  { value: 0, label: '全部' },
  { value: 30, label: '30天' },
  { value: 180, label: '180天' },
  { value: 360, label: '360天' },
]

const platShort = (p) => {
  if (p === 'hyperliquid') return 'Hype'
  if (p === 'okx') return 'OKX'
  if (p === 'binance') return 'Binance'
  if (p === 'crypto_account') return '加密账户'
  if (p === 'us_account') return '美股账户'
  if (typeof p === 'string' && p.startsWith('ba_')) return '账面'
  return (p || '').toUpperCase() || '—'
}

const isBookPlatform = (p) =>
  p === 'crypto_account' || p === 'us_account' || (typeof p === 'string' && p.startsWith('ba_'))
const isExchangePlatform = (p) => ['okx', 'hyperliquid', 'binance'].includes(p)

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
  /** 账户筛选：crypto_account | us_account | okx | hyperliquid | …（无「全部」） */
  const [viewPlatform, setViewPlatform] = useState('')
  const [tradeSymbol, setTradeSymbol] = useState('all')
  const [tradeStrategy, setTradeStrategy] = useState('all')
  const [trades, setTrades] = useState([])
  const [tradeStats, setTradeStats] = useState(null)
  const [tradeOpts, setTradeOpts] = useState({ symbols: [], strategies: [] })
  const [tradeErr, setTradeErr] = useState('')
  const [webhookHint, setWebhookHint] = useState('')
  const [curve, setCurve] = useState(null)
  const isAdmin = useMemo(() => isAdminRole(readStoredUser()?.role), [])
  const [curveErr, setCurveErr] = useState('')
  const [curveLoading, setCurveLoading] = useState(false)
  const [curveDays, setCurveDays] = useState(0)
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
    if (!viewPlatform) {
      setTrades([])
      setTradeStats(null)
      return
    }
    setTradeErr('')
    try {
      const res = await getPortalTrades({
        platform: viewPlatform,
        symbol: tradeSymbol === 'all' ? '' : tradeSymbol,
        strategy: tradeStrategy === 'all' ? '' : tradeStrategy,
      })
      setTrades(res?.items || [])
      setTradeStats(res?.stats || null)
    } catch (e) {
      setTradeErr(e?.response?.data?.detail || e?.message || '交易记录加载失败')
      setTrades([])
      setTradeStats(null)
    }
  }, [viewPlatform, tradeSymbol, tradeStrategy])

  useEffect(() => {
    loadBalances()
  }, [loadBalances])

  useEffect(() => {
    if (!isAdmin) return undefined
    const t = window.setTimeout(() => {
      getTvWebhookHint()
        .then((res) => {
          // 优先用服务端公网地址（80/443，无 :8100），与实盘策略 webhook 一致
          const url = res?.book_journal?.url
          if (url) {
            setWebhookHint(url)
            return
          }
          const base = (res?.public_base || 'http://47.110.57.118').replace(/:8100|:8005|:8050/g, '')
          const p = res?.book_journal?.path || '/api/portal/book-trade-webhook'
          setWebhookHint(`${base.replace(/\/$/, '')}${p.startsWith('/') ? p : `/${p}`}`)
        })
        .catch(() => {
          setWebhookHint('http://47.110.57.118/api/portal/book-trade-webhook')
        })
    }, 800)
    return () => window.clearTimeout(t)
  }, [isAdmin])

  useEffect(() => {
    if (window.location.hash === '#portal-watchlist') {
      const t = window.setTimeout(() => {
        document.getElementById('portal-watchlist')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 300)
      return () => window.clearTimeout(t)
    }
    return undefined
  }, [])

  // 成交/净值不绑死余额 loading：账面接口本地秒回，避免被交易所卡住
  useEffect(() => {
    if (!viewPlatform) return undefined
    const t = window.setTimeout(() => { loadTrades() }, 80)
    return () => window.clearTimeout(t)
  }, [viewPlatform, loadTrades])

  useEffect(() => {
    if (!viewPlatform) return undefined
    const t = window.setTimeout(() => {
      getPortalTrades({ platform: viewPlatform })
        .then((res) => {
          const items = res?.items || []
          setTradeOpts({
            symbols: Array.from(new Set(items.map((r) => r.symbol).filter(Boolean))),
            strategies: Array.from(new Set(items.map((r) => r.strategy_name).filter(Boolean))),
          })
        })
        .catch(() => {})
    }, 120)
    return () => window.clearTimeout(t)
  }, [viewPlatform])

  const loadCurve = useCallback(async () => {
    if (!viewPlatform) {
      setCurve(null)
      return
    }
    setCurveLoading(true)
    setCurveErr('')
    try {
      const res = await getEquityCurve({
        platform: viewPlatform,
        days: curveDays,
      })
      setCurve(res)
    } catch (e) {
      setCurve(null)
      setCurveErr(e?.response?.data?.detail || e?.message || '净值曲线加载失败')
    } finally {
      setCurveLoading(false)
    }
  }, [viewPlatform, curveDays])

  useEffect(() => {
    if (!viewPlatform) return undefined
    const t = window.setTimeout(() => { loadCurve() }, 100)
    return () => window.clearTimeout(t)
  }, [viewPlatform, loadCurve])

  useEffect(() => {
    const onCap = () => {
      loadBalances()
      loadTrades()
      loadCurve()
    }
    window.addEventListener('portal-book-capital-updated', onCap)
    return () => window.removeEventListener('portal-book-capital-updated', onCap)
  }, [loadBalances, loadTrades, loadCurve])

  useEffect(() => {
    const el = chartRef.current
    if (!el) return undefined
    if (!chartInst.current) chartInst.current = echarts.init(el)
    const ch = chartInst.current
    const dates = curve?.dates || []
    const liveIdx = curve?.live_index || []
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
          data: ['净值'],
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
            name: '净值',
            type: 'line',
            smooth: true,
            showSymbol: false,
            data: liveIdx,
            lineStyle: { color: '#4ade80', width: 2.5 },
            itemStyle: { color: '#4ade80' },
            areaStyle: { color: 'rgba(74, 222, 128, 0.12)' },
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

  const exchangeAccounts = useMemo(
    () => allOkAccounts.filter((a) => !a.book && !isBookPlatform(a.platform)),
    [allOkAccounts],
  )

  /** 账户卡片：账面始终显示；OKX/Hype 等仅已连接时显示。三行：名称 / id / 余额 */
  const accountCards = useMemo(() => {
    const cards = []
    for (const a of allOkAccounts) {
      if (isBookPlatform(a.platform)) {
        const market = a.market || (a.platform === 'us_account' ? 'us' : 'crypto')
        const title =
          a.title
          || (market === 'us' || a.platform === 'us_account' ? 'Binance 美股' : 'Binance Crypto')
        cards.push({
          platform: a.platform,
          title,
          accountId: a.account_id || a.address_mask || a.platform,
          balance: a.equity,
          currency: a.currency || 'USD',
          market,
          sortKey:
            a.platform === 'crypto_account'
              ? 0
              : a.platform === 'us_account'
                ? 1
                : 10 + (Number(a.book_account_id) || 0),
        })
      }
    }
    cards.sort((x, y) => (x.sortKey ?? 9) - (y.sortKey ?? 9))
    for (const a of exchangeAccounts) {
      cards.push({
        platform: a.platform,
        title: platShort(a.platform),
        accountId: a.account_id || a.address_mask || a.api_key_mask || a.platform,
        balance: a.equity ?? a.balance,
        currency: a.currency || '',
        canDisconnect: true,
      })
    }
    return cards
  }, [allOkAccounts, exchangeAccounts])

  const okAccounts = useMemo(
    () => allOkAccounts.filter((a) => a.platform === viewPlatform),
    [allOkAccounts, viewPlatform],
  )

  const positions = useMemo(() => {
    return (snap.positions || []).filter((p) => (p.platform || '') === viewPlatform)
  }, [snap.positions, viewPlatform])

  const filteredEquity = useMemo(() => {
    const acc = okAccounts[0]
    return acc?.equity ?? null
  }, [okAccounts])

  const hasLiveOrBook = allOkAccounts.length > 0 || snap.connected

  useEffect(() => {
    if (!accountCards.length) {
      if (viewPlatform) setViewPlatform('')
      return
    }
    if (!accountCards.some((c) => c.platform === viewPlatform)) {
      setViewPlatform(accountCards[0].platform)
    }
  }, [accountCards, viewPlatform])

  const onDisconnect = async (platform) => {
    if (!platform) return
    if (!window.confirm(`确定断开 ${platShort(platform)}？将删除本站保存的 API/私钥绑定。`)) return
    setDisconnectBusy(platform)
    setError('')
    try {
      const res = await disconnectExchange(platform)
      if (res?.balances) applySnap(res.balances)
      else await loadBalances()
      if (viewPlatform === platform) setViewPlatform('')
      await loadTrades()
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '断开失败')
    } finally {
      setDisconnectBusy('')
    }
  }

  return (
    <div>
      <div className="qt-hero">
        <div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'stretch' }}>
            {accountCards.map((card) => {
              const active = viewPlatform === card.platform
              return (
                <button
                  key={card.platform}
                  type="button"
                  onClick={() => setViewPlatform(card.platform)}
                  className="qt-card"
                  style={{
                    minWidth: 168,
                    maxWidth: 220,
                    textAlign: 'left',
                    cursor: 'pointer',
                    padding: '12px 14px',
                    margin: 0,
                    border: active ? '1px solid #4ade80' : '1px solid rgba(148,163,184,0.25)',
                    background: active ? 'rgba(74,222,128,0.08)' : undefined,
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{card.title}</div>
                  <div style={{ color: 'var(--qt-muted)', fontSize: 12, marginTop: 6 }}>
                    号码: {card.accountId}
                  </div>
                  <div className="qt-up" style={{ fontWeight: 700, fontSize: 16, marginTop: 8 }}>
                    {card.balance != null ? `$ ${fmtMoney(card.balance)}` : '—'}
                    {card.currency ? ` ${card.currency}` : ''}
                  </div>
                  {card.canDisconnect ? (
                    <span
                      role="button"
                      tabIndex={0}
                      className="portal-btn portal-btn-ghost"
                      style={{ marginTop: 8, padding: '2px 8px', fontSize: 12, display: 'inline-block' }}
                      disabled={disconnectBusy === card.platform}
                      onClick={(e) => {
                        e.stopPropagation()
                        onDisconnect(card.platform)
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.stopPropagation()
                          onDisconnect(card.platform)
                        }
                      }}
                    >
                      {disconnectBusy === card.platform ? '断开中…' : '断开'}
                    </span>
                  ) : null}
                </button>
              )
            })}
            <button
              type="button"
              className="portal-btn portal-btn-primary"
              style={{ alignSelf: 'center', padding: '10px 14px' }}
              onClick={() => setConnectOpen(true)}
            >
              添加账户
            </button>
          </div>
          <p className="qt-sub" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', marginTop: 10 }}>
            {hasLiveOrBook ? (
              <button
                type="button"
                className="portal-btn portal-btn-ghost"
                style={{ padding: '6px 12px', fontSize: 13 }}
                onClick={() => { setLoading(true); loadBalances() }}
              >
                刷新
              </button>
            ) : null}
            {snap.connected ? '已连接交易所 · 余额实时拉取' : '添加账户后显示实时余额'}
            <span className={`qt-pill ${snap.connected ? 'qt-pill-live' : 'qt-pill-off'}`}>
              {snap.connected ? '在线' : '未连接'}
            </span>
          </p>
          {error ? <p className="qt-down" style={{ marginTop: 8 }}>{error}</p> : null}
        </div>
      </div>

      <section className="qt-card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, gap: 8, flexWrap: 'wrap' }}>
          <strong>净值曲线</strong>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', gap: 4 }}>
              {CURVE_DAY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`portal-btn ${curveDays === opt.value ? 'portal-btn-primary' : 'portal-btn-ghost'}`}
                  style={{ padding: '2px 10px', fontSize: 12 }}
                  onClick={() => setCurveDays(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <span style={{ color: 'var(--qt-muted)', fontSize: 12 }}>
              {curveLoading
                ? '加载中…'
                : curve
                  ? `${curveDays === 0 ? '全部' : `近 ${curve.days || curveDays} 日`} · 收益率 ${fmtSigned(curve.live_return_pct || 0)}%`
                  : (curveErr || '—')}
            </span>
          </div>
        </div>
        <div ref={chartRef} className="qt-chart-live" />
        <div className="qt-grid-4" style={{ marginTop: 14 }}>
          <div>
            <p className="qt-stat-label">账户权益</p>
            <p className="qt-stat-value qt-up">
              {filteredEquity != null ? `$ ${fmtMoney(filteredEquity)}` : '—'}
            </p>
          </div>
          <div>
            <p className="qt-stat-label">收益率</p>
            <p className={`qt-stat-value ${(curve?.live_return_pct || 0) >= 0 ? 'qt-up' : 'qt-down'}`}>
              {curve ? `${fmtSigned(curve.live_return_pct || 0)}%` : '—'}
            </p>
          </div>
          <div>
            <p className="qt-stat-label">持仓数</p>
            <p className="qt-stat-value">{positions.length}</p>
          </div>
          <div>
            <p className="qt-stat-label">状态</p>
            <p className="qt-stat-value">{loading ? '…' : (hasLiveOrBook ? 'LIVE' : 'IDLE')}</p>
          </div>
        </div>
      </section>

      <div className="qt-grid-4">
        <section className="qt-card">
          <p className="qt-stat-label">账户总权益</p>
          <p className="qt-stat-value">
            {filteredEquity != null ? `$ ${fmtMoney(filteredEquity)}` : '—'}
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
            {snap.connected || positions.length
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
        <strong>当前持仓 ({positions.length})</strong>
        <div className="qt-table-wrap" style={{ marginTop: 12 }}>
          <table className="qt-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>币种</th>
                <th>方向</th>
                <th>动作</th>
                <th>仓位</th>
                <th>开仓价</th>
              </tr>
            </thead>
            <tbody>
              {positions.length === 0 ? (
                <tr>
                  <td colSpan={6}>
                    {isBookPlatform(viewPlatform)
                      ? '暂无持仓（TV 开仓信号写入后显示）'
                      : (snap.connected || isExchangePlatform(viewPlatform)
                        ? '暂无持仓'
                        : '添加账户后显示持仓')}
                  </td>
                </tr>
              ) : (
                positions.map((row) => {
                  const sideLabel = row.side === 'BUY' || row.side === 'Long'
                    ? '多'
                    : row.side === 'SELL' || row.side === 'Short'
                      ? '空'
                      : (row.side || '—')
                  const actionLabel = row.action === 'close' || row.action === '平仓'
                    ? '平仓'
                    : '开仓'
                  return (
                    <tr key={`${row.platform}-${row.symbol}-${row.side}-${row.opened_at || ''}`}>
                      <td>{row.opened_at || '—'}</td>
                      <td>{row.symbol || '—'}</td>
                      <td>{sideLabel}</td>
                      <td>{actionLabel}</td>
                      <td>
                        {row.margin != null && Number.isFinite(Number(row.margin))
                          ? `$ ${fmtMoney(row.margin)}`
                          : '—'}
                      </td>
                      <td>
                        {row.entry_price != null && Number.isFinite(Number(row.entry_price))
                          ? fmtMoney(row.entry_price)
                          : '—'}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="qt-card" style={{ marginTop: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <strong>交易记录清单</strong>
          <button type="button" className="portal-btn portal-btn-ghost" onClick={() => { loadTrades() }}>
            刷新
          </button>
        </div>
        {isAdmin && webhookHint ? (
          <p className="qt-sub" style={{ marginTop: 8, wordBreak: 'break-all' }}>
            账面 TV Webhook（只记账）：
            <code style={{ color: '#4ade80' }}>{webhookHint}</code>
          </p>
        ) : null}
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
          </select>
        </div>
        <div className="qt-grid-4" style={{ margin: '12px 0' }}>
          {['7d', '30d', '180d'].map((key) => {
            const bucket = tradeStats?.[key] || {}
            const label = key === '7d' ? '7 天收益 / 订单' : key === '30d' ? '30 天收益 / 订单' : '180 天收益 / 订单'
            return (
              <div key={key}>
                <p className="qt-stat-label">{label}</p>
                <p className={`qt-stat-value ${(bucket.pnl || 0) >= 0 ? 'qt-up' : 'qt-down'}`}>
                  {fmtSigned(bucket.pnl || 0)}
                </p>
                <p className="qt-sub" style={{ margin: 0 }}>
                  {bucket.orders || 0} 笔 · 盈亏比 {fmtRatio(bucket)}
                  {bucket.return_pct != null && Number.isFinite(Number(bucket.return_pct))
                    ? ` · 收益率 ${fmtSigned(bucket.return_pct)}%`
                    : ''}
                </p>
              </div>
            )
          })}
          <div>
            <p className="qt-stat-label">筛选内累计</p>
            <p className={`qt-stat-value ${(tradeStats?.total_pnl || 0) >= 0 ? 'qt-up' : 'qt-down'}`}>
              {fmtSigned(tradeStats?.total_pnl || 0)}
            </p>
            <p className="qt-sub" style={{ margin: 0 }}>
              {tradeStats?.total_orders || 0} 笔 · 盈亏比 {fmtRatio(tradeStats)}
              {tradeStats?.return_pct != null && Number.isFinite(Number(tradeStats.return_pct))
                ? ` · 收益率 ${fmtSigned(tradeStats.return_pct)}%`
                : ''}
            </p>
          </div>
        </div>
        {tradeErr ? <p className="qt-down">{tradeErr}</p> : null}
        <div className="qt-table-wrap">
          <table className="qt-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>币种</th>
                <th>方向</th>
                <th>动作</th>
                <th>仓位</th>
                <th>开仓价</th>
                <th>平仓价</th>
                <th>盈亏</th>
                <th>策略</th>
              </tr>
            </thead>
            <tbody>
              {trades.length === 0 ? (
                <tr><td colSpan={9}>暂无交易记录</td></tr>
              ) : (
                trades.slice(0, 50).map((row) => (
                  <tr key={row.id}>
                    <td>{row.created_at}</td>
                    <td>{row.symbol}</td>
                    <td>{row.side === 'BUY' ? '多' : row.side === 'SELL' ? '空' : row.side}</td>
                    <td>{row.action === 'open' ? '开仓' : row.action === 'close' ? '平仓' : row.action}</td>
                    <td>
                      {row.margin != null && Number.isFinite(Number(row.margin))
                        ? `$ ${fmtMoney(row.margin)}`
                        : '—'}
                    </td>
                    <td>
                      {row.action === 'open' && row.price != null && Number.isFinite(Number(row.price))
                        ? fmtMoney(row.price)
                        : '—'}
                    </td>
                    <td>
                      {row.action === 'close' && row.price != null && Number.isFinite(Number(row.price))
                        ? fmtMoney(row.price)
                        : '—'}
                    </td>
                    <td className={Number(row.pnl) >= 0 ? 'qt-up' : 'qt-down'}>{fmtSigned(row.pnl)}</td>
                    <td>{row.strategy_name || '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="qt-card" style={{ marginTop: 16 }}>
        <PortalWatchlist embedded />
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
