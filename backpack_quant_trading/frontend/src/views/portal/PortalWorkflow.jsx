import React from 'react'

const steps = [
  { title: '信号', desc: 'TV / 指标触发' },
  { title: '选标的', desc: '观察库过滤' },
  { title: '匹配策略', desc: '条件映射' },
  { title: '仓位分配', desc: 'MA 规则' },
  { title: '执行', desc: '下单 / 跟单' },
]

const PortalWorkflow = () => (
  <div>
    <div className="qt-hero">
      <div>
        <p className="qt-kicker">AI WORKFLOW</p>
        <h1 className="qt-title">AI 交易工作流</h1>
        <p className="qt-sub">信号 → 选标的 → 策略匹配 → 仓位分配 → 执行。规则与映射后续可配置，当前仅展示流程壳。</p>
      </div>
    </div>

    <section className="qt-card" style={{ marginBottom: 16 }}>
      <div className="qt-flow">
        {steps.map((step) => (
          <div className="qt-card qt-flow-step" key={step.title} style={{ background: '#0d1522' }}>
            <strong>{step.title}</strong>
            <span>{step.desc}</span>
          </div>
        ))}
      </div>
    </section>

    <div className="qt-grid-2">
      <section className="qt-card">
        <strong>仓位规则示例（占位）</strong>
        <div className="qt-steps">
          <div>站上 MA30 → 参考仓位 50%</div>
          <div>未站上 MA30 → 参考仓位 20%</div>
          <div>站上 MA200 → 偏多仓位权重上调</div>
        </div>
      </section>
      <section className="qt-card">
        <strong>实时示例 · ETH</strong>
        <p className="qt-sub" style={{ marginTop: 10 }}>
          2h 金叉 + 短中长期均线共振偏多 → 匹配「趋势跟随」→ 建议仓位 50%（壳文案）。
        </p>
        <button type="button" className="portal-btn portal-btn-primary" style={{ marginTop: 14 }}>
          跟随此信号
        </button>
      </section>
    </div>
  </div>
)

export default PortalWorkflow
