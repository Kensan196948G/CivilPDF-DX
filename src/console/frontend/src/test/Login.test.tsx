// @vitest-environment jsdom
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { Login } from '../pages/Login'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('../api/auth', () => ({
  login: vi.fn(),
  getMe: vi.fn(),
}))

import { login, getMe } from '../api/auth'

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('renders login form', () => {
    render(<Login />, { wrapper: MemoryRouter })
    expect(screen.getByLabelText('メールアドレス')).toBeInTheDocument()
    expect(screen.getByLabelText('パスワード')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'ログイン' })).toBeInTheDocument()
  })

  it('shows error on failed login', async () => {
    vi.mocked(login).mockRejectedValueOnce(new Error('Unauthorized'))
    const user = userEvent.setup()

    render(<Login />, { wrapper: MemoryRouter })
    await user.type(screen.getByLabelText('メールアドレス'), 'bad@example.com')
    await user.type(screen.getByLabelText('パスワード'), 'wrongpass')
    await user.click(screen.getByRole('button', { name: 'ログイン' }))

    await waitFor(() => {
      expect(screen.getByText('メールアドレスまたはパスワードが正しくありません')).toBeInTheDocument()
    })
  })

  it('navigates to dashboard on successful login', async () => {
    vi.mocked(login).mockResolvedValueOnce({
      access_token: 'access123',
      refresh_token: 'refresh123',
      token_type: 'bearer',
    })
    vi.mocked(getMe).mockResolvedValueOnce({
      id: '1',
      email: 'admin@example.com',
      username: 'admin',
      full_name: 'Admin User',
      role: 'admin',
      status: 'active',
      created_at: '2026-01-01T00:00:00Z',
      last_login: null,
    })
    const user = userEvent.setup()

    render(<Login />, { wrapper: MemoryRouter })
    await user.type(screen.getByLabelText('メールアドレス'), 'admin@example.com')
    await user.type(screen.getByLabelText('パスワード'), 'password')
    await user.click(screen.getByRole('button', { name: 'ログイン' }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
    })
  })

  it('disables button while loading', async () => {
    vi.mocked(login).mockImplementation(() => new Promise(() => {}))
    const user = userEvent.setup()

    render(<Login />, { wrapper: MemoryRouter })
    await user.type(screen.getByLabelText('メールアドレス'), 'admin@example.com')
    await user.type(screen.getByLabelText('パスワード'), 'password')
    await user.click(screen.getByRole('button', { name: 'ログイン' }))

    expect(screen.getByRole('button', { name: 'ログイン中...' })).toBeDisabled()
  })
})
