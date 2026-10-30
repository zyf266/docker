import React, { useMemo, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { createBookAccount } from '../api/portal'
import { isAdminRole, readStoredUser } from '../utils/authRole'
import './PortalLayout.css'

const links = [
  { to: '/portal', end: true, label: '实盘账户' },
]

const PortalLayout = () => {
  const navigate = useNavigate()
  const user = useMemo(() => readStoredUser(), [])
  const showAdminSwitch = isAdminRole(user?.role)
  const [capOpen, setCapOpen] = useState(false)
  const [bookMarket, setBookMarket] = useState('加密')
  const [bookCapital, setBookCapital] = useState('')
  const [bookPhone, setBookPhone] = useState('')
  const [bookBusy, setBookBusy] = useState(false)
  const [bookMsg, setBookMsg] = useState('')

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/login', { replace: true })
  }

  const closeCap = () => {
    setCapOpen(false)
    setBookMsg('')
  }

  const onApplyBookCapital = async () => {
    if (!bookCapital.trim()) {
      setBookMsg('请填写本金，如 200w')
      return
    }
    if (!bookPhone.trim()) {
      setBookMsg('请填写手机号')
      return
    }
    setBookBusy(true)
    setBookMsg('')
    try {
      const res = await createBookAccount({
        market: bookMarket,
        capital: bookCapital.trim(),
        phone: bookPhone.trim(),
      })
      const nw = res?.initial_capital
      const n = Number(nw)
      const shown = Number.isFinite(n)
        ? (n >= 10000 ? `${(n / 10000).toFixed(n % 10000 === 0 ? 0 : 1)}w` : String(n))
        : bookCapital
      const uname = res?.login_username || bookPhone.trim()
      const pwdHint = res?.user_created
        ? `；已建用户 ${uname} / 密码 123456`
        : `；已绑定已有用户 ${uname}`
      setBookMsg(`已新增「${bookMarket}」账户（本金 ${shown}）${pwdHint}`)
      window.dispatchEvent(new CustomEvent('portal-book-capital-updated', { detail: res }))
      setBookCapital('')
      setBookPhone('')
      setTimeout(() => closeCap(), 1200)
    } catch (e) {
      setBookMsg(e?.response?.data?.detail || e?.message || '新增失败')
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
            <button
              type="button"
              className="portal-btn portal-btn-primary"
              onClick={() => {
                setBookMsg('')
                setCapOpen(true)
              }}
            >
              连接
            </button>
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

      {capOpen ? (
        <div className="qt-modal-mask" role="dialog" aria-modal="true">
          <div className="qt-modal" style={{ maxWidth: 420 }}>
            <div className="qt-modal-head">
              <strong>新增账面账户</strong>
              <button type="button" className="portal-btn portal-btn-ghost" onClick={closeCap}>关闭</button>
            </div>
            <p className="qt-sub" style={{ marginTop: 0 }}>
              填写市场、本金与手机号：会新增账面账户、复制历史成交，并同步创建普通用户（默认密码 123456）。
            </p>
            <label className="qt-field">
              市场
              <select
                className="qt-select"
                value={bookMarket}
                onChange={(e) => setBookMarket(e.target.value)}
              >
                <option value="加密">加密</option>
                <option value="美股">美股</option>
              </select>
            </label>
            <label className="qt-field">
              本金
              <input
                className="qt-select"
                value={bookCapital}
                onChange={(e) => setBookCapital(e.target.value)}
                placeholder="如 200w 或 2000000"
              />
            </label>
            <label className="qt-field">
              手机号
              <input
                className="qt-select"
                value={bookPhone}
                onChange={(e) => setBookPhone(e.target.value)}
                placeholder="普通用户登录账号"
                inputMode="numeric"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') onApplyBookCapital()
                }}
              />
            </label>
            <p className="qt-sub" style={{ marginTop: 0 }}>
              默认密码：123456（新用户）；该用户登录门户后可看本账户成交与持仓。
            </p>
            {bookMsg ? <p className="qt-sub">{bookMsg}</p> : null}
            <div className="qt-modal-actions">
              <button
                type="button"
                className="portal-btn portal-btn-primary"
                disabled={bookBusy}
                onClick={onApplyBookCapital}
              >
                {bookBusy ? '新增中…' : '新增账户'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

export default PortalLayout
