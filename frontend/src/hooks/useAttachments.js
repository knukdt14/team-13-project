import { useCallback, useEffect, useState } from 'react'
import { deleteDocument, getDocuments, uploadDocuments } from '../api/endpoints'

export default function useAttachments(sessionId) {
  const [items, setItems] = useState([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const refresh = useCallback(() => getDocuments(sessionId).then(setItems), [sessionId])

  useEffect(() => { refresh().catch(() => {}) }, [refresh])

  const upload = useCallback(async (files) => {
    if (!files?.length) return
    setUploading(true); setError(null)
    try {
      const response = await uploadDocuments(sessionId, files)
      setItems((current) => [...current, ...(response.items || [])])
    } catch (caught) { setError(caught.message) }
    finally { setUploading(false) }
  }, [sessionId])

  const remove = useCallback(async (docId) => {
    await deleteDocument(sessionId, docId)
    setItems((current) => current.filter((item) => item.doc_id !== docId))
  }, [sessionId])

  return { items, uploading, error, upload, remove }
}
