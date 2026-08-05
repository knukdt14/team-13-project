import { useRef } from 'react'

const ACCEPT = '.pdf,.png,.jpg,.jpeg,.webp,.bmp'
export default function Composer({ draft, setDraft, onSubmit, onFiles, disabled, uploading }) {
  const fileRef = useRef(null)
  return <form className="composer" onSubmit={(event) => { event.preventDefault(); onSubmit(draft) }}>
    <input ref={fileRef} type="file" accept={ACCEPT} multiple hidden onChange={(event) => { onFiles(event.target.files); event.target.value = '' }} />
    <button type="button" className="attach-button" onClick={() => fileRef.current?.click()} disabled={uploading} title="공고문 PDF 또는 포스터 사진 첨부" aria-label="파일 첨부">＋</button>
    <input className="input composer-input" value={draft} placeholder="무엇이든 물어보세요" onChange={(event) => setDraft(event.target.value)} disabled={disabled} />
    <button className="button" type="submit" disabled={disabled || !draft.trim()}>보내기</button>
  </form>
}
