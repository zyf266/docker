import React, { useCallback, useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts'
import {
  backtestAShareAiAgent,
  confirmAShareAiAgentPrefs,
  decideAShareAiAgent,
  getAShareAiAgentMeta,
  getAShareAiAgentPrefs,
  getAShareAiAgentStatus,
  getAShareAiAgentTrades,
  getAShareAiAgentTradeSymbols,
  postAShareAiAgentFeedback,
  removeAShareAiAgentTask,
  startAShareAiAgent,
  stopAShareAiAgent,
  testAShareAiAgentDingtalk,
  lookupAShareAiAgent,
} from '../api/aShareAiAgent'
import './AShareAiAgent.css'

const INTERVALS = [
  { id: '30', label: '30分钟' },
  { id: '60', label: '60分钟' },
  { id: 'D', label: '日线' },
]

async function lookupSymbol(q) {
  const raw = String(q || '').trim()
  if (!raw) return null
  try {
    const hit = await lookupAShareAiAgent(raw)
    if (hit?.ok && hit.code) {
      return { code: String(hit.code).padStart(6, '0'), name: String(hit.name || '') }
    }
  } catch {
    /* ignore */
  }
  return null
}

function useAShareAutoFill(code, setCode, name, setName) {
  const codeRef = useRef(code)
  const nameRef = useRef(name)
  const seq = useRef(0)
  const touched = useRef({ code: false, name: false })
  codeRef.current = code
  nameRef.current = name

  useEffect(() => {
    if (!touched.current.code) return undefined
    const q = String(code || '').trim()
    if (!/^\d{6}$/.test(q)) return undefined
    const my = seq.current + 1
    seq.current = my
    const t = window.setTimeout(async () => {
      const hit = await lookupSymbol(q)
      if (my !== seq.current || !hit) return
      if (hit.name && hit.name !== nameRef.current && !/^\d{6}$/.test(hit.name)) {
        setName(hit.name)
      }
    }, 280)
    return () => window.clearTimeout(t)
  }, [code, setName])

  useEffect(() => {
    if (!touched.current.name) return undefined
    const q = String(name || '').trim()
    if (q.length < 2 || !/[\u4e00-\u9fff]/.test(q)) return undefined
    const my = seq.current + 1
    seq.current = my
    const t = window.setTimeout(async () => {
      const hit = await lookupSymbol(q)
      if (my !== seq.current || !hit) return
      if (hit.code && hit.code !== codeRef.current) setCode(hit.code)
      if (hit.name && hit.name !== nameRef.current) setName(hit.name)
    }, 380)
    return () => window.clearTimeout(t)
  }, [name, setCode, setName])

  return {
    onCodeChange: (v) => {
      touched.current.code = true
      setCode(v)
    },
    onNameChange: (v) => {
      touched.current.name = true
      setName(v)
    },
  }
}

const AShareAiAgent = () => {
  const [meta, setMeta] = useState(null)
  const [status, setStatus] = useState({ running: false, tasks: [], recent: [] })
  const [code, setCode] = useState('600519')
  const [name, setName] = useState('贵州茅台')
  const [klineInterval, setKlineInterval] = useState('30')
  const [loading, setLoading] = useState(false)
  const [prefs, setPrefs] = useState({ confirmed: {}, draft: {} })
  const [feedback, setFeedback] = useState('')
  const [btCode, setBtCode] = useState('600519')
  const [btName, setBtName] = useState('贵州茅台')
  const [btStart, setBtStart] = useState('')
  const [btEnd, setBtEnd] = useState('')
  const [btInterval, setBtInterval] = useState('D')
  const [btLoading, setBtLoading] = useState(false)
  const [btElapsed, setBtElapsed] = useState(0)
  const [btResult, setBtResult] = useState(null)
  const [lastDecide, setLastDecide] = useState(null)
  const [tradeSymbols, setTradeSymbols] = useState([])
  const [trades, setTrades] = useState([])
  const [tradeFilterCode, setTradeFilterCode] = useState('')
  const [tradeOpenToday, setTradeOpenToday] = useState(null)
  const [tradeLoading, setTradeLoading] = useState(false)
  const chartRef = useRef(null)
  const chartInst = useRef(null)
  const btSectionRef = useRef(null)
  const taskFill = useAShareAutoFill(code, setCode, name, setName)
  const btFill = useAShareAutoFill(btCode, setBtCode, btName, setBtName)

  useEffect(() => {
    if (!btLoading) {
      setBtElapsed(0)
      return undefined
    }
    const t0 = Date.now()
    const t = setInterval(() => setBtElapsed(Math.floor((Date.now() - t0) / 1000)), 1000)
    return () => clearInterval(t)
  }, [btLoading])

  const refreshTrades = useCallback(async (codeFilter) => {
    setTradeLoading(true)
    try {
      const filter = codeFilter === undefined ? tradeFilterCode : codeFilter
      const [syms, list] = await Promise.all([
        getAShareAiAgentTradeSymbols({ limit: 80 }).catch(() => ({ items: [] })),
        getAShareAiAgentTrades({
          code: filter || undefined,
          limit: 120,
        }).catch(() => ({ items: [], open_buy_today: null })),
      ])
      setTradeSymbols(syms?.items || [])
      setTrades(list?.items || [])
      setTradeOpenToday(list?.open_buy_today || null)
    } catch {
      /* ignore */
    } finally {
      setTradeLoading(false)
    }
  }, [tradeFilterCode])

  const refresh = useCallback(async () => {
    try {
      const [m, s, p] = await Promise.all([
        getAShareAiAgentMeta().catch(() => null),
        getAShareAiAgentStatus().catch(() => ({ running: false, tasks: [] })),
        getAShareAiAgentPrefs().catch(() => ({ confirmed: {}, draft: {} })),
      ])
      if (m) setMeta(m)
      setStatus(s || { running: false, tasks: [] })
      setPrefs(p || { confirmed: {}, draft: {} })
    } catch {
      /* ignore */
    }
  }, [])

  useEffect(() => {
    void refresh()
    void refreshTrades('')
    const t = setInterval(() => void refresh(), 20000)
    return () => clearInterval(t)
  }, [refresh, refreshTrades])

  useEffect(() => {
    if (!btResult?.bars?.length) return undefined
    let disposed = false
    let chart = chartInst.current
    const timer = window.setTimeout(() => {
      if (disposed || !chartRef.current) return
      if (!chart) {
        chart = echarts.init(chartRef.current)
        chartInst.current = chart
      }
      const times = btResult.bars.map((b) =>
        new Date(b.time).toLocaleString('zh-CN', { hour12: false })
      )
      const ohlc = btResult.bars.map((b) => [b.open, b.close, b.low, b.high])
      const markPoints = (btResult.markers || []).map((m) => {
        const idx = btResult.bars.findIndex((b) => b.time === m.time)
        return {
          name: m.side === 'buy' ? '买' : '卖',
          coord: [Math.max(0, idx), m.price],
          value: m.side,
          itemStyle: { color: m.side === 'buy' ? '#16a34a' : '#dc2626' },
        }
      })
      chart.setOption(
        {
          backgroundColor: 'transparent',
          tooltip: { trigger: 'axis' },
          grid: { left: 48, right: 24, top: 24, bottom: 48 },
          xAxis: { type: 'category', data: times, axisLabel: { color: '#94a3b8' } },
          yAxis: {
            scale: true,
            axisLabel: { color: '#94a3b8' },
            splitLine: { lineStyle: { color: '#1e293b' } },
          },
          series: [
            {
              type: 'candlestick',
              data: ohlc,
              itemStyle: {
                color: '#ef4444',
                color0: '#22c55e',
                borderColor: '#ef4444',
                borderColor0: '#22c55e',
              },
              markPoint: {
                symbol: 'pin',
                symbolSize: 42,
                data: markPoints,
                label: { formatter: '{b}', color: '#fff' },
              },
            },
          ],
        },
        true
      )
      chart.resize()
    }, 80)
    const onResize = () => chartInst.current?.resize()
    window.addEventListener('resize', onResize)
    return () => {
      disposed = true
      window.clearTimeout(timer)
      window.removeEventListener('resize', onResize)
    }
  }, [btResult])

  const handleStart = async () => {
    setLoading(true)
    try {
      const q = /^\d{6}$/.test(code.trim()) ? code.trim() : name.trim() || code.trim()
      const hit = await lookupSymbol(q)
      const c = (hit?.code || code).trim()
      const n = (hit?.name || name).trim()
      if (!c) return alert('请输入代码或名称')
      if (hit?.code) setCode(hit.code)
      if (hit?.name) setName(hit.name)
      await startAShareAiAgent({
        tasks: [{ code: c, name: n, interval: klineInterval }],
      })
      alert('已启动/追加任务')
      await refresh()
    } catch (e) {
      alert(e?.response?.data?.detail || '启动失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDecide = async (push) => {
    setLoading(true)
    try {
      const q = /^\d{6}$/.test(code.trim()) ? code.trim() : name.trim() || code.trim()
      const hit = await lookupSymbol(q)
      const c = (hit?.code || code).trim()
      const n = (hit?.name || name).trim()
      if (hit?.code) setCode(hit.code)
      if (hit?.name) setName(hit.name)
      const res = await decideAShareAiAgent({
        code: c,
        name: n,
        interval: klineInterval,
        push,
      })
      setLastDecide(res)
      if (!res?.ok) alert(res?.error || '决策失败')
      await refresh()
      await refreshTrades(tradeFilterCode)
    } catch (e) {
      alert(e?.response?.data?.detail || '决策失败')
    } finally {
      setLoading(false)
    }
  }

  const handleBacktest = async () => {
    const q = /^\d{6}$/.test((btCode || '').trim()) ? (btCode || '').trim() : (btName || '').trim() || (btCode || '').trim()
    const hit = await lookupSymbol(q)
    const c = (hit?.code || btCode || '').trim()
    if (!c) {
      alert('请填写回测标的代码或名称')
      return
    }
    if (hit?.code) setBtCode(hit.code)
    if (hit?.name) setBtName(hit.name)
    setBtLoading(true)
    setBtResult(null)
    btSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    try {
      const res = await backtestAShareAiAgent({
        code: c,
        name: (hit?.name || btName || '').trim(),
        interval: btInterval,
        start: btStart,
        end: btEnd,
        max_llm_calls: 12,
      })
      if (!res?.ok) {
        alert(res?.error || '回测失败')
        return
      }
      setBtResult(res)
      // 等 DOM 挂上图表容器再画
      setTimeout(() => {
        window.dispatchEvent(new Event('resize'))
      }, 50)
    } catch (e) {
      const detail = e?.response?.data?.detail
      const msg =
        typeof detail === 'string'
          ? detail
          : e?.code === 'ECONNABORTED'
            ? '回测超时：请缩短日期区间或稍后再试'
            : e?.message || '回测失败（可能较慢/超时）'
      alert(msg)
    } finally {
      setBtLoading(false)
    }
  }

  const d = lastDecide?.decision

  return (
    <div className="asa-page">
      <header className="asa-hero">
        <div>
          <p className="asa-eyebrow">A-Share Adaptive Agent</p>
          <h1>A股 AI 自适应策略</h1>
          <p className="asa-sub">
            技术面为主 · 30分钟日内 T0（底仓不动、买卖配对、尾盘强平）· 买卖信号入库 · 涨跌停硬规则
          </p>
        </div>
        <div className={`asa-pill${status.running ? ' on' : ''}`}>
          {status.running ? `运行中 · ${status.tasks?.length || 0} 任务` : '未运行'}
        </div>
      </header>

      <section className="asa-card">
        <h2>任务控制</h2>
        <div className="asa-grid">
          <label>
            代码
            <input
              value={code}
              onChange={(e) => taskFill.onCodeChange(e.target.value)}
              placeholder="600519"
            />
          </label>
          <label>
            名称
            <input
              value={name}
              onChange={(e) => taskFill.onNameChange(e.target.value)}
              placeholder="贵州茅台"
            />
          </label>
          <label>
            周期
            <select value={klineInterval} onChange={(e) => setKlineInterval(e.target.value)}>
              {INTERVALS.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="asa-hint">输入 6 位代码会自动填名称；输入中文名称会自动填代码。</p>
        <div className="asa-actions">
          <button type="button" className="asa-btn primary" disabled={loading} onClick={handleStart}>
            启动/追加任务
          </button>
          <button
            type="button"
            className="asa-btn"
            disabled={!status.running}
            onClick={async () => {
              await stopAShareAiAgent()
              await refresh()
            }}
          >
            全部停止
          </button>
          <button type="button" className="asa-btn" disabled={loading} onClick={() => handleDecide(false)}>
            立即决策
          </button>
          <button type="button" className="asa-btn accent" disabled={loading} onClick={() => handleDecide(true)}>
            决策并推钉钉
          </button>
          <button
            type="button"
            className="asa-btn"
            onClick={async () => {
              try {
                await testAShareAiAgentDingtalk()
                alert('测试卡片已发送')
              } catch (e) {
                alert(e?.response?.data?.detail || '发送失败')
              }
            }}
          >
            测试 ActionCard
          </button>
        </div>
        <p className="asa-hint">
          Webhook：{meta?.webhook_configured ? '已配置' : '未配置（设 A_SHARE_AI_AGENT_DINGTALK_WEBHOOK）'} ·
          推送截止 {meta?.push_cutoff || '15:00'}
        </p>
      </section>

      <section className="asa-card">
        <h2>监控中</h2>
        {status.tasks?.length ? (
          <table className="asa-table">
            <thead>
              <tr>
                <th>代码</th>
                <th>名称</th>
                <th>周期</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {status.tasks.map((t) => (
                <tr key={`${t.code}-${t.interval}`}>
                  <td>{t.code}</td>
                  <td>{t.name || '—'}</td>
                  <td>{INTERVALS.find((x) => x.id === t.interval)?.label || t.interval}</td>
                  <td>
                    <button
                      type="button"
                      className="asa-link-del"
                      onClick={async () => {
                        if (!window.confirm('删除该任务？')) return
                        await removeAShareAiAgentTask({ code: t.code, interval: t.interval })
                        await refresh()
                      }}
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="asa-empty">暂无任务</p>
        )}
      </section>

      {d && (
        <section className="asa-card">
          <h2>最近决策</h2>
          <div className={`asa-decision ${d.action}`}>
            <strong>{String(d.action || '').toUpperCase()}</strong>
            <span>{d.thesis}</span>
          </div>
          <pre className="asa-json">{JSON.stringify(d, null, 2)}</pre>
        </section>
      )}

      <section className="asa-card">
        <h2>点评草稿 / 刷新并生效风格</h2>
        <p className="asa-hint">
          钉钉引用信号回复后：机器人回「已收录」= 草稿成功（出现在左侧待确认）。点「刷新并生效风格」后：待确认清空、右侧已生效增加，群里再推「纠偏已生效」。
          {prefs.confirmed?.confirmed_at ? ` 上次生效：${prefs.confirmed.confirmed_at}` : ''}
        </p>
        <textarea
          rows={3}
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="例：量能萎缩时不应因 MACD 金叉买入，警惕诱多…"
        />
        <div className="asa-actions">
          <button
            type="button"
            className="asa-btn"
            onClick={async () => {
              if (!feedback.trim()) return
              await postAShareAiAgentFeedback({ text: feedback, code, interval: klineInterval })
              setFeedback('')
              await refresh()
              alert('已写入草稿')
            }}
          >
            写入偏好草稿
          </button>
          <button
            type="button"
            className="asa-btn primary"
            onClick={async () => {
              if (!window.confirm('将草稿合并进正式风格偏好，并刷新提示词附言？生效后钉钉群会推一条回执。')) return
              const res = await confirmAShareAiAgentPrefs()
              await refresh()
              const n = res?.confirmed?.newly_count ?? res?.confirmed?.newly_confirmed?.length ?? 0
              const ding = res?.dingtalk?.ok ? '群回执已发送' : `群回执未发送：${res?.dingtalk?.detail || '未知'}`
              alert(`纠偏已生效：本次 ${n} 条。${ding}。下一轮扫描会带上这些纠偏。`)
            }}
          >
            刷新并生效风格
          </button>
        </div>
        <div className="asa-prefs">
          <div>
            <h3>待确认 ({prefs.draft?.pending?.length || 0})</h3>
            <ul>
              {(prefs.draft?.pending || []).slice(-8).map((p, i) => (
                <li key={i}>{p.text}</li>
              ))}
            </ul>
          </div>
          <div>
            <h3>已生效 ({prefs.confirmed?.style_notes?.length || 0})</h3>
            <ul>
              {(prefs.confirmed?.style_notes || []).slice(-8).map((p, i) => (
                <li key={i}>{p.text}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      </section>

      <section className="asa-card">
        <h2>交易台账看板</h2>
        <p className="asa-hint">
          记录所有买入/卖出信号（含 T0 忽略、尾盘强平）。30 分钟：无日内仓时首笔卖出忽略；有仓须先卖再买；14:50 后强制平今日买入。
          {tradeOpenToday
            ? ` 当前筛选标的今日未平买入 #${tradeOpenToday.id} @ ${tradeOpenToday.price ?? '—'}`
            : ''}
        </p>
        <div className="asa-actions" style={{ flexWrap: 'wrap', gap: 8 }}>
          <input
            style={{ maxWidth: 140 }}
            value={tradeFilterCode}
            onChange={(e) => setTradeFilterCode(e.target.value)}
            placeholder="筛选代码"
          />
          <button
            type="button"
            className="asa-btn"
            disabled={tradeLoading}
            onClick={() => refreshTrades(tradeFilterCode)}
          >
            {tradeLoading ? '加载中…' : '刷新台账'}
          </button>
          <button
            type="button"
            className="asa-btn"
            onClick={() => {
              setTradeFilterCode('')
              refreshTrades('')
            }}
          >
            全部标的
          </button>
        </div>
        {tradeSymbols.length > 0 && (
          <div className="asa-trade-syms">
            {tradeSymbols.slice(0, 24).map((s) => (
              <button
                key={`${s.code}-${s.interval}`}
                type="button"
                className={`asa-chip${tradeFilterCode === s.code ? ' on' : ''}`}
                onClick={() => {
                  setTradeFilterCode(s.code)
                  refreshTrades(s.code)
                }}
              >
                {s.name || s.code} · 买{s.buy_n}/卖{s.sell_n}
                {s.ignored_n ? ` · 忽略${s.ignored_n}` : ''}
                {s.force_n ? ` · 强平${s.force_n}` : ''}
              </button>
            ))}
          </div>
        )}
        <div className="asa-table-wrap">
          <table className="asa-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>标的</th>
                <th>周期</th>
                <th>方向</th>
                <th>状态</th>
                <th>价格</th>
                <th>配对</th>
                <th>理由</th>
              </tr>
            </thead>
            <tbody>
              {trades.length === 0 ? (
                <tr>
                  <td colSpan={8} className="asa-muted">
                    暂无记录（产生买卖信号后会出现在此）
                  </td>
                </tr>
              ) : (
                trades.map((t) => (
                  <tr key={t.id}>
                    <td>{t.as_of || t.created_at || t.trade_date}</td>
                    <td>
                      {t.name || ''} {t.code}
                    </td>
                    <td>{t.interval === '30' ? '30m' : t.interval === '60' ? '60m' : t.interval}</td>
                    <td className={t.side === 'buy' ? 'asa-buy' : 'asa-sell'}>
                      {t.side === 'buy' ? '买入' : '卖出'}
                    </td>
                    <td>
                      {t.status === 'executed'
                        ? '已执行'
                        : t.status === 'ignored'
                          ? '已忽略'
                          : t.status === 'force_close'
                            ? '尾盘强平'
                            : t.status}
                    </td>
                    <td>{t.price != null ? Number(t.price).toFixed(3) : '—'}</td>
                    <td>{t.pair_id != null ? `#${t.pair_id}` : '—'}</td>
                    <td className="asa-thesis" title={t.thesis || t.reason || ''}>
                      {(t.reason || t.thesis || '—').slice(0, 48)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="asa-card" ref={btSectionRef}>
        <h2>LLM 回测（最长约 1 年 · 采样约 12 次调用）</h2>
        <p className="asa-hint">
            可单独选择回测标的。回测按「空仓→买入→持仓评估卖出」配对成交。
            不会用今天的 PE/PB 去否决历史买点（避免 3 个月全是观望）。
        </p>
        <div className="asa-grid">
          <label>
            回测代码
            <input
              value={btCode}
              onChange={(e) => btFill.onCodeChange(e.target.value)}
              placeholder="如 603629"
            />
          </label>
          <label>
            回测名称
            <input
              value={btName}
              onChange={(e) => btFill.onNameChange(e.target.value)}
              placeholder="如 利通电子"
            />
          </label>
          <label>
            周期
            <select value={btInterval} onChange={(e) => setBtInterval(e.target.value)}>
              {INTERVALS.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            开始
            <input type="date" value={btStart} onChange={(e) => setBtStart(e.target.value)} />
          </label>
          <label>
            结束
            <input type="date" value={btEnd} onChange={(e) => setBtEnd(e.target.value)} />
          </label>
        </div>
        <div className="asa-actions">
          <button
            type="button"
            className="asa-btn"
            disabled={btLoading}
            onClick={() => {
              setBtCode(code)
              setBtName(name)
            }}
          >
            同步上方任务标的
          </button>
          <button type="button" className="asa-btn primary" disabled={btLoading} onClick={handleBacktest}>
            {btLoading ? `回测中… ${btElapsed}s（约需 1～3 分钟）` : `开始回测 ${btCode || ''}`}
          </button>
        </div>
        {btLoading && (
          <p className="asa-hint">
            正在回测 {btCode} {btName}，请勿刷新。若超过 10 分钟仍无结果，请缩短日期后再试。
          </p>
        )}
        {btResult?.ok && (
          <>
            <p className="asa-hint">
              标的 {btResult.code} {btResult.name || ''} · LLM 调用 {btResult.llm_calls} 次
              {btResult.llm_fail ? `（失败 ${btResult.llm_fail}）` : ''}
              {' · '}
              执行 买 {(btResult.action_counts && btResult.action_counts.buy) || 0} /
              卖 {(btResult.action_counts && btResult.action_counts.sell) || 0} /
              观望 {(btResult.action_counts && btResult.action_counts.hold) || 0}
              {' · '}
              成交 {(btResult.trades || []).length} 笔
            </p>
            {btResult.summary && (
              <div className="asa-summary">
                <div>
                  <span>总收益率</span>
                  <strong className={Number(btResult.summary.total_return_pct) >= 0 ? 'up' : 'down'}>
                    {Number(btResult.summary.total_return_pct).toFixed(2)}%
                  </strong>
                </div>
                <div>
                  <span>胜率</span>
                  <strong>{Number(btResult.summary.win_rate).toFixed(1)}%</strong>
                </div>
                <div>
                  <span>平均单笔</span>
                  <strong className={Number(btResult.summary.avg_return_pct) >= 0 ? 'up' : 'down'}>
                    {Number(btResult.summary.avg_return_pct).toFixed(2)}%
                  </strong>
                </div>
                <div>
                  <span>赢/亏</span>
                  <strong>
                    {btResult.summary.wins}/{btResult.summary.losses}
                  </strong>
                </div>
                <div>
                  <span>最大单笔盈</span>
                  <strong className="up">{Number(btResult.summary.max_win_pct).toFixed(2)}%</strong>
                </div>
                <div>
                  <span>最大单笔亏</span>
                  <strong className="down">{Number(btResult.summary.max_loss_pct).toFixed(2)}%</strong>
                </div>
              </div>
            )}
            {(btResult.trades || []).length === 0 && (
              <p className="asa-hint">本区间未开出完整买卖对（可能一直观望）。可换日期或标的再试。</p>
            )}
            <div className="asa-chart" ref={chartRef} />
            {(btResult.trades || []).length > 0 && (
              <div className="asa-decisions">
                <h3>成交明细（买→卖配对）</h3>
                <ul>
                  {(btResult.trades || []).map((t, i) => (
                    <li key={i}>
                      <strong className={Number(t.return_pct) >= 0 ? 'up' : 'down'}>
                        {Number(t.return_pct) >= 0 ? '+' : ''}
                        {Number(t.return_pct).toFixed(2)}%
                      </strong>
                      {' · '}
                      买 {Number(t.entry_price).toFixed(2)} → 卖 {Number(t.exit_price).toFixed(2)}
                      {' · '}
                      持有 {t.bars_held} 根
                      {t.exit_reason === 'force_close' ? ' · 期末强平' : ''}
                      <br />
                      <span className="asa-muted">开：{t.entry_thesis || '—'}</span>
                      <br />
                      <span className="asa-muted">平：{t.exit_thesis || '—'}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {(btResult.decisions || []).length > 0 && (
              <div className="asa-decisions">
                <h3>采样决策摘要</h3>
                <ul>
                  {(btResult.decisions || []).slice(-12).map((x, i) => (
                    <li key={i}>
                      <strong>{String(x.action || '').toUpperCase()}</strong>
                      {x.llm_action && x.llm_action !== x.action ? `（模型:${x.llm_action}）` : ''}
                      {' · '}
                      {x.price != null ? Number(x.price).toFixed(2) : '—'}
                      {x.holding_before ? ' · 持仓中' : ' · 空仓'}
                      {' · '}
                      {x.thesis || '—'}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  )
}

export default AShareAiAgent
