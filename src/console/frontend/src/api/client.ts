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

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const res = await axios.post('/api/v1/auth/refresh', { refresh_token: refresh })
          localStorage.setItem('access_token', res.data.access_token)
          error.config.headers.Authorization = `Bearer ${res.data.access_token}`
          return api.request(error.config)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      } else {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)
