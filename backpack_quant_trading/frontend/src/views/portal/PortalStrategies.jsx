import React from 'react'

const strategies = [
  { name: '趋势跟随', market: '加密', status: '实盘', note: '站上 MA30 偏多，跌破降仓' },
  { name: '美股动量', market: '美股', status: '实盘', note: '动量突破 + 均线过滤' },
  { name: '均值回归', market: '加密', status: '回测', note: '偏离 MA 后回归' },
  { name: '山寨标签', market: '加密', status: '观察', note: 'MA 强弱标签驱动' },
]

const PortalStrategies = () => (
  <div>
    <div className="qt-hero">
      <div>
        <p className="qt-kicker">STRATEGY LIBRARY</p>
        <h1 className="qt-title">策略库</h1>
        <p className="qt-sub">策略条件映射与自定义规则稍后接入。当前仅展示卡片壳。</p>
      </div>
    </div>

    <div className="qt-ma-grid">
      {strategies.map((item) => (
        <article className="qt-ma-card" key={item.name}>
          <div className="qt-ma-card-head">
            <div>
              <h3>{item.name}</h3>
              <p>{item.note}</p>
            </div>
            <span className={`qt-pill ${item.market === '加密' ? 'qt-pill-crypto' : 'qt-pill-us'}`}>
              {item.market}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="qt-pill qt-pill-live">{item.status}</span>
            <button type="button" className="portal-btn portal-btn-ghost">查看映射</button>
          </div>
        </article>
      ))}
    </div>
  </div>
)

export default PortalStrategies
