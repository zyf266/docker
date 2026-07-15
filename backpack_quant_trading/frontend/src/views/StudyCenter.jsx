import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, ExternalLink, Clock, Layers, FileQuestion } from 'lucide-react'
import { getQuizAttempts, getQuizChapters, getQuizHub, getApiError } from '../api/quiz'
import './StudyCenter.css'

export default function StudyCenter() {
  const [hub, setHub] = useState(null)
  const [chapters, setChapters] = useState([])
  const [attempts, setAttempts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const [hubData, chapterData] = await Promise.all([getQuizHub(), getQuizChapters()])
        setHub(hubData)
        setChapters(chapterData || [])
      } catch (e) {
        setError(getApiError(e, '加载学习中心失败'))
      }
      try {
        const attemptData = await getQuizAttempts({ limit: 6 })
        setAttempts(attemptData || [])
      } catch {
        setAttempts([])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const totalQuestions = chapters.reduce((s, c) => s + (c.question_count || 0), 0)
  const availableChapters = chapters.filter((c) => !c.coming_soon && c.question_count > 0)

  return (
    <div className="study-center">
      <section className="study-hero">
        <div className="study-hero-text">
          <div className="study-badge"><BookOpen size={16} /> 个人复习</div>
          <h1>{hub?.title || '学习中心'}</h1>
          <p>{hub?.subtitle || '按章节刷题，巩固 AI Agent 核心知识'}</p>
        </div>
        <div className="study-hero-stats">
          <div className="study-stat">
            <span>可用章节</span>
            <strong>{availableChapters.length}</strong>
          </div>
          <div className="study-stat">
            <span>题目总数</span>
            <strong>{totalQuestions}</strong>
          </div>
          <div className="study-stat">
            <span>分类模块</span>
            <strong>{chapters.reduce((s, c) => s + (c.category_count || 0), 0)}</strong>
          </div>
        </div>
      </section>

      {error && <div className="study-alert error">{error}</div>}
      {loading && <div className="study-alert info">正在加载题库...</div>}

      <section className="study-section">
        <div className="study-section-head">
          <h2>章节列表</h2>
          <p>选择章节开始练习，后续会持续导入更多菜鸟教程内容</p>
        </div>
        <div className="study-chapter-grid">
          {chapters.map((ch) => (
            <article
              key={ch.slug}
              className={`study-chapter-card${ch.coming_soon ? ' soon' : ''}`}
              style={{ '--accent': ch.accent }}
            >
              <div className="study-chapter-top">
                <span className="study-chapter-index">Ch.{String(ch.sort_order || 0).padStart(2, '0')}</span>
                {ch.coming_soon ? (
                  <span className="study-soon-badge">即将上线</span>
                ) : (
                  <span className="study-ready-badge">可练习</span>
                )}
              </div>
              <h3>{ch.title}</h3>
              <p>{ch.description}</p>
              <div className="study-chapter-meta">
                <span><Layers size={14} /> {ch.category_count} 分类</span>
                <span><FileQuestion size={14} /> {ch.question_count} 题</span>
              </div>
              <div className="study-chapter-actions">
                {ch.coming_soon ? (
                  <button type="button" className="study-btn disabled" disabled>题库导入中</button>
                ) : (
                  <Link to={`/study-center/${ch.slug}`} className="study-btn primary">开始练习</Link>
                )}
                {ch.source_url && (
                  <a href={ch.source_url} target="_blank" rel="noreferrer" className="study-btn ghost">
                    原文 <ExternalLink size={14} />
                  </a>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>

      {attempts.length > 0 && (
        <section className="study-section">
          <div className="study-section-head">
            <h2><Clock size={18} /> 最近练习</h2>
          </div>
          <div className="study-history-table">
            {attempts.map((a) => (
              <div key={a.id} className="study-history-row">
                <div>
                  <strong>{a.chapter_title || '未知章节'}</strong>
                  <span>{a.category_name || '全部随机'}</span>
                </div>
                <div className="study-history-score">{a.score}/{a.total}</div>
                <div className={`study-history-acc${a.accuracy >= 80 ? ' good' : a.accuracy >= 60 ? ' mid' : ' low'}`}>
                  {a.accuracy}%
                </div>
                <time>{a.finished_at ? new Date(a.finished_at).toLocaleString() : ''}</time>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
