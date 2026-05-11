import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login, getMe } from '../api/auth'
import { loginWithM365, getMe as getM365Me } from '../api/m365Auth'
import { useAuthStore } from '../store/auth'

type LoginTab = 'password' | 'm365'

export function Login() {
  const [tab, setTab] = useState<LoginTab>('password')

  // Password login
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // M365 login
  const [m365Email, setM365Email] = useState('')
  const [m365Error, setM365Error] = useState('')
  const [m365Loading, setM365Loading] = useState(false)

  const setUser = useAuthStore((s) => s.setUser)
  const navigate = useNavigate()

  async function handlePasswordSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const tokens = await login(email, password)
      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)
      const me = await getMe()
      setUser(me)
      navigate('/dashboard')
    } catch {
      setError('メールアドレスまたはパスワードが正しくありません')
    } finally {
      setLoading(false)
    }
  }

  async function handleM365Submit(e: React.FormEvent) {
    e.preventDefault()
    setM365Error('')
    setM365Loading(true)
    try {
      const res = await loginWithM365(m365Email)
      localStorage.setItem('access_token', res.access_token)
      localStorage.setItem('refresh_token', res.refresh_token)
      const me = await getM365Me()
      setUser(me)
      navigate('/dashboard')
    } catch {
      setM365Error(
        'Microsoft 365 での認証に失敗しました。\nメールアドレスがこのシステムに登録されているか確認してください。',
      )
    } finally {
      setM365Loading(false)
    }
  }

  return (
    <div className="min-h-screen bg-blue-900 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-sm">
        {/* Brand */}
        <h1 className="text-2xl font-bold text-gray-800 mb-1">CivilPDF DX</h1>
        <p className="text-sm text-gray-500 mb-5">建設業向け図面・書類管理システム</p>

        {/* Tab switcher */}
        <div className="flex rounded-lg overflow-hidden border border-gray-200 mb-5 text-sm">
          <button
            type="button"
            className={`flex-1 py-2 font-medium transition-colors ${
              tab === 'password'
                ? 'bg-blue-700 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
            onClick={() => { setTab('password'); setError(''); setM365Error('') }}
          >
            パスワード
          </button>
          <button
            type="button"
            className={`flex-1 py-2 font-medium transition-colors flex items-center justify-center gap-1.5 ${
              tab === 'm365'
                ? 'bg-blue-700 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
            onClick={() => { setTab('m365'); setError(''); setM365Error('') }}
          >
            <M365Icon active={tab === 'm365'} />
            Microsoft 365
          </button>
        </div>

        {/* Password login form */}
        {tab === 'password' && (
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                メールアドレス
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                パスワード
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            {error && <p className="text-red-600 text-sm">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-700 hover:bg-blue-800 text-white rounded-lg py-2 text-sm font-semibold disabled:opacity-50 transition-colors"
            >
              {loading ? 'ログイン中...' : 'ログイン'}
            </button>
          </form>
        )}

        {/* Microsoft 365 non-interactive login */}
        {tab === 'm365' && (
          <form onSubmit={handleM365Submit} className="space-y-4">
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 text-xs text-blue-700 leading-relaxed">
              <strong>非対話式認証</strong>
              <br />
              メールアドレスを入力するとシステムが Microsoft 365 テナントに対して自動認証します。パスワード入力は不要です。
            </div>
            <div>
              <label htmlFor="m365email" className="block text-sm font-medium text-gray-700 mb-1">
                Microsoft 365 メールアドレス
              </label>
              <input
                id="m365email"
                type="email"
                value={m365Email}
                onChange={(e) => setM365Email(e.target.value)}
                required
                placeholder="user@contoso.onmicrosoft.com"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            {m365Error && (
              <p className="text-red-600 text-xs whitespace-pre-line">{m365Error}</p>
            )}
            <button
              type="submit"
              disabled={m365Loading}
              className="w-full bg-blue-700 hover:bg-blue-800 text-white rounded-lg py-2.5 text-sm font-semibold disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
            >
              {m365Loading ? (
                <>
                  <span className="animate-spin inline-block w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full" />
                  Microsoft 365 で認証中...
                </>
              ) : (
                <>
                  <M365Icon active />
                  Microsoft 365 でログイン
                </>
              )}
            </button>
            <p className="text-xs text-gray-400 text-center">
              ロールはシステム管理者により設定されます
            </p>
          </form>
        )}
      </div>
    </div>
  )
}

function M365Icon({ active }: { active: boolean }) {
  const color = active ? '#ffffff' : '#0078d4'
  return (
    <svg width="14" height="14" viewBox="0 0 23 23" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="1" y="1" width="10" height="10" fill={color} opacity="0.9" />
      <rect x="12" y="1" width="10" height="10" fill={color} opacity="0.7" />
      <rect x="1" y="12" width="10" height="10" fill={color} opacity="0.7" />
      <rect x="12" y="12" width="10" height="10" fill={color} opacity="0.9" />
    </svg>
  )
}
