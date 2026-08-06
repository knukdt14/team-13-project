import { useId, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import PolicyCardList from '../policy/PolicyCardList'

export default function AnswerBlock({ message, onSourcesOpen }) {
  const [open, setOpen] = useState(false)
  const [atStart, setAtStart] = useState(true)
  const [atEnd, setAtEnd] = useState(false)
  const listId = useId()
  const sourcesRef = useRef(null)
  const carouselRef = useRef(null)
  const policies = (message.sources || []).map((source) => source.policy).filter(Boolean)
  const sourcesTitle = message.relevant === false
    ? '딱 맞는 정책은 없지만, 조건에 맞는 다른 정책이에요'
    : '이 정책들을 보고 답했어요'

  const updateSlider = () => {
    const carousel = carouselRef.current
    if (!carousel) return
    setAtStart(carousel.scrollLeft <= 2)
    setAtEnd(carousel.scrollLeft + carousel.clientWidth >= carousel.scrollWidth - 2)
  }

  const toggleSources = () => {
    const nextOpen = !open
    setOpen(nextOpen)
    if (nextOpen) {
      requestAnimationFrame(updateSlider)
      onSourcesOpen?.(sourcesRef.current)
    }
  }

  const slidePolicies = (direction) => {
    const carousel = carouselRef.current
    if (!carousel) return
    carousel.scrollBy({ left: direction * carousel.clientWidth * 0.82, behavior: 'smooth' })
  }

  return <div className="answer">
    {message.used_attachments && <p className="answer-tag">첨부한 문서를 읽고 답했어요</p>}
    <div className="answer-text">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown>
    </div>
    {message.elapsed_ms != null && <div className="answer-meta">조건에 맞는 정책 {message.matched?.toLocaleString() || 0}건 · 전체 {message.total?.toLocaleString() || 0}건 · {(message.elapsed_ms / 1000).toFixed(1)}초</div>}
    {policies.length > 0 && <div className="sources" ref={sourcesRef}>
      <button
        type="button"
        className="sources-toggle"
        aria-expanded={open}
        aria-controls={listId}
        onClick={toggleSources}
      >
        <span>{sourcesTitle} · {policies.length}개</span>
        <span className="sources-chevron" aria-hidden="true">⌄</span>
      </button>
      <div id={listId} className={`sources-body${open ? ' is-open' : ''}`} aria-hidden={!open} inert={open ? undefined : ''}>
        <div>
          <div className="sources-slider">
            <button type="button" className="source-slide is-prev" onClick={() => slidePolicies(-1)} aria-label="이전 정책 보기" disabled={atStart}>‹</button>
            <div className="sources-carousel" ref={carouselRef} onScroll={updateSlider}>
              <PolicyCardList policies={policies} />
            </div>
            <button type="button" className="source-slide is-next" onClick={() => slidePolicies(1)} aria-label="다음 정책 보기" disabled={atEnd || policies.length <= 1}>›</button>
          </div>
        </div>
      </div>
    </div>}
  </div>
}
