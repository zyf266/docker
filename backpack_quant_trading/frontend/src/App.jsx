import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import Login from './views/Login'
import Dashboard from './views/Dashboard'
import Trading from './views/Trading'
import AiLab from './views/AiLab'
import GridTrading from './views/GridTrading'
import CurrencyMonitor from './views/CurrencyMonitor'
import StockAi from './views/StockAi'
import AiStock from './views/AiStock'
import AiStockDetail from './views/AiStockDetail'
import AiStockSignals from './views/AiStockSignals'
import AiStockNewsHistory from './views/AiStockNewsHistory'
import StrategyMatrixAlt from './views/StrategyMatrixAlt'
import EthTrendStrategy from './views/EthTrendStrategy'
import PaxgTrendStrategy from './views/PaxgTrendStrategy'
import Nas100TrendStrategy from './views/Nas100TrendStrategy'
import EthOnlyStrategy from './views/EthOnlyStrategy'
import AlphaEthStrategy from './views/AlphaEthStrategy'
import Sse510210Strategy from './views/Sse510210Strategy'
import MnqDipStrategy from './views/MnqDipStrategy'
import OkxConsole from './views/OkxConsole'
import UsMomentumIntcStrategy from './views/UsMomentumIntcStrategy'
import UsMomentumNvdaStrategy from './views/UsMomentumNvdaStrategy'
import UsMomentumMuStrategy from './views/UsMomentumMuStrategy'
import AShareMomentumStrategy from './views/AShareMomentumStrategy'
import UsWeeklyReport from './views/UsWeeklyReport'
import StockNewsAlert from './views/StockNewsAlert'
import PolymarketAlert from './views/PolymarketAlert'
import CryptoSignalHub from './views/CryptoSignalHub'
import AgentMemory from './views/AgentMemory'
import StudyCenter from './views/StudyCenter'
import StudyChapterExam from './views/StudyChapterExam'
import GuestStockLayout from './layouts/GuestStockLayout'

const RequireAuth = ({ children }) => {
  const token = localStorage.getItem('token')
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return children
}

const GuestOnly = ({ children }) => {
  const token = localStorage.getItem('token')
  if (token) {
    return <Navigate to="/" replace />
  }
  return children
}

/** 游客个股分析入口：已登录则进完整泡沫检测页 */
const StockAnalysisEntry = () => {
  if (localStorage.getItem('token')) {
    return <Navigate to="/us-weekly-report?tab=stock" replace />
  }
  return <GuestStockLayout />
}

function App() {
  return (
    <>
      <Routes>
        <Route
          path="/login"
          element={
            <GuestOnly>
              <Login />
            </GuestOnly>
          }
        />

        <Route path="/stock-analysis" element={<StockAnalysisEntry />}>
          <Route index element={<UsWeeklyReport guestOnly />} />
        </Route>

        <Route
          path="/"
          element={
            <RequireAuth>
              <MainLayout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="trading" replace />} />
          <Route path="trading" element={<Trading />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="ai-lab" element={<AiLab />} />
          <Route path="grid-trading" element={<GridTrading />} />
          <Route path="currency-monitor" element={<CurrencyMonitor />} />
          <Route path="stock-ai" element={<StockAi />} />
          <Route path="ai-stock" element={<AiStock />} />
          <Route path="ai-stock/:code" element={<AiStockDetail />} />
          <Route path="ai-stock/:code/signals" element={<AiStockSignals />} />
          <Route path="ai-stock/:code/news" element={<AiStockNewsHistory />} />
          <Route path="strategies" element={<StrategyMatrixAlt />} />
          <Route path="strategies/eth-trend" element={<EthTrendStrategy />} />
          <Route path="strategies/alpha-eth" element={<AlphaEthStrategy />} />
          <Route path="strategies/eth-only" element={<EthOnlyStrategy />} />
          <Route path="strategies/paxg-trend" element={<PaxgTrendStrategy />} />
          <Route path="strategies/nas100-trend" element={<Nas100TrendStrategy />} />
          <Route path="strategies/sse-510210" element={<Sse510210Strategy />} />
          <Route path="strategies/mnq-dip" element={<MnqDipStrategy />} />
          <Route path="strategies/a-share-300308" element={<AShareMomentumStrategy code="300308" />} />
          <Route path="strategies/a-share-603986" element={<AShareMomentumStrategy code="603986" />} />
          <Route path="strategies/a-share-688146" element={<AShareMomentumStrategy code="688146" />} />
          <Route path="strategies/a-share-002837" element={<AShareMomentumStrategy code="002837" />} />
          <Route path="strategies/us-momentum-intc" element={<UsMomentumIntcStrategy />} />
          <Route path="strategies/us-momentum-nvda" element={<UsMomentumNvdaStrategy />} />
          <Route path="strategies/us-momentum-mu" element={<UsMomentumMuStrategy />} />
          <Route path="okx-console" element={<OkxConsole />} />
          <Route path="us-weekly-report" element={<UsWeeklyReport />} />
          <Route path="stock-news-alert" element={<StockNewsAlert />} />
          <Route path="polymarket-alert" element={<PolymarketAlert />} />
          <Route path="crypto-signal-hub" element={<CryptoSignalHub />} />
          <Route path="agent-memory" element={<AgentMemory />} />
          <Route path="study-center" element={<StudyCenter />} />
          <Route path="study-center/:slug" element={<StudyChapterExam />} />
          <Route path="ai-agent-quiz" element={<StudyCenter />} />
        </Route>
      </Routes>
    </>
  )
}

export default App

