import request from './request'

export const getFavorites = () => request.get('/portal/favorites')
export const addFavorite = (data) => request.post('/portal/favorites', data)
export const removeFavorite = (symbol) => request.delete(`/portal/favorites/${encodeURIComponent(symbol)}`)
export const getWatchlist = (metrics = 0, force = 0) =>
  request.get('/portal/watchlist', {
    params: { metrics: metrics ? 1 : 0, force: force ? 1 : 0 },
    // 无指标：快速；有指标缓存：稍长；强制重拉 K 线：最长
    timeout: metrics ? (force ? 120000 : 60000) : 12000,
  })
export const searchBinanceSymbols = (q, market = 'all') =>
  request.get('/portal/watchlist/binance-symbols', { params: { q, market }, timeout: 20000 })
export const addWatchSymbol = (data) => request.post('/portal/watchlist', data, { timeout: 15000 })
export const removeWatchSymbol = (symbol) =>
  request.delete(`/portal/watchlist/${encodeURIComponent(symbol)}`)
export const saveWatchConfig = (data) => request.post('/portal/watchlist/config', data)
export const getExchangeBindings = () => request.get('/portal/exchange/bindings')
export const getExchangeBalances = () =>
  request.get('/portal/exchange/balances', { timeout: 25000 })
export const connectExchange = (data) =>
  request.post('/portal/exchange/connect', data, { timeout: 45000 })
export const disconnectExchange = (platform) =>
  request.delete(`/portal/exchange/bindings/${encodeURIComponent(platform)}`, { timeout: 30000 })
export const getTvWebhookHint = () => request.get('/portal/tv-webhook/hint')
export const getPortalTrades = (params = {}) =>
  request.get('/portal/trades', { params, timeout: 20000 })
export const getEquityCurve = (params = {}) =>
  request.get('/portal/equity-curve', { params, timeout: 25000 })
/** 新增账面账户（市场+本金），并复制对应市场历史成交 */
export const createBookAccount = (data) =>
  request.post('/portal/book-capital', data, { timeout: 90000 })
/** @deprecated 使用 createBookAccount */
export const scaleBookCapital = createBookAccount
export const searchPortal = (q) => request.get('/portal/search', { params: { q } })
export const getInbox = () => request.get('/portal/inbox')
export const testInbox = (data) => request.post('/portal/inbox/test', data)
export const readInbox = (id) => request.post(`/portal/inbox/${id}/read`)
export const stubEmail = (data) => request.post('/portal/email/stub', data)
export const submitContact = (data) => request.post('/portal/contact', data)
export const getEquityOverlay = (ids) =>
  request.get('/portal/equity-overlay', { params: { ids: (ids || []).join(',') } })
