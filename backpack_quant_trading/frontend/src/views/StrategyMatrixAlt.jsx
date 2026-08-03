import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { BarChart3, Activity, TrendingUp, Wallet, Percent, Search, Filter, Plus, LayoutGrid, List, ChevronDown } from 'lucide-react'
import { StatCard } from '../components/StatCard'
import { StrategyCardMatrix } from '../components/StrategyCardMatrix'
import { formatProfitFactor } from '../utils/formatProfitFactor'
import {
  getEthTrendOverview,
  getEthOnlyOverview,
  getAlphaEthOverview,
  getPaxgTrendOverview,
  getNas100TrendOverview,
  getSse510210Overview,
  getMnqDipOverview,
  getIntcOverview,
  getNvdaOverview,
  getMuOverview,
  getAShareOverview,
  getMatrixYearlyReturns,
} from '../api/strategy'

const A_SHARE_KEYS = ['300308', '603986', '688146', '002837', 'sse-510210']
const DEFAULT_USD_CNY = 7.25
const ORDER_STORAGE_KEY = 'strategy-matrix-card-order'
const STATUS_STORAGE_KEY = 'strategy-matrix-card-status'
const STATUS_OPTIONS = ['运行中', '已平仓', '测试中']

const strategies = [
  {
    key: 'nvda',
    to: '/strategies/us-momentum-nvda',
    icon: '🟢',
    title: '美股趋势追踪策略·NVDA',
    code: 'ML-USM',
    description: '聚焦 NVDA 等 AI 龙头，结合趋势强度、回撤过滤与风险预算，进行中短期动量轮动配置，捕捉 AI 主升浪与 Blackwell 出货周期。',
    status: '运行中',
    statusColor: 'bg-green-500 text-white',
    progress: 68,
    progressColor: '#3b82f6',
    riskIndex: '低风险',
    isRiskWarning: false,
  },
  {
    key: 'intc',
    to: '/strategies/us-momentum-intc',
    icon: '💠',
    title: '美股趋势追踪策略·INTC',
    code: 'ML-USM',
    description: '聚焦 INTC 等半导体核心标的，结合趋势强度、回撤过滤与风险预算，进行中短期动量轮动配置，捕捉半导体板块主升浪行情。',
    status: '运行中',
    statusColor: 'bg-green-500 text-white',
    progress: 68,
    progressColor: '#3b82f6',
    riskIndex: '中风险',
    isRiskWarning: true,
  },
  {
    key: 'mu',
    to: '/strategies/us-momentum-mu',
    icon: '💾',
    title: '美股趋势追踪策略·MU',
    code: 'ML-USM',
    description: '聚焦美光科技（MU）等存储龙头，动量轮动全仓复利，捕捉 AI 存储超级周期与 HBM 放量行情。',
    status: '运行中',
    statusColor: 'bg-green-500 text-white',
    progress: 68,
    progressColor: '#3b82f6',
    riskIndex: '中风险',
    isRiskWarning: true,
  },
  {
    key: '300308',
    to: '/strategies/a-share-300308',
    icon: '🏮',
    title: 'A股趋势追踪策略·中际旭创',
    code: 'ML-AMR',
    description: '聚焦中际旭创（300308）AI 光模块龙头，动量轮动全仓复利，捕捉算力基建主升浪。',
    status: '运行中',
    statusColor: 'bg-green-500 text-white',
    progress: 72,
    progressColor: '#10b981',
    riskIndex: '中风险',
    isRiskWarning: true,
  },
  {
    key: '603986',
    to: '/strategies/a-share-603986',
    icon: '🏮',
    title: 'A股趋势追踪策略·兆易创新',
    code: 'ML-AMR',
    description: '聚焦兆易创新（603986）存储龙头，动量轮动全仓复利，捕捉存储超级周期与业绩爆发。',
    status: '运行中',
    statusColor: 'bg-green-500 text-white',
    progress: 72,
    progressColor: '#10b981',
    riskIndex: '中风险',
    isRiskWarning: true,
  },
  {
    key: '688146',
    to: '/strategies/a-share-688146',
    icon: '🏮',
    title: 'A股趋势追踪策略·中船特气',
    code: 'ML-AMR',
    description: '聚焦中船特气（688146）半导体材料龙头，动量轮动全仓复利，捕捉涨价与产能扩张周期。',
    status: '运行中',
    statusColor: 'bg-green-500 text-white',
    progress: 72,
    progressColor: '#10b981',
    riskIndex: '高风险',
    isRiskWarning: true,
  },
  {
    key: '002837',
    to: '/strategies/a-share-002837',
    icon: '🏮',
    title: 'A股趋势追踪策略·英维克',
    code: 'ML-AMR',
    description: '聚焦英维克（002837）精密温控龙头，动量轮动全仓复利，捕捉 AI 液冷与储能温控景气周期。',
    status: '运行中',
    statusColor: 'bg-green-500 text-white',
    progress: 72,
    progressColor: '#10b981',
    riskIndex: '中风险',
    isRiskWarning: true,
  },
  {
    key: 'sse-510210',
    to: '/strategies/sse-510210',
    icon: '🇨🇳',
    title: '上证指数ETH抄底策略',
    code: 'ML-SSE',
    description: '寻找下跌行情的极致释放点介入进场，承接市场恐慌盘，通过量化系统做出理想状态下理性交易，在市场达成共识时平稳离场保证收益的稳定性。这个策略利用人性自身的缺点以及价值的回归完成金融标的物的重新定价。',
    status: '运行中',
    statusColor: 'bg-green-500 text-white',
    progress: 80,
    progressColor: '#3b82f6',
    riskIndex: '低风险',
    isRiskWarning: false,
  },
  {
    key: 'alpha-eth',
    to: '/strategies/alpha-eth',
    icon: 'Ξ',
    title: '【沐龙】长盈叁号·趋势追踪策略',
    code: 'ML-ALP',
    description: '以太坊（ETH）趋势追踪策略，中低风险。',
    status: '运行中',
    statusColor: 'bg-green-500 text-white',
    progress: 85,
    progressColor: '#3b82f6',
    riskIndex: '低风险',
    isRiskWarning: false,
  },
  {
    key: 'eth',
    to: '/strategies/eth-only',
    icon: '₿',
    title: '加密趋势追踪策略 · ETH',
    code: 'ML-DTS',
    description: '专注BTC/ETH/HYPE等主流加密货币，捕捉由波动率扩张驱动的中长期趋势，通过多周期协同过滤震荡噪音，追求稳健的风险调整后收益。',
    status: '运行中',
    statusColor: 'bg-green-500 text-white',
    progress: 98,
    progressColor: '#10b981',
    riskIndex: '低风险',
    isRiskWarning: false,
  },
  {
    key: 'hype',
    to: '/strategies/eth-trend',
    icon: '🔥',
    title: '加密趋势追踪策略 · HYPE',
    code: 'ML-DTS',
    description: '专注BTC/ETH/HYPE等新兴加密货币，捕捉由波动率扩张驱动的中长期趋势，通过多周期协同过滤震荡噪音，追求稳健的风险调整后收益。',
    status: '运行中',
    statusColor: 'bg-green-500 text-white',
    progress: 98,
    progressColor: '#10b981',
    riskIndex: '中风险',
    isRiskWarning: true,
  },
  {
    key: 'paxg',
    to: '/strategies/paxg-trend',
    icon: '🥇',
    title: '黄金波动率周期捕捉策略',
    code: 'ML-GVCS',
    description: '专注 XAU/USD 波动率周期，结合宏观趋势与关键支撑区间布局，坚持「低位等待、确定性介入」原则，利用波动率扩张捕捉中期行情。',
    status: '已平仓',
    statusColor: 'bg-gray-400 text-white',
    progress: 80,
    progressColor: '#9ca3af',
    riskIndex: '低风险',
    isRiskWarning: false,
  },
  {
    key: 'nas100',
    to: '/strategies/nas100-trend',
    icon: '📈',
    title: '纳指波动率增强策略',
    code: 'ML-NAS',
    description: '聚焦纳斯达克指数的中长期趋势行情，结合趋势强度与回撤过滤，围绕关键趋势段进行分批建仓与风控，强调顺势持有与风险控制。',
    status: '已平仓',
    statusColor: 'bg-gray-400 text-white',
    progress: 60,
    progressColor: '#3b82f6',
    riskIndex: '低风险',
    isRiskWarning: false,
  },
  {
    key: 'mnq-dip',
    to: '/strategies/mnq-dip',
    icon: '📉',
    title: '纳指抄底策略',
    code: 'ML-MNQ',
    description: '寻找下跌行情的极致释放点介入进场，承接市场恐慌盘，通过量化系统做出理想状态下理性交易，在市场达成共识时平稳离场保证收益的稳定性。这个策略利用人性自身的缺点以及价值的回归完成金融标的物的重新定价。',
    status: '运行中',
    statusColor: 'bg-green-500 text-white',
    progress: 75,
    progressColor: '#10b981',
    riskIndex: '中风险',
    isRiskWarning: true,
  },
]

