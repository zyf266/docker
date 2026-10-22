import React from 'react'

/** 标的详情壳：无 K 线，多币种卡片展示 MA5 / MA30 / MA200 是否站上 */
const cards = [
  {
    code: 'ETH',
    name: '以太坊',
    market: '加密',
    price: 3512,
    ma5: 3468,
    ma30: 3305,
    ma200: 2984,
  },
  {
    code: 'BTC',
    name: '比特币',
    market: '加密',
    price: 64880,
    ma5: 64120,
    ma30: 62840,
    ma200: 58990,
  },
  {
    code: 'SOL',
    name: 'Solana',
    market: '加密',
    price: 178.4,
    ma5: 182.1,
    ma30: 175.6,
    ma200: 148.2,
  },
  {
    code: 'NVDA',
    name: '英伟达',
    market: '美股',
    price: 142.3,
    ma5: 140.8,
    ma30: 146.2,
    ma200: 128.4,
  },
  {
    code: 'CRCL',
    name: 'Circle',
    market: '加密',
    price: 128.6,
    ma5: 125.4,
    ma30: 119.8,
    ma200: 132.1,
  },
  {
    code: 'TSLA',
    name: '特斯拉',
    market: '美股',
    price: 248.6,
    ma5: 252.0,
    ma30: 255.4,
    ma200: 230.1,
  },
]

const fmt = (n) => {
  const v = Number(n)
  if (!Number.isFinite(v)) return '—'
  return v >= 1000 ? v.toLocaleString('en-US', { maximumFractionDigits: 2 }) : String(v)
}

const MaRow = ({ label, price, ma, tone }) => {
  const on = price >= ma
  return (
    <div className="qt-ma-row">
      <div className="qt-ma-row-top">
        <strong>{label}</strong>
        <span className={on ? (tone === 'long' ? 'qt-up' : 'qt-cyan') : ''} style={{ color: on ? undefined : 'var(--qt-muted)' }}>
          {on ? '✓ 已站上' : '未站上'}
        </span>
      </div>
      <p>
        现价 {fmt(price)} {on ? '>' : '<'} {label.split(' ').pop()} {fmt(ma)}
      </p>
      <div className={`qt-ma-meter ${on ? `on-${tone}` : 'off'}`} />
    </div>
  )
}

const PortalMaCards = () => (
  <div>
    <div className="qt-hero">
      <div>
        <p className="qt-kicker">MA STATUS</p>
        <h1 className="qt-title">标的均线卡片</h1>
        <p className="qt-sub">
          每个卡片展示币种与 MA5 / MA30 / MA200 是否站上。不含 K 线；数据为占位，后续再接真实逻辑。
        </p>
      </div>
      <button type="button" className="portal-btn portal-btn-primary">跟随此信号</button>
    </div>

    <div className="qt-ma-grid">
      {cards.map((item) => (
        <article className="qt-ma-card" key={item.code}>
          <div className="qt-ma-card-head">
            <div>
              <h3>{item.code} / {item.name}</h3>
              <p>最新价 {fmt(item.price)}</p>
            </div>
            <span className={`qt-pill ${item.market === '加密' ? 'qt-pill-crypto' : 'qt-pill-us'}`}>
              {item.market}
            </span>
          </div>
          <div className="qt-ma-rows">
            <MaRow label="短强 · MA5" price={item.price} ma={item.ma5} tone="short" />
            <MaRow label="中强 · MA30" price={item.price} ma={item.ma30} tone="mid" />
            <MaRow label="长强 · MA200" price={item.price} ma={item.ma200} tone="long" />
          </div>
        </article>
      ))}
    </div>
  </div>
)

export default PortalMaCards
