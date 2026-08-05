import { useEffect, useRef, useState } from 'react'
import { getProvinces } from '../api/endpoints'

const KEY = import.meta.env.VITE_KAKAO_MAP_KEY
const KOREA = { lat: 36.4, lng: 127.9, level: 13 }
const FILL = '#7157E8'
const FILL_HOVER = '#4F37C6'
const EMPTY_FILL = '#B9B2C4'
let sdkPromise

function loadSdk() {
  if (sdkPromise) return sdkPromise
  sdkPromise = new Promise((resolve, reject) => {
    if (window.kakao?.maps) return resolve(window.kakao)
    const script = document.createElement('script')
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${KEY}&autoload=false`
    script.onload = () => window.kakao.maps.load(() => resolve(window.kakao))
    script.onerror = () => reject(new Error('카카오맵을 불러오지 못했어요. 키와 도메인 등록을 확인해주세요.'))
    document.head.appendChild(script)
  })
  return sdkPromise
}

function frame(rings) {
  let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180
  for (const ring of rings) for (const [lng, lat] of ring) {
    minLat = Math.min(minLat, lat); maxLat = Math.max(maxLat, lat)
    minLng = Math.min(minLng, lng); maxLng = Math.max(maxLng, lng)
  }
  const span = Math.max(maxLat - minLat, maxLng - minLng)
  return { lat: (minLat + maxLat) / 2, lng: (minLng + maxLng) / 2, level: span > 3 ? 11 : span > 1.5 ? 10 : span > 0.7 ? 9 : 8 }
}

export default function useKakaoMap({ summary, selectedCode, onSelect }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const kakaoRef = useRef(null)
  const shapesRef = useRef([])
  const homeRef = useRef(null)
  const selectRef = useRef(onSelect)
  const summaryRef = useRef(summary)
  const [hovered, setHovered] = useState(null)
  const [error, setError] = useState(null)
  selectRef.current = onSelect
  summaryRef.current = summary

  useEffect(() => {
    if (!KEY) return
    let cancelled = false
    Promise.all([loadSdk(), getProvinces()]).then(([kakao, geo]) => {
      if (cancelled || !containerRef.current) return
      kakaoRef.current = kakao
      const map = new kakao.maps.Map(containerRef.current, { center: new kakao.maps.LatLng(KOREA.lat, KOREA.lng), level: KOREA.level })
      mapRef.current = map
      homeRef.current = { center: map.getCenter(), level: map.getLevel() }
      for (const feature of geo.features) {
        const { code, name } = feature.properties
        const rings = feature.geometry.coordinates.map((polygon) => polygon[0])
        for (const ring of rings) {
          const polygon = new kakao.maps.Polygon({ path: ring.map(([lng, lat]) => new kakao.maps.LatLng(lat, lng)), strokeWeight: 1, strokeColor: '#fff', strokeOpacity: 0.9, fillColor: FILL, fillOpacity: 0.2 })
          polygon.setMap(map)
          kakao.maps.event.addListener(polygon, 'mouseover', () => setHovered((current) => current?.code === code ? current : { code, name }))
          kakao.maps.event.addListener(polygon, 'mouseout', () => setHovered((current) => current?.code === code ? null : current))
          kakao.maps.event.addListener(polygon, 'click', () => {
            const view = frame(rings)
            map.setLevel(view.level, { anchor: new kakao.maps.LatLng(view.lat, view.lng), animate: { duration: 450 } })
            const count = summaryRef.current?.regions.find((item) => item.code === code)?.count ?? 0
            selectRef.current({ code, name, count })
          })
          shapesRef.current.push({ code, polygon, rings })
        }
      }
    }).catch((caught) => setError(caught.message))
    return () => { cancelled = true; shapesRef.current.forEach(({ polygon }) => polygon.setMap(null)); shapesRef.current = [] }
  }, [])

  useEffect(() => {
    if (!summary) return
    const counts = Object.fromEntries(summary.regions.map((region) => [region.code, region.count]))
    shapesRef.current.forEach(({ code, polygon }) => {
      const count = counts[code] || 0
      polygon.setOptions(count === 0
        ? { fillColor: EMPTY_FILL, fillOpacity: 0.35 }
        : { fillColor: FILL, fillOpacity: 0.2 + (summary.max ? count / summary.max : 0) * 0.6 })
    })
  }, [summary])

  useEffect(() => {
    const counts = Object.fromEntries((summary?.regions || []).map((item) => [item.code, item.count]))
    shapesRef.current.forEach(({ code, polygon }) => {
      const lit = code === hovered?.code || code === selectedCode
      const empty = summary && (counts[code] || 0) === 0
      polygon.setOptions({ fillColor: lit ? FILL_HOVER : empty ? EMPTY_FILL : FILL, strokeWeight: lit ? 3 : 1 })
    })
  }, [hovered, selectedCode, summary])

  const reset = () => {
    const map = mapRef.current, home = homeRef.current
    if (!map || !home) return
    map.setLevel(home.level)
    map.panTo(home.center)
  }
  return { containerRef, hovered, error, reset, hasKey: Boolean(KEY) }
}
