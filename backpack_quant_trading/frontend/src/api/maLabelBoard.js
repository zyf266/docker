import request from './request'

export const getMaLabelBoard = (symbols) =>
  request.get('/ma-label-board', { params: { symbols }, timeout: 60000 })
