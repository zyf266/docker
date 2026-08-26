import request from './request'

export const getAShareAiAgentMeta = () => request.get('/a-share-ai-agent/meta')
export const getAShareAiAgentStatus = () => request.get('/a-share-ai-agent/status')
export const startAShareAiAgent = (data) => request.post('/a-share-ai-agent/start', data)
export const stopAShareAiAgent = () => request.post('/a-share-ai-agent/stop')
export const removeAShareAiAgentTask = (data) => request.post('/a-share-ai-agent/remove-task', data)
export const decideAShareAiAgent = (data) =>
  request.post('/a-share-ai-agent/decide', data, { timeout: 120000 })
export const testAShareAiAgentDingtalk = () => request.post('/a-share-ai-agent/test-dingtalk')
export const getAShareAiAgentPrefs = () => request.get('/a-share-ai-agent/prefs')
export const postAShareAiAgentFeedback = (data) => request.post('/a-share-ai-agent/feedback', data)
export const confirmAShareAiAgentPrefs = () => request.post('/a-share-ai-agent/prefs/confirm')
export const getAShareAiAgentTrades = (params) =>
  request.get('/a-share-ai-agent/trades', { params })
export const getAShareAiAgentTradeSymbols = (params) =>
  request.get('/a-share-ai-agent/trades/symbols', { params })
export const backtestAShareAiAgent = (data) =>
  request.post('/a-share-ai-agent/backtest', data, { timeout: 600000 })
export const lookupAShareAiAgent = (q) =>
  request.get('/a-share-ai-agent/lookup', { params: { q }, timeout: 15000 })
