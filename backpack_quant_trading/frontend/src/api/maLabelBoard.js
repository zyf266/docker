import request from './request'

export const getMaLabelBoard = (symbols) =>
  request.get('/ma-label-board', { params: { symbols }, timeout: 60000 })

export const getMaLabelWebhookHint = () =>
  request.get('/ma-label-board/tv-webhook/hint')

export const addMaLabelSymbol = (symbol) =>
  request.post('/ma-label-board/symbols', { symbol })

export const removeMaLabelSymbol = (symbol) =>
  request.delete(`/ma-label-board/symbols/${encodeURIComponent(symbol)}`)