const DEFAULT_ORDER = strategies.map((s) => s.key)
const STRATEGY_BY_KEY = Object.fromEntries(strategies.map((s) => [s.key, s]))
const FIXED_DRAWDOWN = {
  nvda: '--', intc: '--', mu: '--',
  '300308': '--', '603986': '--', '688146': '--', '002837': '--',
  'sse-510210': '--', 'alpha-eth': '-0.9%', eth: '-3.48%', hype: '-6.47%', paxg: '-1.44%', nas100: '-4%', 'mnq-dip': '--',
}
const FIXED_PROFIT_FACTOR = {
  nvda: '--', intc: '--', mu: '--',
  '300308': '--', '603986': '--', '688146': '--', '002837': '--',
  'sse-510210': '--', 'alpha-eth': '2.75', eth: '2.58', hype: '2.84', paxg: '2.25', nas100: '0.71', 'mnq-dip': '--',
}
const USE_LIVE_DRAWDOWN = new Set([
  'intc', 'nvda', 'mu', '300308', '603986', '688146', '002837', 'sse-510210', 'mnq-dip',
])

function loadCardOrder() {
  try {
    const raw = localStorage.getItem(ORDER_STORAGE_KEY)
    const saved = raw ? JSON.parse(raw) : null
    if (!Array.isArray(saved) || !saved.length) return [...DEFAULT_ORDER]
    const known = new Set(DEFAULT_ORDER)
    const ordered = saved.filter((k) => known.has(k))
    DEFAULT_ORDER.forEach((k) => {
      if (!ordered.includes(k)) ordered.push(k)
    })
    return ordered
  } catch {
    return [...DEFAULT_ORDER]
  }
}

