import React, { useMemo, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { scaleBookCapital } from '../api/portal'
import { isAdminRole, readStoredUser } from '../utils/authRole'
import './PortalLayout.css'

const links = [
  { to: '/portal', end: true, label: '实盘账户' },
]

const PortalLayout = () => {
  const navigate = useNavigate()
  const user = useMemo(() => readStoredUser(), [])
  const showAdminSwitch = isAdminRole(user?.role)
  const [bookMarket, setBookMarket] = useState('加密')
  const [bookCapital, setBookCapital] = useState('')
  const [bookBusy, setBookBusy] = useState(false)
  const [bookMsg, setBookMsg] = useState('')

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/login', { replace: true })
  }

  const onApplyBookCapital = async () => {
    if (!bookCapital.trim()) {
      setBookMsg('请填写本金，如 200w')
      return
    }
    setBookBusy(true)
    setBookMsg('')
    try {
      const res = await scaleBookCapital({ market: bookMarket, capital: bookCapital.trim() })
      const nw = res?.new_capital
      const n = Number(nw)
      const shown = Number.isFinite(n)
        ? (n >= 10000 ? `${(n / 10000).toFixed(n % 10000 === 0 ? 0 : 1)}w` : String(n))
        : bookCapital
      setBookMsg(`已将「${bookMarket}」本金调整为 ${shown}`)
      window.dispatchEvent(new CustomEvent('portal-book-capital-updated', { detail: res }))
    } catch (e) {
      setBookMsg(e?.response?.data?.detail || e?.message || '调整失败')
    } finally {
      setBookBusy(false)
    }
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
          {showAdminSwitch ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
              <select
                className="qt-select"
                value={bookMarket}
                onChange={(e) => setBookMarket(e.target.value)}
                style={{ minWidth: 88, height: 34 }}
                title="市场"
              >
                <option value="加密">加密</option>
                <option value="美股">美股</option>
              </select>
              <input
                className="qt-select"
                value={bookCapital}
                onChange={(e) => setBookCapital(e.target.value)}
                placeholder="本金 如 200w"
                style={{ width: 110, height: 34 }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') onApplyBookCapital()
                }}
              />
              <button
                type="button"
                className="portal-btn portal-btn-primary"
                disabled={bookBusy}
                onClick={onApplyBookCapital}
              >
                {bookBusy ? '调整中…' : '应用本金'}
              </button>
              {bookMsg ? (
                <span style={{ fontSize: 12, color: 'var(--qt-muted)', maxWidth: 200 }}>{bookMsg}</span>
              ) : null}
            </div>
          ) : null}
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
