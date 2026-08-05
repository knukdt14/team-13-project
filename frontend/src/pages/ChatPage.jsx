import { useMemo, useState } from 'react'
import ChatWindow from '../components/chat/ChatWindow'
import useAttachments from '../hooks/useAttachments'
import useChatStream from '../hooks/useChatStream'

export default function ChatPage({ conditions, total }) {
  const [sessionId] = useState(() => crypto.randomUUID())
  const [draft, setDraft] = useState('')
  const attachments = useAttachments(sessionId)
  const docIds = useMemo(() => attachments.items.map((item) => item.doc_id), [attachments.items])
  const chat = useChatStream({ sessionId, conditions, docIds })
  const send = (question) => { setDraft(''); chat.send(question) }
  return <ChatWindow total={total} messages={chat.messages} pending={chat.pending} onSend={send} attachments={attachments.items} onFiles={attachments.upload} onRemove={attachments.remove} uploading={attachments.uploading} uploadError={attachments.error} draft={draft} setDraft={setDraft} />
}
