import { Navigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";

// VITE_SKIP_AUTH=true disables the login guard until auth backend is implemented
const SKIP_AUTH = import.meta.env.VITE_SKIP_AUTH === "true";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!SKIP_AUTH && !isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
