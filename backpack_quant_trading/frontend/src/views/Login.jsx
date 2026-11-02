import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { forgotResetPassword, forgotSendCode, login, register } from '../api/auth'
import AisPageBackground from '../components/AisPageBackground'
import '../styles/AisTheme.css'
import './Login.css'

const Login = () => {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('login')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState('success')
  const [codeCooldown, setCodeCooldown] = useState(0)
  const [form, setForm] = useState({
    username: '',
    password: '',
    email: '',
    confirmPassword: '',
    remember: false,
    code: '',
    newPassword: '',
    confirmNewPassword: '',
  })

  useEffect(() => {
    if (codeCooldown <= 0) return undefined
    const t = window.setTimeout(() => setCodeCooldown((c) => c - 1), 1000)
    return () => window.clearTimeout(t)
  }, [codeCooldown])

  const handleChange = (e) => {
    const { name, type, checked, value } = e.target
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleLogin = async () => {
    if (!form.username || !form.password) {
      setMessage('请输入用户名和密码')
      setMessageType('error')
      return
    }
    setLoading(true)
    setMessage('')
    try {
      const res = await login(form)
      localStorage.setItem('token', res.access_token)
      localStorage.setItem('user', JSON.stringify(res.user))
      setMessage('登录成功')
      setMessageType('success')
      const role = String(res?.user?.role || '').toLowerCase()
      const isAdmin = ['superuser', 'admin', 'root'].includes(role)
      navigate(isAdmin ? '/trading' : '/portal')
    } catch (e) {
      setMessage(e?.response?.data?.detail || '登录失败')
      setMessageType('error')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async () => {
    if (!form.username || !form.password) {
      setMessage('请输入用户名和密码')
      setMessageType('error')
      return
    }
    if (form.password !== form.confirmPassword) {
      setMessage('两次密码不一致')
      setMessageType('error')
      return
    }
    if (form.password.length < 6) {
      setMessage('密码至少 6 位')
      setMessageType('error')
      return
    }
    setLoading(true)
    setMessage('')
    try {
      const res = await register({ username: form.username, password: form.password })
      localStorage.setItem('token', res.access_token)
      localStorage.setItem('user', JSON.stringify(res.user))
      setMessage('注册成功，已进入普通用户产品站')
      setMessageType('success')
      navigate('/portal')
    } catch (e) {
      setMessage(e?.response?.data?.detail || '注册失败')
      setMessageType('error')
    } finally {
      setLoading(false)
    }
  }

  const handleSendCode = async () => {
    if (!form.username.trim()) {
      setMessage('请填写手机号/登录账号')
      setMessageType('error')
      return
    }
    setLoading(true)
    setMessage('')
    try {
      const res = await forgotSendCode({ username: form.username.trim() })
      setCodeCooldown(60)
      let tip = res?.message || '验证码已发送'
      if (res?.dev_code) tip += `（调试码 ${res.dev_code}）`
      setMessage(tip)
      setMessageType('success')
    } catch (e) {
      setMessage(e?.response?.data?.detail || '发送失败')
      setMessageType('error')
    } finally {
      setLoading(false)
    }
  }

  const handleResetPassword = async () => {
    if (!form.username.trim() || !form.code.trim()) {
      setMessage('请填写账号与验证码')
      setMessageType('error')
      return
    }
    if (!form.newPassword || form.newPassword.length < 6) {
      setMessage('新密码至少 6 位')
      setMessageType('error')
      return
    }
    if (form.newPassword !== form.confirmNewPassword) {
      setMessage('两次新密码不一致')
      setMessageType('error')
      return
    }
    setLoading(true)
    setMessage('')
    try {
      await forgotResetPassword({
        username: form.username.trim(),
        code: form.code.trim(),
        new_password: form.newPassword,
      })
      setMessage('密码已重置，请登录')
      setMessageType('success')
      setActiveTab('login')
      setForm((prev) => ({
        ...prev,
        password: '',
        code: '',
        newPassword: '',
        confirmNewPassword: '',
      }))
    } catch (e) {
      setMessage(e?.response?.data?.detail || '重置失败')
      setMessageType('error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <AisPageBackground />
      <div className="login-card">
        <div className="login-brand">
          <div className="brand-logo-box">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="brand-logo-icon">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          </div>
          <h1>ApexAI Quant</h1>
          <p>Quantitative Trading Platform</p>
        </div>

        <div className="login-tabs">
          <div className="tabs-header">
            <button
              type="button"
              className={`tab-item${activeTab === 'login' ? ' active' : ''}`}
              onClick={() => {
                setActiveTab('login')
                setMessage('')
              }}
            >
              登录
            </button>
            <button
              type="button"
              className={`tab-item${activeTab === 'register' ? ' active' : ''}`}
              onClick={() => {
                setActiveTab('register')
                setMessage('')
              }}
            >
              注册
            </button>
            {activeTab === 'forgot' ? (
              <button type="button" className="tab-item active">
                忘记密码
              </button>
            ) : null}
          </div>

          <div className="tab-body">
            {activeTab === 'login' && (
              <>
                <div className="form-item">
                  <input
                    name="username"
                    value={form.username}
                    onChange={handleChange}
                    placeholder="号码"
                    disabled={loading}
                  />
                </div>
                <div className="form-item">
                  <input
                    name="password"
                    type="password"
                    value={form.password}
                    onChange={handleChange}
                    placeholder="密码"
                    disabled={loading}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleLogin()
                      }
                    }}
                  />
                </div>
                <div className="login-extra-row">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      name="remember"
                      checked={form.remember}
                      onChange={handleChange}
                      disabled={loading}
                    />
                    记住我
                  </label>
                  <button
                    type="button"
                    className="link-inline"
                    onClick={() => {
                      setActiveTab('forgot')
                      setMessage('')
                    }}
                  >
                    忘记密码?
                  </button>
                </div>
                <div className="form-item">
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={loading}
                    onClick={handleLogin}
                  >
                    {loading ? '处理中...' : '登录'}
                  </button>
                </div>
                <div className="form-item" style={{ textAlign: 'center', marginTop: 8 }}>
                  <Link to="/stock-analysis" className="link-inline">
                    无需登录 · 体验个股分析
                  </Link>
                </div>
              </>
            )}

            {activeTab === 'register' && (
              <>
                <div className="form-item">
                  <input
                    name="username"
                    value={form.username}
                    onChange={handleChange}
                    placeholder="号码（登录账号）"
                    disabled={loading}
                  />
                </div>
                <div className="form-item">
                  <input
                    name="email"
                    value={form.email}
                    onChange={handleChange}
                    placeholder="邮箱（可选）"
                    disabled={loading}
                  />
                </div>
                <div className="form-item">
                  <input
                    name="password"
                    type="password"
                    value={form.password}
                    onChange={handleChange}
                    placeholder="密码"
                    disabled={loading}
                  />
                </div>
                <div className="form-item">
                  <input
                    name="confirmPassword"
                    type="password"
                    value={form.confirmPassword}
                    onChange={handleChange}
                    placeholder="确认密码"
                    disabled={loading}
                  />
                </div>
                <div className="terms-row">
                  <label className="checkbox-label">
                    <input type="checkbox" name="agree" onChange={() => {}} />
                    <span>
                      我同意
                      <button type="button" className="link-inline" disabled>
                        服务条款
                      </button>
                      和
                      <button type="button" className="link-inline" disabled>
                        隐私政策
                      </button>
                    </span>
                  </label>
                </div>
                <div className="form-item">
                  <button
                    type="button"
                    className="btn btn-success"
                    disabled={loading}
                    onClick={handleRegister}
                  >
                    {loading ? '处理中...' : '注册'}
                  </button>
                </div>
              </>
            )}

            {activeTab === 'forgot' && (
              <>
                <div className="form-item">
                  <input
                    name="username"
                    value={form.username}
                    onChange={handleChange}
                    placeholder="手机号 / 登录账号"
                    disabled={loading}
                  />
                </div>
                <div className="form-item" style={{ display: 'flex', gap: 8 }}>
                  <input
                    name="code"
                    value={form.code}
                    onChange={handleChange}
                    placeholder="验证码"
                    disabled={loading}
                    style={{ flex: 1 }}
                  />
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={loading || codeCooldown > 0}
                    onClick={handleSendCode}
                    style={{ whiteSpace: 'nowrap', minWidth: 110 }}
                  >
                    {codeCooldown > 0 ? `${codeCooldown}s` : '获取验证码'}
                  </button>
                </div>
                <div className="form-item">
                  <input
                    name="newPassword"
                    type="password"
                    value={form.newPassword}
                    onChange={handleChange}
                    placeholder="新密码"
                    disabled={loading}
                  />
                </div>
                <div className="form-item">
                  <input
                    name="confirmNewPassword"
                    type="password"
                    value={form.confirmNewPassword}
                    onChange={handleChange}
                    placeholder="确认新密码"
                    disabled={loading}
                  />
                </div>
                <div className="form-item">
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={loading}
                    onClick={handleResetPassword}
                  >
                    {loading ? '处理中...' : '重置密码'}
                  </button>
                </div>
                <div className="form-item" style={{ textAlign: 'center' }}>
                  <button
                    type="button"
                    className="link-inline"
                    onClick={() => {
                      setActiveTab('login')
                      setMessage('')
                    }}
                  >
                    返回登录
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {message && (
          <div className={`login-alert ${messageType === 'error' ? 'login-alert-error' : 'login-alert-success'}`}>
            {message}
          </div>
        )}

        <div className="login-footer">
          © 2024 沐龙量化. All rights reserved.
        </div>
      </div>
    </div>
  )
}

export default Login
