import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  addWatchSymbol,
  getWatchlist,
  removeWatchSymbol,
  saveWatchConfig,
  searchBinanceSymbols,
} from '../../api/portal'
import PortalConnectModal from './PortalConnectModal'

const Strength = ({ on, label }) => (
  <span className={`qt-pill ${on ? (label === '长强' ? 'qt-pill-long' : 'qt-pill-crypto') : 'qt-pill-off'}`}>
    {on ? label : '未站上'}
  </span>
)

const SignalCell = ({ value }) => {
  if (value === '金叉') return <span className="qt-up">金叉</span>
  if (value === '死叉') return <span className="qt-down">死叉</span>
  return <span style={{ color: 'var(--qt-muted)' }}>{value || '—'}</span>
}

const StatusCell = ({ row, onConnect }) => {
  const st = (row?.config?.status || row?.status || '').toLowerCase()
  const ex = row?.config?.exchange || row?.exchange || ''
  if (st === 'connected') {
    return (
      <button type="button" className="qt-status-btn" onClick={() => onConnect?.(row)} title="已连接，可重新绑定">
        <span className="qt-pill qt-pill-live">
          <span className="qt-status-dot" />
          connected
          {ex ? ` · ${ex === 'hyperliquid' ? 'Hype' : ex === 'okx' ? 'OKX' : ex}` : ''}
        </span>
      </button>
    )
  }
  if (st === 'living') {
    return (
      <button type="button" className="qt-status-btn" onClick={() => onConnect?.(row)} title="点击立即连接交易所">
        <span className="qt-pill qt-pill-live">
          <span className="qt-status-dot" />
          living
        </span>
      </button>
    )
  }
  return <span style={{ color: 'var(--qt-muted)' }}>—</span>
}

const emptyConfig = {
  require_short: true,
  require_mid: true,
  require_long: false,
  strategy_name: '',
  timeframe: '2h',
  size_mode: 'percent',
  size_value: '10',
  take_profit: '',
  stop_loss: '',
}

const fmtPrice = (n) => {
  const v = Number(n)
  if (!Number.isFinite(v) || v === 0) return '—'
  if (v >= 1000) return v.toLocaleString('en-US', { maximumFractionDigits: 2 })
  if (v >= 1) return v.toFixed(3)
  return v.toFixed(6)
}

const fmtCacheAge = (sec) => {
  const n = Number(sec)
  if (!Number.isFinite(n) || n < 0) return ''
  if (n < 60) return `${Math.round(n)} 秒前`
  if (n < 3600) return `${Math.round(n / 60)} 分钟前`
  return `${(n / 3600).toFixed(1)} 小时前`
}

/** 路由切走再回来时，先画上一帧，避免误以为每次都在重拉 */
let _watchlistSnap = null

