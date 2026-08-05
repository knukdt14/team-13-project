import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // strictPort 를 켜지 않는다. 5173 이 막힌 PC 에서는 서버가 아예 안 뜬다.
    // 대신 카카오 개발자 콘솔에 5173~5175 를 모두 등록해 두었다.
    // 어느 포트로 밀려도 지도가 뜬다.
    proxy: { '/api': 'http://localhost:8000' },
  },
})
