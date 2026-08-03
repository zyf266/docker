import React from 'react'
import StrategyDetail from './StrategyDetail'
import { getAlphaEthOverview, getAlphaEthTrades, getAlphaEthKlines } from '../api/strategy'

const title = '【沐龙】长盈叁号·趋势追踪策略'
const subtitle =
  '以太坊（ETH）趋势追踪策略，中低风险，本金 100 万 USDT、约 50% 仓位运行。'

export default function AlphaEthStrategy() {
  return (
    <StrategyDetail
      title={title}
      subtitle={subtitle}
      currencyLabel="USDT"
      startDate="2026-07-05"
      initialCapital={1000000}
      getOverview={getAlphaEthOverview}
      getTrades={getAlphaEthTrades}
      getKlines={getAlphaEthKlines}
    />
  )
}
