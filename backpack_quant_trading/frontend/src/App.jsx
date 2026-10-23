import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import PortalLayout from './layouts/PortalLayout'
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
import AShareAiAgent from './views/AShareAiAgent'
import UsWeeklyReport from './views/UsWeeklyReport'
import StockNewsAlert from './views/StockNewsAlert'
import PolymarketAlert from './views/PolymarketAlert'
import CryptoSignalHub from './views/CryptoSignalHub'
import MaLabelBoard from './views/MaLabelBoard'
import AgentMemory from './views/AgentMemory'
import StudyCenter from './views/StudyCenter'
import StudyChapterExam from './views/StudyChapterExam'
import GuestStockLayout from './layouts/GuestStockLayout'
import PortalAccount from './views/portal/PortalAccount'
import PortalTrades from './views/portal/PortalTrades'
import PortalStrategies from './views/portal/PortalStrategies'
import PortalWatchlist from './views/portal/PortalWatchlist'
import PortalMaCards from './views/portal/PortalMaCards'
import PortalMarket from './views/portal/PortalMarket'
import PortalWorkflow from './views/portal/PortalWorkflow'
import PortalFaq from './views/portal/PortalFaq'
import PortalContact from './views/portal/PortalContact'
import { isAdminRole, readStoredUser } from './utils/authRole'

const homeForUser = () => {
  const user = readStoredUser()
  if (!user) return '/login'
  return isAdminRole(user.role) ? '/trading' : '/portal'
}

const RequireAuth = ({ children }) => {
  const token = localStorage.getItem('token')
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return children
}

const RequireAdmin = ({ children }) => {
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/login" replace />
  const user = readStoredUser()
  if (!isAdminRole(user?.role)) {
    return <Navigate to="/portal" replace />
  }
  return children
}

/** 用户端：任意已登录用户可进；管理员也可进 Portal，再用顶栏切回管理端 */
const RequirePortalUser = ({ children }) => {
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

const GuestOnly = ({ children }) => {
  const token = localStorage.getItem('token')
  if (token) {
    return <Navigate to={homeForUser()} replace />
  }
  return children
}

const StockAnalysisEntry = () => {
  if (localStorage.getItem('token')) {
    const user = readStoredUser()
    if (!isAdminRole(user?.role)) {
      return <Navigate to="/portal" replace />
    }
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
          element={(
            <GuestOnly>
              <Login />
            </GuestOnly>
          )}
        />

        <Route path="/stock-analysis" element={<StockAnalysisEntry />}>
          <Route index element={<UsWeeklyReport guestOnly />} />
        </Route>

        <Route
          path="/portal"
          element={(
            <RequirePortalUser>
              <PortalLayout />
            </RequirePortalUser>
          )}
        >
          <Route index element={<PortalAccount />} />
          <Route path="trades" element={<PortalTrades />} />
          <Route path="watchlist" element={<PortalWatchlist />} />
          <Route path="ma-cards" element={<PortalMaCards />} />
          <Route path="market" element={<PortalMarket />} />
          <Route path="workflow" element={<PortalWorkflow />} />
          <Route path="strategies" element={<PortalStrategies />} />
          <Route path="faq" element={<PortalFaq />} />
          <Route path="contact" element={<PortalContact />} />
        </Route>

        <Route
          path="/"
          element={(
            <RequireAdmin>
              <MainLayout />
            </RequireAdmin>
          )}
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
          <Route path="strategies/a-share-ai-agent" element={<AShareAiAgent />} />
          <Route path="strategies/a-share-300308" element={<AShareMomentumStrategy code="300308" />} />
          <Route path="strategies/a-share-603986" element={<AShareMomentumStrategy code="603986" />} />
          <Route path="strategies/a-share-688146" element={<AShareMomentumStrategy code="688146" />} />
          <Route path="strategies/a-share-002837" element={<AShareMomentumStrategy code="002837" />} />
          <Route path="strategies/a-share-159570" element={<AShareMomentumStrategy code="159570" />} />
          <Route path="strategies/us-momentum-intc" element={<UsMomentumIntcStrategy />} />
          <Route path="strategies/us-momentum-nvda" element={<UsMomentumNvdaStrategy />} />
          <Route path="strategies/us-momentum-mu" element={<UsMomentumMuStrategy />} />
          <Route path="okx-console" element={<OkxConsole />} />
          <Route path="us-weekly-report" element={<UsWeeklyReport />} />
          <Route path="stock-news-alert" element={<StockNewsAlert />} />
          <Route path="polymarket-alert" element={<PolymarketAlert />} />
          <Route path="crypto-signal-hub" element={<CryptoSignalHub />} />
          <Route path="ma-label-board" element={<MaLabelBoard />} />
          <Route path="agent-memory" element={<AgentMemory />} />
          <Route path="study-center" element={<StudyCenter />} />
          <Route path="study-center/:slug" element={<StudyChapterExam />} />
          <Route path="ai-agent-quiz" element={<StudyCenter />} />
        </Route>

        <Route path="*" element={<Navigate to={homeForUser()} replace />} />
      </Routes>
    </>
  )
}

export default App
