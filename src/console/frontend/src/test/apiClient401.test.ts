// @vitest-environment jsdom
import { describe, it, expect, beforeEach } from 'vitest'
import type { AxiosAdapter } from 'axios'
import { api } from '../api/client'

// jsdom は location.href 代入によるナビゲーション未実装のため、書換え可能なスタブへ差し替える
function stubLocation(pathname: string) {
  const loc = { pathname, href: `https://example.com${pathname}` }
  Object.defineProperty(window, 'location', {
    value: loc,
    writable: true,
    configurable: true,
  })
  return loc
}

// 指定 URL への全リクエストを 401 で失敗させるアダプタ
function reject401(url: string) {
  api.defaults.adapter = (async (config) =>
    Promise.reject({
      response: { status: 401 },
      config: { ...config, url },
    })) as AxiosAdapter
}

describe('api client 401 interceptor', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('ログインエンドポイント自身の 401 ではリダイレクトしない (フォームが消えない)', async () => {
    const loc = stubLocation('/login')
    reject401('/auth/token')
    await expect(api.post('/auth/token')).rejects.toBeTruthy()
    expect(loc.href).toBe('https://example.com/login')
  })

  it('/login 上で失効 token の 401 が来たら token を破棄しリロードしない (無限ループ防止)', async () => {
    const loc = stubLocation('/login')
    localStorage.setItem('access_token', 'stale')
    reject401('/auth/me')
    await expect(api.get('/auth/me')).rejects.toBeTruthy()
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(loc.href).toBe('https://example.com/login')
  })

  it('他ページでの 401 (refresh なし) は token 破棄のうえ /login へ遷移する', async () => {
    const loc = stubLocation('/dashboard')
    localStorage.setItem('access_token', 'stale')
    reject401('/documents')
    await expect(api.get('/documents')).rejects.toBeTruthy()
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(loc.href).toBe('/login')
  })
})
