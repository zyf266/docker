import React from 'react'
import { Link, Outlet } from 'react-router-dom'
import AisPageBackground from '../components/AisPageBackground'
import '../styles/AisTheme.css'
import './MainLayout.css'
import './GuestStockLayout.css'

/** 未登录访客：仅承载个股分析，无侧栏其它功能 */
const GuestStockLayout = () => {
  return (
    <div className="main-layout guest-stock-layout">
      <div className="content guest-stock-content">
        <header className="header guest-stock-header">
          <div className="header-left">
            <h1 className="page-title">个股分析</h1>
            <span className="status-badge">
              <span className="status-dot" />
              游客模式
            </span>
          </div>
          <div className="header-right">
            <Link to="/login" className="btn-logout guest-login-link">
              登录以使用全部功能
            </Link>
          </div>
        </header>
        <main className="page-content">
          <AisPageBackground />
          <div className="page-content-body">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

export default GuestStockLayout
