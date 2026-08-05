export default function AttachmentChip({ item, onRemove }) {
  const failed = item.chars === 0
  return <span className={`chip-file${failed ? ' is-warn' : ''}`} title={item.note || item.preview}>
    <span className="chip-kind">{item.kind === 'pdf' ? 'PDF' : 'IMG'}</span>{item.filename}
    <em>{failed ? '내용 없음' : item.kind === 'pdf' ? `${item.pages}쪽 · ${item.chars.toLocaleString()}자` : `${item.chars.toLocaleString()}자 인식`}</em>
    <button type="button" onClick={onRemove} aria-label={`${item.filename} 첨부 해제`}>✕</button>
  </span>
}
