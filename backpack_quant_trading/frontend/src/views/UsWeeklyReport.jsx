import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import * as echarts from 'echarts'
import {
  getBubbleHistory,
  getLatestBubbleAnalysis,
  getBubbleReportById,
  getBubbleStrategies,
  triggerBubbleAnalyze,
} from '../api/usWeeklyReport'
import AisPageShell from '../components/AisPageShell'
import './UsWeeklyReport.css'

const fmtScore = (v, max) =>
  v == null ? '—' : `${typeof v === 'number' ? v.toFixed(0) : v} / ${max ?? '—'}`

/** 模型偶发把数组字段写成对象；`(x||[]).map` 会对真值对象崩溃 */
const asList = (v) => (Array.isArray(v) ? v : [])

// 根据「市场状态」匹配情绪色
const marketStateStyle = (s = '') => {
  if (!s) return { color: '#fff', glow: 'rgba(255,255,255,0.4)' }
  if (/破裂|信用压力/.test(s)) return { color: '#f87171', glow: 'rgba(239,68,68,0.55)' }
  if (/下跌/.test(s)) return { color: '#fb7185', glow: 'rgba(244,63,94,0.5)' }
  if (/顶部震荡|震荡/.test(s)) return { color: '#fde047', glow: 'rgba(250,204,21,0.5)' }
  if (/加速/.test(s)) return { color: '#fb923c', glow: 'rgba(251,146,60,0.6)' }
  if (/强趋势|强势|过热/.test(s)) return { color: '#fbbf24', glow: 'rgba(251,191,36,0.55)' }
  if (/上涨|趋势/.test(s)) return { color: '#4ade80', glow: 'rgba(74,222,128,0.5)' }
  return { color: '#fff', glow: 'rgba(255,255,255,0.4)' }
}

