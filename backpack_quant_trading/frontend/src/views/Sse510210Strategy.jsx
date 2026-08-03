import React from 'react'
import StrategyDetail from './StrategyDetail'
import { getSse510210Overview, getSse510210Trades, getSse510210Klines } from '../api/strategy'

const title = '上证指数ETH抄底策略'
const subtitle =
  '聚焦上证综指 ETF（510210），4H 周期趋势追踪，结合回撤过滤分批建仓与风控，强调顺势持有。'

export default function Sse510210Strategy() {
  return (
    <StrategyDetail
      title={title}
      subtitle={subtitle}
      currencyLabel="CNY"
      initialCapital={10000000}
      startDate="2025-04-07"
      getOverview={getSse510210Overview}
      getTrades={getSse510210Trades}
      getKlines={getSse510210Klines}
    />
  )
}
