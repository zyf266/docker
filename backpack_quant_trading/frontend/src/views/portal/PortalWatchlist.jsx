import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  addWatchSymbol,
  getExchangeBindings,
  getWatchlist,
  removeWatchSymbol,
  saveWatchConfig,
  searchBinanceSymbols,
} from '../../api/portal'
import { isAdminRole, readStoredUser } from '../../utils/authRole'
import PortalConnectModal from './PortalConnectModal'

/** 交易配置：允许开仓的 Pine 四态（多选 OR） */
const PINE_STATUS_OPTIONS = [
  { value: '趋势', label: '趋势' },
  { value: '反弹', label: '反弹' },
  { value: '牛市空头', label: '牛市空头' },
  { value: '熊市空头', label: '熊市空头' },
]

const platLabel = (id) => {
  if (id === 'hyperliquid') return 'Hyperliquid'
  if (id === 'okx') return '欧意 OKX'
  if (id === 'binance') return '币安'
  return id || '—'
}

const parseExchanges = (raw) => {
  if (Array.isArray(raw)) return raw.map((x) => String(x || '').toLowerCase()).filter(Boolean)
  return String(raw || '')
    .split(/[,;]/)
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean)
}

const Strength = ({ on, label }) => (
  <span className={`qt-pill ${on ? (label === '长强' ? 'qt-pill-long' : 'qt-pill-crypto') : 'qt-pill-off'}`}>
    {on ? label : '未站上'}
  </span>
)

const SignalCell = ({ value }) => {
  if (value === '站上' || value === '金叉') return <span className="qt-up">{value === '金叉' ? '金叉' : '站上'}</span>
  if (value === '未站上' || value === '死叉') return <span className="qt-down">{value === '死叉' ? '死叉' : '未站上'}</span>
  return <span style={{ color: 'var(--qt-muted)' }}>{value || '—'}</span>
}

const normalizeAllowedStatuses = (raw) => {
  let list = raw
  if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
    list = raw.allowed_statuses || raw.allowed || []
  }
  if (typeof list === 'string') {
    list = list.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
  }
  if (!Array.isArray(list)) return []
  const out = []
  for (const x of list) {
    const s = String(x || '').trim()
    if (s === '空头') {
      ;['牛市空头', '熊市空头'].forEach((lab) => {
        if (!out.includes(lab)) out.push(lab)
      })
      continue
    }
    if (PINE_STATUS_OPTIONS.some((o) => o.value === s) && !out.includes(s)) out.push(s)
  }
  return out
}

/** 状态列排序：趋势 > 反弹 > 牛市空头 > 熊市空头 > — */
const statusSortRank = (row) => {
  const label = row.status_label || row.config?.status_mode || ''
  if (label === '趋势') return 0
  if (label === '反弹') return 1
  if (label === '牛市空头' || label === '空头') return 2
  if (label === '熊市空头') return 3
  return 4
}

/** 趋势绿 / 反弹黄 / 空头红 */
const statusColor = (label) => {
  if (label === '趋势') return '#4ade80'
  if (label === '反弹') return '#facc15'
  if (label === '熊市空头' || label === '牛市空头' || label === '空头') return '#f87171'
  return 'var(--qt-muted)'
}

