import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAppState } from "../context/AppStateContext";


const ProtectedRoute = ({ children }: { children: ReactNode }) => {
  const { token } = useAppState();
  const location = useLocation();

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return children;
};

export default ProtectedRoute;
