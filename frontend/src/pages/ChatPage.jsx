import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import ChatWindow from '../components/chat/ChatWindow'
import useAttachments from '../hooks/useAttachments'
import useChatStream from '../hooks/useChatStream'

const SESSION_KEY = 'youth-policy-session'

function createSessionId() {
  const fresh = crypto.randomUUID()
  localStorage.setItem(SESSION_KEY, fresh)
  return fresh
}

export default function ChatPage({ conditions, total }) {
  const [sessionId, setSessionId] = useState(() => localStorage.getItem(SESSION_KEY) || createSessionId())
  const [draft, setDraft] = useState('')
  const attachments = useAttachments(sessionId)
  const docIds = useMemo(() => attachments.items.map((item) => item.doc_id), [attachments.items])
  const chat = useChatStream({ sessionId, conditions, docIds })
  const send = (question) => { setDraft(''); chat.send(question) }

  // 히어로 입력창에서 넘어온 질문을 그대로 보낸다.
  // 이력을 다 불러온 뒤여야 한다. useChatStream.send 는 loadingHistory 중이면
  // 아무것도 하지 않고 돌아간다.
  const [params, setParams] = useSearchParams()
  const askedRef = useRef(false)
  useEffect(() => {
    const question = params.get('q')
    if (!question || askedRef.current || chat.loadingHistory) return
    askedRef.current = true
    // 주소에서 지운다. 새로고침할 때마다 다시 보내면 안 된다.
    setParams({}, { replace: true })
    send(question)
  }, [params, chat.loadingHistory])  // eslint-disable-line react-hooks/exhaustive-deps
  const startNewConversation = () => {
    localStorage.removeItem(SESSION_KEY)
    setDraft('')
    setSessionId(createSessionId())
  }
  return <ChatWindow total={total} messages={chat.messages} pending={chat.pending || chat.loadingHistory} onSend={send} onNewConversation={startNewConversation} attachments={attachments.items} onFiles={attachments.upload} onRemove={attachments.remove} uploading={attachments.uploading} uploadError={attachments.error} draft={draft} setDraft={setDraft} />
}
