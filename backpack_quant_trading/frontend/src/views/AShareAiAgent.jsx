import React, { useCallback, useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts'
import {
  backtestAShareAiAgent,
  confirmAShareAiAgentPrefs,
  decideAShareAiAgent,
  getAShareAiAgentMeta,
  getAShareAiAgentPrefs,
  getAShareAiAgentStatus,
  postAShareAiAgentFeedback,
  removeAShareAiAgentTask,
  startAShareAiAgent,
  stopAShareAiAgent,
  testAShareAiAgentDingtalk,
} from '../api/aShareAiAgent'
import './AShareAiAgent.css'

const INTERVALS = [
  { id: '30', label: '30分钟' },
  { id: '60', label: '60分钟' },
  { id: 'D', label: '日线' },
]

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
  const chartRef = useRef(null)
  const chartInst = useRef(null)
  const btSectionRef = useRef(null)

  useEffect(() => {
    if (!btLoading) {
      setBtElapsed(0)
      return undefined
    }
    const t0 = Date.now()
    const t = setInterval(() => setBtElapsed(Math.floor((Date.now() - t0) / 1000)), 1000)
    return () => clearInterval(t)
  }, [btLoading])

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
    const t = setInterval(() => void refresh(), 20000)
    return () => clearInterval(t)
  }, [refresh])

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
    if (!code.trim()) return alert('请输入代码')
    setLoading(true)
    try {
      await startAShareAiAgent({
        tasks: [{ code: code.trim(), name: name.trim(), interval: klineInterval }],
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
      const res = await decideAShareAiAgent({
        code: code.trim(),
        name: name.trim(),
        interval: klineInterval,
        push,
      })
      setLastDecide(res)
      if (!res?.ok) alert(res?.error || '决策失败')
      await refresh()
    } catch (e) {
      alert(e?.response?.data?.detail || '决策失败')
    } finally {
      setLoading(false)
    }
  }

  const handleBacktest = async () => {
    const c = (btCode || '').trim()
    if (!c) {
      alert('请填写回测标的代码')
      return
    }
    setBtLoading(true)
    setBtResult(null)
    btSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    try {
      const res = await backtestAShareAiAgent({
        code: c,
        name: (btName || '').trim(),
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
            基本面优先 · 量能为技术终裁 · T+1/涨跌停硬规则 · 交易时段扫描 · 15:00 后不推送 · OpenClaw ActionCard
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
            <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="600519" />
          </label>
          <label>
            名称
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="贵州茅台" />
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
        <p className="asa-hint">钉钉 Stream 纠偏会先进 RAG 与下方草稿；点「刷新并生效风格」后才会并入下一轮扫描提示词。</p>
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
              if (!window.confirm('将草稿合并进正式风格偏好，并刷新提示词附言？')) return
              await confirmAShareAiAgentPrefs()
              await refresh()
              alert('已刷新并生效风格，下一轮扫描会带上这些纠偏')
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

      <section className="asa-card" ref={btSectionRef}>
        <h2>LLM 回测（最长约 1 年 · 采样约 12 次调用）</h2>
        <p className="asa-hint">
          可单独选择回测标的（与上方实时任务互不影响）。页面默认示例是贵州茅台 600519，改成你的代码即可。采样约 12 次 LLM，通常 1～3 分钟。
        </p>
        <div className="asa-grid">
          <label>
            回测代码
            <input
              value={btCode}
              onChange={(e) => setBtCode(e.target.value)}
              placeholder="如 603629"
            />
          </label>
          <label>
            回测名称
            <input
              value={btName}
              onChange={(e) => setBtName(e.target.value)}
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
              买 {(btResult.action_counts && btResult.action_counts.buy) || 0} /
              卖 {(btResult.action_counts && btResult.action_counts.sell) || 0} /
              观望 {(btResult.action_counts && btResult.action_counts.hold) || 0}
              {' · '}
              图上标注 {(btResult.markers || []).length} 个买卖点
            </p>
            {(btResult.markers || []).length === 0 && (
              <p className="asa-hint">
                本区间采样点均为观望/未通过硬规则，所以图上无买卖钉。下方可查看每次采样的结论摘要（属策略风格偏保守，不一定是程序坏了）。
              </p>
            )}
            <div className="asa-chart" ref={chartRef} />
            {(btResult.decisions || []).length > 0 && (
              <div className="asa-decisions">
                <h3>采样决策摘要</h3>
                <ul>
                  {(btResult.decisions || []).slice(-12).map((x, i) => (
                    <li key={i}>
                      <strong>{String(x.action || '').toUpperCase()}</strong>
                      {x.raw_action && x.raw_action !== x.action ? `（原始:${x.raw_action}）` : ''}
                      {' · '}
                      {x.price != null ? Number(x.price).toFixed(2) : '—'}
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
