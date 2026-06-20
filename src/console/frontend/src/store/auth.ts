import { create } from "zustand";
import type { UserResponse } from "../api/auth";

interface AuthState {
  user: UserResponse | null;
  isAuthenticated: boolean;
  setUser: (user: UserResponse | null) => void;
  logout: () => void;
}

function getInitialAuthState(): boolean {
  // Auth backend is not yet implemented; treat every visitor as authenticated.
  // When email/password auth is wired up, replace this with:
  //   try { return !!localStorage.getItem('access_token') } catch { return false }
  return true;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: getInitialAuthState(),
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  logout: () => {
    localStorage.clear();
    set({ user: null, isAuthenticated: false });
  },
}));
