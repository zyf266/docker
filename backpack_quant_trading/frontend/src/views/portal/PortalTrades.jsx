import React from 'react'

const rows = [
  { time: '10-19 14:22', exchange: 'BN', symbol: 'ETH', side: 'Long', action: '开仓', price: '3,512', qty: '1.2', pnl: '+$420', strategy: '趋势跟随' },
  { time: '10-19 11:08', exchange: 'OKX', symbol: 'BTC', side: 'Long', action: '加仓', price: '64,880', qty: '0.15', pnl: '+$210', strategy: '趋势跟随' },
  { time: '10-18 21:40', exchange: 'BN', symbol: 'SOL', side: 'Short', action: '平仓', price: '178.4', qty: '20', pnl: '-$86', strategy: '均值回归' },
  { time: '10-18 16:05', exchange: 'OKX', symbol: 'NVDA', side: 'Short', action: '开仓', price: '142.3', qty: '10', pnl: '+$65', strategy: '美股动量' },
]

const PortalTrades = () => (
  <div>
    <div className="qt-hero">
      <div>
        <p className="qt-kicker">LIVE TRADES</p>
        <h1 className="qt-title">实盘账户 · 交易记录</h1>
        <p className="qt-sub">筛选与导出仅为界面壳，真实成交数据稍后接入。</p>
      </div>
    </div>

    <div className="qt-grid-4" style={{ marginBottom: 16 }}>
      <section className="qt-card">
        <p className="qt-stat-label">本月交易</p>
        <p className="qt-stat-value qt-cyan">86 笔</p>
      </section>
      <section className="qt-card">
        <p className="qt-stat-label">本月胜率</p>
        <p className="qt-stat-value qt-up">66%</p>
      </section>
      <section className="qt-card">
        <p className="qt-stat-label">平均持仓</p>
        <p className="qt-stat-value">1.8 天</p>
      </section>
      <section className="qt-card">
        <p className="qt-stat-label">累计盈亏</p>
        <p className="qt-stat-value qt-up">+$ 28,460</p>
      </section>
    </div>

    <section className="qt-card">
      <div className="qt-toolbar">
        <select className="qt-select" defaultValue="all"><option value="all">交易所: 全部</option></select>
        <select className="qt-select" defaultValue="all"><option value="all">方向: 全部</option></select>
        <select className="qt-select" defaultValue="all"><option value="all">标的: 全部</option></select>
        <input className="qt-input" placeholder="搜索" />
        <button type="button" className="portal-btn portal-btn-ghost" style={{ marginLeft: 'auto' }}>导出 CSV</button>
      </div>
      <div className="qt-table-wrap">
        <table className="qt-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>交易所</th>
              <th>标的</th>
              <th>方向</th>
              <th>动作</th>
              <th>价格</th>
              <th>数量</th>
              <th>盈亏</th>
              <th>策略</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.time}-${row.symbol}-${row.action}`}>
                <td>{row.time}</td>
                <td><span className="qt-pill qt-pill-crypto">{row.exchange}</span></td>
                <td>{row.symbol}</td>
                <td>
                  <span className={`qt-pill ${row.side === 'Long' ? 'qt-pill-long' : 'qt-pill-short'}`}>
                    {row.side}
                  </span>
                </td>
                <td>{row.action}</td>
                <td>{row.price}</td>
                <td>{row.qty}</td>
                <td className={row.pnl.startsWith('+') ? 'qt-up' : 'qt-down'}>{row.pnl}</td>
                <td>{row.strategy}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p style={{ margin: '14px 0 0', color: 'var(--qt-muted)', fontSize: 12, textAlign: 'right' }}>
        分页: 1 / 42 页 · 每页 20 条
      </p>
    </section>
  </div>
)

export default PortalTrades