const StatusCell = ({ row, onConnect }) => {
  const st = (row?.config?.status || row?.status || '').toLowerCase()
  const plats = parseExchanges(row?.config?.exchange || row?.exchange || '')
  const exTip = plats
    .map((ex) => (ex === 'hyperliquid' ? 'Hype' : ex === 'okx' ? 'OKX' : ex))
    .join('+')
  const pineLabel = row?.status_label || ''
  // Pine 三状态：有标签即展示（绿/黄/红）
  if (pineLabel) {
    return (
      <span
        className="qt-pill"
        style={{
          color: statusColor(pineLabel),
          borderColor: statusColor(pineLabel),
        }}
        title={`TV三状态 · ${pineLabel}`}
      >
        <span className="qt-status-dot" style={{ background: statusColor(pineLabel) }} />
        {pineLabel}
        {exTip ? ` · ${exTip}` : ''}
      </span>
    )
  }
  if (st === 'connected') {
    if (!onConnect) {
      return (
        <span className="qt-pill qt-pill-live">
          <span className="qt-status-dot" />
          connected
          {exTip ? ` · ${exTip}` : ''}
        </span>
      )
    }
    return (
      <button type="button" className="qt-status-btn" onClick={() => onConnect?.(row)} title="已连接，可重新绑定">
        <span className="qt-pill qt-pill-live">
          <span className="qt-status-dot" />
          connected
          {exTip ? ` · ${exTip}` : ''}
        </span>
      </button>
    )
  }
  if (st === 'living' || st === 'watching') {
    if (!onConnect) {
      return (
        <span className="qt-pill qt-pill-live">
          <span className="qt-status-dot" />
          {st === 'watching' ? 'watching' : 'living'}
        </span>
      )
    }
    return (
      <button type="button" className="qt-status-btn" onClick={() => onConnect?.(row)} title="点击立即连接交易所">
        <span className="qt-pill qt-pill-live">
          <span className="qt-status-dot" />
          {st === 'watching' ? 'watching' : 'living'}
        </span>
      </button>
    )
  }
  return <span style={{ color: 'var(--qt-muted)' }}>—</span>
}

