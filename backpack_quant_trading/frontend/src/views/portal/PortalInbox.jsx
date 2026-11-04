import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getInbox, readInbox } from '../../api/portal'

const PortalInbox = () => {
  const [items, setItems] = useState([])
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setMsg('')
    try {
      const res = await getInbox()
      setItems(res?.items || [])
    } catch (e) {
      setMsg(e?.response?.data?.detail || e?.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div>
      <div className="qt-hero">
        <div>
          <p className="qt-kicker">INBOX</p>
          <h1 className="qt-title">状态变更消息</h1>
          <p className="qt-sub">观察库 Pine 四态切换时会写入站内信，并同步钉钉群（关键词「信号」）。</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link className="portal-btn portal-btn-ghost" to="/portal">返回实盘</Link>
          <button type="button" className="portal-btn portal-btn-ghost" onClick={load}>刷新</button>
        </div>
      </div>

      <section className="qt-card">
        {loading ? <p className="qt-sub">加载中…</p> : null}
        {msg ? <p className="qt-down">{msg}</p> : null}
        {!loading && items.length === 0 ? <p className="qt-sub">暂无消息</p> : null}
        {items.map((it) => (
          <div
            key={it.id}
            style={{ borderBottom: '1px solid rgba(148,163,184,.12)', padding: '12px 0' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
              <strong style={{ color: it.is_read ? '#94a3b8' : '#f8fafc' }}>{it.title}</strong>
              <span className="qt-sub" style={{ margin: 0 }}>{it.created_at}</span>
            </div>
            <p className="qt-sub" style={{ whiteSpace: 'pre-wrap' }}>{it.body}</p>
            {!it.is_read ? (
              <button
                type="button"
                className="portal-btn portal-btn-ghost"
                style={{ padding: '4px 10px', fontSize: 12 }}
                onClick={async () => {
                  try {
                    await readInbox(it.id)
                    setItems((prev) => prev.map((x) => (x.id === it.id ? { ...x, is_read: true } : x)))
                  } catch (_) { /* ignore */ }
                }}
              >
                标为已读
              </button>
            ) : null}
          </div>
        ))}
      </section>
    </div>
  )
}

export default PortalInbox
