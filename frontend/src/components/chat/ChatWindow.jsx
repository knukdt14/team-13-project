import { useCallback, useEffect, useRef } from 'react'
import AnswerBlock from './AnswerBlock'
import Composer from './Composer'
import AttachmentChip from './AttachmentChip'
import ThinkingDots from './ThinkingDots'
import UserBubble from './UserBubble'

const EXAMPLES = ['나한테 맞는 일자리 정책 뭐 있어?', '월세 지원받을 수 있는 거 알려줘', '창업 준비 중인데 받을 수 있는 지원 있어?', '자격증 응시료 지원해주는 데 있어?']
const NEAR_BOTTOM_PX = 80

export default function ChatWindow({ total, messages, pending, onSend, onNewConversation, attachments, onFiles, onRemove, uploading, uploadError, draft, setDraft }) {
  const logRef = useRef(null)
  const stickRef = useRef(true)
  const raf = useRef(0)
  const follow = useCallback((behavior) => {
    if (!stickRef.current) return
    cancelAnimationFrame(raf.current)
    raf.current = requestAnimationFrame(() => {
      const log = logRef.current
      if (log) log.scrollTo({ top: log.scrollHeight, behavior })
    })
  }, [])

  useEffect(() => { follow('smooth') }, [messages.length, follow])

  const streamingText = messages.at(-1)?.streaming ? messages.at(-1)?.text : null
  useEffect(() => {
    if (streamingText) follow('auto')
  }, [streamingText, follow])

  useEffect(() => () => cancelAnimationFrame(raf.current), [])

  const handleScroll = () => {
    const log = logRef.current
    if (!log) return
    stickRef.current = log.scrollHeight - log.scrollTop - log.clientHeight < NEAR_BOTTOM_PX
  }

  const handleSend = (question) => {
    stickRef.current = true
    onSend(question)
  }

  const handleNewConversation = () => {
    stickRef.current = true
    onNewConversation()
  }

  const revealSources = useCallback((sources) => {
    stickRef.current = true
    cancelAnimationFrame(raf.current)
    const startedAt = performance.now()

    const trackExpansion = (now) => {
      const log = logRef.current
      if (!log || !sources) return
      const logBottom = log.getBoundingClientRect().bottom
      const sourcesBottom = sources.getBoundingClientRect().bottom
      const hiddenHeight = sourcesBottom - logBottom + 12
      if (hiddenHeight > 0) log.scrollTop += hiddenHeight
      if (now - startedAt < 320) raf.current = requestAnimationFrame(trackExpansion)
    }

    raf.current = requestAnimationFrame(trackExpansion)
  }, [])

  return <div className="chat" onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); onFiles(event.dataTransfer.files) }}>
    <div className="chat-toolbar">
      <button type="button" className="new-chat-button" onClick={handleNewConversation} disabled={pending || uploading}>새 대화</button>
    </div>
    <div className="chat-log" ref={logRef} onScroll={handleScroll}>
      {messages.length === 0 && <div className="intro"><p className="intro-badge"><span aria-hidden="true">✦</span> 정책 상담</p><h2>내 조건에 맞는 정책만 골라서 알려드려요</h2><p>왼쪽에 나이나 지역을 넣으면 그 조건에 해당하는 정책만 보고 답해요. 비워두면 전체 {total?.toLocaleString() || ''}건에서 찾고요. 공고문 PDF나 포스터 사진을 붙이면 그것부터 읽어요.</p><ul className="examples">{EXAMPLES.map((question) => <li key={question}><button onClick={() => handleSend(question)} disabled={pending}><span>{question}</span><span aria-hidden="true">→</span></button></li>)}</ul></div>}
      {messages.map((message, index) => message.role === 'user' ? <UserBubble key={index}>{message.text}</UserBubble> : message.role === 'error' ? <p key={index} className="alert">{message.text}</p> : message.streaming && !message.text ? null : <AnswerBlock key={index} message={message} onSourcesOpen={revealSources} />)}
      {pending && messages.at(-1)?.text === '' && <ThinkingDots />}
    </div>
    {(attachments.length > 0 || uploading || uploadError) && <div className="attachments">{attachments.map((item) => <AttachmentChip key={item.doc_id} item={item} onRemove={() => onRemove(item.doc_id)} />)}{uploading && <span className="chip-file is-busy"><span className="dots" aria-hidden="true"><i /><i /><i /></span>읽는 중이에요</span>}{uploadError && <span className="chip-file is-error">{uploadError}</span>}</div>}
    <Composer draft={draft} setDraft={setDraft} onSubmit={handleSend} onFiles={onFiles} disabled={pending} uploading={uploading} />
  </div>
}
