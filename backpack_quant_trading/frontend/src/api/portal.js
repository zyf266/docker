import request from './request'

export const getFavorites = () => request.get('/portal/favorites')
export const addFavorite = (data) => request.post('/portal/favorites', data)
export const removeFavorite = (symbol) => request.delete(`/portal/favorites/${encodeURIComponent(symbol)}`)
export const getWatchlist = (metrics = 0, force = 0) =>
  request.get('/portal/watchlist', {
    params: { metrics: metrics ? 1 : 0, force: force ? 1 : 0 },
    // force 才可能真拉 K 线；缓存命中应很快，仍给足超时兜底
    timeout: metrics ? (force ? 120000 : 45000) : 15000,
  })
export const searchBinanceSymbols = (q, market = 'all') =>
  request.get('/portal/watchlist/binance-symbols', { params: { q, market }, timeout: 20000 })
export const addWatchSymbol = (data) => request.post('/portal/watchlist', data, { timeout: 15000 })
export const removeWatchSymbol = (symbol) =>
  request.delete(`/portal/watchlist/${encodeURIComponent(symbol)}`)
export const saveWatchConfig = (data) => request.post('/portal/watchlist/config', data)
export const getExchangeBindings = () => request.get('/portal/exchange/bindings')
export const getExchangeBalances = () =>
  request.get('/portal/exchange/balances', { timeout: 45000 })
export const connectExchange = (data) =>
  request.post('/portal/exchange/connect', data, { timeout: 45000 })
export const disconnectExchange = (platform) =>
  request.delete(`/portal/exchange/bindings/${encodeURIComponent(platform)}`, { timeout: 30000 })
export const getTvWebhookHint = () => request.get('/portal/tv-webhook/hint')
export const getPortalTrades = (params = {}) =>
  request.get('/portal/trades', { params, timeout: 30000 })
export const getEquityCurve = (params = {}) =>
  request.get('/portal/equity-curve', { params, timeout: 45000 })
export const searchPortal = (q) => request.get('/portal/search', { params: { q } })
export const getInbox = () => request.get('/portal/inbox')
export const testInbox = (data) => request.post('/portal/inbox/test', data)
export const readInbox = (id) => request.post(`/portal/inbox/${id}/read`)
export const stubEmail = (data) => request.post('/portal/email/stub', data)
export const submitContact = (data) => request.post('/portal/contact', data)
export const getEquityOverlay = (ids) =>
  request.get('/portal/equity-overlay', { params: { ids: (ids || []).join(',') } })
