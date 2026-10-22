import React from 'react'

const PortalSystem = () => (
  <div>
    <section className="portal-section portal-card">
      <h2>AI 量化系统架构介绍</h2>
      <p className="portal-muted">从行情到信号再到风控与可视化的完整链路示意。</p>
    </section>
    <section className="portal-section portal-grid-4">
      {[
        ['行情数据模块', '拉取标的行情、清洗与对齐。'],
        ['AI 信号计算', '多因子模型，计算强弱 / MACD 等并生成信号。'],
        ['智能风控模块', '仓位、回撤阈值、止损；信号须过门禁。'],
        ['数据可视化', '净值、标的看板、信号留痕。'],
      ].map(([t, d]) => (
        <div className="portal-card" key={t}>
          <h3>{t}</h3>
          <p className="portal-muted">{d}</p>
        </div>
      ))}
    </section>
    <section className="portal-section" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
      <div className="portal-card">
        <h3>风控机制专项</h3>
        <ol className="portal-muted">
          <li>单标的仓位上限</li>
          <li>账户阶段最大回撤阈值</li>
          <li>极端行情自动熔断</li>
        </ol>
      </div>
      <div className="portal-card">
        <h3>系统能力边界</h3>
        <p className="portal-muted">AI 不能预测市场方向；目标是减少情绪干扰、严格执行风控、追求长期稳健，无法规避系统性风险。</p>
      </div>
    </section>
    <section className="portal-section portal-card">
      <h3>回测说明</h3>
      <p className="portal-muted">历史回测有局限，过往表现不代表未来收益，不构成投资建议。</p>
    </section>
  </div>
)

export default PortalSystem
