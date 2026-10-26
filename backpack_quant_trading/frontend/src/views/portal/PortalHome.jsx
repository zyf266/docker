import React, { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getEquityOverlay } from '../../api/portal'

const FEATURES = [
  { title: 'AI 量化策略系统', desc: '多套成熟策略，覆盖加密与美股，适配不同行情。' },
  { title: '严格风控', desc: '仓位与回撤约束，信号需过风控门禁再输出。' },
  { title: '全市场监控', desc: '标的扫描与多周期指标自动识别，跟踪强弱变化。' },
]

const STRATEGIES = [
  { id: 'trend-crypto', name: '趋势-加密', pair: 'BTC / ETH', tag: '加密', annual: '—', dd: '—' },
  { id: 'grid-crypto', name: '网格-加密', pair: '主流山寨', tag: '加密', annual: '—', dd: '—' },
  { id: 'momentum-us', name: '动量-美股', pair: 'NVDA / TSLA', tag: '美股', annual: '—', dd: '—' },
  { id: 'cross-market', name: '跨市场', pair: '加密 + 美股', tag: '组合', annual: '—', dd: '—' },
]

const PREVIEW_ROWS = [
  { code: 'BTC', market: '加密', strength: '强', d: '金叉', h60: '粘合', h30: '金叉' },
  { code: 'ETH', market: '加密', strength: '中', d: '粘合', h60: '死叉', h30: '金叉' },
  { code: 'SOL', market: '加密', strength: '弱', d: '死叉', h60: '死叉', h30: '粘合' },
  { code: 'NVDA', market: '美股', strength: '强', d: '金叉', h60: '金叉', h30: '粘合' },
  { code: 'AAPL', market: '美股', strength: '中', d: '粘合', h60: '金叉', h30: '死叉' },
  { code: 'TSLA', market: '美股', strength: '弱', d: '死叉', h60: '粘合', h30: '死叉' },
]

const strengthClass = (s) => (s === '强' ? 'portal-tag-up' : s === '弱' ? 'portal-tag-down' : 'portal-tag-mid')

const PortalHome = () => {
  const [fullscreen, setFullscreen] = useState(false)
  const [equity, setEquity] = useState(null)
  const [eqMsg, setEqMsg] = useState('')

  const loadEquity = async () => {
    setEqMsg('加载中…')
    try {
      const res = await getEquityOverlay(['trend-crypto', 'momentum-us'])
      setEquity(res)
      setEqMsg(res?.note || '')
    } catch (e) {
      setEqMsg(e?.response?.data?.detail || e?.message || '加载失败')
    }
  }

  const chartHint = useMemo(() => {
    if (!equity?.series?.length) return '点击「叠加对比」加载占位净值曲线'
    return equity.series.map((s) => `${s.name}: ${s.points?.[s.points.length - 1]?.v ?? '—'}`).join(' · ')
  }, [equity])

  const screen = (
    <div className={fullscreen ? 'portal-fullscreen' : ''}>
      {fullscreen ? (
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
          <h2 style={{ margin: 0, color: '#fff' }}>分析大屏（空壳）</h2>
          <button type="button" className="portal-btn portal-btn-ghost" onClick={() => setFullscreen(false)}>退出全屏</button>
        </div>
      ) : null}
      <section className="portal-section portal-hero">
        <div className="portal-card">
          <h1 className="portal-hero-title">AI 量化交易系统<br />用算法管住风险，追求长期稳健收益</h1>
          <p className="portal-muted">面向个人投资者：策略自动执行框架示意，严格控制回撤。本页数据为演示占位，后期接入真实来源。</p>
          <ul className="portal-muted">
            <li>多套可验证量化策略框架</li>
            <li>AI 动态风控：跟踪单笔与阶段回撤</li>
            <li>标的实时监控与多周期指标识别</li>
          </ul>
          <div className="portal-cta-row">
            <Link className="portal-btn portal-btn-primary" to="/portal/strategies">查看策略详情</Link>
            <Link className="portal-btn portal-btn-ghost" to="/portal/contact">立即咨询</Link>
            <button type="button" className="portal-btn portal-btn-ghost" onClick={() => setFullscreen(true)}>分析大屏</button>
          </div>
        </div>
        <div className="portal-card">
          <h3>主策略净值示意</h3>
          <p className="portal-muted">历史表现趋势（不代表未来）</p>
          <div style={{ height: 160, borderRadius: 10, background: 'linear-gradient(135deg,#1e293b,#0f172a)', display: 'grid', placeItems: 'center', color: '#94a3b8', marginTop: 12 }}>
            净值曲线占位
          </div>
          <p className="portal-muted" style={{ marginTop: 10 }}>最大回撤 — · 年化 —</p>
        </div>
      </section>

      <section className="portal-section">
        <div className="portal-grid-3">
          {FEATURES.map((f) => (
            <div className="portal-card" key={f.title}>
              <h3>{f.title}</h3>
              <p className="portal-muted">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="portal-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <h2>策略速览</h2>
          <button type="button" className="portal-btn portal-btn-primary" onClick={loadEquity}>多策略净值叠加</button>
        </div>
        <p className="portal-muted">{eqMsg || chartHint}</p>
        <div className="portal-grid-4" style={{ marginTop: 12 }}>
          {STRATEGIES.map((s) => (
            <div className="portal-card" key={s.id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <strong>{s.name}</strong>
                <span className={`portal-tag ${s.tag === '美股' ? 'portal-tag-us' : 'portal-tag-crypto'}`}>{s.tag}</span>
              </div>
              <p className="portal-muted">{s.pair}</p>
              <div style={{ height: 56, margin: '10px 0', borderRadius: 8, background: '#0f172a' }} />
              <p className="portal-muted">年化 {s.annual} · 回撤 {s.dd}</p>
              <Link className="portal-btn portal-btn-ghost" to="/portal/strategies">查看详情</Link>
            </div>
          ))}
        </div>
      </section>

      <section className="portal-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>标的实时预览</h2>
          <Link className="portal-btn portal-btn-ghost" to="/portal#portal-watchlist">进入完整标的库</Link>
        </div>
        <div className="portal-card" style={{ overflowX: 'auto' }}>
          <table className="portal-table">
            <thead>
              <tr>
                <th>代码</th>
                <th>市场</th>
                <th>强弱</th>
                <th>日线 MACD</th>
                <th>60分 MACD</th>
                <th>30分 MACD</th>
              </tr>
            </thead>
            <tbody>
              {PREVIEW_ROWS.map((r) => (
                <tr key={r.code}>
                  <td>{r.code}</td>
                  <td><span className={`portal-tag ${r.market === '美股' ? 'portal-tag-us' : 'portal-tag-crypto'}`}>{r.market}</span></td>
                  <td><span className={`portal-tag ${strengthClass(r.strength)}`}>{r.strength}</span></td>
                  <td>{r.d}</td>
                  <td>{r.h60}</td>
                  <td>{r.h30}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="portal-section portal-card">
        <h2>系统流程</h2>
        <p className="portal-muted">行情采集 → AI 信号计算 → 风控校验 → 信号输出。自动化执行框架，风控优先。</p>
      </section>

      <section className="portal-section portal-card">
        <h2>想看完整策略数据？</h2>
        <p className="portal-muted">提交咨询后，工作人员会与你联系（第一期仅落库）。</p>
        <Link className="portal-btn portal-btn-primary" to="/portal/contact">提交咨询</Link>
      </section>
    </div>
  )

  return screen
}

export default PortalHome
