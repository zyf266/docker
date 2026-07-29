import React from 'react'
import StrategyDetail from './StrategyDetail'
import { getAlphaEthOverview, getAlphaEthTrades, getAlphaEthKlines } from '../api/strategy'

const title = '阿尔法策略·ETH'
const subtitle =
  '以太坊（ETH）阿尔法策略，本金 100 万 USDT、约 50% 仓位运行。基于 2 小时周期趋势信号进出场，纪律性执行多头趋势段，追求风险调整后的超额收益。'

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