const emptyConfig = {
  require_short: false,
  require_mid: false,
  require_long: false,
  require_2h: false,
  require_4h: false,
  status_mode: '趋势',
  allowed_statuses: ['趋势'],
  strategy_name: '',
  timeframe: '2h',
  size_mode: 'percent',
  size_value: '10',
  leverage: 5,
  take_profit: '',
  stop_loss: '',
  exchanges: [],
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

const PortalWatchlist = ({ embedded = false }) => {
  const [items, setItems] = useState(() => _watchlistSnap?.items || [])
  const [summary, setSummary] = useState(() => _watchlistSnap?.summary || { short: 0, mid: 0, long: 0 })
  const [loading, setLoading] = useState(!_watchlistSnap)
  const [error, setError] = useState('')
  const [marketFilter, setMarketFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
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
  /** status=批量状态 | trade=批量/单币交易 */
  const [cfgMode, setCfgMode] = useState('status')
  const [cfgMarket, setCfgMarket] = useState('crypto')
  const [cfgSymbols, setCfgSymbols] = useState([])
  const [cfg, setCfg] = useState(emptyConfig)
  const [cfgBusy, setCfgBusy] = useState(false)
  const [cfgMsg, setCfgMsg] = useState('')
  const [bindings, setBindings] = useState([])

  const [connectOpen, setConnectOpen] = useState(false)
  const [connectSymbols, setConnectSymbols] = useState([])
  const isAdmin = useMemo(() => isAdminRole(readStoredUser()?.role), [])

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
      // 两阶段：先秒开库表（metrics=0）；有标的再后台补指标。空库不再打 metrics，避免无谓超时
      if (!_watchlistSnap) setLoading(true)
      try {
        const bare = await getWatchlist(0, 0)
        if (cancelled) return
        applyList(bare)
        setLoading(false)
        const n = (bare?.items || []).length
        if (n === 0) {
          setMetricsLoading(false)
          return
        }
        setMetricsLoading(true)
        try {
          const withMetrics = await getWatchlist(1, 0)
          if (!cancelled) {
            applyList(withMetrics)
            setError('')
          }
        } catch (e) {
          // 列表已出：指标失败只提示，不当整页失败
          if (!cancelled) {
            const msg = e?.response?.data?.detail || e?.message || '指标加载失败'
            setError(/timeout/i.test(String(msg))
              ? '指标加载超时（后端可能正忙于拉余额/K线），可稍后点「刷新指标」'
              : msg)
          }
        } finally {
          if (!cancelled) setMetricsLoading(false)
        }
      } catch (e) {
        if (!cancelled) {
          setError(e?.response?.data?.detail || e?.message || '加载失败')
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
    const rows = (items || []).filter((row) => {
      if (marketFilter === 'crypto' && row.market === 'us') return false
      if (marketFilter === 'us' && row.market !== 'us') return false
      if (statusFilter !== 'all') {
        const lab = row.status_label || ''
        if (lab !== statusFilter) return false
      }
      if (!q) return true
      return `${row.code || ''} ${row.symbol || ''} ${row.name || ''}`.toUpperCase().includes(q)
    })
    return rows.sort((a, b) => {
      const d = statusSortRank(a) - statusSortRank(b)
      if (d !== 0) return d
      return String(a.code || a.symbol || '').localeCompare(String(b.code || b.symbol || ''))
    })
  }, [items, marketFilter, statusFilter, query])

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

  const loadBindings = useCallback(async () => {
    try {
      const res = await getExchangeBindings()
      const items = res?.items || []
      setBindings(items)
      return items
    } catch {
      setBindings([])
      return []
    }
  }, [])

  const buildCfgFromSeed = (seed, boundItems) => {
    const seedEx = parseExchanges(seed?.exchange || seed?.exchanges || '')
    const boundIds = (boundItems || []).map((b) => String(b.platform || '').toLowerCase()).filter(Boolean)
    let exchanges = seedEx.filter((p) => boundIds.includes(p))
    if (!exchanges.length && boundIds.length === 1) exchanges = [...boundIds]
    const allowed = normalizeAllowedStatuses(
      seed?.allowed_statuses ?? seed?.status_profiles,
    )
    return {
      ...emptyConfig,
      ...(seed || {}),
      require_short: false,
      require_mid: false,
      require_long: false,
      require_2h: false,
      require_4h: false,
      status_mode: '趋势',
      allowed_statuses: allowed.length ? allowed : ['趋势'],
      strategy_name: '',
      timeframe: seed?.timeframe || '2h',
      size_mode: seed?.size_mode || 'percent',
      size_value: seed?.size_value || '10',
      leverage: Number(seed?.leverage) > 0 ? Number(seed.leverage) : 5,
      take_profit: seed?.take_profit || '',
      stop_loss: seed?.stop_loss || '',
      exchanges,
    }
  }

  const toggleAllowedStatus = (label) => {
    setCfg((prev) => {
      const cur = normalizeAllowedStatuses(prev.allowed_statuses)
      const next = cur.includes(label) ? cur.filter((x) => x !== label) : [...cur, label]
      return { ...prev, allowed_statuses: next }
    })
  }

  /** 批量交易配置（市场级） */
  const openTradeBatch = async () => {
    const mkt = marketFilter === 'us' ? 'us' : 'crypto'
    const seedRow = (items || []).find((r) => (mkt === 'us' ? r.market === 'us' : r.market !== 'us') && r.config)
    const bound = await loadBindings()
    setCfgMode('trade')
    setCfgMarket(mkt)
    setCfgSymbols([])
    setCfg(buildCfgFromSeed(seedRow?.config, bound))
    setCfgStep(2)
    setCfgMsg('')
    setCfgOpen(true)
  }

  /** 单币种：仅交易配置 */
  const openTradeSingle = async (row) => {
    if (!row?.symbol) return
    const bound = await loadBindings()
    setCfgMode('trade')
    setCfgMarket(row.market === 'us' ? 'us' : 'crypto')
    setCfgSymbols([row.symbol])
    setCfg(buildCfgFromSeed(row.config, bound))
    setCfgStep(2)
    setCfgMsg('')
    setCfgOpen(true)
  }

  const toggleExchange = (plat) => {
    setCfg((prev) => {
      const cur = parseExchanges(prev.exchanges)
      const next = cur.includes(plat) ? cur.filter((p) => p !== plat) : [...cur, plat]
      return { ...prev, exchanges: next }
    })
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

  const onSaveTradeConfig = async () => {
    const allowed = normalizeAllowedStatuses(cfg.allowed_statuses)
    if (!allowed.length) {
      setCfgMsg('请至少勾选一个允许开仓的状态')
      return
    }
    const boundIds = bindings.map((b) => String(b.platform || '').toLowerCase()).filter(Boolean)
    let selectedEx = parseExchanges(cfg.exchanges).filter((p) => boundIds.includes(p))
    if (boundIds.length === 1 && !selectedEx.length) {
      selectedEx = [...boundIds]
    }
    if (boundIds.length > 0 && selectedEx.length === 0) {
      setCfgMsg('请至少选择一个已连接的下单平台')
      return
    }
    const isBatch = !cfgSymbols.length
    setCfgBusy(true)
    setCfgMsg('')
    try {
      await saveWatchConfig({
        symbols: cfgSymbols,
        market: isBatch ? cfgMarket : '',
        config_kind: 'trade',
        require_short: false,
        require_mid: false,
        require_long: false,
        require_2h: false,
        require_4h: false,
        status_mode: '趋势',
        allowed_statuses: allowed,
        status_profiles: { allowed_statuses: allowed },
        strategy_name: '',
        timeframe: cfg.timeframe,
        size_mode: cfg.size_mode,
        size_value: cfg.size_value,
        leverage: Number(cfg.leverage) > 0 ? Number(cfg.leverage) : 5,
        take_profit: cfg.take_profit,
        stop_loss: cfg.stop_loss,
        exchanges: selectedEx,
        gates_only: false,
      })
      setCfgOpen(false)
      await load({ force: true })
      if (!boundIds.length || !selectedEx.length) {
        setConnectSymbols(cfgSymbols.length ? [...cfgSymbols] : [])
        setConnectOpen(true)
      }
    } catch (e) {
      setCfgMsg(e?.response?.data?.detail || e?.message || '保存失败')
    } finally {
      setCfgBusy(false)
    }
  }

  return (
    <div id="portal-watchlist">
      {embedded ? (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
          <strong style={{ fontSize: 16 }}>标的观察库</strong>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {isAdmin ? (
              <button type="button" className="portal-btn portal-btn-primary" onClick={() => setAddOpen(true)}>
                + 添加标的
              </button>
            ) : null}
          </div>
        </div>
      ) : (
        <div className="qt-hero">
          <div>
            <p className="qt-kicker">WATCHLIST</p>
            <h1 className="qt-title">标的观察库 · 概览</h1>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {isAdmin ? (
              <button type="button" className="portal-btn portal-btn-primary" onClick={() => setAddOpen(true)}>
                + 添加标的
              </button>
            ) : null}
          </div>
        </div>
      )}

      <section className="qt-card" style={{ marginBottom: embedded ? 0 : 16 }}>
        <div className="qt-toolbar">
          <select className="qt-select" value={marketFilter} onChange={(e) => setMarketFilter(e.target.value)}>
            <option value="all">市场: 全部</option>
            <option value="crypto">加密</option>
            <option value="us">美股</option>
          </select>
          <select className="qt-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="all">状态: 全部</option>
            {PINE_STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
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
          {isAdmin ? (
            <button
              type="button"
              className="portal-btn portal-btn-primary"
              onClick={openTradeBatch}
            >
              交易配置
            </button>
          ) : null}
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
                <th>2h状态</th>
                <th>4h状态</th>
                <th>中强 (MA30)</th>
                <th>长强 (MA200)</th>
                <th>状态</th>
                <th>配置</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={11} className="qt-empty">
                    {loading
                      ? '加载中…'
                      : (isAdmin
                        ? '暂无标的，点击「添加标的」选择美股或币安交易对'
                        : '暂无标的')}
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
                    <td><Strength on={row.mid_on} label="中强" /></td>
                    <td><Strength on={row.long_on} label="长强" /></td>
                    <td><StatusCell row={row} onConnect={isAdmin ? openConnect : undefined} /></td>
                    <td>
                      {isAdmin ? (
                        <>
                          <button
                            type="button"
                            className="portal-btn portal-btn-ghost"
                            style={{ padding: '4px 10px' }}
                            onClick={() => openTradeSingle(row)}
                          >
                            交易配置
                          </button>
                          <button
                            type="button"
                            className="portal-btn portal-btn-ghost"
                            style={{ padding: '4px 10px', marginLeft: 6 }}
                            onClick={() => onRemove(row.symbol)}
                          >
                            移除
                          </button>
                        </>
                      ) : (
                        <span style={{ color: 'var(--qt-muted)' }}>—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

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
                {cfgMode === 'status' ? '状态配置（批量）' : (cfgSymbols.length ? '交易配置' : '交易配置（批量）')}
                <span style={{ color: 'var(--qt-muted)', fontWeight: 500, marginLeft: 8 }}>
                  {cfgSymbols.length
                    ? cfgSymbols.map((s) => s.replace(/USDT$/, '')).join('、')
                    : (cfgMarket === 'us' ? '美股市场' : '加密市场')}
                </span>
              </strong>
              <button type="button" className="portal-btn portal-btn-ghost" onClick={() => setCfgOpen(false)}>关闭</button>
            </div>

            {!cfgSymbols.length ? (
              <div className="qt-toolbar" style={{ marginBottom: 12 }}>
                <button
                  type="button"
                  className={`portal-btn ${cfgMarket === 'crypto' ? 'portal-btn-primary' : 'portal-btn-ghost'}`}
                  onClick={() => setCfgMarket('crypto')}
                >
                  加密
                </button>
                <button
                  type="button"
                  className={`portal-btn ${cfgMarket === 'us' ? 'portal-btn-primary' : 'portal-btn-ghost'}`}
                  onClick={() => setCfgMarket('us')}
                >
                  美股
                </button>
                <span className="qt-sub" style={{ margin: 0, fontSize: 12 }}>
                  保存后对该市场全部标的生效；新加标的默认继承
                </span>
              </div>
            ) : null}

            {cfgMode === 'status' || cfgStep === 1 ? (
              <div>
                <p className="qt-sub">状态配置已改为交易配置内的「允许开仓状态」多选，请关闭后点「交易配置」。</p>
                <div className="qt-modal-actions">
                  <button type="button" className="portal-btn portal-btn-ghost" onClick={() => setCfgOpen(false)}>关闭</button>
                </div>
              </div>
            ) : (
              <div>
                <div className="qt-field">
                  <span>允许开仓状态（可多选，OR：命中任一即可）</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 6 }}>
                    {PINE_STATUS_OPTIONS.map((opt) => {
                      const checked = normalizeAllowedStatuses(cfg.allowed_statuses).includes(opt.value)
                      return (
                        <label key={opt.value} className="qt-check" style={{ margin: 0 }}>
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleAllowedStatus(opt.value)}
                          />
                          {opt.label}
                        </label>
                      )
                    })}
                  </div>
                  <span className="qt-sub" style={{ margin: '6px 0 0', fontSize: 12 }}>
                    信号进线后，标的当前状态须落在勾选项内才开仓；平仓不受此限制。
                  </span>
                </div>
                <div className="qt-field">
                  <span>下单平台（可多选）</span>
                  {bindings.length ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {bindings.map((b) => {
                        const id = String(b.platform || '').toLowerCase()
                        const checked = parseExchanges(cfg.exchanges).includes(id)
                        return (
                          <label key={id || b.id} className="qt-check" style={{ margin: 0 }}>
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleExchange(id)}
                            />
                            {platLabel(id)}
                            {b.demo ? ' · 模拟盘' : ''}
                            {b.label ? ` · ${b.label}` : ''}
                          </label>
                        )
                      })}
                    </div>
                  ) : (
                    <p className="qt-sub" style={{ margin: 0, fontSize: 13 }}>
                      尚未连接交易所。点「保存配置」后将弹出连接窗口。
                    </p>
                  )}
                </div>
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
                  杠杆 (x)
                  <input
                    className="qt-input"
                    type="number"
                    min={1}
                    max={125}
                    step={1}
                    value={cfg.leverage}
                    onChange={(e) => setCfg((prev) => ({ ...prev, leverage: e.target.value }))}
                    placeholder="默认 5"
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
                  <button type="button" className="portal-btn portal-btn-primary" disabled={cfgBusy} onClick={onSaveTradeConfig}>
                    {cfgBusy ? '保存中…' : '保存交易配置'}
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
        onDone={async () => {
          await loadBindings()
          await load({ force: false })
        }}
      />
    </div>
  )
}

export default PortalWatchlist
