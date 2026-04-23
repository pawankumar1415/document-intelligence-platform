import { Navigate } from "react-router-dom";
import { useAppState } from "../context/AppStateContext";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, user } = useAppState();
  if (!token || !user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}