function saveCardOrder(order) {
  try {
    localStorage.setItem(ORDER_STORAGE_KEY, JSON.stringify(order))
  } catch {
    /* ignore quota */
  }
}

function loadCardStatuses() {
  try {
    const raw = localStorage.getItem(STATUS_STORAGE_KEY)
    const saved = raw ? JSON.parse(raw) : null
    return saved && typeof saved === 'object' ? saved : {}
  } catch {
    return {}
  }
}

function saveCardStatuses(map) {
  try {
    localStorage.setItem(STATUS_STORAGE_KEY, JSON.stringify(map))
  } catch {
    /* ignore quota */
  }
}

function statusColorFor(status) {
  const s = String(status || '')
  if (s.includes('运行')) return 'bg-green-500 text-white'
  if (s.includes('测试')) return 'bg-blue-500 text-white'
  if (s.includes('已平仓')) return 'bg-gray-400 text-white'
  return 'bg-gray-100 text-gray-700'
}

/** 卡片左上角：展示当年收益（非年化）。 */
function resolveCardYearReturn(key, ov, yearlyReturns) {
  const cy = String(new Date().getFullYear())
  const yearBlock = yearlyReturns?.years?.[cy]
  const row = Array.isArray(yearBlock?.by_strategy)
    ? yearBlock.by_strategy.find((x) => x.key === key)
    : null
  if (row && row.return_pct != null && Number.isFinite(Number(row.return_pct))) {
    return { pct: Number(row.return_pct), label: '当年收益' }
  }
  if (ov?.total_return_pct != null && Number.isFinite(Number(ov.total_return_pct))) {
    return { pct: Number(ov.total_return_pct), label: '当年收益' }
  }
  return null
}

