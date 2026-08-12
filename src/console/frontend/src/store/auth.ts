import { create } from "zustand";
import type { UserResponse } from "../api/auth";

interface AuthState {
  user: UserResponse | null;
  isAuthenticated: boolean;
  setUser: (user: UserResponse | null) => void;
  clearAuth: () => void;
  logout: () => void;
}

function getInitialAuthState(): boolean {
  // DEV builds skip the login screen so the console is usable without
  // credentials during development (the real flow lives in pages/Login.tsx).
  // Production builds MUST NOT auto-authenticate (Issue #59): gate on a real
  // access token so the dev bypass never leaks into a deployed bundle.
  if (import.meta.env.DEV) {
    return true;
  }
  try {
    return !!localStorage.getItem("access_token");
  } catch {
    return false;
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: getInitialAuthState(),
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  clearAuth: () => {
    // 401 失効時は認証トークンだけを破棄する（アプリの他キーは保持）。
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    set({ user: null, isAuthenticated: false });
  },
  logout: () => {
    localStorage.clear();
    set({ user: null, isAuthenticated: false });
  },
}));
