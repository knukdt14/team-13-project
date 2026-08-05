export default function HoverLabel({ region }) {
  return <p className={`map-hover${region ? ' is-on' : ''}`} aria-live="polite">{region?.name || ''}</p>
}
