import { useMemo, useState } from 'react'
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
  const startNewConversation = () => {
    localStorage.removeItem(SESSION_KEY)
    setDraft('')
    setSessionId(createSessionId())
  }
  return <ChatWindow total={total} messages={chat.messages} pending={chat.pending || chat.loadingHistory} onSend={send} onNewConversation={startNewConversation} attachments={attachments.items} onFiles={attachments.upload} onRemove={attachments.remove} uploading={attachments.uploading} uploadError={attachments.error} draft={draft} setDraft={setDraft} />
}
