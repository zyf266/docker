import axios from 'axios'
import request from './request'

const longRequest = (config) =>
  axios({ baseURL: '/api', timeout: 180000, withCredentials: true, ...config }).then((r) => r.data)

export const getSymbols = () => request.get('/currency-monitor/symbols')
export const getSpotSymbols = (params) => request.get('/currency-monitor/spot-symbols', { params })
export const getStatus = () => request.get('/currency-monitor/status')
export const startMonitor = (data) => request.post('/currency-monitor/start', data)
export const stopMonitor = () => request.post('/currency-monitor/stop')
export const removePair = (data) => request.post('/currency-monitor/remove-pair', data)

// 合约分钟预警（波动/量能/订单簿墙）
export const getMinuteAlertStatus = () => request.get('/currency-monitor/minute-alert/status')
export const startMinuteAlert = (data) => request.post('/currency-monitor/minute-alert/start', data)
export const stopMinuteAlert = () => request.post('/currency-monitor/minute-alert/stop')

// 现货分钟预警
export const getSpotMinuteAlertStatus = () => request.get('/currency-monitor/spot-minute-alert/status')
export const startSpotMinuteAlert = (data) => request.post('/currency-monitor/spot-minute-alert/start', data)
export const stopSpotMinuteAlert = () => request.post('/currency-monitor/spot-minute-alert/stop')
export const probeSpotMinuteAlert = (params) =>
  request.get('/currency-monitor/spot-minute-alert/probe', { params })
export const testSpotMinuteDingtalk = (params) =>
  request.post('/currency-monitor/spot-minute-alert/test-dingtalk', null, { params })

// 现货 24h 资金净流入
export const getSpotNetInflowStatus = () => request.get('/currency-monitor/spot-net-inflow/status')
export const startSpotNetInflow = (data) => request.post('/currency-monitor/spot-net-inflow/start', data)
export const stopSpotNetInflow = () => request.post('/currency-monitor/spot-net-inflow/stop')
export const getSpotNetInflowSeries = (params) =>
  request.get('/currency-monitor/spot-net-inflow/series', { params })

// 链上活跃度监控
export const getChainActivityChains = () => request.get('/currency-monitor/chain-activity/chains')
export const getChainActivityStatus = () => request.get('/currency-monitor/chain-activity/status')
export const startChainActivity = (data) => request.post('/currency-monitor/chain-activity/start', data)
export const stopChainActivity = () => request.post('/currency-monitor/chain-activity/stop')
export const probeChainActivity = (params) =>
  request.get('/currency-monitor/chain-activity/probe', { params, timeout: 60000 })
export const checkChainActivityNow = () =>
  longRequest({
    method: 'post',
    url: '/currency-monitor/chain-activity/check-now',
    headers: (() => {
      const token = localStorage.getItem('token')
      return token ? { Authorization: `Bearer ${token}` } : {}
    })(),
  })
export const getChainRpcInfo = () => request.get('/currency-monitor/chain-activity/rpc-info')
export const testChainActivityDingtalk = () =>
  request.post('/currency-monitor/chain-activity/test-dingtalk')

// A股标的监控
export const getASharePool = (params) =>
  request.get('/currency-monitor/a-share-monitor/pool', { params, timeout: 120000 })
export const getAShareMonitorMeta = () => request.get('/currency-monitor/a-share-monitor/meta')
export const getAShareMonitorStatus = () => request.get('/currency-monitor/a-share-monitor/status')
export const startAShareMonitor = (data) => request.post('/currency-monitor/a-share-monitor/start', data)
export const stopAShareMonitor = () => request.post('/currency-monitor/a-share-monitor/stop')
export const getAShareMonitorSignals = (params) =>
  request.get('/currency-monitor/a-share-monitor/signals', { params })
export const testAShareMonitorDingtalk = () =>
  request.post('/currency-monitor/a-share-monitor/test-dingtalk')
