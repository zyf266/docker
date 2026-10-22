import React, { useCallback, useEffect, useState } from 'react'
import { getInbox, readInbox, stubEmail, testInbox } from '../../api/portal'

const PortalInbox = () => {
  const [items, setItems] = useState([])
  const [msg, setMsg] = useState('')
  const [email, setEmail] = useState('')

  const load = useCallback(async () => {
    try {
      const res = await getInbox()
      setItems(res?.items || [])
    } catch (e) {
      setMsg(e?.response?.data?.detail || e?.message || '加载失败')
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const onTest = async () => {
    setMsg('')
    try {
      await testInbox({ title: '信号变动提醒（测试）', body: '自选标的状态变化示意。正式自动推送后期接入。' })
      await load()
      setMsg('已写入站内信')
    } catch (e) {
      setMsg(e?.response?.data?.detail || e?.message || '失败')
    }
  }

  const onEmail = async () => {
    setMsg('')
    try {
      const res = await stubEmail({
        to_addr: email,
        subject: '信号变动提醒（邮件口子）',
        body: 'SMTP 尚未接通，本条已记入 outbox，并同步一条站内信。',
      })
      await load()
      setMsg(res?.message || '邮件口子已记录')
    } catch (e) {
      setMsg(e?.response?.data?.detail || e?.message || '失败')
    }
  }

  return (
    <div>
      <section className="portal-section">
        <h2>站内消息 / 推送设置</h2>
        <p className="portal-muted">站内信已接通；邮件先走口子落库，真正 SMTP 后期补。</p>
        <div className="portal-cta-row">
          <button type="button" className="portal-btn portal-btn-primary" onClick={onTest}>测试站内信</button>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="测试邮箱"
            style={{ height: 36, borderRadius: 8, border: '1px solid #334155', background: '#0f172a', color: '#e2e8f0', padding: '0 10px', minWidth: 200 }}
          />
          <button type="button" className="portal-btn portal-btn-ghost" onClick={onEmail}>邮件口子测试</button>
        </div>
        {msg ? <p className="portal-muted">{msg}</p> : null}
      </section>
      <section className="portal-section portal-card">
        {(items || []).length === 0 ? (
          <p className="portal-muted">暂无消息</p>
        ) : (
          items.map((it) => (
            <div key={it.id} style={{ borderBottom: '1px solid rgba(148,163,184,.12)', padding: '10px 0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <strong style={{ color: it.is_read ? '#94a3b8' : '#f8fafc' }}>{it.title}</strong>
                <span className="portal-muted">{it.created_at}</span>
              </div>
              <p className="portal-muted">{it.body}</p>
              {!it.is_read ? (
                <button
                  type="button"
                  className="portal-btn portal-btn-ghost"
                  onClick={async () => {
                    await readInbox(it.id)
                    load()
                  }}
                >
                  标为已读
                </button>
              ) : null}
            </div>
          ))
        )}
      </section>
    </div>
  )
}

export default PortalInbox
