import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// VITE_MOCK=1 (npm run dev:mock): answer every request from the in-memory
// mock store instead of the network. Lazy import keeps mock data out of
// non-mock bundles (the env check is statically eliminated at build time).
// DEV-only: production builds can never activate the mock (the /auth/token
// mock accepts any credentials, so shipping it would amount to auth bypass).
if (import.meta.env.DEV && import.meta.env.VITE_MOCK === '1') {
  api.defaults.adapter = async (config) => {
    const { mockAdapter } = await import('../mock/mockAdapter')
    return mockAdapter(config)
  }
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// /login に居るときに再度 /login へ代入するとページ全体がリロードされ、
// 入力中のフォームが消える (401 が続くと無限リロードループになる) — 必ずガードする。
function redirectToLogin() {
  if (window.location.pathname !== '/login') window.location.href = '/login'
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const url: string = error.config?.url ?? ''
    // ログイン/リフレッシュ等の認証エンドポイント自身の 401 は呼び出し元
    // (ログインフォーム) がエラー表示を担う。ここでリダイレクトしない。
    const isAuthCall =
      url.includes('/auth/token') ||
      url.includes('/auth/refresh') ||
      url.includes('/auth/m365')
    if (error.response?.status === 401 && !isAuthCall) {
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const res = await axios.post('/api/v1/auth/refresh', { refresh_token: refresh })
          localStorage.setItem('access_token', res.data.access_token)
          error.config.headers.Authorization = `Bearer ${res.data.access_token}`
          return api.request(error.config)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          redirectToLogin()
        }
      } else {
        // 失効 token を破棄してからリダイレクト (残すと再マウント→401→リロードが循環する)
        localStorage.removeItem('access_token')
        redirectToLogin()
      }
    }
    return Promise.reject(error)
  }
)
