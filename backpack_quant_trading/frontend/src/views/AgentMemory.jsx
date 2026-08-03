import React, { useCallback, useEffect, useState } from 'react'
import AisPageShell from '../components/AisPageShell'
import { getAgentMemoryStats, queryAgentMemory } from '../api/agentMemory'
import './AgentMemory.css'

const KINDS = [
  { value: 'agent_reports', label: '分析报告' },
  { value: 'agent_reviews', label: '复盘' },
  { value: 'agent_prefs', label: '偏好' },
  { value: 'agent_research', label: '检索' },
  { value: 'score_feedback', label: '评分反馈' },
]

const AgentMemory = () => {
  const [stats, setStats] = useState(null)
  const [kind, setKind] = useState('agent_reports')
  const [q, setQ] = useState('ETH')
  const [symbol, setSymbol] = useState('')
  const [items, setItems] = useState([])
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(false)

  const loadStats = useCallback(async () => {
    try {
      const res = await getAgentMemoryStats()
      setStats(res?.counts || {})
    } catch (e) {
      setMsg(String(e?.message || e))
    }
  }, [])

  useEffect(() => {
    loadStats()
  }, [loadStats])

  const onSearch = async () => {
    setLoading(true)
    setMsg('')
    try {
      const res = await queryAgentMemory({ kind, q, symbol, n: 10 })
      setItems(res?.items || [])
      if (!(res?.items || []).length) setMsg('无匹配结果')
    } catch (e) {
      setMsg(String(e?.message || e))
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <AisPageShell title="Agent 记忆" subtitle="只读浏览 · 语义检索（不支持删除）">
      <div className="am-page">
        <section className="am-stats">
          {stats &&
            Object.entries(stats).map(([k, v]) => (
              <div key={k} className="am-stat">
                <span className="am-stat-k">{k}</span>
                <span className="am-stat-v">{v}</span>
              </div>
            ))}
        </section>

        <section className="am-toolbar">
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            {KINDS.map((k) => (
              <option key={k.value} value={k.value}>
                {k.label}
              </option>
            ))}
          </select>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="检索词，如 ETH 止损"
            onKeyDown={(e) => e.key === 'Enter' && onSearch()}
          />
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="可选 symbol"
            style={{ maxWidth: 120 }}
          />
          <button type="button" onClick={onSearch} disabled={loading || !q.trim()}>
            {loading ? '检索中…' : '检索'}
          </button>
        </section>

        {msg ? <p className="am-msg">{msg}</p> : null}

        <ul className="am-list">
          {items.map((it) => (
            <li key={it.id || it.document}>
              <div className="am-meta">
                <code>{it.id}</code>
                {it.distance != null ? (
                  <span>dist {Number(it.distance).toFixed(3)}</span>
                ) : null}
                {it.metadata?.symbol ? <span>{it.metadata.symbol}</span> : null}
              </div>
              <pre className="am-doc">{it.document}</pre>
            </li>
          ))}
        </ul>
      </div>
    </AisPageShell>
  )
}

export default AgentMemory
