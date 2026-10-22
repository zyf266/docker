import React from 'react'

const PortalContact = () => (
  <div>
    <p className="qt-kicker">CONTACT</p>
    <h1 className="qt-title">联系我们</h1>
    <section className="qt-card" style={{ marginTop: 18, maxWidth: 520 }}>
      <p className="qt-sub" style={{ marginTop: 0 }}>咨询表单逻辑后接。当前仅壳。</p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 14 }}>
        <input className="qt-input" placeholder="称呼" disabled />
        <input className="qt-input" placeholder="联系方式" disabled />
        <textarea className="qt-input" rows={4} placeholder="需求描述" disabled style={{ resize: 'vertical' }} />
        <button type="button" className="portal-btn portal-btn-primary" disabled>提交（稍后开放）</button>
      </div>
    </section>
  </div>
)

export default PortalContact