const SegmentBar = ({ score, max, color }) => {
  const pct = score != null && max ? Math.max(0, Math.min(100, (Number(score) / Number(max)) * 100)) : 0
  return (
    <div className="uwr-seg-bar">
      <div className="uwr-seg-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  )
}

const StatPill = ({ label, value, tone = 'default' }) => (
  <div className={`uwr-pill uwr-pill-${tone}`}>
    <span className="uwr-pill-label">{label}</span>
    <span className="uwr-pill-value">{value || '—'}</span>
  </div>
)

const Stars = ({ n = 0 }) => (
  <span className="uwr-stars" aria-label={`${n}星`}>
    {'★'.repeat(Math.max(0, Math.min(5, n)))}
    <span className="uwr-stars-dim">{'★'.repeat(Math.max(0, 5 - n))}</span>
  </span>
)

/** 将 Markdown 按 ## / 【Lx】 拆成章节卡片 */
const parseMdSections = (md = '') => {
  const lines = String(md || '').split('\n')
  const sections = []
  let cur = { title: '', body: [] }
  const flush = () => {
    const body = cur.body.join('\n').trim()
    const title = cur.title || ''
    // 去掉附注 / 免责声明
    if (/附注|数据溯源|免责声明/.test(title)) return
    if (cur.title || body) sections.push({ title, body })
  }
  for (const line of lines) {
    const t = line.trim()
    if (/^#{1,3}\s/.test(line) || /^【L\d】/.test(t) || /^##\s*【L/.test(line) || /^【附注】/.test(t)
      || /^#{1,3}\s*[一二三四五六七八九十]+[、.]/.test(line)
      || /^[一二三四五六七八九十]+[、.]/.test(t)) {
      flush()
      cur = { title: t.replace(/^#+\s*/, ''), body: [] }
    } else {
      cur.body.push(line)
    }
  }
  flush()
  return sections.length ? sections : [{ title: '报告正文', body: String(md || '').trim() }]
}

const sectionTone = (title = '') => {
  if (/L1|终端|一[、.]|宏观/.test(title)) return 'cyan'
  if (/L2|供应链|地图|二[、.]|产业/.test(title)) return 'indigo'
  if (/L3|卡点|竞争|三[、.]|盈利/.test(title)) return 'amber'
  if (/L4|财务|毛利|四[、.]|估值/.test(title)) return 'emerald'
  if (/L5|管理|指引|五[、.]|资金/.test(title)) return 'violet'
  if (/L6|估值|目标价|六[、.]|技术/.test(title)) return 'rose'
  if (/L7|投资|仓位|操作|七[、.]|逆向/.test(title)) return 'sky'
  if (/八[、.]|事件/.test(title)) return 'amber'
  if (/九[、.]|综合|总分/.test(title)) return 'indigo'
  if (/十[、.]|仓位模型|加减仓/.test(title)) return 'emerald'
  if (/十二|十三|十四|投委会|情景/.test(title)) return 'violet'
  if (/附注|免责|一句话/.test(title)) return 'slate'
  return 'indigo'
}

const escapeHtml = (s) =>
  String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')

const inlineMd = (text) => {
  let s = escapeHtml(text)
  s = s.replace(/`([^`]+)`/g, '<code class="ssr-code">$1</code>')
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  s = s.replace(/(^|[^*])\*([^*]+)\*(?!\*)/g, '$1<em>$2</em>')
  return s
}

/** 轻量 Markdown → HTML（表格 / 列表 / 标题 / 引用） */
const markdownToHtml = (md = '') => {
  const lines = String(md || '').replace(/\r\n/g, '\n').split('\n')
  const html = []
  let i = 0
  let inUl = false
  let inOl = false
  const closeLists = () => {
    if (inUl) { html.push('</ul>'); inUl = false }
    if (inOl) { html.push('</ol>'); inOl = false }
  }

  while (i < lines.length) {
    const raw = lines[i]
    const line = raw.trimEnd()
    const t = line.trim()

    // 表格块
    if (t.startsWith('|') && t.includes('|', 1)) {
      closeLists()
      const rows = []
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        const cells = lines[i].trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim())
        if (!cells.every((c) => /^:?-{3,}:?$/.test(c))) rows.push(cells)
        i += 1
      }
      if (rows.length) {
        const head = rows[0]
        const body = rows.slice(1)
        html.push('<div class="ssr-table-wrap"><table class="ssr-table"><thead><tr>')
        head.forEach((c) => html.push(`<th>${inlineMd(c)}</th>`))
        html.push('</tr></thead><tbody>')
        ;(body.length ? body : []).forEach((r) => {
          html.push('<tr>')
          head.forEach((_, j) => html.push(`<td>${inlineMd(r[j] ?? '')}</td>`))
          html.push('</tr>')
        })
        html.push('</tbody></table></div>')
      }
      continue
    }

    if (!t) {
      closeLists()
      html.push('<div class="ssr-spacer"></div>')
      i += 1
      continue
    }

    if (/^#{1,3}\s/.test(t)) {
      closeLists()
      const level = (t.match(/^#+/) || ['#'])[0].length
      const title = t.replace(/^#+\s*/, '')
      html.push(`<h${Math.min(level + 2, 5)} class="ssr-h">${inlineMd(title)}</h${Math.min(level + 2, 5)}>`)
      i += 1
      continue
    }

    if (/^>\s?/.test(t)) {
      closeLists()
      html.push(`<blockquote class="ssr-quote">${inlineMd(t.replace(/^>\s?/, ''))}</blockquote>`)
      i += 1
      continue
    }

    if (/^[-*•]\s+/.test(t)) {
      if (!inUl) { closeLists(); html.push('<ul class="ssr-ul">'); inUl = true }
      html.push(`<li>${inlineMd(t.replace(/^[-*•]\s+/, ''))}</li>`)
      i += 1
      continue
    }

    if (/^\d+[.)、]\s+/.test(t)) {
      if (!inOl) { closeLists(); html.push('<ol class="ssr-ol">'); inOl = true }
      html.push(`<li>${inlineMd(t.replace(/^\d+[.)、]\s+/, ''))}</li>`)
      i += 1
      continue
    }

    if (/^---+$/.test(t)) {
      closeLists()
      html.push('<hr class="ssr-hr" />')
      i += 1
      continue
    }

    closeLists()
    html.push(`<p class="ssr-p">${inlineMd(t)}</p>`)
    i += 1
  }
  closeLists()
  return html.join('')
}

const StockReportSections = ({ markdown }) => {
  const sections = useMemo(() => parseMdSections(markdown), [markdown])
  if (!markdown) {
    return (
      <div className="uwr-card">
        <div className="uwr-meta" style={{ padding: '14px 16px' }}>
          暂无报告。输入股票并点击「生成个股报告」。
        </div>
      </div>
    )
  }
  return (
    <div className="ssr-stack">
      {sections.map((sec, i) => {
        const tone = sectionTone(sec.title)
        return (
          <article key={`${sec.title}-${i}`} className={`ssr-section ssr-tone-${tone}`}>
            {sec.title && (
              <div className="ssr-section-head">
                <span className="ssr-section-badge">{`0${i + 1}`.slice(-2)}</span>
                <h3 className="ssr-section-title">{sec.title}</h3>
              </div>
            )}
            <div
              className="ssr-section-body"
              dangerouslySetInnerHTML={{ __html: markdownToHtml(sec.body) }}
            />
          </article>
        )
      })}
    </div>
  )
}

const UsWeeklyReport = ({ guestOnly = false }) => {
  const [searchParams] = useSearchParams()
  const forceStock =
    guestOnly ||
    searchParams.get('tab') === 'stock' ||
    searchParams.get('mode') === 'stock'
  // weekly=市场周报(美股泡沫周报)；stock=个股分析(美股+A股)
  const [viewMode, setViewMode] = useState(forceStock ? 'stock' : 'weekly') // weekly | stock
  const [strategy, setStrategy] = useState('A')
  const [strategies, setStrategies] = useState([
    { id: 'A', name: '策略A · 供应链个股深度', enabled: true, report_type: 'stock_supply_chain' },
    { id: 'B', name: '策略B · 百分配仓评分卡', enabled: true, report_type: 'stock_scorecard' },
  ])
  const [stockQuery, setStockQuery] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [history, setHistory] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [showHistory, setShowHistory] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState('')
  const chartRef = useRef(null)

  useEffect(() => {
    if (forceStock && viewMode !== 'stock') setViewMode('stock')
  }, [forceStock, viewMode])

  const market = analysis?.market || (viewMode === 'stock' ? 'a_share' : 'us')
  const marketLabel = market === 'a_share' ? 'A股' : '美股'
  const strategyMeta = strategies.find((s) => s.id === strategy) || strategies[0]
  const isStockReport =
    viewMode === 'stock' ||
    ['stock_supply_chain', 'stock_scorecard'].includes(analysis?.report_type)
  const focusLabel = analysis?.stock_name
    ? `${analysis.stock_name}${analysis.symbol ? `（${analysis.symbol}）` : ''}`
    : (analysis?.symbol || '')

  const detectStockMarket = (q) => {
    const s = String(q || '').trim()
    if (!s) return 'a_share'
    if (/^\$?[A-Za-z]{1,5}$/.test(s)) return 'us'
    if (/^\d{6}$/.test(s) || /[\u4e00-\u9fff]/.test(s)) return 'a_share'
    return 'a_share'
  }

  const loadAll = useCallback(async () => {
    try {
      if (viewMode === 'stock') {
        const [latestA, latestU, histA, histU] = await Promise.all([
          getLatestBubbleAnalysis('a_share', { strategy }).catch(() => null),
          getLatestBubbleAnalysis('us', { strategy }).catch(() => null),
          getBubbleHistory(80, 'a_share', { strategy }).catch(() => null),
          getBubbleHistory(80, 'us', { strategy }).catch(() => null),
        ])
        const pickNewer = (a, b) => {
          if (a && !a.empty && b && !b.empty) {
            return (a.generated_at_utc || '') >= (b.generated_at_utc || '') ? a : b
          }
          if (a && !a.empty) return a
          if (b && !b.empty) return b
          return null
        }
        const latest = pickNewer(latestA, latestU)
        if (latest) {
          setAnalysis(latest)
          setSelectedId(latest.generated_at_utc || null)
        } else {
          setAnalysis(null)
          setSelectedId(null)
        }
        const merged = [...(histA?.items || []), ...(histU?.items || [])].filter(
          (h) =>
            ['stock_supply_chain', 'stock_scorecard'].includes(h.report_type) ||
            (h.symbol && h.strategy && ['A', 'B'].includes(String(h.strategy).toUpperCase()))
        )
        setHistory(merged)
        return
      }
      const [latest, hist] = await Promise.all([
        getLatestBubbleAnalysis('us').catch(() => null),
        getBubbleHistory(80, 'us').catch(() => null),
      ])
      if (latest && !latest.empty) {
        setAnalysis(latest)
        setSelectedId(latest.generated_at_utc || null)
      } else {
        setAnalysis(null)
        setSelectedId(null)
      }
      if (hist?.items) setHistory(hist.items)
      else setHistory([])
    } catch (_) {
      // ignore
    }
  }, [viewMode, strategy])

  useEffect(() => {
    if (viewMode !== 'stock') return
    getBubbleStrategies('a_share', 'stock')
      .then((res) => {
        if (res?.items?.length) setStrategies(res.items)
      })
      .catch(() => {})
  }, [viewMode])

  const onSelectReport = useCallback(async (id) => {
    if (!id || id === selectedId) return
    setSelectedId(id)
    const hit = (history || []).find((h) => h.generated_at_utc === id)
    const mkt = hit?.market || (viewMode === 'stock' ? 'a_share' : 'us')
    try {
      const res = await getBubbleReportById(id, mkt)
      if (res && !res.empty) setAnalysis(res)
    } catch (_) {
      // ignore
    }
  }, [selectedId, history, viewMode])

  const onGenerate = useCallback(async () => {
    if (viewMode === 'stock' && !stockQuery.trim()) {
      setGenError('请先输入股票名称或代码（A股如贵州茅台/600519，美股如 NVDA）')
      return
    }
    if (viewMode === 'stock' && strategyMeta && strategyMeta.enabled === false) {
      setGenError(`「${strategyMeta.name || strategy}」尚未开放，请选用策略 A`)
      return
    }
    setGenerating(true)
    setGenError('')
    try {
      const stockMkt = detectStockMarket(stockQuery)
      const res = await triggerBubbleAnalyze({
        market: viewMode === 'stock' ? stockMkt : 'us',
        mode: viewMode === 'stock' ? 'stock' : 'weekly',
        force_refresh: true,
        save: true,
        ...(viewMode === 'stock'
          ? { strategy, symbol: stockQuery.trim() }
          : {}),
      })
      if (res?.ok === false) {
        setGenError(res.error || '生成失败')
      } else if (res && !res.error) {
        setAnalysis(res)
        setSelectedId(res.generated_at_utc || null)
        await loadAll()
      } else {
        setGenError(res?.error || '生成失败')
      }
    } catch (e) {
      setGenError(e?.message || String(e))
    } finally {
      setGenerating(false)
    }
  }, [viewMode, strategy, strategyMeta, stockQuery, loadAll])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  // 主图：泡沫总分曲线（短/中/长/总分 四条折线）
  useEffect(() => {
    if (!chartRef.current || isStockReport) return
    const items = (history || []).filter((x) => x.bubble_total_score != null)
    if (!items.length) return
    const ch = echarts.init(chartRef.current)
    const xs = items.map((x) => (x.generated_at_utc || x.report_date || '').slice(0, 10))
    const mkLine = (name, color, key, width = 2) => ({
      name,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 9,
      data: items.map((x) => (x[key] != null ? x[key] : null)),
      lineStyle: { color, width },
      itemStyle: { color },
      connectNulls: true,
    })
    ch.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          const i = params[0]?.dataIndex ?? 0
          const it = items[i] || {}
          return [
            `<b>${xs[i]}</b>`,
            `短期：${it.short_term_score ?? '—'}/${it.short_term_max ?? 20}`,
            `中期：${it.mid_term_score ?? '—'}/${it.mid_term_max ?? 25}`,
            `长期：${it.long_term_score ?? '—'}/${it.long_term_max ?? 25}`,
          ].join('<br/>')
        },
      },
      legend: { data: ['短期', '中期', '长期'], top: 4, right: 10 },
      grid: { left: 50, right: 24, top: 40, bottom: 32 },
      xAxis: { type: 'category', data: xs, boundaryGap: false },
      yAxis: { type: 'value', min: 0, max: 25, name: '分数 (0-25)' },
      series: [
        mkLine('短期', '#fb7185', 'short_term_score', 2.5),
        mkLine('中期', '#f59e0b', 'mid_term_score', 2.5),
        mkLine('长期', '#a855f7', 'long_term_score', 2.5),
      ],
    })
    const onResize = () => ch.resize()
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      ch.dispose()
    }
  }, [history, isStockReport])

  const report = analysis?.report || null
  const hasStructuredReport = Boolean(
    report && (
      asList(report.top5_events).length ||
      asList(report.synthesis).length ||
      asList(report.actions).length ||
      asList(report.score_short).length
    )
  )
  const coreSummaryText =
    typeof report?.core_summary === 'string'
      ? report.core_summary
      : report?.core_summary?.one_liner || analysis?.one_liner || ''
  // 有卡片时不再强调「Markdown」；附录默认折叠

  const sortedHistory = useMemo(() => {
    let items = [...(history || [])]
    if (isStockReport) {
      items = items.filter((h) =>
        ['stock_supply_chain', 'stock_scorecard'].includes(h.report_type) ||
        (h.symbol && (h.markdown || '').length > 400 && h.report_type !== 'bubble_weekly')
      )
    }
    return items.sort((a, b) => {
      const ta = a.generated_at_utc || a.report_date || ''
      const tb = b.generated_at_utc || b.report_date || ''
      return tb.localeCompare(ta)
    })
  }, [history, isStockReport])

  return (
    <AisPageShell
      title={guestOnly ? '个股分析' : '泡沫检测'}
      subtitle={
        viewMode === 'stock'
          ? '个股分析支持美股与 A 股：策略A 供应链 L1-L7；策略B 百分评分卡。输入代码/名称生成 Markdown 报告。'
          : '美股周度泡沫评分、供应链卡点视角与历史趋势；可切换至个股分析，或钉钉 @分析师 生成周报。'
      }
    >
      <div className="uwr-stack">
      <div className="uwr-toolbar">
        <div className="uwr-toolbar-left">
          {!guestOnly && (
            <div className="uwr-market-toggle" role="tablist" aria-label="模式切换">
              <button
                type="button"
                className={`uwr-market-btn ${viewMode === 'weekly' ? 'active' : ''}`}
                onClick={() => setViewMode('weekly')}
              >
                市场周报
              </button>
              <button
                type="button"
                className={`uwr-market-btn ${viewMode === 'stock' ? 'active' : ''}`}
                onClick={() => setViewMode('stock')}
              >
                个股分析
              </button>
            </div>
          )}
          {viewMode === 'stock' && (
            <div className="uwr-a-share-controls">
              <label className="uwr-field">
                <span className="uwr-field-label">股票</span>
                <input
                  className="uwr-stock-input"
                  type="text"
                  value={stockQuery}
                  onChange={(e) => setStockQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') onGenerate()
                  }}
                  placeholder="A股名称/代码 或 美股代码，如 贵州茅台 / 600519 / NVDA"
                  autoComplete="off"
                />
              </label>
              <label className="uwr-field">
                <span className="uwr-field-label">策略</span>
                <select
                  className="uwr-strategy-select"
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                >
                  {strategies.map((s) => (
                    <option key={s.id} value={s.id} disabled={s.enabled === false}>
                      {s.name}{s.enabled === false ? '（未开放）' : ''}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}
        </div>
        <button
          type="button"
          className="uwr-gen-btn"
          disabled={generating}
          onClick={onGenerate}
        >
          {generating
            ? 'DeepSeek 生成中…'
            : viewMode === 'stock'
              ? '生成个股报告'
              : '生成美股本周周报'}
        </button>
      </div>
      {viewMode === 'stock' && strategyMeta?.description && (
        <div className="uwr-strategy-hint">{strategyMeta.description}</div>
      )}
      {focusLabel && viewMode === 'stock' && (
        <div className="uwr-focus-chip">
          当前报告标的：{focusLabel}
          {analysis?.market ? ` · ${analysis.market === 'us' ? '美股' : 'A股'}` : ''}
        </div>
      )}
      {genError && (
        <div className="uwr-meta" style={{ padding: '10px 14px', color: '#b91c1c' }}>
          {genError}
        </div>
      )}
      {/* 历史周报选择栏 */}
      {sortedHistory.length > 0 && (
        <div className="uwr-history-bar">
          <div className="uwr-history-bar-l">
            <span className="uwr-history-bar-title">{isStockReport ? '历史个股报告' : '历史周报'}</span>
            <span className="uwr-history-bar-count">共 {sortedHistory.length} 期</span>
          </div>
          <div className="uwr-history-tabs">
            {sortedHistory.slice(0, 4).map((h) => {
              const id = h.generated_at_utc
              const date = h.report_date || (h.generated_at_utc || '').slice(0, 10) || '—'
              const active = id === selectedId
              return (
                <button
                  type="button"
                  key={id}
                  className={`uwr-history-tab ${active ? 'active' : ''}`}
                  onClick={() => onSelectReport(id)}
                  title={h.report_label || ''}
                >
                  <span className="uwr-history-tab-date">{date}</span>
                  <span className="uwr-history-tab-score">
                    {isStockReport
                      ? (h.stock_name || h.symbol || '—')
                      : (h.bubble_total_score ?? '—')}
                  </span>
                  {h.report_label && <span className="uwr-history-tab-label">{h.report_label}</span>}
                </button>
              )
            })}
            {sortedHistory.length > 4 && (
              <button
                type="button"
                className="uwr-history-tab uwr-history-tab-more"
                onClick={() => setShowHistory(true)}
              >
                查看全部 ▾
              </button>
            )}
          </div>
        </div>
      )}

      {/* 历史抽屉（全部周报） */}
      {showHistory && (
        <div className="uwr-history-drawer-mask" onClick={() => setShowHistory(false)}>
          <div className="uwr-history-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="uwr-history-drawer-h">
              <span>全部历史周报</span>
              <button type="button" className="uwr-history-close" onClick={() => setShowHistory(false)}>✕</button>
            </div>
            <div className="uwr-history-list">
              {sortedHistory.map((h) => {
                const id = h.generated_at_utc
                const date = h.report_date || id?.slice(0, 10) || '—'
                const active = id === selectedId
                return (
                  <button
                    type="button"
                    key={id}
                    className={`uwr-history-item ${active ? 'active' : ''}`}
                    onClick={() => {
                      onSelectReport(id)
                      setShowHistory(false)
                    }}
                  >
                    <div className="uwr-history-item-l">
                      <div className="uwr-history-item-date">{date}</div>
                      <div className="uwr-history-item-meta">
                        <span>{h.stage || '—'}</span>
                        <span>·</span>
                        <span>{h.market_state || '—'}</span>
                        <span>·</span>
                        <span>下周：{h.next_week_bias || '—'}</span>
                      </div>
                      {h.one_liner && <div className="uwr-history-item-one">{h.one_liner}</div>}
                    </div>
                    <div className="uwr-history-item-r">
                      <div className="uwr-history-item-score">
                        {h.bubble_total_score ?? '—'}
                      </div>
                      {!h.has_report && <div className="uwr-history-item-seed">仅评分摘要</div>}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {isStockReport ? (
        <>
          <div className="ssr-hero">
            <div className="ssr-hero-tag">
              {strategyMeta?.report_type === 'stock_scorecard' || analysis?.report_type === 'stock_scorecard'
                ? '百分配仓评分卡 · 个股'
                : '供应链瓶颈投研 · 个股深度'}
            </div>
            <h2 className="ssr-hero-title">
              {focusLabel || stockQuery.trim() || '—'}
            </h2>
            <div className="ssr-hero-sub">
              报告日期：{analysis?.report_date || (analysis?.generated_at_utc || '').slice(0, 10) || '—'}
              {analysis?.one_liner && <> ｜ {analysis.one_liner}</>}
            </div>
          </div>
          <StockReportSections markdown={analysis?.markdown} />
        </>
      ) : (
        <>
      <div className="uwr-hero">
        <div className="uwr-hero-left">
          <div className="uwr-hero-tag">泡沫检测 · {marketLabel} · 周度</div>
          <h2
            className="uwr-hero-title"
            style={{
              color: marketStateStyle(analysis?.market_state).color,
              textShadow: `0 0 18px ${marketStateStyle(analysis?.market_state).glow}`,
            }}
          >
            {analysis?.market_state || '—'}
          </h2>
          <div className="uwr-hero-sub">
            报告日期：{analysis?.report_date || (analysis?.generated_at_utc || '').slice(0, 10) || '—'}
            ｜下周倾向：<b>{analysis?.next_week_bias || '—'}</b>
          </div>
          {analysis?.one_liner && <div className="uwr-hero-one">{analysis.one_liner}</div>}
        </div>

        <div className="uwr-hero-right">
          <div className="uwr-score-3">
            <div className="uwr-score-cell">
              <div className="uwr-score-cell-h">短期 1-4 周</div>
              <div className="uwr-score-cell-v" style={{ color: '#fda4af' }}>
                {fmtScore(analysis?.short_term_score, analysis?.short_term_max ?? 20)}
              </div>
              <SegmentBar score={analysis?.short_term_score} max={analysis?.short_term_max ?? 20} color="#fb7185" />
            </div>
            <div className="uwr-score-cell">
              <div className="uwr-score-cell-h">中期 3-6 月</div>
              <div className="uwr-score-cell-v" style={{ color: '#fcd34d' }}>
                {fmtScore(analysis?.mid_term_score, analysis?.mid_term_max ?? 25)}
              </div>
              <SegmentBar score={analysis?.mid_term_score} max={analysis?.mid_term_max ?? 25} color="#f59e0b" />
            </div>
            <div className="uwr-score-cell">
              <div className="uwr-score-cell-h">长期 1-3 年</div>
              <div className="uwr-score-cell-v" style={{ color: '#c4b5fd' }}>
                {fmtScore(analysis?.long_term_score, analysis?.long_term_max ?? 25)}
              </div>
              <SegmentBar score={analysis?.long_term_score} max={analysis?.long_term_max ?? 25} color="#a855f7" />
            </div>
          </div>
        </div>
      </div>

      <div className="uwr-card">
        <div className="uwr-card-h">泡沫评分趋势（短期 / 中期 / 长期，0-25）</div>
        <div ref={chartRef} style={{ height: 360, padding: '8px 12px 16px' }} />
      </div>

      {/* 旧数据无卡片字段：提示重新生成 */}
      {analysis && !hasStructuredReport && (
        <div className="uwr-card">
          <div className="uwr-meta" style={{ padding: '14px 16px' }}>
            本期尚未生成结构化卡片（三层次判断 / 5 件事 / 评分模型等）。
            请点击上方「生成{marketLabel}本周周报」重新生成，即可与历史周报同一版式对齐。
          </div>
        </div>
      )}

      {/* 综合判断 */}
      {asList(report?.synthesis).length > 0 && (
        <div className="uwr-card">
          <div className="uwr-card-h">三层次综合判断</div>
          <div className="uwr-pill-grid">
            {asList(report.synthesis).map((s, i) => (
              <StatPill key={i} label={s.label} value={s.value} tone={i === 3 ? 'danger' : i === 0 ? 'rose' : i === 1 ? 'amber' : 'violet'} />
            ))}
          </div>
        </div>
      )}

      {/* 5 件事 */}
      {asList(report?.top5_events).length > 0 && (
        <div className="uwr-card">
          <div className="uwr-card-h">本周真正重要的 5 件事</div>
          <div className="uwr-events">
            {asList(report.top5_events).map((e) => (
              <div className="uwr-event" key={e.id}>
                <div className="uwr-event-h">
                  <span className="uwr-event-id">#{e.id}</span>
                  <span className="uwr-event-title">{e.title}</span>
                </div>
                <div className="uwr-event-body">
                  <div><b>事实：</b>{e.fact}</div>
                  <div><b>来源 / 日期：</b><span className="uwr-mono">{e.source_date}</span></div>
                  <div><b>为什么重要：</b>{e.why_matters}</div>
                  <div><b>影响方向：</b>{e.direction}</div>
                  <div><b>是否改变交易计划：</b><span className="uwr-event-change">{e.plan_change}</span></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 评分模型 三段 */}
      {(asList(report?.score_short).length > 0 || asList(report?.score_mid).length > 0 || asList(report?.score_long).length > 0) && (
        <div className="uwr-card">
          <div className="uwr-card-h">泡沫评分模型 · 三时间维度（0-5 分制）</div>
          <div className="uwr-score-3-block">
            {[
              { key: 'short', title: '短期泡沫压力 · 1-4 周', rows: asList(report?.score_short), total: report?.score_short_total, max: report?.score_short_max, conclusion: report?.score_short_conclusion, color: '#fb7185' },
              { key: 'mid', title: '中期泡沫积累 · 3-6 月', rows: asList(report?.score_mid), total: report?.score_mid_total, max: report?.score_mid_max, conclusion: report?.score_mid_conclusion, color: '#f59e0b' },
              { key: 'long', title: '长期结构性泡沫 · 1-3 年', rows: asList(report?.score_long), total: report?.score_long_total, max: report?.score_long_max, conclusion: report?.score_long_conclusion, color: '#a855f7' },
            ].map((seg) => (
              <div key={seg.key} className="uwr-score-block">
                <div className="uwr-score-block-h" style={{ borderTopColor: seg.color }}>
                  <span className="uwr-score-block-title">{seg.title}</span>
                  <span className="uwr-score-block-total" style={{ color: seg.color }}>
                    {seg.total ?? '—'} / {seg.max ?? '—'}
                  </span>
                </div>
                <div className="uwr-table-wrap">
                  <table className="uwr-table">
                    <thead>
                      <tr>
                        <th style={{ width: 180 }}>维度</th>
                        <th style={{ width: 70 }}>得分</th>
                        <th>依据</th>
                      </tr>
                    </thead>
                    <tbody>
                      {seg.rows.map((r, i) => (
                        <tr key={i}>
                          <td><b>{r.dim}</b></td>
                          <td>
                            <span className="uwr-score-tag" style={{ background: seg.color }}>
                              {r.score}/{r.max}
                            </span>
                          </td>
                          <td>{r.basis}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {seg.conclusion && <div className="uwr-score-block-foot">{seg.conclusion}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 持仓 */}
      {asList(report?.positions).length > 0 && (
        <div className="uwr-card">
          <div className="uwr-card-h">我的持仓周度处理</div>
          <div className="uwr-table-wrap">
            <table className="uwr-table">
              <thead>
                <tr>
                  <th>代码</th>
                  <th>当前状态</th>
                  <th>本周风险变化</th>
                  <th>建议动作</th>
                  <th>触发条件</th>
                  <th>失效条件</th>
                  <th>下周重点观察</th>
                </tr>
              </thead>
              <tbody>
                {asList(report.positions).map((p, i) => (
                  <tr key={i}>
                    <td><b className="uwr-mono-em">{p.code}</b></td>
                    <td>{p.status}</td>
                    <td>{p.risk_change}</td>
                    <td><span className="uwr-tag tag-action">{p.action}</span></td>
                    <td>{p.trigger}</td>
                    <td>{p.invalidation}</td>
                    <td>{p.watch}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 三种情景 */}
      {asList(report?.scenarios).length > 0 && (
        <div className="uwr-card">
          <div className="uwr-card-h">下周三种情景计划</div>
          <div className="uwr-scenarios">
            {asList(report.scenarios).map((s, i) => {
              const tone = i === 0 ? 'green' : i === 1 ? 'amber' : 'red'
              return (
                <div className={`uwr-scen uwr-scen-${tone}`} key={i}>
                  <div className="uwr-scen-h">
                    <span>{s.name}</span>
                    {s.probability != null && (
                      <span className="uwr-scen-prob">{(s.probability * 100).toFixed(0)}%</span>
                    )}
                  </div>
                  <div className="uwr-scen-row"><b>触发：</b>{s.trigger}</div>
                  <div className="uwr-scen-row uwr-scen-do"><b>应该做：</b>{s.do}</div>
                  <div className="uwr-scen-row uwr-scen-dont"><b>不能做：</b>{s.dont}</div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 8 条行动 */}
      {asList(report?.actions).length > 0 && (
        <div className="uwr-card">
          <div className="uwr-card-h">下周交易行动清单（最多 8 条）</div>
          <div className="uwr-actions-list">
            {asList(report.actions).map((a) => (
              <div className="uwr-act" key={a.idx}>
                <div className="uwr-act-num">{a.idx}</div>
                <div className="uwr-act-body">
                  <div className="uwr-act-h">
                    <span className="uwr-act-action">{a.action}</span>
                    <span className="uwr-act-target">{a.target}</span>
                  </div>
                  <div className="uwr-act-row"><b>原因：</b>{a.reason}</div>
                  <div className="uwr-act-row"><b>触发：</b>{a.trigger}</div>
                  <div className="uwr-act-row"><b>止损 / 失效：</b>{a.stop}</div>
                  <div className="uwr-act-row"><b>时间周期：</b><span className="uwr-tag tag-period">{a.period}</span></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 转折点 */}
      {asList(report?.watch_points).length > 0 && (
        <div className="uwr-card">
          <div className="uwr-card-h">下周必须盯的转折点</div>
          <div className="uwr-table-wrap">
            <table className="uwr-table">
              <thead>
                <tr>
                  <th style={{ width: 36 }}>#</th>
                  <th style={{ width: 240 }}>转折点</th>
                  <th>具体内容</th>
                  <th style={{ width: 110 }}>关键性</th>
                </tr>
              </thead>
              <tbody>
                {asList(report.watch_points).map((w) => (
                  <tr key={w.idx}>
                    <td>{w.idx}</td>
                    <td><b>{w.point}</b></td>
                    <td>{w.detail}</td>
                    <td><Stars n={w.stars} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 核心总结 */}
      {coreSummaryText && (
        <div className="uwr-card uwr-summary">
          <div className="uwr-card-h">核心总结</div>
          <pre className="uwr-summary-body">{coreSummaryText}</pre>
        </div>
      )}

      {/* 关键反证条件 */}
      {analysis?.key_invalidation && (
        <div className="uwr-disclaimer" style={{ background: '#fff7ed', borderColor: '#fed7aa', color: '#9a3412' }}>
          <b>最关键反证条件：</b>{analysis.key_invalidation}
        </div>
      )}

      {/* 附录原文（有卡片时默认折叠，不当主内容） */}
      {analysis?.markdown && (
        <details className="uwr-card" open={!hasStructuredReport}>
          <summary className="uwr-card-h" style={{ cursor: 'pointer' }}>
            {hasStructuredReport ? '附录：生成原文（可选）' : `${marketLabel}周报原文`}
          </summary>
          <pre
            style={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              padding: '12px 16px 16px',
              margin: 0,
              lineHeight: 1.65,
              fontFamily: 'inherit',
              background: 'transparent',
            }}
          >
            {analysis.markdown}
          </pre>
        </details>
      )}

      {!analysis && (
        <div className="uwr-card">
          <div className="uwr-meta" style={{ padding: '14px 16px' }}>
            暂无{marketLabel}报告。点击上方「生成本周周报」，或等待每周六 10:00 自动调度；也可钉钉发送
            「@{marketLabel}分析师 这周{marketLabel}周报」。
          </div>
        </div>
      )}
        </>
      )}
      </div>
    </AisPageShell>
  )
}

export default UsWeeklyReport