const formatYearPct = (v) => {
  if (v == null || !Number.isFinite(Number(v))) return '--'
  const n = Number(v)
  return `${n > 0 ? '+' : ''}${n.toFixed(2)}%`
}

export default function StrategyMatrixAlt() {
  const path = useLocation().pathname
  const [overviews, setOverviews] = useState({})
  const [yearlyReturns, setYearlyReturns] = useState(null)
  const [cardOrder, setCardOrder] = useState(loadCardOrder)
  const [statusMap, setStatusMap] = useState(loadCardStatuses)
  const [draggingKey, setDraggingKey] = useState(null)
  const [dragOverKey, setDragOverKey] = useState(null)
  const suppressClickRef = useRef(false)

  useEffect(() => {
    const reqs = [
      { key: 'alpha-eth', fn: getAlphaEthOverview },
      { key: 'eth', fn: getEthOnlyOverview },
      { key: 'hype', fn: getEthTrendOverview },
      { key: 'paxg', fn: getPaxgTrendOverview },
      { key: 'nas100', fn: getNas100TrendOverview },
      { key: 'sse-510210', fn: getSse510210Overview },
      { key: 'mnq-dip', fn: getMnqDipOverview },
      { key: 'intc', fn: getIntcOverview },
      { key: 'nvda', fn: getNvdaOverview },
      { key: 'mu', fn: getMuOverview },
      { key: '300308', fn: () => getAShareOverview('300308') },
      { key: '603986', fn: () => getAShareOverview('603986') },
      { key: '688146', fn: () => getAShareOverview('688146') },
      { key: '002837', fn: () => getAShareOverview('002837') },
    ]

    reqs.forEach((r) => {
      r.fn()
        .then((value) => {
          if (value) setOverviews((prev) => ({ ...prev, [r.key]: value }))
        })
        .catch(() => {})
    })

    getMatrixYearlyReturns()
      .then((value) => {
        if (value) setYearlyReturns(value)
      })
      .catch(() => {})
  }, [])

  const usdCny = Number(yearlyReturns?.usd_cny) > 0 ? Number(yearlyReturns.usd_cny) : DEFAULT_USD_CNY

  const profitToUsd = (key, profit) => {
    if (profit == null) return 0
    if (A_SHARE_KEYS.includes(key)) return Number(profit) / usdCny
    return Number(profit)
  }

  // 动态计算统计数据（运行状态可页面修改，计入本地覆盖）
  const resolveStatus = (s) => statusMap[s.key] || s.status
  const runningCount = strategies.filter((s) => resolveStatus(s) === '运行中').length
  const overviewEntries = Object.entries(overviews)
  const avgWinRate = overviewEntries.length
    ? (overviewEntries.reduce((s, [, o]) => s + (o.win_rate_pct || 0), 0) / overviewEntries.length).toFixed(2)
    : '--'
  const totalProfit = overviewEntries.length
    ? overviewEntries.reduce((s, [key, o]) => s + profitToUsd(key, o.strategy_profit), 0)
    : null
  const totalProfitStr = totalProfit != null
    ? totalProfit >= 1e6
      ? `$${(totalProfit / 1e6).toFixed(2)}M`
      : `$${(totalProfit / 1e3).toFixed(1)}K`
    : '--'

  const yearRows = yearlyReturns?.years || {}
  const y2024 = yearRows['2024']
  const y2025 = yearRows['2025']
  const y2026 = yearRows['2026']

  const statsPrimary = [
    {
      title: '策略总数',
      value: String(strategies.length),
      icon: BarChart3,
      iconColor: 'bg-blue-500',
    },
    {
      title: '运行中策略',
      value: String(runningCount),
      percentage: `${Math.round((runningCount / strategies.length) * 100)}%`,
      icon: Activity,
      iconColor: 'bg-blue-400',
    },
    {
      title: '平均胜率',
      value: overviewEntries.length ? `${avgWinRate}%` : '--',
      icon: TrendingUp,
      iconColor: 'bg-blue-500',
    },
    {
      title: '累计收益',
      value: totalProfitStr,
      icon: Wallet,
      iconColor: 'bg-blue-500',
    },
  ]

  const statsYearly = [
    { title: '2024年化', value: formatYearPct(y2024?.annualized_pct) },
    { title: '2025年化', value: formatYearPct(y2025?.annualized_pct) },
    { title: '2026年化', value: formatYearPct(y2026?.annualized_pct) },
    { title: '2027年化', value: '--' },
  ]

  const enrichedStrategies = useMemo(() => {
    return cardOrder
      .map((key) => STRATEGY_BY_KEY[key])
      .filter(Boolean)
      .map((s) => {
        const key = s.key
        const status = statusMap[key] || s.status
        const statusColor = statusColorFor(status)
        const ov = overviews[key]
        const liveDrawdown = ov?.max_drawdown_pct != null
          ? `-${Number(ov.max_drawdown_pct).toFixed(2)}%`
          : null
        const drawdown = USE_LIVE_DRAWDOWN.has(key) && liveDrawdown
          ? liveDrawdown
          : (FIXED_DRAWDOWN[key] ?? '--')
        const profitFactor =
          key === 'intc'
            ? '10.39'
            : key === 'nvda'
              ? '9.8'
              : (ov ? formatProfitFactor(ov.profit_factor) : (FIXED_PROFIT_FACTOR[key] ?? '--'))
        if (!ov) {
          return { ...s, status, statusColor, annualReturn: '--', annualReturnLabel: '当年收益', drawdown, profitFactor }
        }
        const resolved = resolveCardYearReturn(key, ov, yearlyReturns)
        let annualReturn = '--'
        let annualReturnLabel = '当年收益'
        if (resolved) {
          annualReturnLabel = resolved.label
          const p = resolved.pct
          annualReturn = `${p > 0 ? '+' : ''}${p.toFixed(2)}%`
        }
        return { ...s, status, statusColor, annualReturn, annualReturnLabel, drawdown, profitFactor }
      })
  }, [cardOrder, overviews, statusMap, yearlyReturns])

  const updateCardStatus = (key, nextStatus) => {
    setStatusMap((prev) => {
      const next = { ...prev, [key]: nextStatus }
      saveCardStatuses(next)
      return next
    })
  }

  const reorderCards = (fromKey, toKey) => {
    if (!fromKey || !toKey || fromKey === toKey) return
    setCardOrder((prev) => {
      const next = [...prev]
      const from = next.indexOf(fromKey)
      const to = next.indexOf(toKey)
      if (from < 0 || to < 0) return prev
      next.splice(from, 1)
      next.splice(to, 0, fromKey)
      saveCardOrder(next)
      return next
    })
  }

  return (
    <div className="strategy-matrix-alt min-h-full w-full">
      <div className="mx-auto w-full max-w-[1920px] px-4 py-5">
        <div className="stats-grid-strategy mb-3 grid grid-cols-2 gap-3 md:grid-cols-4">
          {statsPrimary.map((stat) => (
            <StatCard
              key={stat.title}
              title={stat.title}
              value={stat.value}
              change={stat.change}
              isPositive={stat.isPositive}
              percentage={stat.percentage}
              icon={stat.icon}
              iconColor={stat.iconColor}
            />
          ))}
        </div>
        <div className="stats-grid-strategy mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
          {statsYearly.map((stat) => (
            <StatCard
              key={stat.title}
              title={stat.title}
              value={stat.value}
              icon={Percent}
              iconColor="bg-indigo-500"
            />
          ))}
        </div>

        <div className="mb-6 flex flex-1 flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div className="relative max-w-[400px] flex-1">
              <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-[#9ca3af]" />
              <input
                type="text"
                placeholder="搜索策略名称或代码..."
                className="w-full rounded-lg border border-[#e5e7eb] bg-white py-2.5 pl-[40px] pr-4 text-sm outline-none transition-[border-color,box-shadow] focus:border-[#3b82f6] focus:shadow-[0_0_0_3px_rgba(59,130,246,0.1)]"
              />
            </div>
            <button
              type="button"
              className="flex items-center gap-2 rounded-lg border border-[#e5e7eb] bg-white px-4 py-2.5 text-sm text-[#374151] transition-colors hover:bg-[#f9fafb]"
            >
              <Filter className="h-4 w-4 shrink-0" />
              <span>全部状态</span>
              <ChevronDown className="h-4 w-4 shrink-0" />
            </button>
            <span className="hidden text-xs text-[#9ca3af] sm:inline">拖拽调序 · 点击状态可切换</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg bg-[#f3f4f6] p-1">
              <button
                type="button"
                className="rounded-md bg-[#3b82f6] p-2 text-white transition-colors hover:bg-[#2563eb]"
                title="网格"
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
              <button
                type="button"
                className="rounded-md p-2 text-[#6b7280] transition-colors hover:bg-[#e5e7eb]"
                title="列表"
              >
                <List className="h-4 w-4" />
              </button>
            </div>
            <button
              type="button"
              className="flex items-center gap-2 rounded-lg bg-[#3b82f6] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#2563eb]"
            >
              <Plus className="h-4 w-4" />
              <span>新建策略</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {enrichedStrategies.map((s) => (
            <StrategyCardMatrix
              key={s.key}
              to={s.to}
              icon={s.icon}
              title={s.title}
              code={s.code}
              description={s.description}
              status={s.status}
              statusColor={s.statusColor}
              statusEditable
              statusOptions={STATUS_OPTIONS}
              onStatusChange={(next) => updateCardStatus(s.key, next)}
              progress={s.progress}
              progressColor={s.progressColor}
              annualReturn={s.annualReturn}
              annualReturnLabel={s.annualReturnLabel}
              drawdown={s.drawdown}
              profitFactor={s.profitFactor}
              riskIndex={s.riskIndex}
              isRiskWarning={s.isRiskWarning}
              isActive={path === s.to}
              draggable
              isDragging={draggingKey === s.key}
              isDragOver={dragOverKey === s.key && draggingKey !== s.key}
              onDragStart={(e) => {
                suppressClickRef.current = false
                setDraggingKey(s.key)
                e.dataTransfer.effectAllowed = 'move'
                e.dataTransfer.setData('text/plain', s.key)
              }}
              onDragOver={(e) => {
                e.preventDefault()
                e.dataTransfer.dropEffect = 'move'
                if (dragOverKey !== s.key) setDragOverKey(s.key)
              }}
              onDragLeave={() => {
                if (dragOverKey === s.key) setDragOverKey(null)
              }}
              onDrop={(e) => {
                e.preventDefault()
                const fromKey = e.dataTransfer.getData('text/plain') || draggingKey
                reorderCards(fromKey, s.key)
                suppressClickRef.current = true
                setDraggingKey(null)
                setDragOverKey(null)
              }}
              onDragEnd={() => {
                setDraggingKey(null)
                setDragOverKey(null)
              }}
              onNavigateClick={(e) => {
                if (suppressClickRef.current) {
                  e.preventDefault()
                  suppressClickRef.current = false
                }
              }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
