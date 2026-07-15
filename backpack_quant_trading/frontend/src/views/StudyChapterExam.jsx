import React, { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft, CheckCircle2, XCircle, ChevronLeft, ChevronRight,
  Eye, ListChecks, AlertCircle,
} from 'lucide-react'
import {
  getChapterCategories,
  getQuizAttempts,
  getQuizChapter,
  startQuizExam,
  submitQuizExam,
  checkQuizAnswer,
  getApiError,
} from '../api/quiz'
import './StudyCenter.css'

const LIMIT_OPTIONS = [5, 10, 15, 20, 30]

export default function StudyChapterExam() {
  const { slug } = useParams()
  const [chapter, setChapter] = useState(null)
  const [categories, setCategories] = useState([])
  const [attempts, setAttempts] = useState([])
  const [categoryId, setCategoryId] = useState('')
  const [limit, setLimit] = useState(10)
  const [loading, setLoading] = useState(true)
  const [phase, setPhase] = useState('setup')
  const [attemptId, setAttemptId] = useState(null)
  const [questions, setQuestions] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answers, setAnswers] = useState({})
  const [revealed, setRevealed] = useState({}) // questionId -> check-answer 结果
  const [checking, setChecking] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [resultView, setResultView] = useState('summary') // summary | review | list
  const [reviewIndex, setReviewIndex] = useState(0)
  const [reviewFilter, setReviewFilter] = useState('all') // all | wrong

  const currentQuestion = questions[currentIndex]
  const answeredCount = useMemo(() => Object.keys(answers).length, [answers])

  const maxQuestions = useMemo(() => {
    if (!chapter) return 0
    if (categoryId) {
      const cat = categories.find((c) => String(c.id) === categoryId)
      return cat?.question_count || 0
    }
    return chapter.question_count || 0
  }, [chapter, categoryId, categories])

  useEffect(() => {
    if (!slug) return
    setLoading(true)
    setError('')
    Promise.all([
      getQuizChapter(slug),
      getChapterCategories(slug),
      getQuizAttempts({ limit: 5 }),
    ])
      .then(([ch, cats, hist]) => {
        setChapter(ch)
        setCategories(cats || [])
        setAttempts((hist || []).filter((a) => a.chapter_title === ch.title))
        const max = ch.question_count || 10
        setLimit(Math.min(10, max))
      })
      .catch((e) => setError(getApiError(e, '加载章节失败')))
      .finally(() => setLoading(false))
  }, [slug])

  useEffect(() => {
    if (!maxQuestions) return
    if (limit === 0) return
    const valid = LIMIT_OPTIONS.filter((n) => n <= maxQuestions)
    if (!valid.includes(limit)) {
      setLimit(valid.length ? valid[valid.length - 1] : 0)
    }
  }, [maxQuestions, limit])

  const handleStart = async () => {
    if (!chapter) return
    setLoading(true)
    setError('')
    try {
      const res = await startQuizExam({
        chapter_id: chapter.id,
        category_id: categoryId ? Number(categoryId) : null,
        limit,
      })
      setAttemptId(res.attempt_id)
      setQuestions(res.questions || [])
      setCurrentIndex(0)
      setAnswers({})
      setRevealed({})
      setResult(null)
      setPhase('exam')
    } catch (e) {
      setError(getApiError(e, '开始考试失败'))
    } finally {
      setLoading(false)
    }
  }

  const currentFeedback = currentQuestion ? revealed[currentQuestion.id] : null

  const handleSelect = async (questionId, optionKey) => {
    if (revealed[questionId] || checking) return
    setAnswers((prev) => ({ ...prev, [questionId]: optionKey }))
    setChecking(true)
    setError('')
    try {
      const feedback = await checkQuizAnswer({
        question_id: questionId,
        selected_option_key: optionKey,
      })
      setRevealed((prev) => ({ ...prev, [questionId]: feedback }))
    } catch (e) {
      setError(getApiError(e, '获取解析失败'))
      setAnswers((prev) => {
        const next = { ...prev }
        delete next[questionId]
        return next
      })
    } finally {
      setChecking(false)
    }
  }

  const handleSubmit = async (force = false) => {
    const unanswered = questions.length - answeredCount
    if (!force && unanswered > 0) {
      const ok = window.confirm(`还有 ${unanswered} 题未作答，确定交卷吗？未作答将计为错误。`)
      if (!ok) return
    }
    setLoading(true)
    setError('')
    try {
      const res = await submitQuizExam({
        attempt_id: attemptId,
        answers: questions.map((q) => ({
          question_id: q.id,
          selected_option_key: answers[q.id] || '',
        })),
      })
      setResult(res)
      setResultView('summary')
      setReviewIndex(0)
      setPhase('result')
      const hist = await getQuizAttempts({ chapter_id: chapter.id, limit: 5 })
      setAttempts(hist || [])
    } catch (e) {
      setError(getApiError(e, '提交失败'))
    } finally {
      setLoading(false)
    }
  }

  const filteredReviews = useMemo(() => {
    if (!result?.reviews) return []
    if (reviewFilter === 'wrong') return result.reviews.filter((r) => !r.is_correct)
    return result.reviews
  }, [result, reviewFilter])

  const currentReview = filteredReviews[reviewIndex]

  const resetExam = () => {
    setPhase('setup')
    setAttemptId(null)
    setQuestions([])
    setAnswers({})
    setRevealed({})
    setResult(null)
    setResultView('summary')
    setReviewIndex(0)
    setCurrentIndex(0)
    setError('')
  }

  if (loading && !chapter) {
    return <div className="study-center"><div className="study-alert info">加载中...</div></div>
  }

  if (!chapter) {
    return (
      <div className="study-center">
        <div className="study-alert error">{error || '章节不存在'}</div>
        <Link to="/study-center" className="study-back-link"><ArrowLeft size={16} /> 返回学习中心</Link>
      </div>
    )
  }

  return (
    <div className="study-center study-exam-page" style={{ '--accent': chapter.accent }}>
      <Link to="/study-center" className="study-back-link"><ArrowLeft size={16} /> 返回章节列表</Link>

      <section className="study-chapter-header">
        <div>
          <span className="study-badge">章节练习</span>
          <h1>{chapter.title}</h1>
          <p>{chapter.description}</p>
        </div>
        <div className="study-chapter-header-stats">
          <span>{categories.length} 个分类</span>
          <span>{chapter.question_count} 道题</span>
        </div>
      </section>

      {error && <div className="study-alert error">{error}</div>}

      {phase === 'setup' && (
        <section className="study-panel">
          <h2>考试设置</h2>
          <div className="study-form-row">
            <label>
              练习范围
              <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
                <option value="">本章全部随机</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}（{c.question_count} 题）</option>
                ))}
              </select>
            </label>
            <label>
              抽题数量
              <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
                {LIMIT_OPTIONS.filter((n) => n <= maxQuestions).map((n) => (
                  <option key={n} value={n}>{n} 题</option>
                ))}
                {maxQuestions > 0 && (
                  <option value={0}>全部（{maxQuestions} 题）</option>
                )}
              </select>
            </label>
          </div>

          {categories.length > 0 && (
            <div className="study-category-chips">
              {categories.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className={`study-chip${String(c.id) === categoryId ? ' active' : ''}`}
                  onClick={() => setCategoryId(String(c.id) === categoryId ? '' : String(c.id))}
                >
                  {c.name} · {c.question_count}
                </button>
              ))}
            </div>
          )}

          <button type="button" className="study-btn primary large" onClick={handleStart} disabled={loading}>
            {loading ? '准备试卷...' : '开始考试'}
          </button>

          {attempts.length > 0 && (
            <div className="study-mini-history">
              <h3>本章最近成绩</h3>
              {attempts.map((a) => (
                <div key={a.id} className="study-mini-history-row">
                  <span>{a.category_name || '全部'}</span>
                  <strong>{a.score}/{a.total}</strong>
                  <em>{a.accuracy}%</em>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {phase === 'exam' && currentQuestion && (
        <section className="study-panel exam-active">
          <div className="study-exam-progress">
            <div className="study-exam-progress-text">
              <span>第 {currentIndex + 1} / {questions.length} 题</span>
              <span>已答 {answeredCount} 题</span>
            </div>
            <div className="study-progress-track">
              <div style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }} />
            </div>
            <div className="study-question-dots">
              {questions.map((q, idx) => {
                const fb = revealed[q.id]
                let dotCls = 'study-dot'
                if (idx === currentIndex) dotCls += ' current'
                if (fb) dotCls += fb.is_correct ? ' correct' : ' wrong'
                else if (answers[q.id]) dotCls += ' done'
                return (
                  <button
                    key={q.id}
                    type="button"
                    className={dotCls}
                    onClick={() => setCurrentIndex(idx)}
                    title={`第 ${idx + 1} 题`}
                  />
                )
              })}
            </div>
          </div>

          {currentFeedback && (
            <div className={`study-answer-status${currentFeedback.is_correct ? ' ok' : ' bad'}`}>
              {currentFeedback.is_correct ? (
                <><CheckCircle2 size={18} /> 回答正确</>
              ) : (
                <><XCircle size={18} /> 回答错误，正确答案：{currentFeedback.correct_key}</>
              )}
            </div>
          )}

          <div className="study-question-box">
            <div className="study-question-tags">
              <span className="study-tag">{currentQuestion.category_name}</span>
              <span className="study-tag muted">{currentQuestion.question_type === 'true_false' ? '判断题' : '单选题'}</span>
            </div>
            <h2>{currentQuestion.question_text}</h2>
            {!currentFeedback && !checking && (
              <p className="study-practice-hint">点击选项后立即显示正确答案与解析</p>
            )}
            <div className={`study-options${currentFeedback ? ' readonly' : ''}`}>
              {currentQuestion.options.map((opt) => {
                const selected = answers[currentQuestion.id] === opt.key
                const isCorrect = currentFeedback && opt.key === currentFeedback.correct_key
                const isWrong = currentFeedback && selected && !currentFeedback.is_correct
                let cls = 'study-option'
                if (currentFeedback) {
                  if (isCorrect) cls += ' answer-correct'
                  else if (isWrong) cls += ' answer-wrong'
                } else if (selected) {
                  cls += ' selected'
                }
                return (
                  <button
                    key={opt.key}
                    type="button"
                    className={cls}
                    disabled={!!currentFeedback || checking}
                    onClick={() => handleSelect(currentQuestion.id, opt.key)}
                  >
                    <span className="study-option-key">{opt.key}</span>
                    <span>{opt.text}</span>
                    {isCorrect && currentFeedback && (
                      <span className="study-option-badge correct">正确答案</span>
                    )}
                    {isWrong && (
                      <span className="study-option-badge wrong">你的选择</span>
                    )}
                  </button>
                )
              })}
            </div>

            {currentFeedback?.explanation && (
              <div className="study-review-exp block instant">
                <strong>解析：</strong>{currentFeedback.explanation}
              </div>
            )}

            {checking && (
              <div className="study-alert info" style={{ marginTop: 12 }}>正在加载解析...</div>
            )}
          </div>

          <div className="study-exam-nav">
            <button type="button" className="study-btn ghost" disabled={currentIndex === 0} onClick={() => setCurrentIndex((i) => i - 1)}>
              <ChevronLeft size={16} /> 上一题
            </button>
            {currentIndex < questions.length - 1 ? (
              <button
                type="button"
                className="study-btn primary"
                onClick={() => setCurrentIndex((i) => i + 1)}
                disabled={!currentFeedback}
                title={!currentFeedback ? '请先选择答案查看解析' : ''}
              >
                下一题 <ChevronRight size={16} />
              </button>
            ) : (
              <button
                type="button"
                className="study-btn primary"
                onClick={() => handleSubmit(false)}
                disabled={loading || !currentFeedback}
              >
                {loading ? '提交中...' : '交卷查看成绩'}
              </button>
            )}
          </div>
        </section>
      )}

      {phase === 'result' && result && (
        <section className="study-panel">
          <div className="study-result-tabs">
            <button
              type="button"
              className={`study-tab${resultView === 'summary' ? ' active' : ''}`}
              onClick={() => setResultView('summary')}
            >
              成绩摘要
            </button>
            <button
              type="button"
              className={`study-tab${resultView === 'review' ? ' active' : ''}`}
              onClick={() => { setResultView('review'); setReviewIndex(0) }}
            >
              <Eye size={15} /> 逐题看答案
            </button>
            <button
              type="button"
              className={`study-tab${resultView === 'list' ? ' active' : ''}`}
              onClick={() => setResultView('list')}
            >
              <ListChecks size={15} /> 全部解析
            </button>
          </div>

          {resultView === 'summary' && (
            <div className="study-result-card">
              <div className={`study-result-ring${result.accuracy >= 80 ? ' good' : result.accuracy >= 60 ? ' mid' : ' low'}`}>
                <strong>{result.accuracy}%</strong>
                <span>{result.score} / {result.total}</span>
              </div>
              <h2>{result.accuracy >= 80 ? '掌握不错！' : result.accuracy >= 60 ? '继续加油' : '建议再复习一遍'}</h2>
              <p className="study-result-hint">
                正确 {result.score} 题 · 错误 {result.total - result.score} 题
              </p>
              <div className="study-result-actions">
                <button type="button" className="study-btn primary" onClick={() => { setResultView('review'); setReviewIndex(0) }}>
                  <Eye size={16} /> 查看答案
                </button>
                <button type="button" className="study-btn ghost" onClick={resetExam}>再练一次</button>
                <Link to="/study-center" className="study-btn ghost">返回学习中心</Link>
              </div>
            </div>
          )}

          {resultView === 'review' && filteredReviews.length === 0 && (
            <div className="study-alert info">没有符合条件的题目</div>
          )}

          {resultView === 'review' && currentReview && (
            <div className="study-answer-review">
              <div className="study-review-toolbar">
                <div className="study-review-filters">
                  <button type="button" className={`study-chip${reviewFilter === 'all' ? ' active' : ''}`} onClick={() => { setReviewFilter('all'); setReviewIndex(0) }}>
                    全部 {result.reviews.length}
                  </button>
                  <button type="button" className={`study-chip${reviewFilter === 'wrong' ? ' active' : ''}`} onClick={() => { setReviewFilter('wrong'); setReviewIndex(0) }}>
                    错题 {result.reviews.filter((r) => !r.is_correct).length}
                  </button>
                </div>
                <span className="study-review-counter">
                  第 {reviewIndex + 1} / {filteredReviews.length} 题
                </span>
              </div>

              <div className="study-question-dots review-dots">
                {filteredReviews.map((r, idx) => (
                  <button
                    key={r.id}
                    type="button"
                    className={`study-dot${idx === reviewIndex ? ' current' : ''}${r.is_correct ? ' correct' : ' wrong'}`}
                    onClick={() => setReviewIndex(idx)}
                    title={`第 ${idx + 1} 题`}
                  />
                ))}
              </div>

              <div className={`study-answer-status${currentReview.is_correct ? ' ok' : ' bad'}`}>
                {currentReview.skipped ? (
                  <><AlertCircle size={18} /> 未作答</>
                ) : currentReview.is_correct ? (
                  <><CheckCircle2 size={18} /> 回答正确</>
                ) : (
                  <><XCircle size={18} /> 回答错误</>
                )}
              </div>

              <div className="study-question-box">
                <div className="study-question-tags">
                  <span className="study-tag">{currentReview.category_name}</span>
                  <span className="study-tag muted">{currentReview.question_type === 'true_false' ? '判断题' : '单选题'}</span>
                </div>
                <h2>{currentReview.question_text}</h2>
                <div className="study-options readonly">
                  {currentReview.options.map((opt) => {
                    const isCorrect = opt.key === currentReview.correct_key
                    const isSelected = opt.key === currentReview.selected_key
                    let cls = 'study-option'
                    if (isCorrect) cls += ' answer-correct'
                    else if (isSelected && !isCorrect) cls += ' answer-wrong'
                    else if (isSelected) cls += ' selected'
                    return (
                      <div key={opt.key} className={cls}>
                        <span className="study-option-key">{opt.key}</span>
                        <span>{opt.text}</span>
                        {isCorrect && <span className="study-option-badge correct">正确答案</span>}
                        {isSelected && !isCorrect && <span className="study-option-badge wrong">你的选择</span>}
                      </div>
                    )
                  })}
                </div>
              </div>

              {currentReview.explanation && (
                <div className="study-review-exp block">{currentReview.explanation}</div>
              )}

              <div className="study-answer-summary-row">
                {!currentReview.skipped && (
                  <p>你的答案：<strong>{currentReview.selected_key}</strong> {currentReview.selected_text && `（${currentReview.selected_text}）`}</p>
                )}
                <p>正确答案：<strong>{currentReview.correct_key}</strong> {currentReview.correct_text && `（${currentReview.correct_text}）`}</p>
              </div>

              <div className="study-exam-nav">
                <button type="button" className="study-btn ghost" disabled={reviewIndex === 0} onClick={() => setReviewIndex((i) => i - 1)}>
                  <ChevronLeft size={16} /> 上一题
                </button>
                {reviewIndex < filteredReviews.length - 1 ? (
                  <button type="button" className="study-btn primary" onClick={() => setReviewIndex((i) => i + 1)}>
                    下一题 <ChevronRight size={16} />
                  </button>
                ) : (
                  <button type="button" className="study-btn primary" onClick={() => setResultView('list')}>
                    查看全部解析
                  </button>
                )}
              </div>
            </div>
          )}

          {resultView === 'list' && (
            <div className="study-review-block">
              <h3>全部题目解析（{result.reviews.length} 题）</h3>
              {result.reviews.map((item, idx) => (
                <article key={item.id} className={`study-review-item${item.is_correct ? ' ok' : ' bad'}`}>
                  <div className="study-review-title">
                    <span>第 {idx + 1} 题</span>
                    <span className="study-tag">{item.category_name}</span>
                    {item.skipped && <span className="study-tag muted">未作答</span>}
                    {item.is_correct ? <CheckCircle2 size={18} className="icon-ok" /> : <XCircle size={18} className="icon-bad" />}
                  </div>
                  <p className="study-review-q">{item.question_text}</p>
                  <div className="study-options readonly compact">
                    {item.options.map((opt) => {
                      const isCorrect = opt.key === item.correct_key
                      const isSelected = opt.key === item.selected_key
                      let cls = 'study-option'
                      if (isCorrect) cls += ' answer-correct'
                      else if (isSelected) cls += ' answer-wrong'
                      return (
                        <div key={opt.key} className={cls}>
                          <span className="study-option-key">{opt.key}</span>
                          <span>{opt.text}</span>
                        </div>
                      )
                    })}
                  </div>
                  {!item.skipped && (
                    <p>你的答案：<strong>{item.selected_key}</strong> {item.selected_text && `（${item.selected_text}）`}</p>
                  )}
                  <p>正确答案：<strong>{item.correct_key}</strong> {item.correct_text && `（${item.correct_text}）`}</p>
                  {item.explanation && <div className="study-review-exp">{item.explanation}</div>}
                  <button type="button" className="study-link-btn" onClick={() => {
                    setReviewFilter('all')
                    setReviewIndex(idx)
                    setResultView('review')
                  }}>
                    在逐题模式中查看
                  </button>
                </article>
              ))}
              <div className="study-result-actions" style={{ marginTop: 20 }}>
                <button type="button" className="study-btn primary" onClick={resetExam}>再练一次</button>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  )
}
