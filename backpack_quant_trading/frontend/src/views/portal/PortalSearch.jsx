import React, { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { searchPortal } from '../../api/portal'

const PortalSearch = () => {
  const [params] = useSearchParams()
  const q = params.get('q') || ''
  const [items, setItems] = useState([])
  const [msg, setMsg] = useState('')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setMsg('搜索中…')
      try {
        const res = await searchPortal(q)
        if (!cancelled) {
          setItems(res?.items || [])
          setMsg('')
        }
      } catch (e) {
        if (!cancelled) setMsg(e?.response?.data?.detail || e?.message || '搜索失败')
      }
    })()
    return () => { cancelled = true }
  }, [q])

  return (
    <div>
      <section className="portal-section">
        <h2>搜索结果</h2>
        <p className="portal-muted">关键词：{q || '（全部示意目录）'}</p>
        {msg ? <p className="portal-muted">{msg}</p> : null}
      </section>
      <section className="portal-section portal-card">
        {(items || []).length === 0 ? (
          <p className="portal-muted">没有匹配结果</p>
        ) : (
          <table className="portal-table">
            <thead>
              <tr>
                <th>类型</th>
                <th>名称</th>
                <th>说明</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={`${it.type}-${it.id}`}>
                  <td>{it.type === 'strategy' ? '策略' : '标的'}</td>
                  <td>{it.title}</td>
                  <td className="portal-muted">{it.subtitle}</td>
                  <td>
                    {it.type === 'strategy' ? (
                      <Link className="portal-btn portal-btn-ghost" to="/portal/strategies">查看</Link>
                    ) : (
                      <Link className="portal-btn portal-btn-ghost" to="/portal/watchlist">跟踪库</Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}

export default PortalSearch
