import request from './request'

export const login = (data) => request.post('/auth/login', data)
export const register = (data) => request.post('/auth/register', data)
export const getMe = () => request.get('/auth/me')
export const logout = () => request.post('/auth/logout')
export const forgotSendCode = (data) => request.post('/auth/forgot-password/send-code', data)
export const forgotResetPassword = (data) => request.post('/auth/forgot-password/reset', data)
