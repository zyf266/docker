import request from './request'

export const getAgentMemoryStats = () => request.get('/agent-memory/stats')

export const queryAgentMemory = ({ kind = 'agent_reports', q, symbol = '', n = 8 } = {}) =>
  request.get('/agent-memory/query', {
    params: { kind, q, symbol: symbol || undefined, n },
    timeout: 60000,
  })
