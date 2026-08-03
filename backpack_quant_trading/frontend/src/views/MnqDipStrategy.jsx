import React from 'react'
import StrategyDetail from './StrategyDetail'
import { getMnqDipOverview, getMnqDipTrades, getMnqDipKlines } from '../api/strategy'

const title = '纳指抄底策略'
const subtitle =
  '聚焦纳斯达克微盘期货（MNQ）4H 周期抄底与趋势修复段，结合回撤过滤控制风险，强调低位布局与分批兑现。'

export default function MnqDipStrategy() {
  return (
    <StrategyDetail
      title={title}
      subtitle={subtitle}
      currencyLabel="USD"
      initialCapital={2000000}
      startDate="2025-08-01"
      getOverview={getMnqDipOverview}
      getTrades={getMnqDipTrades}
      getKlines={getMnqDipKlines}
    />
  )
}
