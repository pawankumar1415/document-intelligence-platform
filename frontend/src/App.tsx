import { Navigate, Route, Routes } from "react-router-dom";

import AIControlDrawer from "./components/AIControlDrawer";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import { AppStateProvider } from "./context/AppStateContext";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import OutputsPage from "./pages/OutputsPage";
import "./App.css";

function App() {
  return (
    <AppStateProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="*"
          element={
            <ProtectedRoute>
              <div className="app-shell">
                <Navbar />
                <AIControlDrawer />
                <main className="main-content">
                  <Routes>
                    <Route path="/dashboard" element={<DashboardPage />} />
                    <Route path="/outputs" element={<OutputsPage />} />
                    {/* Legacy redirects */}
                    <Route path="/upload" element={<Navigate to="/dashboard" replace />} />
                    <Route path="/generate" element={<Navigate to="/dashboard" replace />} />
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </main>
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </AppStateProvider>
  );
}

export default App;