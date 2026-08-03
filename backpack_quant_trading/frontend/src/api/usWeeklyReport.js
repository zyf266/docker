import request from './request'

// 这个接口聚合 20+ 个外部免费源，首次冷启动较慢；这里用更长的超时（默认 axios 30s 会被切断）。
export const getUsWeeklySnapshot = (forceRefresh = false, market = 'us') =>
  request.get('/us-weekly-report/snapshot', {
    timeout: 120000,
    params: {
      market,
      ...(forceRefresh ? { force_refresh: true } : {}),
    },
  })

// 历史泡沫分析（用于首页曲线 & 详情页）；market: us | a_share
export const getBubbleHistory = (limit = 80, market = 'us', opts = {}) =>
  request.get('/us-weekly-report/history', {
    params: {
      limit,
      market,
      ...(opts.strategy ? { strategy: opts.strategy } : {}),
      ...(opts.symbol ? { symbol: opts.symbol } : {}),
    },
  })

// 最新一份 DeepSeek 分析
export const getLatestBubbleAnalysis = (market = 'us', opts = {}) =>
  request.get('/us-weekly-report/latest', {
    params: {
      market,
      ...(opts.strategy ? { strategy: opts.strategy } : {}),
      ...(opts.symbol ? { symbol: opts.symbol } : {}),
    },
  })

// 按 ID（generated_at_utc）取某一周完整报告
export const getBubbleReportById = (id, market = 'us') =>
  request.get('/us-weekly-report/report', { params: { id, market } })

// A股/个股策略模板列表（策略A / B…）
export const getBubbleStrategies = (market = 'a_share', mode = 'stock') =>
  request.get('/us-weekly-report/strategies', { params: { market, mode } })

// 手动触发一次分析（调用 DeepSeek，可能 30~90 秒）
export const triggerBubbleAnalyze = (payload = {}) =>
  request.post('/us-weekly-report/analyze', payload, { timeout: 300000 })