const PortalWatchlist = () => {
  const [items, setItems] = useState(() => _watchlistSnap?.items || [])
  const [summary, setSummary] = useState(() => _watchlistSnap?.summary || { short: 0, mid: 0, long: 0 })
  const [loading, setLoading] = useState(!_watchlistSnap)
  const [error, setError] = useState('')
  const [marketFilter, setMarketFilter] = useState('all')
  const [strengthFilter, setStrengthFilter] = useState('all')
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState([])

  const [addOpen, setAddOpen] = useState(false)
  const [addMarket, setAddMarket] = useState('us')
  const [addQ, setAddQ] = useState('')
  const [addHits, setAddHits] = useState([])
  const [addBusy, setAddBusy] = useState(false)
  const [addMsg, setAddMsg] = useState('')
  const [metricsLoading, setMetricsLoading] = useState(false)
  const [cacheMeta, setCacheMeta] = useState(() => ({
    fromCache: !!_watchlistSnap?.from_cache,
    ageSec: _watchlistSnap?.oldest_cache_age_sec ?? null,
    ttlSec: _watchlistSnap?.cache_ttl_sec ?? 1800,
  }))

  const [cfgOpen, setCfgOpen] = useState(false)
  const [cfgStep, setCfgStep] = useState(1)
  const [cfgSymbols, setCfgSymbols] = useState([])
  const [cfg, setCfg] = useState(emptyConfig)
  const [cfgBusy, setCfgBusy] = useState(false)
  const [cfgMsg, setCfgMsg] = useState('')

  const [connectOpen, setConnectOpen] = useState(false)
  const [connectSymbols, setConnectSymbols] = useState([])

  const applyList = (res) => {
    const next = {
      items: res?.items || [],
      summary: res?.summary || { short: 0, mid: 0, long: 0 },
      from_cache: !!res?.from_cache,
      oldest_cache_age_sec: res?.oldest_cache_age_sec ?? null,
      cache_ttl_sec: res?.cache_ttl_sec ?? 1800,
    }
    _watchlistSnap = next
    setItems(next.items)
    setSummary(next.summary)
    setCacheMeta({
      fromCache: next.from_cache,
      ageSec: next.oldest_cache_age_sec,
      ttlSec: next.cache_ttl_sec,
    })
  }

  /** force=true 才忽略 30 分钟缓存重拉 K 线 */
  const load = useCallback(async ({ force = false } = {}) => {
    if (force) setMetricsLoading(true)
    else if (!_watchlistSnap) setLoading(true)
    setError('')
    try {
      const res = await getWatchlist(1, force ? 1 : 0)
      applyList(res)
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '加载失败')
    } finally {
      setLoading(false)
      setMetricsLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setError('')
      // 有本地快照则静默读服务端缓存；无快照才显示加载
      if (!_watchlistSnap) setLoading(true)
      try {
        const res = await getWatchlist(1, 0)
        if (!cancelled) applyList(res)
      } catch (e) {
        if (!cancelled) setError(e?.response?.data?.detail || e?.message || '加载失败')
      } finally {
        if (!cancelled) {
          setLoading(false)
          setMetricsLoading(false)
        }
      }
    })()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!addOpen) return undefined
    let cancelled = false
    const timer = setTimeout(async () => {
      try {
        const res = await searchBinanceSymbols(addQ, addMarket)
        if (!cancelled) setAddHits(res?.items || [])
      } catch (_) {
        if (!cancelled) setAddHits([])
      }
    }, 250)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [addOpen, addQ, addMarket])

  const filtered = useMemo(() => {
    const q = query.trim().toUpperCase()
    return (items || []).filter((row) => {
      if (marketFilter === 'crypto' && row.market === 'us') return false
      if (marketFilter === 'us' && row.market !== 'us') return false
      if (strengthFilter === 'short' && !row.short_on) return false
      if (strengthFilter === 'mid' && !row.mid_on) return false
      if (strengthFilter === 'long' && !row.long_on) return false
      if (!q) return true
      return `${row.code || ''} ${row.symbol || ''} ${row.name || ''}`.toUpperCase().includes(q)
    })
  }, [items, marketFilter, strengthFilter, query])

  const allChecked = filtered.length > 0 && filtered.every((row) => selected.includes(row.symbol))

  const toggleAll = () => {
    if (allChecked) {
      setSelected((prev) => prev.filter((s) => !filtered.some((row) => row.symbol === s)))
      return
    }
    setSelected((prev) => Array.from(new Set([...prev, ...filtered.map((row) => row.symbol)])))
  }

  const toggleOne = (symbol) => {
    setSelected((prev) => (prev.includes(symbol) ? prev.filter((s) => s !== symbol) : [...prev, symbol]))
  }

  const openConfig = (symbols, seed) => {
    const list = Array.from(new Set(symbols.filter(Boolean)))
    if (!list.length) return
    setCfgSymbols(list)
    setCfg({
      ...emptyConfig,
      ...(seed || {}),
      require_short: seed?.require_short ?? true,
      require_mid: seed?.require_mid ?? true,
      require_long: seed?.require_long ?? false,
      strategy_name: seed?.strategy_name || '',
      timeframe: seed?.timeframe || '2h',
      size_mode: seed?.size_mode || 'percent',
      size_value: seed?.size_value || '10',
      take_profit: seed?.take_profit || '',
      stop_loss: seed?.stop_loss || '',
    })
    setCfgStep(1)
    setCfgMsg('')
    setCfgOpen(true)
  }

  const onAdd = async (hit) => {
    setAddBusy(true)
    setAddMsg('')
    setError('')
    try {
      const res = await addWatchSymbol({
        symbol: hit.symbol,
        name: hit.name || '',
        market: hit.market || addMarket || 'crypto',
      })
      const item = res?.item || res
      const code = item?.code || hit.code || hit.symbol
      setAddMsg(`已添加 ${code}，已写入观察库`)
      setItems((prev) => {
        const next = prev.filter((row) => row.symbol !== item.symbol)
        return [item, ...next]
      })
      setTimeout(() => {
        setAddOpen(false)
        setAddQ('')
        setAddMsg('')
      }, 600)
      // 新标的无缓存，后台算一次指标
      load({ force: true })
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || '添加失败'
      setAddMsg(msg)
      setError(msg)
    } finally {
      setAddBusy(false)
    }
  }

  const onRemove = async (symbol) => {
    try {
      await removeWatchSymbol(symbol)
      setItems((prev) => prev.filter((row) => row.symbol !== symbol))
      load({ force: false })
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '删除失败')
    }
  }

  const openConnect = (rowOrSymbols) => {
    if (Array.isArray(rowOrSymbols)) {
      setConnectSymbols(rowOrSymbols)
    } else if (rowOrSymbols?.symbol) {
      setConnectSymbols([rowOrSymbols.symbol])
    } else {
      setConnectSymbols([])
    }
    setConnectOpen(true)
  }

  const onSaveConfig = async () => {
    setCfgBusy(true)
    setCfgMsg('')
    try {
      await saveWatchConfig({
        symbols: cfgSymbols,
        require_short: !!cfg.require_short,
        require_mid: !!cfg.require_mid,
        require_long: !!cfg.require_long,
        strategy_name: cfg.strategy_name,
        timeframe: cfg.timeframe,
        size_mode: cfg.size_mode,
        size_value: cfg.size_value,
        take_profit: cfg.take_profit,
        stop_loss: cfg.stop_loss,
      })
      setCfgOpen(false)
      await load({ force: false })
      // 保存后状态变 living，引导去连交易所
      setConnectSymbols([...cfgSymbols])
      setConnectOpen(true)
    } catch (e) {
      setCfgMsg(e?.response?.data?.detail || e?.message || '保存失败')
    } finally {
      setCfgBusy(false)
    }
  }

  return (
    <div>
      <div className="qt-hero">
        <div>
          <p className="qt-kicker">WATCHLIST</p>
          <h1 className="qt-title">标的观察库 · 概览</h1>
          <p className="qt-sub">
            添加只写库、秒返回；指标默认读 30 分钟缓存。配置保存后点 living 连接交易所 → 状态 connected 后，
            TradingView webhook（策略名+币种+周期一致）会按仓位自动下单并挂止盈止损。
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button type="button" className="portal-btn portal-btn-primary" onClick={() => setAddOpen(true)}>
            + 添加标的
          </button>
          <Link className="portal-btn portal-btn-cyan" to="/portal/ma-cards">多卡片均线视图</Link>
        </div>
      </div>

      <section className="qt-card" style={{ marginBottom: 16 }}>
        <div className="qt-toolbar">
          <select className="qt-select" value={marketFilter} onChange={(e) => setMarketFilter(e.target.value)}>
            <option value="all">市场: 全部</option>
            <option value="crypto">加密</option>
            <option value="us">美股</option>
          </select>
          <select className="qt-select" value={strengthFilter} onChange={(e) => setStrengthFilter(e.target.value)}>
            <option value="all">强弱: 全部</option>
            <option value="short">短强</option>
            <option value="mid">中强</option>
            <option value="long">长强</option>
          </select>
          <input
            className="qt-input"
            placeholder="搜索代码/名称"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button
            type="button"
            className="portal-btn portal-btn-ghost"
            onClick={() => load({ force: true })}
            disabled={loading || metricsLoading}
          >
            {metricsLoading ? '指标刷新中…' : '刷新指标'}
          </button>
          <button
            type="button"
            className="portal-btn portal-btn-primary"
            disabled={!selected.length}
            onClick={() => openConfig(selected)}
          >
            批量配置 ({selected.length})
          </button>
          <span style={{ marginLeft: 'auto', color: 'var(--qt-muted)', fontSize: 12 }}>
            <span className="qt-pill qt-pill-live">●</span>
            {metricsLoading
              ? ' 正在拉 K 线…'
              : cacheMeta.fromCache
                ? ` 缓存 · ${fmtCacheAge(cacheMeta.ageSec) || '已命中'} · ${Math.round((cacheMeta.ttlSec || 1800) / 60)} 分钟更新`
                : ' 已拉取最新'}
          </span>
        </div>

        {error ? <p className="qt-down" style={{ marginBottom: 10 }}>{error}</p> : null}

        <div className="qt-table-wrap">
          <table className="qt-table">
            <thead>
              <tr>
                <th>
                  <input type="checkbox" checked={allChecked} onChange={toggleAll} aria-label="全选" />
                </th>
                <th>代码</th>
                <th>名称</th>
                <th>市场</th>
                <th>最新价</th>
                <th>2h信号</th>
                <th>4h信号</th>
                <th>短强 (MA5)</th>
                <th>中强 (MA30)</th>
                <th>长强 (MA200)</th>
                <th>状态</th>
                <th>配置</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={12} className="qt-empty">
                    {loading ? '加载中…' : '暂无标的，点击「添加标的」选择美股或币安交易对'}
                  </td>
                </tr>
              ) : (
                filtered.map((row) => (
                  <tr key={row.symbol}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selected.includes(row.symbol)}
                        onChange={() => toggleOne(row.symbol)}
                        aria-label={`选择 ${row.code}`}
                      />
                    </td>
                    <td><strong>{row.code}</strong></td>
                    <td>{row.name}</td>
                    <td>
                      <span className={`qt-pill ${row.market === 'us' ? 'qt-pill-us' : 'qt-pill-crypto'}`}>
                        {row.market === 'us' ? '美股' : '加密'}
                      </span>
                    </td>
                    <td>{fmtPrice(row.price)}</td>
                    <td><SignalCell value={row.signal_2h} /></td>
                    <td><SignalCell value={row.signal_4h} /></td>
                    <td><Strength on={row.short_on} label="短强" /></td>
                    <td><Strength on={row.mid_on} label="中强" /></td>
                    <td><Strength on={row.long_on} label="长强" /></td>
                    <td><StatusCell row={row} onConnect={openConnect} /></td>
                    <td>
                      <button
                        type="button"
                        className="portal-btn portal-btn-ghost"
                        style={{ padding: '4px 10px' }}
                        onClick={() => openConfig([row.symbol], row.config)}
                      >
                        配置
                      </button>
                      <button
                        type="button"
                        className="portal-btn portal-btn-ghost"
                        style={{ padding: '4px 10px', marginLeft: 6 }}
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
      </section>

      <div className="qt-grid-3">
        <section className="qt-card">
          <p className="qt-stat-label">短强 (站上 MA5)</p>
          <p className="qt-stat-value qt-cyan">{summary.short}</p>
        </section>
        <section className="qt-card">
          <p className="qt-stat-label">中强 (站上 MA30)</p>
          <p className="qt-stat-value qt-blue">{summary.mid}</p>
        </section>
        <section className="qt-card">
          <p className="qt-stat-label">长强 (站上 MA200)</p>
          <p className="qt-stat-value qt-up">{summary.long}</p>
        </section>
      </div>

      {addOpen ? (
        <div className="qt-modal-mask" role="dialog" aria-modal="true">
          <div className="qt-modal">
            <div className="qt-modal-head">
              <strong>添加标的</strong>
              <button type="button" className="portal-btn portal-btn-ghost" onClick={() => setAddOpen(false)}>关闭</button>
            </div>
            <div className="qt-toolbar" style={{ marginBottom: 10 }}>
              <button
                type="button"
                className={`portal-btn ${addMarket === 'us' ? 'portal-btn-primary' : 'portal-btn-ghost'}`}
                onClick={() => { setAddMarket('us'); setAddQ('') }}
              >
                美股
              </button>
              <button
                type="button"
                className={`portal-btn ${addMarket === 'crypto' ? 'portal-btn-primary' : 'portal-btn-ghost'}`}
                onClick={() => { setAddMarket('crypto'); setAddQ('') }}
              >
                币安加密
              </button>
            </div>
            <input
              className="qt-input"
              style={{ width: '100%', marginBottom: 12 }}
              placeholder={addMarket === 'us' ? '搜索，例如 NVDA / 英伟达' : '搜索，例如 BTC / ETHUSDT'}
              value={addQ}
              onChange={(e) => setAddQ(e.target.value)}
              autoFocus
            />
            {addBusy ? <p className="qt-sub" style={{ margin: '0 0 8px' }}>正在添加…</p> : null}
            {addMsg ? (
              <p className={addMsg.startsWith('已添加') ? 'qt-up' : 'qt-down'} style={{ margin: '0 0 8px' }}>
                {addMsg}
              </p>
            ) : null}
            <div className="qt-modal-list">
              {addHits.map((hit) => (
                <button
                  key={`${hit.market}-${hit.symbol}`}
                  type="button"
                  className="qt-modal-item"
                  disabled={addBusy}
                  onClick={() => onAdd(hit)}
                >
                  <span>
                    <strong>{hit.code}</strong>
                    {' · '}
                    {hit.name}
                    {' '}
                    <span className={`qt-pill ${hit.market === 'us' ? 'qt-pill-us' : 'qt-pill-crypto'}`}>
                      {hit.market === 'us' ? '美股' : '加密'}
                    </span>
                  </span>
                  <span style={{ color: 'var(--qt-muted)' }}>{hit.symbol}</span>
                </button>
              ))}
              {!addHits.length ? <p className="qt-empty">无匹配标的</p> : null}
            </div>
          </div>
        </div>
      ) : null}

      {cfgOpen ? (
        <div className="qt-modal-mask" role="dialog" aria-modal="true">
          <div className="qt-modal">
            <div className="qt-modal-head">
              <strong>
                配置面板 · 第 {cfgStep} / 2 步
                <span style={{ color: 'var(--qt-muted)', fontWeight: 500, marginLeft: 8 }}>
                  {cfgSymbols.map((s) => s.replace(/USDT$/, '')).join('、')}
                </span>
              </strong>
              <button type="button" className="portal-btn portal-btn-ghost" onClick={() => setCfgOpen(false)}>关闭</button>
            </div>

            {cfgStep === 1 ? (
              <div>
                <p className="qt-sub" style={{ marginTop: 0 }}>第一步：选定需要「站上」的强弱条件（可多选）</p>
                <label className="qt-check">
                  <input
                    type="checkbox"
                    checked={!!cfg.require_short}
                    onChange={(e) => setCfg((prev) => ({ ...prev, require_short: e.target.checked }))}
                  />
                  短强 · 站上 MA5
                </label>
                <label className="qt-check">
                  <input
                    type="checkbox"
                    checked={!!cfg.require_mid}
                    onChange={(e) => setCfg((prev) => ({ ...prev, require_mid: e.target.checked }))}
                  />
                  中强 · 站上 MA30
                </label>
                <label className="qt-check">
                  <input
                    type="checkbox"
                    checked={!!cfg.require_long}
                    onChange={(e) => setCfg((prev) => ({ ...prev, require_long: e.target.checked }))}
                  />
                  长强 · 站上 MA200
                </label>
                <div className="qt-modal-actions">
                  <button type="button" className="portal-btn portal-btn-primary" onClick={() => setCfgStep(2)}>
                    下一步
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <p className="qt-sub" style={{ marginTop: 0 }}>
                  第二步：策略名称、K 线级别、仓位大小（保存后须连接交易所，webhook 才会自动下单）
                </p>
                <label className="qt-field">
                  策略名称
                  <input
                    className="qt-input"
                    value={cfg.strategy_name}
                    onChange={(e) => setCfg((prev) => ({ ...prev, strategy_name: e.target.value }))}
                    placeholder="例如 趋势跟随"
                  />
                </label>
                <label className="qt-field">
                  K 线级别
                  <select
                    className="qt-select"
                    value={cfg.timeframe}
                    onChange={(e) => setCfg((prev) => ({ ...prev, timeframe: e.target.value }))}
                  >
                    <option value="30m">30m</option>
                    <option value="1h">1h</option>
                    <option value="2h">2h</option>
                    <option value="4h">4h</option>
                    <option value="1d">1d</option>
                  </select>
                </label>
                <label className="qt-field">
                  仓位模式
                  <select
                    className="qt-select"
                    value={cfg.size_mode}
                    onChange={(e) => setCfg((prev) => ({ ...prev, size_mode: e.target.value }))}
                  >
                    <option value="percent">仓位比例 (%)</option>
                    <option value="fixed">固定金额 (USDT)</option>
                  </select>
                </label>
                <label className="qt-field">
                  {cfg.size_mode === 'fixed' ? '固定金额' : '仓位比例'}
                  <input
                    className="qt-input"
                    value={cfg.size_value}
                    onChange={(e) => setCfg((prev) => ({ ...prev, size_value: e.target.value }))}
                    placeholder={cfg.size_mode === 'fixed' ? '例如 500' : '例如 10'}
                  />
                </label>
                <label className="qt-field">
                  止盈 (%)
                  <input
                    className="qt-input"
                    value={cfg.take_profit}
                    onChange={(e) => setCfg((prev) => ({ ...prev, take_profit: e.target.value }))}
                    placeholder="例如 5，留空表示未设置"
                  />
                </label>
                <label className="qt-field">
                  止损 (%)
                  <input
                    className="qt-input"
                    value={cfg.stop_loss}
                    onChange={(e) => setCfg((prev) => ({ ...prev, stop_loss: e.target.value }))}
                    placeholder="例如 2，留空表示未设置"
                  />
                </label>
                {cfgMsg ? <p className="qt-down">{cfgMsg}</p> : null}
                <div className="qt-modal-actions">
                  <button type="button" className="portal-btn portal-btn-ghost" onClick={() => setCfgStep(1)}>
                    返回上一步
                  </button>
                  <button type="button" className="portal-btn portal-btn-primary" disabled={cfgBusy} onClick={onSaveConfig}>
                    {cfgBusy ? '保存中…' : '保存配置'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : null}

      <PortalConnectModal
        open={connectOpen}
        symbols={connectSymbols}
        onClose={() => setConnectOpen(false)}
        onDone={() => load({ force: false })}
      />
    </div>
  )
}

export default PortalWatchlist
