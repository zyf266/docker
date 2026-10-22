import React from 'react'

const PortalMarket = () => (
  <div>
    <div className="qt-hero">
      <div>
        <p className="qt-kicker">GLOBAL MARKET</p>
        <h1 className="qt-title">市场全局状态</h1>
        <p className="qt-sub">加密与美股四态占位：高位震荡 / 上升 / 下降 / 低位震荡。进度条与指数后续接真实计算。</p>
      </div>
    </div>

    <div className="qt-grid-2" style={{ marginBottom: 16 }}>
      <section className="qt-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <strong>加密市场</strong>
          <span className="qt-pill qt-pill-long">上升趋势</span>
        </div>
        <p className="qt-sub" style={{ marginTop: 10 }}>阶段进度（壳）</p>
        <div className="qt-bar" style={{ marginTop: 8 }}>
          <span style={{ width: '68%', background: 'var(--qt-green)' }} />
        </div>
        <p style={{ margin: '14px 0 0', color: 'var(--qt-muted)', fontSize: 13 }}>
          BTC 主导偏多，山寨跟涨分化。占位文案，不接行情源。
        </p>
      </section>
      <section className="qt-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <strong>美股市场</strong>
          <span className="qt-pill" style={{ background: 'rgba(251,146,60,0.16)', color: 'var(--qt-orange)' }}>高位震荡</span>
        </div>
        <p className="qt-sub" style={{ marginTop: 10 }}>阶段进度（壳）</p>
        <div className="qt-bar" style={{ marginTop: 8 }}>
          <span style={{ width: '42%', background: 'var(--qt-orange)' }} />
        </div>
        <p style={{ margin: '14px 0 0', color: 'var(--qt-muted)', fontSize: 13 }}>
          纳指高位波动加大，科技龙头强弱切换。占位文案。
        </p>
      </section>
    </div>

    <div className="qt-grid-4">
      <section className="qt-card">
        <p className="qt-stat-label">市场情绪</p>
        <p className="qt-stat-value qt-up">72 贪婪</p>
      </section>
      <section className="qt-card">
        <p className="qt-stat-label">BTC 年化波动</p>
        <p className="qt-stat-value">48%</p>
      </section>
      <section className="qt-card">
        <p className="qt-stat-label">美股波动指数</p>
        <p className="qt-stat-value qt-orange">18.6</p>
      </section>
      <section className="qt-card">
        <p className="qt-stat-label">资金费率中位</p>
        <p className="qt-stat-value qt-cyan">0.012%</p>
      </section>
    </div>
  </div>
)

export default PortalMarket
