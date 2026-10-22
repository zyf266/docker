import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getExchangeBalances, getTvWebhookHint } from '../../api/portal'
import PortalConnectModal from './PortalConnectModal'

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

const PortalAccount = () => {
  const [connectOpen, setConnectOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [snap, setSnap] = useState({
    connected: false,
    accounts: [],
    positions: [],
    total_equity: null,
  })
  const [webhookHint, setWebhookHint] = useState(null)

  const loadBalances = useCallback(async () => {
    setError('')
    try {
      const res = await getExchangeBalances()
      setSnap({
        connected: !!res?.connected,
        accounts: res?.accounts || [],
        positions: res?.positions || [],
        total_equity: res?.total_equity,
      })
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '余额加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadBalances()
    getTvWebhookHint()
      .then((res) => setWebhookHint(res))
      .catch(() => setWebhookHint(null))
  }, [loadBalances])

  const okAccounts = (snap.accounts || []).filter((a) => a.status === 'ok')
  const platforms = okAccounts.map((a) => a.platform)
  const positions = snap.positions || []

  return (
    <div>
      <div className="qt-hero">
        <div>
          <p className="qt-kicker">LIVE ACCOUNT</p>
          <h1 className="qt-title">AI 实盘主账户</h1>
          <p className="qt-sub">
            {snap.connected ? '已连接交易所 · 余额实时拉取' : '连接交易所后显示真实账户余额'}
            {' '}
            <span className={`qt-pill ${snap.connected ? 'qt-pill-live' : 'qt-pill-off'}`}>
              {snap.connected ? '在线' : '未连接'}
            </span>
            {platforms.includes('okx') ? <span className="qt-pill qt-pill-crypto">OKX</span> : null}
            {platforms.includes('hyperliquid') ? <span className="qt-pill qt-pill-us">Hyperliquid</span> : null}
            {platforms.includes('binance') ? <span className="qt-pill qt-pill-crypto">Binance</span> : null}
          </p>
        </div>
        <Link className="portal-btn portal-btn-cyan" to="/portal/trades">查看交易记录</Link>
      </div>

      <div className="qt-grid-2" style={{ marginBottom: 16 }}>
        <section className="qt-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <strong>净值曲线 · AI 实盘 vs 基准 BTC</strong>
            <span className="qt-muted" style={{ color: 'var(--qt-muted)', fontSize: 12 }}>占位图，逻辑后接</span>
          </div>
          <div className="qt-chart-fake">
            <svg viewBox="0 0 640 220" preserveAspectRatio="none">
              <polyline
                fill="none"
                stroke="#38bdf8"
                strokeWidth="2.5"
                strokeDasharray="5 4"
                points="0,160 80,150 160,145 240,120 320,110 400,95 480,70 560,55 640,40"
              />
              <polyline
                fill="none"
                stroke="#4ade80"
                strokeWidth="2.5"
                points="0,175 80,168 160,155 240,150 320,140 400,125 480,118 560,105 640,90"
              />
            </svg>
          </div>
          <div className="qt-grid-4" style={{ marginTop: 14 }}>
            <div>
              <p className="qt-stat-label">账户权益</p>
              <p className="qt-stat-value qt-up">
                {snap.connected ? `$ ${fmtMoney(snap.total_equity)}` : '—'}
              </p>
            </div>
            <div>
              <p className="qt-stat-label">已连接平台</p>
              <p className="qt-stat-value qt-blue">{okAccounts.length || 0}</p>
            </div>
            <div>
              <p className="qt-stat-label">持仓数</p>
              <p className="qt-stat-value">{positions.length}</p>
            </div>
            <div>
              <p className="qt-stat-label">状态</p>
              <p className="qt-stat-value">{loading ? '…' : (snap.connected ? 'LIVE' : 'IDLE')}</p>
            </div>
          </div>
        </section>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <section className="qt-card">
            <strong>一键跟随 AI 实盘</strong>
            {loading ? (
              <p className="qt-sub">正在读取交易所余额…</p>
            ) : snap.connected ? (
              <div className="qt-balance-list">
                {okAccounts.map((acc) => (
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
                  </p>
                ))}
              </div>
            ) : (
              <div className="qt-steps">
                <div>1. 连接 Hyperliquid / 欧意 OKX API</div>
                <div>2. 设置跟随比例</div>
                <div>3. 确认风险提示后启动</div>
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
                {snap.connected ? '重新连接 / 添加平台' : '立即连接 · 一键跟随'}
              </button>
              {snap.connected ? (
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
                          {row.platform === 'hyperliquid' ? 'Hype' : row.platform.toUpperCase()}
                        </span>
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

      {webhookHint ? (
        <section className="qt-card" style={{ marginBottom: 16 }}>
          <strong>TradingView Webhook · 自动跟单</strong>
          <p className="qt-sub" style={{ margin: '8px 0' }}>
            {webhookHint.note || '观察库配置 connected 后，信号匹配策略名+币种+周期即下单。'}
          </p>
          <p style={{ fontFamily: 'ui-monospace, monospace', fontSize: 13, wordBreak: 'break-all' }}>
            POST {typeof window !== 'undefined' ? window.location.origin : ''}{webhookHint.path || '/api/portal/tv-webhook'}
          </p>
          <pre
            style={{
              margin: '10px 0 0',
              padding: 12,
              borderRadius: 10,
              background: 'rgba(0,0,0,0.35)',
              fontSize: 12,
              overflow: 'auto',
            }}
          >
            {JSON.stringify(webhookHint.example || {
              strategy_name: 'test',
              symbol: 'BTC',
              timeframe: '2h',
              signal: 'buy',
            }, null, 2)}
          </pre>
        </section>
      ) : null}

      <div className="qt-grid-4">
        <section className="qt-card">
          <p className="qt-stat-label">账户总权益</p>
          <p className="qt-stat-value">
            {snap.connected ? `$ ${fmtMoney(snap.total_equity)}` : '—'}
          </p>
        </section>
        <section className="qt-card">
          <p className="qt-stat-label">可用余额合计</p>
          <p className="qt-stat-value qt-up">
            {snap.connected
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
          <p className="qt-stat-label">已连接账户</p>
          <p className="qt-stat-value qt-blue">{okAccounts.length}</p>
        </section>
      </div>

      <PortalConnectModal
        open={connectOpen}
        symbols={[]}
        onClose={() => setConnectOpen(false)}
        onDone={(res) => {
          if (res?.balances) {
            setSnap({
              connected: !!res.balances.connected,
              accounts: res.balances.accounts || [],
              positions: res.balances.positions || [],
              total_equity: res.balances.total_equity,
            })
            setLoading(false)
          } else {
            setLoading(true)
            loadBalances()
          }
        }}
      />
    </div>
  )
}

export default PortalAccount
