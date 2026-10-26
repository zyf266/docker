import React, { useMemo } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { isAdminRole, readStoredUser } from '../utils/authRole'
import './PortalLayout.css'

const links = [
  { to: '/portal', end: true, label: '实盘账户' },
  { to: '/portal/market', label: '市场状态' },
  { to: '/portal/strategies', label: '策略库' },
]

const PortalLayout = () => {
  const navigate = useNavigate()
  const user = useMemo(() => readStoredUser(), [])
  const showAdminSwitch = isAdminRole(user?.role)

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/login', { replace: true })
  }

  return (
    <div className="portal-root">
      <header className="portal-nav">
        <Link className="portal-logo" to="/portal">
          <span className="portal-logo-mark" aria-hidden />
          QUANT TERMINAL
        </Link>
        <nav className="portal-nav-links">
          {links.map((item) => (
            <NavLink key={item.to} to={item.to} end={!!item.end}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="portal-nav-actions">
          {showAdminSwitch ? (
            <Link className="portal-btn portal-btn-cyan" to="/trading">进入管理端</Link>
          ) : null}
          <Link className="portal-btn portal-btn-primary" to="/portal">一键连接</Link>
          <button type="button" className="portal-btn portal-btn-ghost" onClick={logout}>退出</button>
        </div>
      </header>
      <main className="portal-main">
        <Outlet />
      </main>
      <footer className="portal-footer">
        <div className="portal-logo">
          <span className="portal-logo-mark" aria-hidden />
          QUANT TERMINAL
        </div>
        <div>均线与信号自动计算，不构成投资建议。</div>
        <div>
          <Link to="/portal/contact">联系我们</Link>
          {' · '}
          <Link to="/portal/faq">隐私政策</Link>
        </div>
      </footer>
    </div>
  )
}

export default PortalLayout
