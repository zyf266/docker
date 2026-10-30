import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  addWatchSymbol,
  getExchangeBindings,
  getWatchlist,
  removeWatchSymbol,
  saveWatchConfig,
  searchBinanceSymbols,
} from '../../api/portal'
import PortalConnectModal from './PortalConnectModal'

const STRATEGY_OPTIONS = [
  { value: '自适应做多策略', hint: 'buy 开多 · sell 平多' },
  { value: '自适应做空策略', hint: 'sell 开空 · buy 平空' },
  { value: '自适应平仓策略', hint: '多仓 sell 平 · 空仓 buy 平' },
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

const STATUS_MODE_OPTIONS = [
  { value: '趋势', label: '趋势' },
  { value: '反弹', label: '反弹' },
  { value: '空头', label: '空头' },
]

const emptyStatusProfile = () => ({
  require_2h: false,
  require_4h: false,
  require_mid: false,
  require_long: false,
})

const emptyStatusProfiles = () => ({
  趋势: { ...emptyStatusProfile(), require_2h: true, require_4h: true, require_mid: true },
  反弹: { ...emptyStatusProfile(), require_2h: true },
  空头: { ...emptyStatusProfile(), require_long: true },
})

const normalizeProfiles = (raw) => {
  const base = emptyStatusProfiles()
  if (!raw || typeof raw !== 'object') return base
  for (const mode of ['趋势', '反弹', '空头']) {
    const src = raw[mode] || {}
    base[mode] = {
      require_2h: !!src.require_2h,
      require_4h: !!src.require_4h,
      require_mid: !!src.require_mid,
      require_long: !!src.require_long,
    }
  }
  return base
}

const profilesConfigured = (profiles) =>
  ['趋势', '反弹', '空头'].some((m) => {
    const g = profiles?.[m] || {}
    return g.require_2h || g.require_4h || g.require_mid || g.require_long
  })

/** 状态列排序：趋势 > 反弹 > 空头 > — */
const statusSortRank = (row) => {
  if (!row?.tradable) return 3
  const label = row.status_label || row.config?.status_mode || ''
  if (label === '趋势') return 0
  if (label === '反弹') return 1
  if (label === '空头') return 2
  return 3
}

const StatusCell = ({ row, onConnect }) => {
  const st = (row?.config?.status || row?.status || '').toLowerCase()
  const plats = parseExchanges(row?.config?.exchange || row?.exchange || '')
  const exTip = plats
    .map((ex) => (ex === 'hyperliquid' ? 'Hype' : ex === 'okx' ? 'OKX' : ex))
    .join('+')
  const missing = row?.tradable_missing || []
  // 已配置站上条件：全部满足 → 显示空头/反弹/趋势；否则 —
  if (row?.gates_configured) {
    if (row?.tradable) {
      const label = row.status_label || row.config?.status_mode || '趋势'
      return (
        <span
          className="qt-pill qt-pill-live"
          title={missing.length ? '' : `条件均已满足 · ${label}`}
        >
          <span className="qt-status-dot" />
          {label}
          {exTip ? ` · ${exTip}` : ''}
        </span>
      )
    }
    return (
      <span
        style={{ color: 'var(--qt-muted)' }}
        title={missing.length ? `未满足: ${missing.join('、')}` : '条件未满足'}
      >
        —
      </span>
    )
  }
  if (st === 'connected') {
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
  require_mid: true,
  require_long: false,
  require_2h: true,
  require_4h: true,
  status_mode: '趋势',
  status_profiles: emptyStatusProfiles(),
  strategy_name: STRATEGY_OPTIONS[0].value,
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
    const rows = (items || []).filter((row) => {
      if (marketFilter === 'crypto' && row.market === 'us') return false
      if (marketFilter === 'us' && row.market !== 'us') return false
      if (strengthFilter === 'mid' && !row.mid_on) return false
      if (strengthFilter === 'long' && !row.long_on) return false
      if (!q) return true
      return `${row.code || ''} ${row.symbol || ''} ${row.name || ''}`.toUpperCase().includes(q)
    })
    return rows.sort((a, b) => {
      const d = statusSortRank(a) - statusSortRank(b)
      if (d !== 0) return d
      return String(a.code || a.symbol || '').localeCompare(String(b.code || b.symbol || ''))
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
    const seedStrategy = (seed?.strategy_name || '').trim()
    const strategyOk = STRATEGY_OPTIONS.some((o) => o.value === seedStrategy)
    const seedMode = STATUS_MODE_OPTIONS.some((o) => o.value === seed?.status_mode)
      ? seed.status_mode
      : '趋势'
    let profiles = normalizeProfiles(seed?.status_profiles)
    if (!profilesConfigured(profiles) && (seed?.require_2h || seed?.require_4h || seed?.require_mid || seed?.require_long)) {
      profiles = normalizeProfiles({
        [seedMode]: {
          require_2h: !!seed.require_2h,
          require_4h: !!seed.require_4h,
          require_mid: !!seed.require_mid,
          require_long: !!seed.require_long,
        },
      })
    }
    return {
      ...emptyConfig,
      ...(seed || {}),
      require_short: false,
      require_mid: seed?.require_mid ?? true,
      require_long: seed?.require_long ?? false,
      require_2h: seed?.require_2h ?? true,
      require_4h: seed?.require_4h ?? true,
      status_mode: seedMode,
      status_profiles: profiles,
      strategy_name: strategyOk ? seedStrategy : STRATEGY_OPTIONS[0].value,
      timeframe: seed?.timeframe || '2h',
      size_mode: seed?.size_mode || 'percent',
      size_value: seed?.size_value || '10',
      leverage: Number(seed?.leverage) > 0 ? Number(seed.leverage) : 5,
      take_profit: seed?.take_profit || '',
      stop_loss: seed?.stop_loss || '',
      exchanges,
    }
  }

  /** 批量状态配置（市场级，新标的会继承） */
  const openStatusBatch = async () => {
    const mkt = marketFilter === 'us' ? 'us' : 'crypto'
    const seedRow = (items || []).find((r) => (mkt === 'us' ? r.market === 'us' : r.market !== 'us') && r.config)
    const bound = await loadBindings()
    setCfgMode('status')
    setCfgMarket(mkt)
    setCfgSymbols([])
    setCfg(buildCfgFromSeed(seedRow?.config, bound))
    setCfgStep(1)
    setCfgMsg('')
    setCfgOpen(true)
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

  const onSaveStatusBatch = async () => {
    const profiles = normalizeProfiles(cfg.status_profiles)
    if (!profilesConfigured(profiles)) {
      setCfgMsg('请至少为「趋势 / 反弹 / 空头」中的一套勾选站上条件')
      return
    }
    setCfgBusy(true)
    setCfgMsg('')
    try {
      await saveWatchConfig({
        symbols: [],
        market: cfgMarket,
        config_kind: 'status',
        require_short: false,
        require_mid: !!profiles[cfg.status_mode]?.require_mid,
        require_long: !!profiles[cfg.status_mode]?.require_long,
        require_2h: !!profiles[cfg.status_mode]?.require_2h,
        require_4h: !!profiles[cfg.status_mode]?.require_4h,
        status_mode: cfg.status_mode || '趋势',
        status_profiles: profiles,
        gates_only: true,
      })
      setCfgOpen(false)
      await load({ force: true })
    } catch (e) {
      setCfgMsg(e?.response?.data?.detail || e?.message || '保存失败')
    } finally {
      setCfgBusy(false)
    }
  }

  const setProfileGate = (key, checked) => {
    const mode = cfg.status_mode || '趋势'
    setCfg((prev) => ({
      ...prev,
      status_profiles: {
        ...normalizeProfiles(prev.status_profiles),
        [mode]: {
          ...normalizeProfiles(prev.status_profiles)[mode],
          [key]: checked,
        },
      },
    }))
  }

  const onSaveTradeConfig = async () => {
    if (!STRATEGY_OPTIONS.some((o) => o.value === cfg.strategy_name)) {
      setCfgMsg('请选择策略名称')
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
        require_mid: !!cfg.require_mid,
        require_long: !!cfg.require_long,
        require_2h: !!cfg.require_2h,
        require_4h: !!cfg.require_4h,
        status_mode: cfg.status_mode || '趋势',
        strategy_name: cfg.strategy_name,
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
          <div>
            <strong style={{ fontSize: 16 }}>标的观察库</strong>
            <p className="qt-sub" style={{ margin: '4px 0 0' }}>
              配置策略与平台后，Webhook 自动跟单
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button type="button" className="portal-btn portal-btn-primary" onClick={() => setAddOpen(true)}>
              + 添加标的
            </button>
            <Link className="portal-btn portal-btn-cyan" to="/portal/ma-cards">多卡片均线</Link>
          </div>
        </div>
      ) : (
        <div className="qt-hero">
          <div>
            <p className="qt-kicker">WATCHLIST</p>
            <h1 className="qt-title">标的观察库 · 概览</h1>
            <p className="qt-sub">
              添加只写库、秒返回；指标默认读 Hyperliquid。勾选条件全部满足后，状态显示所选的空头/反弹/趋势，否则为 —。
              TradingView webhook（策略名+币种+周期一致）在条件满足且已连接时按仓位下单。
            </p>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button type="button" className="portal-btn portal-btn-primary" onClick={() => setAddOpen(true)}>
              + 添加标的
            </button>
            <Link className="portal-btn portal-btn-cyan" to="/portal/ma-cards">多卡片均线视图</Link>
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
          <select className="qt-select" value={strengthFilter} onChange={(e) => setStrengthFilter(e.target.value)}>
            <option value="all">强弱: 全部</option>
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
            onClick={openStatusBatch}
          >
            状态配置
          </button>
          <button
            type="button"
            className="portal-btn portal-btn-primary"
            onClick={openTradeBatch}
          >
            交易配置
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
                    <td><Strength on={row.mid_on} label="中强" /></td>
                    <td><Strength on={row.long_on} label="长强" /></td>
                    <td><StatusCell row={row} onConnect={openConnect} /></td>
                    <td>
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
                  保存后对该市场全部标的生效；新加标的默认继承状态配置
                </span>
              </div>
            ) : null}

            {cfgMode === 'status' || cfgStep === 1 ? (
              <div>
                <p className="qt-sub" style={{ marginTop: 0 }}>
                  趋势 / 反弹 / 空头是三套独立配置：点下方标签切换，再勾选该状态下的「站上」条件。判定优先级：趋势 → 反弹 → 空头；都不满足显示 —。
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
                  {STATUS_MODE_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      className={`portal-btn ${cfg.status_mode === opt.value ? 'portal-btn-primary' : 'portal-btn-ghost'}`}
                      onClick={() => setCfg((prev) => ({ ...prev, status_mode: opt.value }))}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
                <p className="qt-sub" style={{ margin: '0 0 8px' }}>
                  正在编辑「{cfg.status_mode || '趋势'}」的站上条件（可多选）
                </p>
                {(() => {
                  const g = normalizeProfiles(cfg.status_profiles)[cfg.status_mode || '趋势'] || emptyStatusProfile()
                  return (
                    <>
                      <label className="qt-check">
                        <input
                          type="checkbox"
                          checked={!!g.require_2h}
                          onChange={(e) => setProfileGate('require_2h', e.target.checked)}
                        />
                        2h状态 · 2H收盘站上日线 WMA15
                      </label>
                      <label className="qt-check">
                        <input
                          type="checkbox"
                          checked={!!g.require_4h}
                          onChange={(e) => setProfileGate('require_4h', e.target.checked)}
                        />
                        4h状态 · 4H收盘站上日线 WMA15
                      </label>
                      <label className="qt-check">
                        <input
                          type="checkbox"
                          checked={!!g.require_mid}
                          onChange={(e) => setProfileGate('require_mid', e.target.checked)}
                        />
                        中强 · 日线站上 MA30
                      </label>
                      <label className="qt-check">
                        <input
                          type="checkbox"
                          checked={!!g.require_long}
                          onChange={(e) => setProfileGate('require_long', e.target.checked)}
                        />
                        长强 · 站上 MA200
                      </label>
                    </>
                  )
                })()}
                {cfgMsg ? <p className="qt-sub" style={{ marginTop: 8 }}>{cfgMsg}</p> : null}
                <div className="qt-modal-actions" style={{ gap: 8 }}>
                  <button
                    type="button"
                    className="portal-btn portal-btn-primary"
                    disabled={cfgBusy}
                    onClick={onSaveStatusBatch}
                  >
                    {cfgBusy ? '保存中…' : '保存三套状态配置'}
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <p className="qt-sub" style={{ marginTop: 0 }}>
                  策略、下单平台、K 线与仓位（TradingView 策略名须一致）
                </p>
                <label className="qt-field">
                  策略名称
                  <select
                    className="qt-select"
                    value={cfg.strategy_name}
                    onChange={(e) => setCfg((prev) => ({ ...prev, strategy_name: e.target.value }))}
                  >
                    {STRATEGY_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.value}
                      </option>
                    ))}
                  </select>
                  <span className="qt-sub" style={{ margin: '4px 0 0', fontSize: 12 }}>
                    {STRATEGY_OPTIONS.find((o) => o.value === cfg.strategy_name)?.hint || ''}
                  </span>
                </label>
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
