import { useEffect, useRef } from 'react'
import AnswerBlock from './AnswerBlock'
import Composer from './Composer'
import AttachmentChip from './AttachmentChip'
import ThinkingDots from './ThinkingDots'
import UserBubble from './UserBubble'

const EXAMPLES = ['나한테 맞는 일자리 정책 뭐 있어?', '월세 지원받을 수 있는 거 알려줘', '창업 준비 중인데 받을 수 있는 지원 있어?', '자격증 응시료 지원해주는 데 있어?']

export default function ChatWindow({ total, messages, pending, onSend, attachments, onFiles, onRemove, uploading, uploadError, draft, setDraft }) {
  const endRef = useRef(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, pending, attachments])
  return <div className="chat" onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); onFiles(event.dataTransfer.files) }}>
    <div className="chat-log">
      {messages.length === 0 && <div className="intro"><p className="intro-badge"><span aria-hidden="true">✦</span> 정책 상담</p><h2>내 조건에 맞는 정책만 골라서 알려드려요</h2><p>왼쪽에 나이나 지역을 넣으면 그 조건에 해당하는 정책만 보고 답해요. 비워두면 전체 {total?.toLocaleString() || ''}건에서 찾고요. 공고문 PDF나 포스터 사진을 붙이면 그것부터 읽어요.</p><ul className="examples">{EXAMPLES.map((question) => <li key={question}><button onClick={() => onSend(question)}><span>{question}</span><span aria-hidden="true">→</span></button></li>)}</ul></div>}
      {messages.map((message, index) => message.role === 'user' ? <UserBubble key={index}>{message.text}</UserBubble> : message.role === 'error' ? <p key={index} className="alert">{message.text}</p> : message.streaming && !message.text ? null : <AnswerBlock key={index} message={message} />)}
      {pending && messages.at(-1)?.text === '' && <ThinkingDots />}
      <div ref={endRef} />
    </div>
    {(attachments.length > 0 || uploading || uploadError) && <div className="attachments">{attachments.map((item) => <AttachmentChip key={item.doc_id} item={item} onRemove={() => onRemove(item.doc_id)} />)}{uploading && <span className="chip-file is-busy"><span className="dots" aria-hidden="true"><i /><i /><i /></span>읽는 중이에요</span>}{uploadError && <span className="chip-file is-error">{uploadError}</span>}</div>}
    <Composer draft={draft} setDraft={setDraft} onSubmit={onSend} onFiles={onFiles} disabled={pending} uploading={uploading} />
  </div>
}
