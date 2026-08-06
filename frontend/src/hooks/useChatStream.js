import { useCallback, useEffect, useRef, useState } from 'react'
import { ask, getMessages, streamUrl } from '../api/endpoints'
import { USE_MOCK } from '../api/client'

export default function useChatStream({ sessionId, conditions, docIds }) {
  const [messages, setMessages] = useState([])
  const [pending, setPending] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const sourceRef = useRef(null)

  useEffect(() => {
    let active = true
    sourceRef.current?.close()
    sourceRef.current = null
    setPending(false)
    setLoadingHistory(true)
    setMessages([])

    getMessages(sessionId)
      .then((rows) => {
        if (!active) return
        const restored = (Array.isArray(rows) ? rows : []).map((row) => ({
          role: row.role,
          text: row.content,
          sources: row.sources,
        }))
        setMessages(restored)
      })
      .catch(() => {
        if (active) setMessages([])
      })
      .finally(() => {
        if (active) setLoadingHistory(false)
      })

    return () => {
      active = false
      sourceRef.current?.close()
      sourceRef.current = null
    }
  }, [sessionId])

  const send = useCallback(async (question) => {
    const text = question.trim()
    if (!text || pending || loadingHistory) return
    setMessages((current) => [...current, { role: 'user', text }, { role: 'assistant', text: '', sources: [], streaming: true }])
    setPending(true)
    const profile = {
      age: conditions.age ? Number(conditions.age) : null,
      region: conditions.region || null,
      employment: conditions.employment || null,
      education: conditions.education || null,
    }

    if (USE_MOCK) {
      try {
        const response = await ask({ question: text, session_id: sessionId, profile, doc_ids: docIds })
        setMessages((current) => [...current.slice(0, -1), { role: 'assistant', text: response.answer, ...response }])
      } catch (caught) {
        setMessages((current) => [...current.slice(0, -1), { role: 'error', text: caught.message }])
      } finally { setPending(false) }
      return
    }

    const source = new EventSource(streamUrl({
      question: text, session_id: sessionId, ...profile,
      doc_ids: docIds, include_closed: conditions.include_closed,
      include_nationwide: conditions.include_nationwide,
    }))
    sourceRef.current = source
    source.addEventListener('token', (event) => {
      const { token } = JSON.parse(event.data)
      setMessages((current) => {
        const next = [...current]
        next[next.length - 1] = { ...next[next.length - 1], text: next[next.length - 1].text + token }
        return next
      })
    })
    source.addEventListener('done', (event) => {
      const payload = JSON.parse(event.data || '{}')
      setMessages((current) => {
        const next = [...current]
        next[next.length - 1] = { ...next[next.length - 1], ...payload, streaming: false }
        return next
      })
      source.close(); sourceRef.current = null; setPending(false)
    })
    source.onerror = () => {
      source.close(); sourceRef.current = null; setPending(false)
      setMessages((current) => [...current.slice(0, -1), { role: 'error', text: '답변을 이어받지 못했어요. 잠시 뒤 다시 시도해주세요.' }])
    }
  }, [conditions, docIds, loadingHistory, pending, sessionId])

  return { messages, pending, loadingHistory, send }
}
