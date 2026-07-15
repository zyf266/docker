import request from './request'

export const getQuizHub = () => request.get('/quiz/hub')

export const getQuizChapters = () => request.get('/quiz/chapters')

export const getQuizChapter = (slug) => request.get(`/quiz/chapters/${slug}`)

export const getChapterCategories = (slug) => request.get(`/quiz/chapters/${slug}/categories`)

export const startQuizExam = (data) => request.post('/quiz/start', data)

export const submitQuizExam = (data) => request.post('/quiz/submit', data)

export const checkQuizAnswer = (data) => request.post('/quiz/check-answer', data)

export const getQuizAttempts = (params) => request.get('/quiz/attempts', { params })

export function getApiError(err, fallback = '操作失败') {
  if (!err) return fallback
  if (typeof err === 'string') return err
  return err.detail || err.response?.data?.detail || err.message || fallback
}
